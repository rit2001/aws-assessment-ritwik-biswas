"""Grounded local answer composition from retrieved passages."""

from __future__ import annotations

from .retriever import BM25Retriever


class ExtractivePolicyGenerator:
    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever

    def answer(self, question: str) -> str:
        results = self.retriever.search(question, limit=2)
        if not results:
            return "I could not find a relevant answer in the supplied policy documents."
        # Returning the strongest passage avoids introducing facts absent from the corpus.
        chunk, _ = results[0]
        return f"{chunk.text}\n{chunk.citation}"
