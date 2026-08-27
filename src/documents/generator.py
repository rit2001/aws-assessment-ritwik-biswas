"""Grounded local answer composition from retrieved passages."""

from __future__ import annotations

from .retriever import BM25Retriever, heading_intent_terms, tokenize


class ExtractivePolicyGenerator:
    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever

    def answer(self, question: str) -> str:
        results = self.retriever.search(question, limit=2)
        if not results:
            return "I could not find a relevant answer in the supplied policy documents."
        # Include a second same-source section only when it covers an additional
        # heading intent, as in a question asking for both channels and timings.
        chunks = [results[0][0]]
        if len(results) > 1 and results[1][0].source == chunks[0].source:
            intents = heading_intent_terms(question)
            first_heading = set(tokenize(chunks[0].section or "")).intersection(intents)
            second_heading = set(tokenize(results[1][0].section or "")).intersection(intents)
            if second_heading.difference(first_heading):
                chunks.append(results[1][0])
        return "\n\n".join(f"{chunk.text}\n{chunk.citation}" for chunk in chunks)
