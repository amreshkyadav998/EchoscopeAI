"""Report file storage — S3 when configured, else local filesystem (HLD §4.7).

S3 path: boto3 put_object + a 24h pre-signed URL.
Local fallback: write under reports_dir; the download_url points at the service's
own /reports/{id}/download streaming endpoint (so it runs without AWS).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger as log

from config import get_settings


@dataclass
class StoredFile:
    key: str                 # s3 key OR local path
    size: int
    download_url: str | None  # pre-signed URL (S3) or None for local (served via endpoint)


def _s3_enabled() -> bool:
    return bool(get_settings().aws_bucket)


def store_report(org_id: str, report_id: str, ext: str, data: bytes) -> StoredFile:
    settings = get_settings()
    key = f"reports/{org_id}/{report_id}.{ext}"

    if _s3_enabled():
        import boto3

        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        client.put_object(Bucket=settings.aws_bucket, Key=key, Body=data)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_bucket, "Key": key},
            ExpiresIn=settings.presigned_ttl,
        )
        log.info("report uploaded to S3", key=key, size=len(data))
        return StoredFile(key=key, size=len(data), download_url=url)

    # local fallback
    path = Path(settings.reports_dir) / org_id / f"{report_id}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    log.info("report saved locally", path=str(path), size=len(data))
    return StoredFile(key=str(path), size=len(data), download_url=None)


def local_path(key: str) -> Path:
    return Path(key)


def presigned_url(key: str) -> str | None:
    """Fresh pre-signed URL for an S3 key, or None when using local storage."""
    if not _s3_enabled():
        return None
    import boto3

    settings = get_settings()
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_bucket, "Key": key},
        ExpiresIn=settings.presigned_ttl,
    )
