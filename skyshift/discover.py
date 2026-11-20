"""Discover AWS dependencies and choose a Leaseweb target (WS1).

Contract: tasks/contracts.md (Python API, shared envelope, data map, target choice).
Standard library only. Importing this module performs no I/O, network or service start.

Current state: offline stubs only (WS1-01). ``stub=True`` returns realistic synthetic
records labelled as such; non-stub calls return an explicit not-implemented
incomplete envelope until WS1-02/WS1-03 land. No stub ever reports PASS.
"""

from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = 1

READINESS_FORMULA = "max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)"

# Resource types with a known template mapping (contracts.md, translated IaC section).
SUPPORTED_RESOURCE_TYPES = frozenset({"aws_instance", "aws_security_group", "aws_s3_bucket"})

# S3 operations the S3-compatible target is expected to serve; anything else counts as unsupported.
SUPPORTED_S3_OPERATIONS = frozenset(
    {
        "put_object",
        "get_object",
        "list_objects_v2",
        "head_object",
        "delete_object",
        "create_multipart_upload",
        "upload_part",
        "complete_multipart_upload",
        "generate_presigned_url",
    }
)

DATA_MAP_KEYS = ("resources", "calls", "buckets", "readiness")
CHOICE_KEYS = (
    "target_id",
    "operator",
    "jurisdiction",
    "storage_mode",
    "criteria",
    "prices",
    "explanation",
)


def _envelope(step: str, mode: str, status: str, checks: list, data: dict, errors: list) -> dict:
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


def compute_readiness(resources: list[dict], calls: list[dict]) -> dict:
    """Deterministic readiness score v1 (no AI).

    proprietary: resources whose type has no supported mapping.
    unsupported: distinct S3 calls using an operation outside the supported set.
    us_calls: distinct non-S3 calls to AWS-operated services (e.g. telemetry).
    Calls are deduplicated by (file, line, service, operation).
    """
    seen: set[tuple] = set()
    unique_calls = []
    for call in calls:
        key = (call["file"], call["line"], call["service"], call["operation"])
        if key not in seen:
            seen.add(key)
            unique_calls.append(call)

    proprietary = sum(1 for r in resources if not r["supported"])
    unsupported = sum(
        1
        for c in unique_calls
        if c["service"] == "s3" and c["operation"] not in SUPPORTED_S3_OPERATIONS
    )
    us_calls = sum(1 for c in unique_calls if c["service"] != "s3")
    score = max(0, 100 - 20 * proprietary - 10 * unsupported - 5 * us_calls)
    return {
        "score": score,
        "formula": READINESS_FORMULA,
        "proprietary": proprietary,
        "unsupported": unsupported,
        "us_calls": us_calls,
    }


def _stub_data_map(workload: Path) -> dict:
    app_file = (workload / "app.py").as_posix()
    resources = [
        {"id": "aws_instance.app", "type": "aws_instance", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_security_group.app", "type": "aws_security_group", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_s3_bucket.demo", "type": "aws_s3_bucket", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_cloudwatch_metric_alarm.app_errors", "type": "aws_cloudwatch_metric_alarm",
         "provider": "aws", "region": "eu-central-1", "synthetic": True},
    ]
    for resource in resources:
        resource["supported"] = resource["type"] in SUPPORTED_RESOURCE_TYPES

    calls = [
        {"file": app_file, "line": 18, "service": "s3", "operation": "put_object",
         "bucket": "demo", "endpoint_host": None},
        {"file": app_file, "line": 24, "service": "s3", "operation": "get_object",
         "bucket": "demo", "endpoint_host": None},
        {"file": app_file, "line": 31, "service": "s3", "operation": "list_objects_v2",
         "bucket": "demo", "endpoint_host": None},
        # Visible telemetry dependency on an AWS-operated endpoint (severance target in WS3).
        {"file": app_file, "line": 40, "service": "cloudwatch", "operation": "put_metric_data",
         "bucket": None, "endpoint_host": "monitoring.eu-central-1.amazonaws.com",
         "dependency": "telemetry"},
    ]
    buckets = [
        {"name": "demo", "provider": "aws", "jurisdiction": "US-controlled",
         "object_count": 12, "total_bytes": 48213, "synthetic": True},
    ]
    return {
        "resources": resources,
        "calls": calls,
        "buckets": buckets,
        "readiness": compute_readiness(resources, calls),
    }


