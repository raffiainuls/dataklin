from __future__ import annotations
import boto3
from botocore.client import Config

from ..config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)


def put_object(key: str, body: bytes) -> None:
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=body)


def get_object(key: str) -> bytes:
    resp = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    return resp["Body"].read()
