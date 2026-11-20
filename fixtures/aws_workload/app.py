"""Synthetic AWS workload application for SkyShift migration, parity, and severance tests.

This file is the unchanged baseline artifact (WS2-02). Later migration, runner,
parity, and severance tasks must configure it strictly through documented
environment variables without modifying this file's bytes:

- ``AWS_ENDPOINT_URL``: S3-compatible endpoint override.
- ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` / ``AWS_DEFAULT_REGION``:
  S3/telemetry credentials and region supplied privately at runtime.
- ``SKYSHIFT_TARGET_BUCKET`` / ``SKYSHIFT_SOURCE_BUCKET``: synthetic bucket name.
- ``SKYSHIFT_TELEMETRY_ENDPOINT``: overrides the default AWS CloudWatch
  telemetry endpoint (``https://monitoring.eu-central-1.amazonaws.com``).

Importing this module performs no I/O, network calls, or client creation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

try:
    import boto3
except ImportError:  # pragma: no cover - optional when running offline with test doubles
    boto3 = None  # type: ignore[assignment]

try:
    from botocore.config import Config as BotocoreConfig
except ImportError:  # pragma: no cover - optional when running offline with test doubles
    BotocoreConfig = None  # type: ignore[assignment]

DEFAULT_REGION = "eu-central-1"
DEFAULT_BUCKET = "skyshift-demo-workload-bucket"
DEFAULT_PREFIX = "skyshift-workload-check"
DEFAULT_TELEMETRY_ENDPOINT = "https://monitoring.eu-central-1.amazonaws.com"

CONNECT_TIMEOUT_SECONDS = 3
READ_TIMEOUT_SECONDS = 5
MAX_RETRY_ATTEMPTS = 1
STREAM_CHUNK_BYTES = 16384
DEFAULT_MULTIPART_PART_SIZE = 5 * 1024 * 1024  # 5 MiB S3 standard minimum part size
MULTIPART_RECORD_COUNT = 1024
MULTIPART_RECORD_BYTES = 128

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


def sanitize_endpoint_host(url: str | None) -> str | None:
    """Extract only scheme-stripped host[:port] without userinfo, path, or query."""
    if not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if not parts.hostname:
        return None
    host = parts.hostname.lower()
    if parts.port is not None:
        return f"{host}:{parts.port}"
    return host


def generate_multipart_payload() -> bytes:
    """Deterministically generate the 128 KiB synthetic binary payload."""
    blocks = []
    for index in range(MULTIPART_RECORD_COUNT):
        header = f"SKYSHIFT-PART-{index:04d}:".encode("ascii")  # 19 bytes
        body = bytes(((index * 31 + offset) % 256) for offset in range(108))
        blocks.append(header + body + b"\n")  # 128 bytes total
    return b"".join(blocks)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stream_body_sha256(body: Any, chunk_size: int = STREAM_CHUNK_BYTES) -> tuple[str, int]:
    """Stream an S3 response Body through SHA-256 without unbounded reads."""
    digest = hashlib.sha256()
    total = 0
    try:
        while True:
            chunk = body.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    finally:
        close_fn = getattr(body, "close", None)
        if callable(close_fn):
            close_fn()
    return digest.hexdigest(), total


def _build_client_config(addressing_style: str | None = None) -> Any:
    if BotocoreConfig is None:
        return None
    kwargs: dict[str, Any] = {
        "connect_timeout": CONNECT_TIMEOUT_SECONDS,
        "read_timeout": READ_TIMEOUT_SECONDS,
        "retries": {"max_attempts": MAX_RETRY_ATTEMPTS, "mode": "standard"},
    }
    if addressing_style is not None:
        kwargs["s3"] = {"addressing_style": addressing_style}
    return BotocoreConfig(**kwargs)


def build_s3_client(env: Mapping[str, str] | None = None) -> Any:
    """Create a bounded S3 client configured strictly from contract env names."""
    if boto3 is None:
        raise RuntimeError("boto3 is required when no S3 test double is supplied")
    cfg = os.environ if env is None else env
    endpoint_url = cfg.get("AWS_ENDPOINT_URL") or None
    region_name = cfg.get("AWS_DEFAULT_REGION") or DEFAULT_REGION
    access_key = cfg.get("AWS_ACCESS_KEY_ID") or None
    secret_key = cfg.get("AWS_SECRET_ACCESS_KEY") or None
    client_config = _build_client_config(addressing_style="path")

    kwargs: dict[str, Any] = {
        "region_name": region_name,
        "endpoint_url": endpoint_url,
    }
    if access_key is not None:
        kwargs["aws_access_key_id"] = access_key
    if secret_key is not None:
        kwargs["aws_secret_access_key"] = secret_key
    if client_config is not None:
        kwargs["config"] = client_config

    s3_client = boto3.client("s3", **kwargs)
    return s3_client


def build_telemetry_client(env: Mapping[str, str] | None = None) -> tuple[Any, str]:
    """Create a bounded CloudWatch telemetry client and return (client, endpoint_url).

    Defaults to the AWS-controlled monitoring endpoint unless overridden by
    ``SKYSHIFT_TELEMETRY_ENDPOINT`` (config-only remediation for WS3).
    """
    if boto3 is None:
        raise RuntimeError("boto3 is required when no telemetry test double is supplied")
    cfg = os.environ if env is None else env
    telemetry_endpoint = (cfg.get("SKYSHIFT_TELEMETRY_ENDPOINT") or "").strip()
    region_name = cfg.get("AWS_DEFAULT_REGION") or DEFAULT_REGION
    access_key = cfg.get("AWS_ACCESS_KEY_ID") or None
    secret_key = cfg.get("AWS_SECRET_ACCESS_KEY") or None
    client_config = _build_client_config()

    common_kwargs: dict[str, Any] = {"region_name": region_name}
    if access_key is not None:
        common_kwargs["aws_access_key_id"] = access_key
    if secret_key is not None:
        common_kwargs["aws_secret_access_key"] = secret_key
    if client_config is not None:
        common_kwargs["config"] = client_config

    if telemetry_endpoint and telemetry_endpoint != DEFAULT_TELEMETRY_ENDPOINT:
        return (
            boto3.client("cloudwatch", endpoint_url=telemetry_endpoint, **common_kwargs),
            telemetry_endpoint,
        )

    cloudwatch_client = boto3.client(
        "cloudwatch",
        endpoint_url="https://monitoring.eu-central-1.amazonaws.com",
        **common_kwargs,
    )
    return cloudwatch_client, DEFAULT_TELEMETRY_ENDPOINT


def load_multipart_payload(seed_dir: Path | None = None) -> bytes:
    """Load the deterministic multipart payload from seed_data or regenerate it."""
    base = SEED_DIR if seed_dir is None else Path(seed_dir)
    candidate = base / "multipart.bin"
    if candidate.is_file():
        return candidate.read_bytes()
    return generate_multipart_payload()


def run_s3_operations(
    s3_client: Any,
    bucket: str,
    prefix: str,
    *,
    multipart_payload: bytes,
    part_size: int = DEFAULT_MULTIPART_PART_SIZE,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Run put, get, list, and multipart upload checks on the supplied S3 client."""
    if part_size <= 0:
        raise ValueError("part_size must be positive")

    clean_prefix = prefix.strip("/")
    smoke_key = f"{clean_prefix}/smoke.json" if clean_prefix else "smoke.json"
    multipart_key = f"{clean_prefix}/multipart.bin" if clean_prefix else "multipart.bin"
    smoke_payload = json.dumps(
        {"app": "skyshift-aws-workload", "synthetic": True, "version": 1},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    smoke_sha256 = _sha256_bytes(smoke_payload)
    multipart_sha256 = _sha256_bytes(multipart_payload)

    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    # 1. put_object
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=smoke_key,
            Body=smoke_payload,
            ContentType="application/json",
        )
        checks.append(
            {
                "operation": "put_object",
                "status": "PASS",
                "detail": f"uploaded {len(smoke_payload)} bytes to {smoke_key}",
            }
        )
    except Exception as exc:
        msg = f"put_object failed: {type(exc).__name__}"
        errors.append(msg)
        checks.append({"operation": "put_object", "status": "FAIL", "detail": msg})

    # 2. get_object
    try:
        response = s3_client.get_object(Bucket=bucket, Key=smoke_key)
        got_sha256, got_bytes = _stream_body_sha256(response["Body"])
        if got_sha256 == smoke_sha256 and got_bytes == len(smoke_payload):
            checks.append(
                {
                    "operation": "get_object",
                    "status": "PASS",
                    "detail": f"verified {got_bytes} bytes SHA-256 {got_sha256}",
                }
            )
        else:
            msg = "get_object payload mismatch"
            errors.append(msg)
            checks.append({"operation": "get_object", "status": "FAIL", "detail": msg})
    except Exception as exc:
        msg = f"get_object failed: {type(exc).__name__}"
        errors.append(msg)
        checks.append({"operation": "get_object", "status": "FAIL", "detail": msg})

    # 3. list_objects_v2
    try:
        list_prefix = f"{clean_prefix}/" if clean_prefix else ""
        list_response = s3_client.list_objects_v2(Bucket=bucket, Prefix=list_prefix)
        found_keys = sorted(
            item["Key"] for item in list_response.get("Contents", []) if "Key" in item
        )
        if smoke_key in found_keys:
            checks.append(
                {
                    "operation": "list_objects_v2",
                    "status": "PASS",
                    "detail": f"listed {len(found_keys)} objects including {smoke_key}",
                }
            )
        else:
            msg = f"list_objects_v2 did not return {smoke_key}"
            errors.append(msg)
            checks.append({"operation": "list_objects_v2", "status": "FAIL", "detail": msg})
    except Exception as exc:
        msg = f"list_objects_v2 failed: {type(exc).__name__}"
        errors.append(msg)
        checks.append({"operation": "list_objects_v2", "status": "FAIL", "detail": msg})

    # 4. Multipart upload + verification readback
    upload_id: str | None = None
    try:
        created = s3_client.create_multipart_upload(
            Bucket=bucket,
            Key=multipart_key,
            ContentType="application/octet-stream",
        )
        upload_id = created["UploadId"]
        parts: list[dict[str, Any]] = []
        part_number = 1
        offset = 0
        payload_len = len(multipart_payload)
        while offset < payload_len:
            chunk = multipart_payload[offset : offset + part_size]
            uploaded = s3_client.upload_part(
                Bucket=bucket,
                Key=multipart_key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=chunk,
            )
            parts.append({"ETag": uploaded["ETag"], "PartNumber": part_number})
            part_number += 1
            offset += part_size

        s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=multipart_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts},
        )
        upload_id = None

        mp_response = s3_client.get_object(Bucket=bucket, Key=multipart_key)
        got_mp_sha256, got_mp_bytes = _stream_body_sha256(mp_response["Body"])
        if got_mp_sha256 == multipart_sha256 and got_mp_bytes == payload_len:
            checks.append(
                {
                    "operation": "multipart_upload",
                    "status": "PASS",
                    "detail": f"uploaded {len(parts)} part(s), verified {got_mp_bytes} bytes",
                }
            )
        else:
            msg = "multipart_upload readback mismatch"
            errors.append(msg)
            checks.append({"operation": "multipart_upload", "status": "FAIL", "detail": msg})
    except Exception as exc:
        if upload_id is not None:
            try:
                s3_client.abort_multipart_upload(
                    Bucket=bucket,
                    Key=multipart_key,
                    UploadId=upload_id,
                )
            except Exception:
                pass
        msg = f"multipart_upload failed: {type(exc).__name__}"
        errors.append(msg)
        checks.append({"operation": "multipart_upload", "status": "FAIL", "detail": msg})

    return checks, errors


