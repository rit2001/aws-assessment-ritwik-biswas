from __future__ import annotations

from src.config import ROOT
from src.documents.generator import ExtractivePolicyGenerator
from src.documents.loader import discover_documents, load_documents
from src.documents.retriever import BM25Retriever


DOCUMENTS = ROOT / "data" / "product_docs"


def generator():
    return ExtractivePolicyGenerator(BM25Retriever(load_documents(DOCUMENTS)))


def test_discovers_all_eight_mixed_format_documents():
    files = discover_documents(DOCUMENTS)
    assert len(files) == 8
    assert {path.suffix for path in files} == {".pdf", ".json", ".txt", ".csv"}
    chunks = load_documents(DOCUMENTS)
    assert chunks
    assert all(chunk.text and chunk.source for chunk in chunks)
    assert any(chunk.page for chunk in chunks if chunk.source.endswith(".pdf"))


def test_shipping_retrieval_is_grounded_and_cited():
    answer = generator().answer("How long does standard cross-region shipping take?")
    assert "7 to 10 business days" in answer
    assert "Source: shipping.json — Standard and Express Delivery" in answer


def test_loyalty_retrieval_is_grounded_and_cited():
    answer = generator().answer("When do unused loyalty points expire?")
    assert "18 months" in answer
    assert "Source: loyalty.json — Expiry" in answer


def test_stationery_retrieval_has_row_topic_source():
    answer = generator().answer("Are stationery products covered by the electronics warranty?")
    assert "not covered" in answer
    assert "Source: stationery-faq.csv — Warranty coverage" in answer


def test_return_pdf_retrieval_finds_window_with_page_source():
    answer = generator().answer("How many days do I have to return an eligible item?")
    assert "30 days from the Delivery Date" in answer
    assert "Source: returns.pdf" in answer
    assert "page 12" in answer


def test_warranty_pdf_retrieval_prefers_warranty_document():
    answer = generator().answer("What warranty applies to electronics?")
    assert "manufacturer warranty terms" in answer
    assert "Source: warranty.pdf" in answer


def test_warranty_period_retrieval_prefers_coverage_section():
    answer = generator().answer("How long is the warranty period for electronics?")
    assert "12 month" in answer
    assert "Source: warranty.pdf" in answer


def test_support_contact_and_response_time_retrieval_combines_relevant_sections():
    answer = generator().answer(
        "How can I contact customer support and what response time should I expect?"
    )
    assert "chat" in answer.lower() or "email" in answer.lower()
    assert "24 hours" in answer
    assert "Source: support.pdf" in answer


def test_unresolved_support_issue_retrieves_escalation_process():
    answer = generator().answer("What support options are available for an unresolved issue?")
    assert "supervisor review" in answer
    assert "Source: support.pdf — 5. Escalation Process" in answer
