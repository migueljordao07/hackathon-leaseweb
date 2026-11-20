"""S3-to-S3 object migration and per-object SHA-256 verification (WS2).

Contract: tasks/contracts.md (Python API, shared envelope, Migration section).
Standard library only. Importing this module performs no I/O, network, process,
or client creation side effects.

Current state: offline contract stub (WS2-01). ``stub=True`` returns a
deterministic synthetic migration record marked ``mode="stub"`` and
``status="incomplete"``. Non-stub calls return an explicit not-implemented
incomplete envelope until WS2-03 lands. No stub ever reports PASS.
"""

from __future__ import annotations

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

    data = {
        "objects": [],
        "source_count": 0,
        "target_count": 0,
        "matched": 0,
        "missing": 0,
        "different": 0,
        "extra": 0,
    }
    checks = [
        {
            "id": "rclone_copy",
            "status": "incomplete",
            "detail": "live migration not implemented yet (WS2-03); no source or target measured",
        }
    ]
    return _envelope(
        "migrate",
        "live",
        "incomplete",
        checks,
        data,
        ["live migration not implemented (WS2-03)"],
    )