def emit_telemetry(
    cloudwatch_client: Any,
    *,
    endpoint_url: str,
    s3_passed: bool,
) -> dict[str, Any]:
    """Send one bounded synthetic CloudWatch metric; fail visibly and quickly on error."""
    endpoint_host = sanitize_endpoint_host(endpoint_url)
    try:
        cloudwatch_client.put_metric_data(
            Namespace="SkyShift/Workload",
            MetricData=[
                {
                    "MetricName": "WorkloadS3CheckSuccess",
                    "Value": 1.0 if s3_passed else 0.0,
                    "Unit": "Count",
                }
            ],
        )
        return {
            "operation": "put_metric_data",
            "endpoint_host": endpoint_host,
            "status": "PASS",
            "detail": f"telemetry metric accepted by {endpoint_host or 'configured-endpoint'}",
        }
    except Exception as exc:
        return {
            "operation": "put_metric_data",
            "endpoint_host": endpoint_host,
            "status": "FAIL",
            "detail": f"telemetry metric failed ({type(exc).__name__})",
        }


def run_workload(
    *,
    env: Mapping[str, str] | None = None,
    s3_client: Any | None = None,
    telemetry_client: Any | None = None,
    bucket: str | None = None,
    prefix: str = DEFAULT_PREFIX,
    seed_dir: Path | None = None,
    part_size: int = DEFAULT_MULTIPART_PART_SIZE,
    require_telemetry: bool = False,
) -> tuple[dict[str, Any], int]:
    """Execute the deterministic S3 and telemetry checks and return (result, exit_code)."""
    cfg = os.environ if env is None else env
    resolved_bucket = (
        bucket
        or cfg.get("SKYSHIFT_TARGET_BUCKET")
        or cfg.get("SKYSHIFT_SOURCE_BUCKET")
        or DEFAULT_BUCKET
    )
    s3_endpoint_host = sanitize_endpoint_host(cfg.get("AWS_ENDPOINT_URL"))
    telemetry_url = (cfg.get("SKYSHIFT_TELEMETRY_ENDPOINT") or "").strip() or DEFAULT_TELEMETRY_ENDPOINT

    if s3_client is None:
        s3_client = build_s3_client(cfg)
    if telemetry_client is None:
        telemetry_client, telemetry_url = build_telemetry_client(cfg)

    multipart_payload = load_multipart_payload(seed_dir=seed_dir)
    checks, errors = run_s3_operations(
        s3_client,
        resolved_bucket,
        prefix,
        multipart_payload=multipart_payload,
        part_size=part_size,
    )
    s3_passed = bool(checks) and all(item["status"] == "PASS" for item in checks)
    telemetry_result = emit_telemetry(
        telemetry_client,
        endpoint_url=telemetry_url,
        s3_passed=s3_passed,
    )

    overall_pass = s3_passed and (telemetry_result["status"] == "PASS" or not require_telemetry)
    if require_telemetry and telemetry_result["status"] != "PASS":
        errors.append(telemetry_result["detail"])

    result = {
        "status": "PASS" if overall_pass else "FAIL",
        "bucket": resolved_bucket,
        "prefix": prefix,
        "endpoint_host": s3_endpoint_host,
        "checks": checks,
        "telemetry": telemetry_result,
        "errors": errors,
    }
    return result, (0 if overall_pass else 1)


