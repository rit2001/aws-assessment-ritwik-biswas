from __future__ import annotations

import sqlite3

import pandas as pd

from src.sales.sqlite_service import SQLiteSalesService, create_sales_database


def sales_frame():
    rows = [
        ("O1", "2026-01-10", "P1", "Alpha", "Home", 2, 10.0, "North"),
        ("O2", "2026-01-09", "P2", "Beta", "Toys", 5, 5.0, "South"),
        ("O3", "2026-01-08", "P1", "Alpha", "Home", 1, 10.0, "North"),
        ("O4", "2026-01-03", "P3", "Gamma", "Toys", 10, 2.0, "West"),
        ("O5", "2026-01-02", "P4", "Delta", "Other", 100, 1.0, "East"),
        ("O6", "2026-01-07", "P5", "Epsilon", "Home", 2, 1.0, "North"),
    ]
    frame = pd.DataFrame(rows, columns=[
        "order_id", "order_date", "product_id", "product_name", "category",
        "quantity", "unit_price", "region",
    ])
    frame["revenue"] = frame.quantity * frame.unit_price
    return frame


def test_creates_queryable_sqlite_table(tmp_path):
    path = tmp_path / "sales.db"
    create_sales_database(sales_frame(), path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 6


def test_top_five_products(tmp_path):
    path = tmp_path / "sales.db"
    create_sales_database(sales_frame(), path)
    answer = SQLiteSalesService(path).answer("What are the top 5 products by total revenue?")
    assert "Delta (P4): 100.00" in answer
    assert answer.index("Delta") < answer.index("Alpha")


def test_revenue_by_region(tmp_path):
    path = tmp_path / "sales.db"
    create_sales_database(sales_frame(), path)
    answer = SQLiteSalesService(path).answer("What is total revenue by region?")
    assert "North: 32.00" in answer
    assert "East: 100.00" in answer


def test_best_category_uses_previous_seven_dates_and_excludes_latest(tmp_path):
    path = tmp_path / "sales.db"
    create_sales_database(sales_frame(), path)
    answer = SQLiteSalesService(path).answer(
        "What is the best-selling category by revenue in the 7 days immediately before the latest order date in the dataset?"
    )
    assert "Toys (45.00)" in answer
    assert "2026-01-03 through the day before 2026-01-10" in answer
    assert "latest order date 2026-01-10 is excluded" in answer
