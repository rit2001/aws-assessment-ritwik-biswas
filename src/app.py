"""NorthStar command-line assistant."""

from __future__ import annotations

import argparse

from .config import get_settings
from .documents.generator import ExtractivePolicyGenerator
from .documents.loader import read_index
from .documents.retriever import BM25Retriever
from .router import Route, route_question
from .sales.sqlite_service import SQLiteSalesService


AMBIGUOUS_RESPONSE = (
    "I cannot safely determine whether this is a sales-analysis or policy question. "
    "Please mention the sales metric (for example, revenue by region) or the policy topic."
)


def answer_question(question: str) -> str:
    settings = get_settings()
    if settings.app_mode != "local":
        raise NotImplementedError("The CLI default supports APP_MODE=local; AWS adapters are deployment seams.")
    route = route_question(question)
    if route == Route.SALES:
        return SQLiteSalesService(settings.sqlite_path).answer(question)
    if route == Route.DOCUMENTS:
        if not settings.document_index_path.exists():
            raise FileNotFoundError("Document index is missing; run `python -m src.ingest` first.")
        chunks = read_index(settings.document_index_path)
        return ExtractivePolicyGenerator(BM25Retriever(chunks)).answer(question)
    return AMBIGUOUS_RESPONSE


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask NorthStar about sales or policies")
    parser.add_argument("--question", required=True)
    args = parser.parse_args()
    print(answer_question(args.question))


if __name__ == "__main__":
    main()
