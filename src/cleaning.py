"""Explicit, auditable cleaning rules for the supplied sales history."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "order_id", "order_date", "store_id", "product_id", "product_name",
    "category", "quantity", "unit_price", "region",
}
STRING_COLUMNS = [
    "order_id", "order_date", "store_id", "product_id", "product_name",
    "category", "region",
]


@dataclass
class CleaningReport:
    raw_rows: int = 0
    trimmed_string_cells: int = 0
    invalid_date_rows_removed: int = 0
    exact_duplicate_rows_removed: int = 0
    conflicting_order_ids: int = 0
    conflicting_order_rows_removed: int = 0
    product_name_values_imputed: int = 0
    unit_price_values_imputed: int = 0
    unresolved_product_name_rows_removed: int = 0
    missing_or_invalid_quantity_rows_removed: int = 0
    non_positive_quantity_rows_removed: int = 0
    missing_or_invalid_unit_price_rows_removed: int = 0
    non_positive_unit_price_rows_removed: int = 0
    cleaned_rows: int = 0

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def _parse_date(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _stable_mapping(frame: pd.DataFrame, value_column: str) -> dict[str, object]:
    available = frame.dropna(subset=["product_id", value_column])
    result: dict[str, object] = {}
    for product_id, group in available.groupby("product_id"):
        values = group[value_column].dropna().unique()
        if len(values) == 1:
            result[str(product_id)] = values[0]
    return result


def clean_sales(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply the documented policy in order and return data plus rule counts."""
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"sales.csv is missing required columns: {sorted(missing)}")

    frame = raw.copy()
    report = CleaningReport(raw_rows=len(frame))

    for column in STRING_COLUMNS:
        before = frame[column].copy()
        frame[column] = frame[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        frame[column] = frame[column].replace("", pd.NA)
        report.trimmed_string_cells += int(
            sum(
                isinstance(old, str) and old != (new if isinstance(new, str) else "")
                for old, new in zip(before, frame[column])
            )
        )

    normalized_dates = frame["order_date"].map(_parse_date)
    invalid_dates = normalized_dates.isna()
    report.invalid_date_rows_removed = int(invalid_dates.sum())
    frame = frame.loc[~invalid_dates].copy()
    frame["order_date"] = normalized_dates.loc[~invalid_dates]

    before_dedup = len(frame)
    frame = frame.drop_duplicates().copy()
    report.exact_duplicate_rows_removed = before_dedup - len(frame)

    conflicting = frame["order_id"].notna() & frame["order_id"].duplicated(keep=False)
    report.conflicting_order_ids = int(frame.loc[conflicting, "order_id"].nunique())
    report.conflicting_order_rows_removed = int(conflicting.sum())
    frame = frame.loc[~conflicting].copy()

    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
    name_map = _stable_mapping(frame, "product_name")
    price_map = _stable_mapping(frame, "unit_price")

    missing_name = frame["product_name"].isna()
    frame.loc[missing_name, "product_name"] = frame.loc[missing_name, "product_id"].map(name_map)
    report.product_name_values_imputed = int(
        (missing_name & frame["product_name"].notna()).sum()
    )
    unresolved_name = frame["product_name"].isna()
    report.unresolved_product_name_rows_removed = int(unresolved_name.sum())
    frame = frame.loc[~unresolved_name].copy()

    missing_price = frame["unit_price"].isna()
    frame.loc[missing_price, "unit_price"] = frame.loc[missing_price, "product_id"].map(price_map)
    report.unit_price_values_imputed = int(
        (missing_price & frame["unit_price"].notna()).sum()
    )

    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    invalid_quantity = frame["quantity"].isna()
    report.missing_or_invalid_quantity_rows_removed = int(invalid_quantity.sum())
    frame = frame.loc[~invalid_quantity].copy()

    non_positive_quantity = frame["quantity"] <= 0
    report.non_positive_quantity_rows_removed = int(non_positive_quantity.sum())
    frame = frame.loc[~non_positive_quantity].copy()

    invalid_price = frame["unit_price"].isna()
    report.missing_or_invalid_unit_price_rows_removed = int(invalid_price.sum())
    frame = frame.loc[~invalid_price].copy()

    non_positive_price = frame["unit_price"] <= 0
    report.non_positive_unit_price_rows_removed = int(non_positive_price.sum())
    frame = frame.loc[~non_positive_price].copy()

    frame["quantity"] = frame["quantity"].astype(float)
    frame["unit_price"] = frame["unit_price"].astype(float)
    frame["revenue"] = frame["quantity"] * frame["unit_price"]
    report.cleaned_rows = len(frame)
    return frame.reset_index(drop=True), report


def clean_sales_csv(path: Path) -> tuple[pd.DataFrame, CleaningReport]:
    return clean_sales(pd.read_csv(path, dtype=str, keep_default_na=True))
