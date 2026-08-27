"""SQLite-backed local analytical warehouse and question service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from . import queries
from .base import SalesService


def create_sales_database(frame: pd.DataFrame, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        frame.to_sql("sales", connection, if_exists="replace", index=False)
        connection.execute("CREATE INDEX idx_sales_date ON sales(order_date)")
        connection.execute("CREATE INDEX idx_sales_product ON sales(product_id)")


class SQLiteSalesService(SalesService):
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def _query(self, sql: str, parameters: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        if not self.database_path.exists():
            raise FileNotFoundError("Sales database is missing; run `python -m src.ingest` first.")
        with sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(sql, parameters).fetchall()

    @staticmethod
    def _money(value: float) -> str:
        return f"{value:,.2f}"

    def answer(self, question: str) -> str:
        normalized = question.lower()
        if "top" in normalized and "product" in normalized and "revenue" in normalized:
            rows = self._query(queries.TOP_PRODUCTS, (5,))
            lines = ["Top 5 products by total revenue:"]
            lines.extend(
                f"{number}. {row['product_name']} ({row['product_id']}): {self._money(row['total_revenue'])}"
                for number, row in enumerate(rows, 1)
            )
            return "\n".join(lines)
        if "revenue" in normalized and "region" in normalized:
            rows = self._query(queries.REVENUE_BY_REGION)
            return "Total revenue by region:\n" + "\n".join(
                f"- {row['region']}: {self._money(row['total_revenue'])}" for row in rows
            )
        if (
            "category" in normalized
            and "revenue" in normalized
            and ("7 day" in normalized or "seven day" in normalized)
        ):
            latest = self._query(queries.LATEST_DATE)[0]["latest_date"]
            row = self._query(queries.BEST_CATEGORY_PREVIOUS_7_DAYS)
            if not row:
                return f"No sales occurred in the seven calendar dates before {latest}."
            start = self._query("SELECT date(?, '-7 days') AS start", (latest,))[0]["start"]
            winner = row[0]
            return (
                f"Best-selling category by revenue: {winner['category']} "
                f"({self._money(winner['total_revenue'])}).\n"
                f"Window: {start} through the day before {latest}; latest order date {latest} is excluded."
            )
        return "I recognized a sales question, but only the three documented analytical questions are supported."
