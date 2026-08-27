"""Deterministic, independently testable question routing."""

from __future__ import annotations

from enum import Enum


class Route(str, Enum):
    SALES = "sales"
    DOCUMENTS = "documents"
    AMBIGUOUS = "ambiguous"


SALES_TERMS = {
    "revenue", "sales", "top product", "region", "category", "best-selling",
    "best selling", "order date",
}
POLICY_TERMS = {
    "return", "refund", "warranty", "shipping", "delivery", "loyalty", "points",
    "sizing", "size", "exchange", "promotion", "discount", "support", "stationery",
}
STRONG_SALES_TERMS = {"revenue", "sales", "top product", "best-selling", "best selling", "order date"}
STRONG_POLICY_TERMS = {
    "return", "refund", "warranty", "shipping", "delivery", "loyalty", "points",
    "sizing", "size", "exchange", "promotion", "support", "stationery",
}


def route_question(question: str) -> Route:
    normalized = " ".join(question.lower().split())
    sales_score = sum(term in normalized for term in SALES_TERMS)
    policy_score = sum(term in normalized for term in POLICY_TERMS)
    if sales_score and policy_score:
        strong_sales = any(term in normalized for term in STRONG_SALES_TERMS)
        strong_policy = any(term in normalized for term in STRONG_POLICY_TERMS)
        if strong_policy and not strong_sales:
            return Route.DOCUMENTS
        return Route.AMBIGUOUS
    if sales_score:
        return Route.SALES
    if policy_score:
        return Route.DOCUMENTS
    return Route.AMBIGUOUS
