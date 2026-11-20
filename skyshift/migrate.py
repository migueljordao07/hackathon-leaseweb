"""S3-to-S3 object migration and per-object SHA-256 verification (WS2).

Contract: tasks/contracts.md (Python API, shared envelope, Migration section).
Standard library only. Importing this module performs no I/O, network, process,
or client creation side effects.

``stub=True`` returns a deterministic synthetic record (mode stub, status
incomplete, never PASS). Live (WS2-03): ``rclone copy`` of the seed scope
prefix between explicit SKYSHIFT_SOURCE_* and SKYSHIFT_TARGET_* endpoints,
then complete paginated listings with every object streamed through SHA-256
on both sides (no ETags). boto3 is imported lazily for the live path only.
"""

from __future__ import annotations

import hashlib
import os
import time

SCHEMA_VERSION = 1

DATA_MAP_KEYS = ("resources", "calls", "buckets", "readiness")
TARGET_KEYS = (
    "target_id",
    "operator",
    "jurisdiction",
    "storage_mode",
    "criteria",
    "prices",
    "explanation",
)

# Deterministic 64-character lowercase hex placeholder (synthetic, not measured).
_STUB_OBJECT_SHA256 = "a1b2c3d4" * 8


def _envelope(
    step: str,
    mode: str,
    status: str,
    checks: list[dict],
    data: dict,
    errors: list[str],
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "step": step,
        "mode": mode,
        "status": status,
        "checks": checks,
        "data": data,
        "errors": errors,
    }


def _check_config(config: object) -> None:
    if not isinstance(config, dict):
        raise ValueError("config must be a dict of environment names to values")


def _require_data_object(obj: object, required_keys: tuple[str, ...], name: str) -> None:
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be the preceding envelope's data dict")
    if "schema_version" in obj and "data" in obj:
        raise ValueError(f"{name} must be the envelope's data object, not the whole envelope")
    missing = [key for key in required_keys if key not in obj]
    if missing:
        raise ValueError(f"{name} missing required keys: {', '.join(missing)}")


