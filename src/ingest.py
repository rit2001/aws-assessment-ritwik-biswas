"""Build all local artifacts from immutable source files."""

from __future__ import annotations

from dataclasses import asdict

from .cleaning import clean_sales_csv
from .config import get_settings
from .documents.loader import load_documents, write_index
from .sales.sqlite_service import create_sales_database


def ingest() -> dict[str, object]:
    settings = get_settings()
    if not settings.sales_csv.exists():
        raise FileNotFoundError(f"Supplied sales data not found: {settings.sales_csv}")
    documents = load_documents(settings.documents_dir)
    if not documents:
        raise FileNotFoundError(f"No supported policy documents found: {settings.documents_dir}")

    cleaned, report = clean_sales_csv(settings.sales_csv)
    create_sales_database(cleaned, settings.sqlite_path)
    write_index(documents, settings.document_index_path)
    report.write(settings.artifacts_dir / "cleaning_report.json")
    return {**asdict(report), "documents_discovered": len(set(c.source for c in documents)), "document_chunks": len(documents)}


def main() -> None:
    result = ingest()
    print("Ingestion complete")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
