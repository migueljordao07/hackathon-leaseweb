"""Single schema-constrained model client for SkyShift (WS3).

Contract: tasks/contracts.md (Python API ``complete``). The model drafts
explanations and proposals only; it never decides PASS/FAIL verdicts, costs or
hashes. Standard library only. Importing this module performs no I/O, network
or process activity.

Current state: offline stub (WS3-01). Every call answers from the labelled
replay fixture ``fixtures/llm/replay.json`` and reports ``status: incomplete``.
No model request is ever sent: a call with ``replay=False`` is served from the
same fixture with an explicit error saying the live client is not implemented
(WS3-06). Replay output is never presented as a model call.
"""

from __future__ import annotations

import json
from pathlib import Path

REPLAY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm" / "replay.json"

COMPLETION_KEYS = ("mode", "status", "data", "errors")

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, expected) -> bool:
    if isinstance(expected, list):
        return any(_type_ok(value, item) for item in expected)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    py_type = _JSON_TYPES.get(expected)
    return True if py_type is None else isinstance(value, py_type)


def validate(value, schema: dict, path: str = "$") -> list[str]:
    """Validate ``value`` against a small JSON Schema subset.

    Supported keywords: type, required, properties, additionalProperties (false),
    items, enum, minLength, maxLength, minItems, maxItems. Returns a list of
    sanitized error strings; empty means valid. WS3-07 may extend this subset.
    """
    if not isinstance(schema, dict):
        raise ValueError("schema must be a dict")
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None and not _type_ok(value, expected):
        return [f"{path}: expected type {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string too long")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}: unexpected key {key!r}")
        for key, sub in props.items():
            if key in value:
                errors.extend(validate(value[key], sub, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate(item, schema["items"], f"{path}[{index}]"))
    return errors


def _load_replay(fixture: Path) -> dict:
    with fixture.open("r", encoding="utf-8") as handle:
        doc = json.load(handle)
    responses = doc.get("responses")
    if not isinstance(responses, dict):
        raise ValueError("replay fixture has no 'responses' object")
    return responses


def complete(task: str, payload: dict, schema: dict, *, config: dict, replay: bool = False) -> dict:
    """Return a schema-validated completion envelope (offline stub).

    Always ``mode: replay`` and ``status: incomplete`` in WS3-01: the data comes
    from a synthetic cached fixture, not a model. ``payload`` and ``config`` are
    accepted for signature compatibility but never sent anywhere or echoed back.
    """
    if not isinstance(task, str) or not task:
        raise ValueError("task must be a non-empty string")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if not isinstance(schema, dict):
        raise ValueError("schema must be a dict")
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")

    errors: list[str] = ["replay stub: synthetic cached response, no model call was made"]
    if not replay:
        errors.append("live model client not implemented (WS3-06); served labelled replay instead")

    try:
        responses = _load_replay(REPLAY_FIXTURE)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"replay fixture unavailable: {type(exc).__name__}")
        return {"mode": "replay", "status": "incomplete", "data": {}, "errors": errors}

    entry = responses.get(task)
    if entry is None:
        errors.append(f"no replay entry for task {task!r}")
        return {"mode": "replay", "status": "incomplete", "data": {}, "errors": errors}

    data = entry.get("data") if isinstance(entry, dict) else None
    schema_errors = validate(data, schema)
    if schema_errors:
        errors.append("replay data failed schema validation")
        errors.extend(schema_errors[:10])
        return {"mode": "replay", "status": "incomplete", "data": {}, "errors": errors}

    return {"mode": "replay", "status": "incomplete", "data": data, "errors": errors}
