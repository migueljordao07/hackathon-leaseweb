"""Single schema-constrained model client for SkyShift (WS3).

Contract: tasks/contracts.md (Python API ``complete``). The model drafts
explanations and proposals only; it never decides PASS/FAIL verdicts, costs or
hashes. Standard library only. Importing this module performs no I/O, network
or process activity.

One provider-neutral route: an OpenAI-compatible ``/chat/completions``
endpoint configured by SKYSHIFT_LLM_BASE_URL, SKYSHIFT_LLM_API_KEY and
SKYSHIFT_LLM_MODEL (WS3-06). Every payload is sanitized locally *before* any
request is built: secret-like keys and values, configuration values, URL query
strings (signed URLs), credential patterns and non-global IP addresses are
redacted. Replay answers come from ``fixtures/llm/replay.json``, are always
labelled ``mode: replay`` and ``status: incomplete``, and never masquerade as a
model call. Missing credentials, transport failure, timeout, malformed output,
schema failure or sanitizer rejection all yield ``status: incomplete``.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

REPLAY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "llm" / "replay.json"

COMPLETION_KEYS = ("mode", "status", "data", "errors")
LIVE_KEYS = ("SKYSHIFT_LLM_BASE_URL", "SKYSHIFT_LLM_API_KEY", "SKYSHIFT_LLM_MODEL")
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_TRANSPORT_ATTEMPTS = 2
MAX_PAYLOAD_BYTES = 32 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
REDACTED = "[REDACTED]"

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}

_SENSITIVE_KEY = re.compile(
    r"(secret|passw|token|api[_-]?key|access[_-]?key|credential|authori[sz]ation|cookie|session|private[_-]?key|signature)",
    re.IGNORECASE,
)
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\b[A-Za-z0-9+/]{40}\b"),  # AWS secret access key shape
]
_ENV_ASSIGNMENT = re.compile(r"\b([A-Z][A-Z0-9_]{2,})=(\S+)")
_URL = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s\"'<>]+")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IPV6 = re.compile(r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![0-9A-Fa-f:])")


# --------------------------------------------------------------------------
# Schema validation
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Local sanitization (runs before any request is constructed)
# --------------------------------------------------------------------------

def _private_ip(text: str) -> bool:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    return not ip.is_global


def _strip_url(match: re.Match) -> str:
    url = match.group(0)
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        return REDACTED
    if parts.username or parts.password:
        url = url.replace(parts.netloc, parts.netloc.rsplit("@", 1)[-1])
    if parts.query or parts.fragment:
        url = url.split("?", 1)[0].split("#", 1)[0] + "?" + REDACTED
    if host and _private_ip(host.strip("[]")):
        url = url.replace(host, "[PRIVATE-IP]")
    return url


def _sanitize_text(text: str, secrets: list[str], report: set) -> str:
    original = text
    for secret in secrets:
        if secret in text:
            text = text.replace(secret, REDACTED)
            report.add("config-value")
    for pattern in _SECRET_PATTERNS:
        text, count = pattern.subn(REDACTED, text)
        if count:
            report.add("credential-pattern")
    text, count = _ENV_ASSIGNMENT.subn(lambda m: f"{m.group(1)}={REDACTED}", text)
    if count:
        report.add("env-assignment")
    before_urls = text
    text = _URL.sub(_strip_url, text)
    if text != before_urls:
        report.add("url-query-or-userinfo")

    def private(match: re.Match) -> str:
        if _private_ip(match.group(0)):
            report.add("private-address")
            return "[PRIVATE-IP]"
        return match.group(0)

    for pattern in (_IPV4, _IPV6):
        text = pattern.sub(private, text)
    if "[PRIVATE-IP]" in text and "[PRIVATE-IP]" not in original:
        report.add("private-address")
    return text


def sanitize(payload, config: dict | None = None) -> tuple[object, list[str]]:
    """Return a redacted deep copy of ``payload`` and the categories redacted.

    Deterministic and local. Configuration values (length >= 4) are treated as
    secrets wherever they appear; keys that look sensitive have their values
    replaced entirely.
    """
    secrets = sorted({str(v) for v in (config or {}).values() if isinstance(v, str) and len(v) >= 4},
                     key=len, reverse=True)
    report: set = set()

    def walk(value, depth=0):
        if depth > 20:
            report.add("depth-limit")
            return REDACTED
        if isinstance(value, dict):
            clean = {}
            for key, item in value.items():
                safe_key = _sanitize_text(str(key), secrets, report)
                if _SENSITIVE_KEY.search(str(key)):
                    clean[safe_key] = REDACTED
                    report.add("sensitive-key")
                else:
                    clean[safe_key] = walk(item, depth + 1)
            return clean
        if isinstance(value, (list, tuple)):
            return [walk(item, depth + 1) for item in value]
        if isinstance(value, str):
            return _sanitize_text(value, secrets, report)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        report.add("unsupported-type")
        return REDACTED

    return walk(payload), sorted(report)


# --------------------------------------------------------------------------
# Replay and live transport
# --------------------------------------------------------------------------

def _load_replay(fixture: Path) -> dict:
    with fixture.open("r", encoding="utf-8") as handle:
        doc = json.load(handle)
    responses = doc.get("responses")
    if not isinstance(responses, dict):
        raise ValueError("replay fixture has no 'responses' object")
    return responses


def _replay(task: str, schema: dict, errors: list[str]) -> dict:
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


def _endpoint(base_url: str) -> str:
    parts = urlsplit(base_url.strip())
    host = parts.hostname or ""
    loopback = host in ("localhost",) or (host and not _is_hostname(host) and ipaddress.ip_address(host).is_loopback)
    if parts.scheme != "https" and not (parts.scheme == "http" and loopback):
        raise ValueError("LLM base URL must use https (plain http only for loopback)")
    if parts.query or parts.username or parts.password:
        raise ValueError("LLM base URL must not carry credentials or query strings")
    return base_url.rstrip("/") + "/chat/completions"


def _is_hostname(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return True
    return False


def _transport(url: str, headers: dict, body: bytes, timeout: float) -> bytes:
    """Single HTTP POST adapter (urllib). Tests replace this; never runs at import."""
    import urllib.request

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - scheme checked
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("response exceeds size bound")
    return raw


def _parse_model_json(raw: bytes):
    doc = json.loads(raw.decode("utf-8"))
    content = doc["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("model content is not text")
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):] if "{" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def _live(task: str, clean_payload, schema: dict, config: dict, errors: list[str]) -> dict | None:
    """Attempt one bounded live completion. Returns an envelope, or None to fall back to replay."""
    missing = [k for k in LIVE_KEYS if not (isinstance(config.get(k), str) and config.get(k))]
    if missing:
        errors.append("live model credentials/configuration unavailable: " + ", ".join(missing)
                      + "; no model call was made")
        return None
    try:
        url = _endpoint(config["SKYSHIFT_LLM_BASE_URL"])
    except ValueError as exc:
        errors.append(f"live model endpoint rejected: {exc}")
        return None
    instructions = (
        "You draft explanations for an infrastructure exit tool. You never decide pass/fail verdicts, "
        "costs or hashes. Reply with exactly one JSON object that validates against this JSON Schema: "
        + json.dumps(schema, sort_keys=True)
    )
    body = json.dumps({
        "model": config["SKYSHIFT_LLM_MODEL"],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps({"task": task, "payload": clean_payload}, sort_keys=True)},
        ],
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + config["SKYSHIFT_LLM_API_KEY"]}
    raw = None
    for _attempt in range(MAX_TRANSPORT_ATTEMPTS):
        try:
            raw = _transport(url, headers, body, REQUEST_TIMEOUT_SECONDS)
            break
        except Exception as exc:  # noqa: BLE001 - transport errors are reported by type only
            errors.append(f"live model transport failed: {type(exc).__name__}")
    if raw is None:
        return None
    try:
        data = _parse_model_json(raw)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"live model output malformed: {type(exc).__name__}")
        return {"mode": "live", "status": "incomplete", "data": {}, "errors": errors}
    schema_errors = validate(data, schema)
    if schema_errors:
        errors.append("live model output failed schema validation")
        errors.extend(schema_errors[:10])
        return {"mode": "live", "status": "incomplete", "data": {}, "errors": errors}
    return {"mode": "live", "status": "ok", "data": data, "errors": errors}


def _replay_requested(config: dict) -> bool:
    return str(config.get("SKYSHIFT_LLM_REPLAY", "")).strip().lower() in ("1", "true", "yes", "on")


def complete(task: str, payload: dict, schema: dict, *, config: dict, replay: bool = False) -> dict:
    """Return ``{"mode","status","data","errors"}``; data validates against ``schema`` or is empty.

    Replay (explicit, SKYSHIFT_LLM_REPLAY, or fallback after a failed live
    attempt) is always ``mode: replay`` / ``status: incomplete``. Only a live
    response that parses and validates is ``status: ok``. Error strings never
    contain payload or credential material.
    """
    if not isinstance(task, str) or not task:
        raise ValueError("task must be a non-empty string")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if not isinstance(schema, dict):
        raise ValueError("schema must be a dict")
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")

    errors: list[str] = []
    if replay or _replay_requested(config):
        errors.append("replay stub: synthetic cached response, no model call was made")
        return _replay(task, schema, errors)

    clean, redactions = sanitize(payload, config)
    encoded = json.dumps(clean, sort_keys=True)
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        errors.append("sanitizer rejected payload: exceeds size bound; no model call was made")
        return _replay(task, schema, errors)
    if redactions:
        errors.append("sanitizer redacted: " + ", ".join(redactions))

    result = _live(task, clean, schema, config, errors)
    if result is not None:
        return result
    errors.append("served labelled replay instead; no live model response was used")
    return _replay(task, schema, errors)
