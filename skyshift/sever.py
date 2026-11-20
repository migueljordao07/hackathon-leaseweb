"""Severance test: deny hyperscaler egress, detect bypasses, retry with replacements (WS3).

Contract: tasks/contracts.md (Python API ``sever``, shared envelope, severance).
The proxy enforces; the socket radar only detects; the model never decides a
verdict. Standard library only. Importing this module performs no I/O, network,
socket or process activity.

Current state: offline stub (WS3-01). ``stub=True`` returns a realistic
synthetic red -> config-only fix -> retry history labelled ``mode: stub`` with
overall ``status: incomplete``. Synthetic events use RFC 5737 documentation
addresses. Non-stub calls return an explicit not-implemented incomplete
envelope until WS3-02..WS3-05 land; no proxy or radar is started. No stub ever
reports PASS or a ``green`` final.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS_PATH = REPO_ROOT / "skyshift" / "catalogue" / "replacements.yaml"

SEVER_DATA_KEYS = ("attempts", "max_attempts", "final", "radar_scope")
FINAL_STATES = ("green", "blocked", "incomplete")
RADAR_SCOPE = "socket detection only; proxy enforces requests using it"


def _envelope(mode: str, status: str, checks: list, data: dict, errors: list) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "step": "sever",
        "mode": mode,
        "status": status,
        "checks": checks,
        "data": data,
        "errors": errors,
    }


def _validate_inputs(data_map, target, config, max_attempts) -> None:
    if not isinstance(data_map, dict):
        raise ValueError("data_map must be the discover envelope's data dict")
    if not isinstance(target, dict):
        raise ValueError("target must be the choose envelope's data dict")
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")


def _load_replacement(replacement_id: str) -> dict | None:
    """Read one replacement catalogue entry (JSON-subset YAML). Called only at run time."""
    try:
        with REPLACEMENTS_PATH.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    for entry in doc.get("replacements", []):
        if isinstance(entry, dict) and entry.get("id") == replacement_id:
            return entry
    return None


def _telemetry_hosts(data_map: dict) -> list[str]:
    """Hosts of non-S3 calls in the data map (e.g. telemetry), for a realistic stub."""
    hosts = []
    for call in data_map.get("calls", []) or []:
        if isinstance(call, dict) and call.get("service") not in (None, "s3") and call.get("endpoint_host"):
            hosts.append(str(call["endpoint_host"]))
    return hosts


def _stub_record(data_map: dict, max_attempts: int) -> dict:
    host = (_telemetry_hosts(data_map) or ["monitoring.amazonaws.com"])[0]
    replacement = _load_replacement("local-otel")
    applied_keys = list(replacement.get("applied_config_keys", [])) if replacement else []

    attempts = [
        {
            "number": 1,
            "events": [
                {
                    "host": host,
                    "ip": "192.0.2.10",
                    "port": 443,
                    "decision": "deny",
                    "reason": "published cloud range (synthetic fixture)",
                    "via": "proxy",
                }
            ],
            "blocked": 1,
            "bypasses": [],
            "replacement": None,
            "status": "incomplete",
        }
    ]
    if max_attempts >= 2:
        attempts.append(
            {
                "number": 2,
                "events": [
                    {
                        "host": "127.0.0.1",
                        "ip": "127.0.0.1",
                        "port": 4318,
                        "decision": "allow",
                        "reason": "approved local replacement (synthetic)",
                        "via": "proxy",
                    }
                ],
                "blocked": 0,
                "bypasses": [],
                "replacement": {
                    "id": "local-otel",
                    "mode": "replay",
                    "applied_config_keys": applied_keys,
                },
                "status": "incomplete",
            }
        )

    checks = [
        {
            "id": "proxy_denies_cloud_egress",
            "status": "incomplete",
            "detail": "synthetic stub; no proxy started, no VM validation",
        },
        {
            "id": "radar_bypass_detection",
            "status": "incomplete",
            "detail": "synthetic stub; no socket inspection performed",
        },
        {
            "id": "config_only_replacement_retry",
            "status": "incomplete",
            "detail": "synthetic stub; app not run, replacement not applied",
        },
    ]
    data = {
        "attempts": attempts,
        "max_attempts": max_attempts,
        "final": "incomplete",
        "radar_scope": RADAR_SCOPE,
    }
    errors = [] if replacement else ["replacement catalogue entry 'local-otel' unavailable"]
    return _envelope("stub", "incomplete", checks, data, errors)


def sever(data_map: dict, target: dict, *, config: dict, max_attempts: int = 2, stub: bool = False) -> dict:
    """Return the severance envelope.

    ``data_map`` and ``target`` are the ``data`` objects of the discover and
    choose envelopes. Secrets in ``config`` are never read into the record.
    """
    _validate_inputs(data_map, target, config, max_attempts)
    if stub:
        return _stub_record(data_map, max_attempts)

    checks = [
        {
            "id": "proxy_denies_cloud_egress",
            "status": "incomplete",
            "detail": "not implemented (WS3-03); no proxy started",
        },
        {
            "id": "radar_bypass_detection",
            "status": "incomplete",
            "detail": "not implemented (WS3-04); no socket inspection performed",
        },
        {
            "id": "config_only_replacement_retry",
            "status": "incomplete",
            "detail": "not implemented (WS3-05); no retry attempted",
        },
    ]
    data = {"attempts": [], "max_attempts": max_attempts, "final": "incomplete", "radar_scope": RADAR_SCOPE}
    return _envelope("live", "incomplete", checks, data, ["live severance not implemented yet; nothing was measured"])
