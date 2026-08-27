from __future__ import annotations

import pandas as pd

from src.cleaning import clean_sales


def row(**overrides):
    base = {
        "order_id": "O-1", "order_date": "2026-01-02", "store_id": "S-1",
        "product_id": "P-1", "product_name": "Widget", "category": "Home",
        "quantity": "2", "unit_price": "3.50", "region": "North",
    }
    base.update(overrides)
    return base


def test_mixed_dates_trimming_and_exact_duplicate():
    raw = pd.DataFrame([
        row(order_id=" O-1 ", order_date="2026/01/02", product_name=" Widget "),
        row(order_id="O-1", order_date="2026-01-02"),
    ])
    cleaned, report = clean_sales(raw)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["order_date"] == "2026-01-02"
    assert cleaned.iloc[0]["product_name"] == "Widget"
    assert report.exact_duplicate_rows_removed == 1
    assert report.trimmed_string_cells == 2


def test_conflicting_order_ids_excludes_every_conflicting_row():
    raw = pd.DataFrame([
        row(order_id="O-1"),
        row(order_id="O-1", quantity="9"),
        row(order_id="O-2"),
    ])
    cleaned, report = clean_sales(raw)
    assert cleaned["order_id"].tolist() == ["O-2"]
    assert report.conflicting_order_ids == 1
    assert report.conflicting_order_rows_removed == 2


def test_sku_imputations_and_revenue():
    raw = pd.DataFrame([
        row(order_id="O-1"),
        row(order_id="O-2", product_name=None, unit_price=None, quantity="3"),
    ])
    cleaned, report = clean_sales(raw)
    imputed = cleaned.loc[cleaned["order_id"] == "O-2"].iloc[0]
    assert imputed["product_name"] == "Widget"
    assert imputed["unit_price"] == 3.5
    assert imputed["revenue"] == 10.5
    assert report.product_name_values_imputed == 1
    assert report.unit_price_values_imputed == 1


def test_missing_invalid_and_non_positive_quantities_are_removed():
    raw = pd.DataFrame([
        row(order_id="O-1", quantity=None),
        row(order_id="O-2", quantity="not-a-number"),
        row(order_id="O-3", quantity="0"),
        row(order_id="O-4", quantity="-1"),
        row(order_id="O-5", quantity="2"),
    ])
    cleaned, report = clean_sales(raw)
    assert cleaned["order_id"].tolist() == ["O-5"]
    assert report.missing_or_invalid_quantity_rows_removed == 2
    assert report.non_positive_quantity_rows_removed == 2


def test_invalid_dates_and_non_positive_price_are_removed():
    raw = pd.DataFrame([
        row(order_id="O-1", order_date="01-31-2026"),
        row(order_id="O-2", unit_price="0"),
        row(order_id="O-3"),
    ])
    cleaned, report = clean_sales(raw)
    assert cleaned["order_id"].tolist() == ["O-3"]
    assert report.invalid_date_rows_removed == 1
    assert report.non_positive_unit_price_rows_removed == 1
