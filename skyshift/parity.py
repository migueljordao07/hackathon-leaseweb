"""Unchanged-application runner and Moto-vs-target parity suite (WS2).

Contract: tasks/contracts.md (Python API, shared envelope, Run and Parity sections).
Standard library only. Importing this module performs no I/O, network, process,
or client creation side effects.

Current state: offline contract stubs (WS2-01). ``stub=True`` returns
deterministic synthetic ``run`` and ``parity`` records marked ``mode="stub"``
and ``status="incomplete"``. Non-stub calls return explicit not-implemented
incomplete envelopes until WS2-04/WS2-05 land. No stub ever reports PASS.
"""

from __future__ import annotations

from pathlib import Path

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

REQUIRED_PARITY_OPERATIONS = ("put_object", "get_object", "list_objects_v2")

# Deterministic 64-character lowercase hex placeholder (synthetic, not measured).
_STUB_APP_SHA256 = "b2c3d4e5" * 8


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


def run_app(workload: Path, target: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a run envelope recording unchanged-app execution against the target.

    ``target`` is the preceding ``choose`` envelope ``data`` object.
    Does not mutate inputs, read credentials, start processes, or write files.
    """
    if not isinstance(workload, (Path, str)):
        raise ValueError("workload must be a pathlib.Path or str")
    _require_data_object(target, TARGET_KEYS, "target")
    _check_config(config)
    _ = Path(workload)

    target_identity = str(target.get("target_id") or "leaseweb-selfhosted")

    if stub:
        data = {
            "app_sha256_before": _STUB_APP_SHA256,
            "app_sha256_after": _STUB_APP_SHA256,
            "endpoint_changed": {
                "changed": True,
                "config_only": True,
                "env_var": "AWS_ENDPOINT_URL",
                "source_identity": "synthetic-aws-s3",
                "target_identity": target_identity,
                "synthetic": True,
            },
            "functional_checks": [
                {
                    "operation": op,
                    "status": "incomplete",
                    "detail": f"synthetic stub; application did not run {op} against any endpoint",
                }
                for op in REQUIRED_PARITY_OPERATIONS
            ],
            "host_network": {
                "status": "incomplete",
                "public_ip": None,
                "network_owner": None,
                "provenance": None,
                "observed_at": None,
                "detail": "synthetic stub; host network was not observed on a VM",
            },
        }
        checks = [
            {
                "id": "app_unchanged_sha256",
                "status": "incomplete",
                "detail": "synthetic stub; placeholder before/after app hashes only, file not executed",
            },
            {
                "id": "app_functional_checks",
                "status": "incomplete",
                "detail": "synthetic stub; fixture application was not executed on any target",
            },
            {
                "id": "host_network_observation",
                "status": "incomplete",
                "detail": "synthetic stub; host network not measured on an approved VM",
            },
        ]
        return _envelope("run", "stub", "incomplete", checks, data, [])

    data = {
        "app_sha256_before": None,
        "app_sha256_after": None,
        "endpoint_changed": {
            "changed": False,
            "config_only": True,
            "env_var": "AWS_ENDPOINT_URL",
            "source_identity": None,
            "target_identity": target_identity,
        },
        "functional_checks": [],
        "host_network": {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": None,
            "observed_at": None,
            "detail": "live unchanged-app runner not implemented yet (WS2-04)",
        },
    }
    checks = [
        {
            "id": "app_functional_checks",
            "status": "incomplete",
            "detail": "live unchanged-app runner not implemented yet (WS2-04); no process executed",
        }
    ]
    return _envelope(
        "run",
        "live",
        "incomplete",
        checks,
        data,
        ["live unchanged-app runner not implemented (WS2-04)"],
    )


def verify(data_map: dict, target: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a parity envelope comparing Moto before versus target after.

    Inputs are the preceding ``discover`` and ``choose`` envelope ``data`` objects.
    Does not mutate inputs, read credentials, start processes, or write files.
    """
    _require_data_object(data_map, DATA_MAP_KEYS, "data_map")
    _require_data_object(target, TARGET_KEYS, "target")
    _check_config(config)

    if stub:
        operations = [
            {
                "operation": op,
                "before": {
                    "status": "incomplete",
                    "detail": f"synthetic stub; Moto baseline did not execute {op}",
                },
                "after": {
                    "status": "incomplete",
                    "detail": f"synthetic stub; target endpoint did not execute {op}",
                },
                "equal": False,
                "synthetic": True,
            }
            for op in REQUIRED_PARITY_OPERATIONS
        ]
        data = {
            "operations": operations,
            "selection": {
                "source": "stub_required",
                "operations": list(REQUIRED_PARITY_OPERATIONS),
                "ai_mode": "replay",
                "synthetic": True,
                "detail": "synthetic stub selection; no Moto baseline or target parity measured",
            },
        }
        checks = [
            {
                "id": "parity_suite",
                "status": "incomplete",
                "detail": "synthetic stub; Moto baseline and target endpoint were not executed",
            },
            {
                "id": "parity_operations_equal",
                "status": "incomplete",
                "detail": "synthetic stub; equal is false until both Moto and target are measured",
            },
        ]
        return _envelope("parity", "stub", "incomplete", checks, data, [])

    data = {
        "operations": [],
        "selection": {
            "source": "unimplemented",
            "operations": [],
            "ai_mode": "replay",
            "detail": "live parity suite not implemented yet (WS2-05)",
        },
    }
    checks = [
        {
            "id": "parity_suite",
            "status": "incomplete",
            "detail": "live parity verification not implemented yet (WS2-05); no Moto or target run",
        }
    ]
    return _envelope(
        "parity",
        "live",
        "incomplete",
        checks,
        data,
        ["live parity verification not implemented (WS2-05)"],
    )
