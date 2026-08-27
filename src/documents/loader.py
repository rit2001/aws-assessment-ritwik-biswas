"""Load mixed support documents into normalized, attributable chunks."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".json", ".txt", ".csv"}


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    source: str
    title: str | None = None
    section: str | None = None
    page: int | None = None

    @property
    def citation(self) -> str:
        if self.section and self.page:
            detail = f"{self.section}, page {self.page}"
        else:
            detail = self.section or (f"page {self.page}" if self.page else None)
        return f"Source: {self.source}" + (f" — {detail}" if detail else "")


def _paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]


def _load_pdf(path: Path) -> list[DocumentChunk]:
    title = None
    chunks: list[DocumentChunk] = []
    reader = PdfReader(path)
    if reader.metadata:
        title = reader.metadata.title

    page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    first_lines = [text.splitlines()[0].strip() for text in page_texts if text]
    repeated_headers = {line for line, count in Counter(first_lines).items() if count > 1}

    for page_number, raw_text in enumerate(page_texts, 1):
        lines = raw_text.splitlines()
        if lines and lines[0].strip() in repeated_headers:
            lines.pop(0)
        lines = [line for line in lines if not re.fullmatch(r".*\bPage\s+\d+", line.strip())]
        text = "\n".join(lines).strip()
        if not text:
            continue
        # Policy PDFs contain numbered headings. Smaller sections sharply reduce the
        # influence of repeated headers, definitions, and legal boilerplate.
        matches = list(re.finditer(r"(?m)^(\d+(?:\.\d+)*\.?)\s+([^\n]+)$", text))
        if not matches:
            if chunks and chunks[-1].section:
                previous = chunks[-1]
                chunks[-1] = DocumentChunk(
                    f"{previous.text}\n{text}", previous.source, previous.title,
                    previous.section, previous.page,
                )
            else:
                chunks.append(DocumentChunk(text, path.name, title=title, page=page_number))
            continue
        prefix = text[:matches[0].start()].strip()
        if prefix:
            if chunks and chunks[-1].section:
                previous = chunks[-1]
                chunks[-1] = DocumentChunk(
                    f"{previous.text}\n{prefix}", previous.source, previous.title,
                    previous.section, previous.page,
                )
            else:
                chunks.append(DocumentChunk(prefix, path.name, title=title, page=page_number))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = f"{match.group(1)} {match.group(2).strip()}"
            section_text = text[match.end():end].strip()
            if section_text:
                chunks.append(DocumentChunk(
                    section_text, path.name, title=title, section=section, page=page_number
                ))
    return chunks


def _load_json(path: Path) -> list[DocumentChunk]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    title = payload.get("title") if isinstance(payload, dict) else None
    chunks: list[DocumentChunk] = []
    if isinstance(payload, dict) and isinstance(payload.get("sections"), list):
        for section in payload["sections"]:
            if isinstance(section, dict) and section.get("text"):
                chunks.append(DocumentChunk(
                    str(section["text"]).strip(), path.name, title,
                    str(section.get("heading")) if section.get("heading") else None,
                ))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        chunks.append(DocumentChunk(text, path.name, title))
    return chunks


def _load_txt(path: Path) -> list[DocumentChunk]:
    paragraphs = _paragraphs(path.read_text(encoding="utf-8"))
    title = paragraphs[0].splitlines()[0] if paragraphs else path.stem
    body = paragraphs[1:] if len(paragraphs) > 1 else paragraphs
    return [DocumentChunk(text, path.name, title=title) for text in body]


def _load_csv(path: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            section = row.get("topic") or row.get("heading") or row.get("title")
            text_fields = [
                f"{key}: {value.strip()}" for key, value in row.items()
                if value and key not in {"topic", "heading", "title"}
            ]
            text = " ".join(text_fields) or str(section or "").strip()
            if text:
                chunks.append(DocumentChunk(text, path.name, title=path.stem, section=section))
    return chunks


def load_document(path: Path) -> list[DocumentChunk]:
    loaders = {".pdf": _load_pdf, ".json": _load_json, ".txt": _load_txt, ".csv": _load_csv}
    if path.suffix.lower() not in loaders:
        return []
    return loaders[path.suffix.lower()](path)


def discover_documents(directory: Path, excluded_names: Iterable[str] = ("sales.csv",)) -> list[Path]:
    excluded = set(excluded_names)
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.name not in excluded and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def load_documents(directory: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in discover_documents(directory):
        chunks.extend(load_document(path))
    return chunks


def write_index(chunks: list[DocumentChunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(chunk) for chunk in chunks], indent=2) + "\n", encoding="utf-8")


def read_index(path: Path) -> list[DocumentChunk]:
    return [DocumentChunk(**item) for item in json.loads(path.read_text(encoding="utf-8"))]