def migrate(data_map: dict, target: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a migrate envelope comparing source and target synthetic objects.

    Inputs are the preceding ``discover`` and ``choose`` envelope ``data`` objects.
    Does not mutate inputs, read credentials, invoke processes, or write files.
    """
    _require_data_object(data_map, DATA_MAP_KEYS, "data_map")
    _require_data_object(target, TARGET_KEYS, "target")
    _check_config(config)

    if stub:
        objects = [
            {
                "key": "synthetic/sample.txt",
                "source_bytes": 128,
                "target_bytes": 128,
                "source_sha256": _STUB_OBJECT_SHA256,
                "target_sha256": _STUB_OBJECT_SHA256,
                "status": "matched",
                "synthetic": True,
            }
        ]
        data = {
            "objects": objects,
            "source_count": 1,
            "target_count": 1,
            "matched": 1,
            "missing": 0,
            "different": 0,
            "extra": 0,
        }
        checks = [
            {
                "id": "rclone_copy",
                "status": "incomplete",
                "detail": "synthetic stub; rclone did not run and no S3 endpoints were accessed",
            },
            {
                "id": "object_sha256_parity",
                "status": "incomplete",
                "detail": "synthetic stub; placeholder SHA-256 hashes only, no VM or bucket measured",
            },
        ]
        return _envelope("migrate", "stub", "incomplete", checks, data, [])

    return _live_migrate(config)


# ---------------------------------------------------------------------------
# Live migration (WS2-03): rclone copy + streamed per-object SHA-256 proof.
# ---------------------------------------------------------------------------

#: Only keys under this prefix are migrated and compared (seed fixture scope).
#: The unchanged app writes its runtime objects elsewhere, so they never count as extra.
SCOPE_PREFIX = "seed_data/"
RCLONE_TIMEOUT_SECONDS = 180
HASH_CHUNK = 64 * 1024
_SOURCE = "SKYSHIFT_SOURCE"
_TARGET = "SKYSHIFT_TARGET"


def _side_config(config: dict, ns: str) -> dict | None:
    side = {
        "endpoint": config.get(f"{ns}_ENDPOINT_URL"),
        "key": config.get(f"{ns}_ACCESS_KEY_ID"),
        "secret": config.get(f"{ns}_SECRET_ACCESS_KEY"),
        "bucket": config.get(f"{ns}_BUCKET"),
        "region": config.get("AWS_DEFAULT_REGION") or "us-east-1",
    }
    if not all(isinstance(side[k], str) and side[k] for k in ("endpoint", "key", "secret", "bucket")):
        return None
    return side


def _client(side: dict):
    import boto3  # lazy: stub path stays stdlib-only
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=side["endpoint"],
        aws_access_key_id=side["key"],
        aws_secret_access_key=side["secret"],
        region_name=side["region"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=5, read_timeout=30, retries={"max_attempts": 2}),
    )


def _sanitize_exc(exc: BaseException) -> str:
    code = None
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = (response.get("Error") or {}).get("Code")
    return f"{type(exc).__name__}" + (f" ({code})" if isinstance(code, str) and code.isalnum() else "")


def list_and_hash(client, bucket: str, prefix: str = SCOPE_PREFIX) -> dict:
    """Paginate the full listing and stream every object through SHA-256.

    Returns {key: (bytes, sha256hex)}. Raises on any list/read failure, so an
    incomplete listing can never be reported as complete.
    """
    result: dict = {}
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        for item in page.get("Contents", []) or []:
            key = item["Key"]
            if key in result:
                raise ValueError("duplicate key in listing")
            body = client.get_object(Bucket=bucket, Key=key)["Body"]
            digest, size = hashlib.sha256(), 0
            while True:
                chunk = body.read(HASH_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
            result[key] = (size, digest.hexdigest())
        if page.get("IsTruncated"):
            token = page.get("NextContinuationToken")
            if not token:
                raise ValueError("truncated listing without continuation token")
            continue
        return result


def compare(source: dict, target: dict, prefix: str = SCOPE_PREFIX) -> dict:
    """Build contract migrate.data from two {key: (bytes, sha256)} listings."""
    rows = []
    for key in sorted(set(source) | set(target)):
        s, t = source.get(key), target.get(key)
        if s and t:
            status = "matched" if s == t else "different"
        elif s:
            status = "missing"
        else:
            status = "extra"
        rows.append({
            "key": key[len(prefix):] if prefix and key.startswith(prefix) else key,
            "source_bytes": s[0] if s else None,
            "target_bytes": t[0] if t else None,
            "source_sha256": s[1] if s else None,
            "target_sha256": t[1] if t else None,
            "status": status,
        })
    count = lambda st: sum(1 for r in rows if r["status"] == st)  # noqa: E731
    return {
        "objects": rows,
        "source_count": len(source),
        "target_count": len(target),
        "matched": count("matched"),
        "missing": count("missing"),
        "different": count("different"),
        "extra": count("extra"),
    }


def rclone_args(binary: str, src: str, dst: str, *, mode: str = "copy",
                disposable_target: bool = False, human_approved: bool = False) -> list[str]:
    """Argument list for rclone (never a shell string). ``sync`` needs both safety flags."""
    if mode == "sync":
        if not (disposable_target and human_approved):
            raise ValueError("rclone sync requires a disposable target and explicit human approval")
    elif mode != "copy":
        raise ValueError("unsupported rclone mode")
    return [binary, mode, "--s3-no-check-bucket", "--retries", "2", "--contimeout", "10s", src, dst]


def _rclone_env(src: dict, dst: dict) -> dict:
    env = {k: os.environ[k] for k in ("PATH", "HOME", "SYSTEMROOT", "TMPDIR") if k in os.environ}
    for name, side in (("SRC", src), ("DST", dst)):
        env.update({
            f"RCLONE_CONFIG_{name}_TYPE": "s3",
            f"RCLONE_CONFIG_{name}_PROVIDER": "Other",
            f"RCLONE_CONFIG_{name}_ENDPOINT": side["endpoint"],
            f"RCLONE_CONFIG_{name}_ACCESS_KEY_ID": side["key"],
            f"RCLONE_CONFIG_{name}_SECRET_ACCESS_KEY": side["secret"],
            f"RCLONE_CONFIG_{name}_REGION": side["region"],
            f"RCLONE_CONFIG_{name}_FORCE_PATH_STYLE": "true",
        })
    return env


def run_rclone(src: dict, dst: dict, *, runner=None, which=None, timeout: float = RCLONE_TIMEOUT_SECONDS) -> dict:
    """Run ``rclone copy`` for the scope prefix. Returns {"status", "detail"} with no secrets."""
    import shutil
    import subprocess  # lazy: importing this module never loads process tooling

    which = which or shutil.which
    binary = which("rclone")
    if not binary:
        return {"status": "incomplete", "detail": "rclone binary not found; copy not run"}
    args = rclone_args(binary, f"SRC:{src['bucket']}/{SCOPE_PREFIX}", f"DST:{dst['bucket']}/{SCOPE_PREFIX}")
    runner = runner or subprocess.run
    started = time.monotonic()
    try:
        proc = runner(args, env=_rclone_env(src, dst), capture_output=True, timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "detail": f"rclone copy timed out after {timeout:.0f}s"}
    except OSError as exc:
        return {"status": "FAIL", "detail": f"rclone could not start ({type(exc).__name__})"}
    elapsed = time.monotonic() - started
    if proc.returncode != 0:
        return {"status": "FAIL", "detail": f"rclone copy exit {proc.returncode} after {elapsed:.1f}s"}
    return {"status": "PASS", "detail": f"rclone copy exit 0 in {elapsed:.1f}s (scope prefix {SCOPE_PREFIX})"}


def _live_migrate(config: dict, *, client_factory=None, rclone=None) -> dict:
    empty = compare({}, {})
    src, dst = _side_config(config, _SOURCE), _side_config(config, _TARGET)
    if src is None or dst is None:
        missing = [ns for ns, side in ((_SOURCE, src), (_TARGET, dst)) if side is None]
        detail = "missing configuration for " + ", ".join(f"{ns}_*" for ns in missing)
        return _envelope("migrate", "live", "incomplete",
                         [{"id": "rclone_copy", "status": "incomplete", "detail": detail + "; nothing measured"}],
                         empty, [detail])
    client_factory = client_factory or _client
    errors: list[str] = []
    copy = (rclone or run_rclone)(src, dst)
    checks = [{"id": "rclone_copy", "status": copy["status"], "detail": copy["detail"]}]
    if copy["status"] != "PASS":
        errors.append("rclone_copy: " + copy["detail"])
    try:
        source = list_and_hash(client_factory(src), src["bucket"])
        target = list_and_hash(client_factory(dst), dst["bucket"])
    except Exception as exc:  # noqa: BLE001 - listing/read failure is a measured FAIL
        detail = f"listing or streamed read failed: {_sanitize_exc(exc)}"
        checks.append({"id": "object_sha256_parity", "status": "FAIL", "detail": detail})
        errors.append("object_sha256_parity: " + detail)
        return _envelope("migrate", "live", "FAIL", checks, empty, errors)
    data = compare(source, target)
    bad = data["missing"] + data["different"] + data["extra"]
    if data["source_count"] == 0:
        parity = {"id": "object_sha256_parity", "status": "incomplete",
                  "detail": f"source scope {SCOPE_PREFIX} is empty; nothing to prove"}
    elif bad:
        parity = {"id": "object_sha256_parity", "status": "FAIL",
                  "detail": f"{data['matched']}/{data['source_count']} matched; missing={data['missing']} "
                            f"different={data['different']} extra={data['extra']}"}
    else:
        parity = {"id": "object_sha256_parity", "status": "PASS",
                  "detail": f"{data['matched']}/{data['source_count']} objects: equal bytes and streamed SHA-256 "
                            f"(no ETags), complete paginated listings, scope {SCOPE_PREFIX}"}
    checks.append(parity)
    if parity["status"] != "PASS":
        errors.append("object_sha256_parity: " + parity["detail"])
    statuses = [c["status"] for c in checks]
    overall = "FAIL" if "FAIL" in statuses else ("PASS" if all(s == "PASS" for s in statuses) else "incomplete")
    return _envelope("migrate", "live", overall, checks, data, errors)
