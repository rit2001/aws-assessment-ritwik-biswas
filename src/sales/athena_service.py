"""AWS Athena adapter; unused in local mode and safe to import without credentials."""

from __future__ import annotations

import time
from typing import Any

import boto3

from .base import SalesService


class AthenaSalesService(SalesService):
    def __init__(self, database: str, output_location: str, region: str = "ap-south-1"):
        if not database or not output_location:
            raise ValueError("Athena database and output location are required")
        self.database = database
        self.output_location = output_location
        self.client = boto3.client("athena", region_name=region)

    def execute(self, sql: str) -> list[dict[str, Any]]:
        response = self.client.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": self.database},
            ResultConfiguration={"OutputLocation": self.output_location},
            WorkGroup="northstar",
        )
        execution_id = response["QueryExecutionId"]
        while True:
            status = self.client.get_query_execution(QueryExecutionId=execution_id)
            state = status["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                break
            if state in {"FAILED", "CANCELLED"}:
                reason = status["QueryExecution"]["Status"].get("StateChangeReason", state)
                raise RuntimeError(f"Athena query {state.lower()}: {reason}")
            time.sleep(0.5)
        return self.client.get_query_results(QueryExecutionId=execution_id)["ResultSet"]["Rows"]

    def answer(self, question: str) -> str:
        raise NotImplementedError(
            "Production question-to-approved-query mapping should reuse the local query intents; "
            "the adapter's authenticated Athena execution is implemented separately."
        )
