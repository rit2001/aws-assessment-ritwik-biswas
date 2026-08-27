"""Small deterministic BM25 retriever with no model or credential requirement."""

from __future__ import annotations

import math
import re
from collections import Counter

from .loader import DocumentChunk


TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {"a", "an", "and", "are", "be", "do", "for", "how", "i", "in", "is", "it", "of", "on", "the", "to", "what", "with"}


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    normalized = []
    for token in tokens:
        if token in STOP_WORDS:
            continue
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 4 and token.endswith("s"):
            token = token[:-1]
        normalized.append(token)
    return normalized


class BM25Retriever:
    def __init__(self, chunks: list[DocumentChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(self._search_text(chunk))) for chunk in chunks]
        self.lengths = [sum(counts.values()) for counts in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1.0
        self.document_frequency = Counter()
        for counts in self.term_frequencies:
            self.document_frequency.update(counts.keys())

    @staticmethod
    def _search_text(chunk: DocumentChunk) -> str:
        return " ".join(filter(None, [chunk.source, chunk.title, chunk.section, chunk.text]))

    def search(self, query: str, limit: int = 3) -> list[tuple[DocumentChunk, float]]:
        if not self.chunks:
            return []
        query_terms = Counter(tokenize(query))
        scored: list[tuple[DocumentChunk, float]] = []
        total = len(self.chunks)
        for chunk, frequencies, length in zip(self.chunks, self.term_frequencies, self.lengths):
            score = 0.0
            for term, query_count in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self.document_frequency[term]
                inverse_frequency = math.log(1 + (total - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += query_count * inverse_frequency * frequency * (self.k1 + 1) / denominator
            # A query naming a policy domain (for example, warranty or returns)
            # should prefer that source over incidental cross-references elsewhere.
            source_terms = set(tokenize(chunk.source.rsplit(".", 1)[0]))
            score += 3.0 * len(source_terms.intersection(query_terms))
            if score > 0:
                scored.append((chunk, score))
        return sorted(scored, key=lambda item: (-item[1], item[0].source))[:limit]