def discover(workload: Path, *, config: dict, stub: bool = False) -> dict:
    """Return a discover envelope whose data is the data map."""
    if not isinstance(workload, (Path, str)):
        raise ValueError("workload must be a path")
    _check_config(config)
    workload = Path(workload)

    if stub:
        data = _stub_data_map(workload)
        checks = [
            {"id": "inventory_parsed", "status": "incomplete",
             "detail": "synthetic stub; workload IaC not parsed, no VM validation"},
            {"id": "calls_scanned", "status": "incomplete",
             "detail": "synthetic stub; application source not scanned"},
            {"id": "bucket_inventory", "status": "incomplete",
             "detail": "synthetic stub; counts are synthetic, no source bucket listed"},
            {"id": "telemetry_dependency_visible", "status": "incomplete",
             "detail": "synthetic telemetry call to monitoring.eu-central-1.amazonaws.com listed"},
        ]
        return _envelope("discover", "stub", "incomplete", checks, data, [])

    data = {
        "resources": [],
        "calls": [],
        "buckets": [],
        "readiness": {"score": None, "formula": READINESS_FORMULA,
                      "proprietary": None, "unsupported": None, "us_calls": None},
    }
    checks = [{"id": "inventory_parsed", "status": "incomplete",
               "detail": "live discovery not implemented yet (WS1-02); inventory unknown"}]
    return _envelope("discover", "live", "incomplete", checks, data,
                     ["live discovery not implemented; inventory unknown, not empty"])


def _require_keys(obj: object, keys: tuple, name: str) -> None:
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be the preceding envelope's data dict")
    if "schema_version" in obj and "data" in obj:
        raise ValueError(f"{name} must be the envelope's data object, not the envelope")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"{name} missing required keys: {', '.join(missing)}")


def choose(data_map: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a choose envelope selecting a Leaseweb deployment option."""
    _require_keys(data_map, DATA_MAP_KEYS, "data_map")
    _check_config(config)

    if stub:
        data = {
            "target_id": "leaseweb-selfhosted",
            "operator": "Leaseweb",
            "jurisdiction": "EU",
            # No native storage verified accessible (human gate NOT RUN) -> self-hosted S3.
            "storage_mode": "self_hosted_s3",
            "criteria": [
                {"name": "operator_jurisdiction", "value": "EU",
                 "source_url": "https://www.leaseweb.com/", "synthetic": True},
                {"name": "provider_availability", "value": None, "source_url": None,
                 "assumptions": "human VM gate not run; provider mode unapproved"},
                {"name": "native_storage_verified", "value": False, "source_url": None,
                 "assumptions": "not verified accessible; falls back to self-hosted S3"},
            ],
            "prices": [
                {"item": "compute", "amount": None, "currency": "EUR", "unit": "hour",
                 "source_url": None, "assumptions": "not verified"},
                {"item": "storage", "amount": None, "currency": "EUR", "unit": "GB-month",
                 "source_url": None, "assumptions": "not verified"},
            ],
            "explanation": {
                "mode": "replay",
                "text": "SYNTHETIC STUB, no model call: only Leaseweb options are considered; "
                        "native storage is unverified, so self-hosted S3 on Leaseweb compute is "
                        "selected. Prices are unknown and left null.",
            },
            "open_items": ["prices unverified", "provider mode awaits human VM gate"],
        }
        checks = [
            {"id": "provider_availability", "status": "incomplete",
             "detail": "synthetic stub; human-approved provider availability not recorded"},
            {"id": "prices_cited", "status": "incomplete",
             "detail": "prices null; no cited public source"},
        ]
        return _envelope("choose", "stub", "incomplete", checks, data, [])

    data = {
        "target_id": None,
        "operator": "Leaseweb",
        "jurisdiction": None,
        "storage_mode": None,
        "criteria": [],
        "prices": [],
        "explanation": {"mode": "replay", "text": "not generated: live choice not implemented"},
    }
    checks = [{"id": "provider_availability", "status": "incomplete",
               "detail": "live choice not implemented yet (WS1-03)"}]
    return _envelope("choose", "live", "incomplete", checks, data,
                     ["live target choice not implemented"])