def main(argv: list[str] | None = None) -> int:
    """Bounded CLI entry point emitting sanitized JSON results to stdout."""
    parser = argparse.ArgumentParser(description="Synthetic SkyShift AWS workload app")
    parser.add_argument("--bucket", default=None, help="Synthetic S3 bucket name")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Synthetic object key prefix")
    parser.add_argument("--seed-dir", type=Path, default=None, help="Seed data directory")
    parser.add_argument(
        "--part-size",
        type=int,
        default=DEFAULT_MULTIPART_PART_SIZE,
        help="Multipart upload part size in bytes",
    )
    parser.add_argument(
        "--require-telemetry",
        action="store_true",
        help="Return nonzero exit code if telemetry emission fails",
    )
    args = parser.parse_args(argv)

    try:
        result, exit_code = run_workload(
            bucket=args.bucket,
            prefix=args.prefix,
            seed_dir=args.seed_dir,
            part_size=args.part_size,
            require_telemetry=args.require_telemetry,
        )
    except Exception as exc:
        result = {
            "status": "FAIL",
            "bucket": args.bucket,
            "prefix": args.prefix,
            "endpoint_host": sanitize_endpoint_host(os.environ.get("AWS_ENDPOINT_URL")),
            "checks": [],
            "telemetry": {
                "operation": "put_metric_data",
                "endpoint_host": sanitize_endpoint_host(
                    os.environ.get("SKYSHIFT_TELEMETRY_ENDPOINT") or DEFAULT_TELEMETRY_ENDPOINT
                ),
                "status": "incomplete",
                "detail": "not executed due to startup error",
            },
            "errors": [f"workload execution failed: {type(exc).__name__}"],
        }
        exit_code = 1

    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
