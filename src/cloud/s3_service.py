"""Narrow S3 boundary for promoting local artifacts to AWS."""

from __future__ import annotations

from pathlib import Path

import boto3


class S3Service:
    def __init__(self, bucket: str, region: str = "ap-south-1"):
        if not bucket:
            raise ValueError("AWS_S3_BUCKET is required")
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def upload_file(self, local_path: Path, key: str) -> None:
        self.client.upload_file(str(local_path), self.bucket, key)
