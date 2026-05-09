import boto3
import structlog
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

log = structlog.get_logger()


def _make_client():  # type: ignore[return]
    """Client for server-side S3 operations (uses Docker-internal endpoint)."""
    kwargs: dict = dict(
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def _make_public_client():  # type: ignore[return]
    """Client for generating browser-facing presigned URLs.

    S3v4 signatures include the host in the signing payload, so the URL must
    be signed against the host the browser will actually reach (e.g.
    ``localhost:9000``), NOT the Docker-internal name (``minio:9000``).
    Falls back to the normal internal client when no public endpoint is set.
    """
    endpoint = settings.s3_public_endpoint_url or settings.s3_endpoint_url
    kwargs: dict = dict(
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
    )
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def generate_presigned_put_url(
    s3_key: str, content_type: str, expires_in: int = 900
) -> str:
    client = _make_public_client()
    url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    return url


def generate_presigned_get_url(s3_key: str, expires_in: int = 3600) -> str:
    client = _make_public_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )
    return url


def download_file(s3_key: str) -> bytes:
    client = _make_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
    return response["Body"].read()  # type: ignore[return-value]


def delete_object(s3_key: str) -> None:
    client = _make_client()
    client.delete_object(Bucket=settings.s3_bucket, Key=s3_key)


def ensure_bucket_exists() -> None:
    client = _make_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)

    # Allow browsers to PUT directly via presigned URLs.
    # MinIO doesn't implement PutBucketCors — it's configured via the
    # MINIO_API_CORS_ALLOW_ORIGIN env var on the MinIO container instead.
    try:
        client.put_bucket_cors(
            Bucket=settings.s3_bucket,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "HEAD"],
                        "AllowedOrigins": settings.cors_origins,
                        "ExposeHeaders": ["ETag"],
                        "MaxAgeSeconds": 3000,
                    }
                ]
            },
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "NotImplemented":
            log.debug("bucket_cors_skipped_minio")
        else:
            raise
