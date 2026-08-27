"""Environment-backed configuration with credential-free local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - useful before dependencies are installed
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    app_mode: str = "local"
    aws_region: str = "ap-south-1"
    aws_s3_bucket: str = ""
    aws_athena_database: str = ""
    aws_athena_output_location: str = ""
    aws_bedrock_model_id: str = ""
    aws_bedrock_knowledge_base_id: str = ""
    data_dir: Path = ROOT / "data"
    artifacts_dir: Path = ROOT / "artifacts"

    @property
    def sales_csv(self) -> Path:
        return self.data_dir / "sales.csv"

    @property
    def documents_dir(self) -> Path:
        nested = self.data_dir / "product_docs"
        return nested if nested.is_dir() else self.data_dir

    @property
    def sqlite_path(self) -> Path:
        return self.artifacts_dir / "northstar.db"

    @property
    def document_index_path(self) -> Path:
        return self.artifacts_dir / "document_index.json"


def get_settings() -> Settings:
    if load_dotenv:
        load_dotenv(ROOT / ".env")
    return Settings(
        app_mode=os.getenv("APP_MODE", "local").lower(),
        aws_region=os.getenv("AWS_REGION", "ap-south-1"),
        aws_s3_bucket=os.getenv("AWS_S3_BUCKET", ""),
        aws_athena_database=os.getenv("AWS_ATHENA_DATABASE", ""),
        aws_athena_output_location=os.getenv("AWS_ATHENA_OUTPUT_LOCATION", ""),
        aws_bedrock_model_id=os.getenv("AWS_BEDROCK_MODEL_ID", ""),
        aws_bedrock_knowledge_base_id=os.getenv("AWS_BEDROCK_KNOWLEDGE_BASE_ID", ""),
    )
