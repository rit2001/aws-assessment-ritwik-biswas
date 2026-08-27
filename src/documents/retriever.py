"""Small deterministic BM25 retriever with no model or credential requirement."""

from __future__ import annotations

import math
import re
from collections import Counter

from .loader import DocumentChunk


TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {"a", "an", "and", "are", "be", "do", "for", "how", "i", "in", "is", "it", "of", "on", "the", "to", "what", "with"}

# Small lexical expansions let intent-bearing section headings participate in
# scoring even when a customer uses an everyday synonym. These are deliberately
# policy-agnostic and contain no answer text.
HEADING_INTENT_EXPANSIONS = {
    "contact": {"channel", "chat", "email", "phone"},
    "duration": {"coverage", "period"},
    "long": {"coverage", "duration", "period"},
    "unresolved": {"escalate", "escalated", "escalation", "supervisor"},
}
HEADING_INTENT_TERMS = {
    "channel", "chat", "coverage", "duration", "email", "escalate", "escalated",
    "escalation", "period", "phone", "response", "supervisor", "time",
}
GENERIC_SECTIONS = {"definitions", "purpose", "scope"}


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


def heading_intent_terms(query: str) -> set[str]:
    query_terms = set(tokenize(query))
    intents = query_terms.intersection(HEADING_INTENT_TERMS)
    for term in query_terms:
        intents.update(HEADING_INTENT_EXPANSIONS.get(term, ()))
    return intents


def _is_definition(chunk: DocumentChunk) -> bool:
    text = chunk.text.lstrip()
    return (text.startswith('"') and '" means' in text[:160]) or text.startswith('See "')


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
        query_term_set = set(query_terms)
        exact_heading_intents = query_term_set.intersection(HEADING_INTENT_TERMS)
        expanded_heading_intents = heading_intent_terms(query).difference(query_term_set)
        has_specific_intent = bool(exact_heading_intents or expanded_heading_intents)
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
            heading_terms = set(tokenize(" ".join(filter(None, [chunk.title, chunk.section]))))
            score += 3.0 * len(heading_terms.intersection(exact_heading_intents))
            score += 8.0 * len(heading_terms.intersection(expanded_heading_intents))
            if has_specific_intent and heading_terms.intersection(GENERIC_SECTIONS):
                score *= 0.5
            if has_specific_intent and _is_definition(chunk):
                score *= 0.5
            if score > 0:
                scored.append((chunk, score))
        return sorted(scored, key=lambda item: (-item[1], item[0].source))[:limit]
