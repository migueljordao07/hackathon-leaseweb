"""Unchanged-application runner and Moto-vs-target parity suite (WS2).

Contract: tasks/contracts.md (Python API, shared envelope, Run and Parity sections).
Standard library only at import time. Importing this module performs no I/O,
network, process, or client creation side effects (subprocess, socket, boto3,
and optional helpers are imported lazily inside live execution paths).

``stub=True`` returns deterministic synthetic ``run`` and ``parity`` records
marked ``mode="stub"`` and ``status="incomplete"``. No stub ever reports PASS.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

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
KNOWN_PARITY_OPERATIONS = (
    "put_object",
    "get_object",
    "list_objects_v2",
    "head_object",
    "multipart_upload",
    "presigned_url",
    "delete_object",
)
PARITY_SELECTION_SCHEMA = {
    "type": "object",
    "required": ["operations"],
    "additionalProperties": False,
    "properties": {
        "operations": {
            "type": "array",
            "minItems": 1,
            "maxItems": 10,
            "items": {"type": "string", "enum": list(KNOWN_PARITY_OPERATIONS)},
        }
    },
}
_AST_OP_MAP = {
    "put_object": "put_object",
    "get_object": "get_object",
    "list_objects_v2": "list_objects_v2",
    "list_objects": "list_objects_v2",
    "head_object": "head_object",
    "delete_object": "delete_object",
    "create_multipart_upload": "multipart_upload",
    "upload_part": "multipart_upload",
    "complete_multipart_upload": "multipart_upload",
    "abort_multipart_upload": "multipart_upload",
    "multipart_upload": "multipart_upload",
    "generate_presigned_url": "presigned_url",
    "presigned_url": "presigned_url",
}
_PARITY_SMOKE_PAYLOAD = b'{"parity":"skyshift","synthetic":true,"version":1}'
_PARITY_MULTIPART_RECORDS = 1024
_PARITY_STREAM_CHUNK = 16384
_PARITY_HTTP_TIMEOUT = 10.0

# Deterministic 64-character lowercase hex placeholder (synthetic, not measured).
_STUB_APP_SHA256 = "b2c3d4e5" * 8

HASH_CHUNK_BYTES = 64 * 1024
DEFAULT_APP_TIMEOUT_SECONDS = 45.0
DEFAULT_TERMINATE_GRACE_SECONDS = 2.0
MAX_TEXT_CHARS = 300
REDACTED = "[REDACTED]"

SECRET_ENV_NAMES = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "SKYSHIFT_SOURCE_ACCESS_KEY_ID",
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY",
    "SKYSHIFT_TARGET_ACCESS_KEY_ID",
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY",
    "SKYSHIFT_LLM_API_KEY",
    "OS_APPLICATION_CREDENTIAL_ID",
    "OS_APPLICATION_CREDENTIAL_SECRET",
    "LEASEWEB_API_KEY",
)
MIN_SECRET_LENGTH = 8

_PASSTHROUGH_OS_ENV = (
    "PATH",
    "HOME",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "PATHEXT",
    "PYTHONHOME",
    "VIRTUAL_ENV",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
)
_PROXY_AND_TELEMETRY_KEYS = (
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "NO_PROXY",
    "SKYSHIFT_TELEMETRY_ENDPOINT",
)

_URL_USERINFO_RE = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
_URL_QUERY_RE = re.compile(r"(?i)(\bhttps?://[^\s?#'\"<>]*)\?[^\s'\"<>]*")
_SIGNED_PARAM_RE = re.compile(r"(?i)\b(X-Amz-[A-Za-z-]+|Signature|AWSAccessKeyId)=[^\s&'\"<>]+")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _nonempty_str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _secret_values(config: dict) -> list[str]:
    values = {config.get(name) for name in SECRET_ENV_NAMES}
    return sorted(
        (v for v in values if isinstance(v, str) and len(v) >= MIN_SECRET_LENGTH),
        key=len,
        reverse=True,
    )


def _sanitize_text(text: str, config: dict) -> str:
    """Redact configured secrets, URL userinfo, and signed URL query strings."""
    out = str(text)
    for value in _secret_values(config):
        out = out.replace(value, REDACTED)
    out = _URL_USERINFO_RE.sub(rf"\1{REDACTED}@", out)
    out = _URL_QUERY_RE.sub(rf"\1?{REDACTED}", out)
    out = _SIGNED_PARAM_RE.sub(rf"\1={REDACTED}", out)
    out = " ".join(out.split())
    return out if len(out) <= MAX_TEXT_CHARS else out[: MAX_TEXT_CHARS - 3] + "..."


def _sanitize_endpoint_host(url: str | None) -> str | None:
    """Return lowercase host[:port] without scheme, userinfo, path, or query."""
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if not parts.hostname:
        return None
    host = parts.hostname.lower()
    if parts.port is not None:
        return f"{host}:{parts.port}"
    return host


def _sha256_file(path: Path) -> str | None:
    """Stream a file through SHA-256 in fixed chunks; return None on read error."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(HASH_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _resolve_app_path(workload: Path) -> Path:
    path = Path(workload)
    if path.is_file():
        return path.resolve()
    return (path / "app.py").resolve()


def _build_child_env(
    config: dict,
    *,
    target_endpoint: str,
    target_access: str,
    target_secret: str,
    target_bucket: str,
    base_environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Construct a minimal child environment using contract env names only."""
    source_env = os.environ if base_environ is None else base_environ
    child: dict[str, str] = {
        key: source_env[key]
        for key in _PASSTHROUGH_OS_ENV
        if key in source_env and isinstance(source_env[key], str)
    }
    child["AWS_ENDPOINT_URL"] = target_endpoint
    child["AWS_ACCESS_KEY_ID"] = target_access
    child["AWS_SECRET_ACCESS_KEY"] = target_secret
    child["AWS_DEFAULT_REGION"] = _nonempty_str(config.get("AWS_DEFAULT_REGION")) or "eu-central-1"
    child["SKYSHIFT_TARGET_BUCKET"] = target_bucket

    for key in _PROXY_AND_TELEMETRY_KEYS:
        value = config.get(key)
        if key == "NO_PROXY":
            if isinstance(value, str):
                child[key] = value
        elif isinstance(value, str) and value.strip():
            child[key] = value.strip()

    return child


def _is_loopback_host(hostname: str) -> bool:
    low = hostname.strip().lower().strip("[]")
    if low in ("localhost", "localhost.localdomain"):
        return True
    try:
        return ipaddress.ip_address(low).is_loopback
    except ValueError:
        return False


def _observe_host_network(target_endpoint: str, target: dict, config: dict) -> dict[str, Any]:
    """Gather a bounded, zero-secret host-network observation with explicit scope.

    Under an active egress proxy or against a loopback endpoint, stays
    ``incomplete`` and makes no external network calls.
    """
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    proxy_active = bool(
        _nonempty_str(config.get("HTTPS_PROXY")) or _nonempty_str(config.get("HTTP_PROXY"))
    )
    if proxy_active:
        return {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": "skipped_under_proxy",
            "observed_at": observed_at,
            "target_endpoint_class": "proxied",
            "limitations": "skipped direct DNS/route observation while egress proxy is active",
            "detail": "host network probe skipped while HTTPS_PROXY/HTTP_PROXY is configured",
        }

    try:
        parts = urlsplit(target_endpoint.strip())
    except ValueError:
        parts = None
    hostname = parts.hostname.lower() if parts and parts.hostname else None
    port = parts.port if parts and parts.port is not None else (443 if parts and parts.scheme == "https" else 80)

    if not hostname or _is_loopback_host(hostname):
        return {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": "local_endpoint_check",
            "observed_at": observed_at,
            "target_endpoint_class": "loopback",
            "limitations": "loopback endpoint; does not represent a remote VM/provider network",
            "detail": "target endpoint is loopback; VM host-network observation incomplete",
        }

    import socket  # lazy: importing skyshift.parity must not import socket

    resolved_ips: list[str] = []
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        seen: set[str] = set()
        for info in infos:
            addr = info[4][0]
            if addr not in seen:
                seen.add(addr)
                resolved_ips.append(addr)
    except OSError as exc:
        return {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": "local_dns_and_route_socket",
            "observed_at": observed_at,
            "target_endpoint_class": "unresolved",
            "limitations": "DNS lookup failed; no host-network ownership could be observed",
            "detail": f"could not resolve target host ({type(exc).__name__})",
        }

    global_target_ips: list[str] = []
    for raw_ip in resolved_ips:
        try:
            ip_obj = ipaddress.ip_address(raw_ip)
            if ip_obj.is_global:
                global_target_ips.append(raw_ip)
        except ValueError:
            continue

    if not global_target_ips:
        return {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": "local_dns_and_route_socket",
            "observed_at": observed_at,
            "target_endpoint_class": "non_global",
            "limitations": "target resolved only to non-global/private addresses",
            "detail": "target endpoint resolved only to non-global IP(s); VM network observation incomplete",
        }

    # Zero-packet kernel routing lookup for primary outbound interface IP.
    public_ip: str | None = None
    interface_scope = "unknown"
    probe_target_ip = global_target_ips[0]
    try:
        family = socket.AF_INET6 if ":" in probe_target_ip else socket.AF_INET
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.connect((probe_target_ip, port))
            local_ip = sock.getsockname()[0]
        local_ip_obj = ipaddress.ip_address(local_ip)
        if local_ip_obj.is_global:
            public_ip = str(local_ip_obj)
            interface_scope = "global_interface"
        else:
            interface_scope = "private_interface_nat"
    except (OSError, ValueError):
        interface_scope = "unavailable"

    operator = _nonempty_str(target.get("operator")) or "declared-operator"
    jurisdiction = _nonempty_str(target.get("jurisdiction")) or "unspecified"
    network_owner = f"{operator} ({jurisdiction}; declared by approved target)"
    limitations = (
        "local DNS resolution and zero-packet kernel route check only; "
        "does not independently verify ASN, BGP origin, or legal sovereignty"
    )
    return {
        "status": "PASS",
        "public_ip": public_ip,
        "network_owner": network_owner,
        "provenance": "local_dns_and_route_socket",
        "observed_at": observed_at,
        "target_endpoint_class": "public_global",
        "interface_scope": interface_scope,
        "limitations": limitations,
        "detail": (
            f"configured target endpoint ({operator}) resolved to public global IP "
            f"(interface_scope={interface_scope}); {limitations}"
        ),
    }


def _run_bounded_subprocess(
    argv: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    timeout: float,
    grace_timeout: float,
    popen_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Execute ``argv`` without a shell, escalating terminate -> kill on timeout."""
    import subprocess  # lazy: importing skyshift.parity must not import subprocess

    factory = popen_factory or subprocess.Popen
    popen_kwargs: dict[str, Any] = {
        "env": env,
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "shell": False,
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True

    started = time.monotonic()
    try:
        proc = factory(argv, **popen_kwargs)
    except OSError as exc:
        return {
            "started": False,
            "exit_code": None,
            "timed_out": False,
            "escalated_kill": False,
            "stdout": "",
            "stderr": "",
            "elapsed": time.monotonic() - started,
            "start_error": type(exc).__name__,
        }

    timed_out = False
    escalated_kill = False
    stdout = ""
    stderr = ""
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=grace_timeout)
        except subprocess.TimeoutExpired:
            escalated_kill = True
            try:
                proc.kill()
            except OSError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=grace_timeout)
            except subprocess.TimeoutExpired:
                proc.wait()
                stdout, stderr = "", ""

    return {
        "started": True,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "escalated_kill": escalated_kill,
        "stdout": stdout or "",
        "stderr": stderr or "",
        "elapsed": time.monotonic() - started,
        "start_error": None,
    }


def _parse_child_json(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse the final non-empty stdout line as a JSON object without NaN."""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None, "child process emitted empty stdout"
    candidate = lines[-1]
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"malformed child JSON ({exc.msg})"
    if not isinstance(parsed, dict):
        return None, "child JSON output must be an object"
    try:
        json.dumps(parsed, allow_nan=False)
    except ValueError:
        return None, "child JSON contained non-finite numbers"
    return parsed, None


def _normalize_functional_checks(raw_checks: object, config: dict) -> tuple[list[dict[str, str]], list[str]]:
    """Convert raw child check rows into sanitized deterministic records."""
    if not isinstance(raw_checks, list):
        return [], ["child JSON missing 'checks' list"]
    normalized: list[dict[str, str]] = []
    parse_errors: list[str] = []
    for index, item in enumerate(raw_checks):
        if not isinstance(item, dict):
            parse_errors.append(f"child check[{index}] is not an object")
            continue
        op = _nonempty_str(item.get("operation"))
        status = item.get("status")
        detail = item.get("detail")
        if not op or status not in ("PASS", "FAIL", "incomplete"):
            parse_errors.append(f"child check[{index}] has invalid operation or status")
            continue
        normalized.append(
            {
                "operation": op,
                "status": status,
                "detail": _sanitize_text(str(detail or ""), config),
            }
        )
    return normalized, parse_errors


def _normalize_telemetry(raw_telemetry: object, config: dict) -> dict[str, Any]:
    if not isinstance(raw_telemetry, dict):
        return {
            "operation": "put_metric_data",
            "endpoint_host": None,
            "status": "incomplete",
            "detail": "telemetry result not reported by child process",
        }
    status = raw_telemetry.get("status")
    if status not in ("PASS", "FAIL", "incomplete"):
        status = "incomplete"
    endpoint_host = raw_telemetry.get("endpoint_host")
    if isinstance(endpoint_host, str):
        endpoint_host = _sanitize_text(endpoint_host, config)
    else:
        endpoint_host = None
    return {
        "operation": _nonempty_str(raw_telemetry.get("operation")) or "put_metric_data",
        "endpoint_host": endpoint_host,
        "status": status,
        "detail": _sanitize_text(str(raw_telemetry.get("detail") or ""), config),
    }


def _live_run_app(
    workload: Path,
    target: dict,
    *,
    config: dict,
    timeout: float = DEFAULT_APP_TIMEOUT_SECONDS,
    grace_timeout: float = DEFAULT_TERMINATE_GRACE_SECONDS,
    popen_factory: Callable[..., Any] | None = None,
    host_network_probe: Callable[[str, dict, dict], dict[str, Any]] | None = None,
    extra_args: list[str] | None = None,
) -> dict:
    """Execute the unchanged fixture application in a bounded subprocess."""
    target_identity = str(target.get("target_id") or "leaseweb-selfhosted")
    app_path = _resolve_app_path(workload)

    target_endpoint = _nonempty_str(config.get("SKYSHIFT_TARGET_ENDPOINT_URL")) or _nonempty_str(
        config.get("AWS_ENDPOINT_URL")
    )
    target_access = _nonempty_str(config.get("SKYSHIFT_TARGET_ACCESS_KEY_ID")) or _nonempty_str(
        config.get("AWS_ACCESS_KEY_ID")
    )
    target_secret = _nonempty_str(config.get("SKYSHIFT_TARGET_SECRET_ACCESS_KEY")) or _nonempty_str(
        config.get("AWS_SECRET_ACCESS_KEY")
    )
    target_bucket = _nonempty_str(config.get("SKYSHIFT_TARGET_BUCKET"))

    source_host = _sanitize_endpoint_host(config.get("SKYSHIFT_SOURCE_ENDPOINT_URL"))
    target_host = _sanitize_endpoint_host(target_endpoint)

    missing_cfg = []
    if not target_endpoint:
        missing_cfg.append("SKYSHIFT_TARGET_ENDPOINT_URL")
    if not target_access:
        missing_cfg.append("SKYSHIFT_TARGET_ACCESS_KEY_ID")
    if not target_secret:
        missing_cfg.append("SKYSHIFT_TARGET_SECRET_ACCESS_KEY")
    if not target_bucket:
        missing_cfg.append("SKYSHIFT_TARGET_BUCKET")

    endpoint_changed = {
        "changed": bool(target_host and target_host != source_host),
        "config_only": True,
        "env_var": "AWS_ENDPOINT_URL",
        "source_identity": "local-moto-source" if (source_host and _is_loopback_host(source_host.split(":")[0])) else ("configured-source" if source_host else "aws-s3-default"),
        "target_identity": target_identity,
    }

    if missing_cfg or not app_path.is_file():
        reason = (
            "missing target configuration: " + ", ".join(missing_cfg)
            if missing_cfg
            else f"fixture application not found at {app_path.name}"
        )
        data = {
            "app_sha256_before": _sha256_file(app_path) if app_path.is_file() else None,
            "app_sha256_after": None,
            "endpoint_changed": endpoint_changed,
            "functional_checks": [],
            "functional_checks_passed": False,
            "ok": False,
            "telemetry": {
                "operation": "put_metric_data",
                "endpoint_host": None,
                "status": "incomplete",
                "detail": "not executed; " + reason,
            },
            "exit_code": None,
            "timed_out": False,
            "host_network": {
                "status": "incomplete",
                "public_ip": None,
                "network_owner": None,
                "provenance": None,
                "observed_at": None,
                "detail": f"not observed; {reason}",
            },
        }
        checks = [
            {
                "id": "app_unchanged_sha256",
                "status": "incomplete",
                "detail": f"application did not execute ({reason})",
            },
            {
                "id": "app_functional_checks",
                "status": "incomplete",
                "detail": f"application did not execute ({reason})",
            },
            {
                "id": "host_network_observation",
                "status": "incomplete",
                "detail": f"host network not observed ({reason})",
            },
        ]
        return _envelope("run", "live", "incomplete", checks, data, [reason])

    hash_before = _sha256_file(app_path)
    child_env = _build_child_env(
        config,
        target_endpoint=target_endpoint,
        target_access=target_access,
        target_secret=target_secret,
        target_bucket=target_bucket,
    )
    argv = [sys.executable, "-B", str(app_path)]
    if extra_args:
        argv.extend(extra_args)

    proc_result = _run_bounded_subprocess(
        argv,
        env=child_env,
        cwd=app_path.parent,
        timeout=timeout,
        grace_timeout=grace_timeout,
        popen_factory=popen_factory,
    )

    hash_after = _sha256_file(app_path)
    app_unchanged = bool(
        hash_before
        and hash_after
        and _SHA256_RE.match(hash_before)
        and hash_before == hash_after
    )

    errors: list[str] = []
    if app_unchanged:
        hash_check = {
            "id": "app_unchanged_sha256",
            "status": "PASS",
            "detail": f"unchanged fixture SHA-256 verified before and after execution ({hash_before[:16]}...)",
        }
    else:
        msg = "fixture application bytes changed or became unreadable during execution"
        errors.append(msg)
        hash_check = {"id": "app_unchanged_sha256", "status": "FAIL", "detail": msg}

    functional_checks: list[dict[str, str]] = []
    telemetry = _normalize_telemetry(None, config)
    functional_checks_passed = False

    if not proc_result["started"]:
        msg = _sanitize_text(
            f"failed to start fixture app process ({proc_result['start_error']})", config
        )
        errors.append(msg)
        func_check = {"id": "app_functional_checks", "status": "FAIL", "detail": msg}
    elif proc_result["timed_out"]:
        escalation = "terminate+kill" if proc_result["escalated_kill"] else "terminate"
        msg = f"fixture app timed out after {timeout:.1f}s (reaped via {escalation})"
        errors.append(msg)
        func_check = {"id": "app_functional_checks", "status": "FAIL", "detail": msg}
    else:
        parsed, parse_err = _parse_child_json(proc_result["stdout"])
        if parse_err is not None or parsed is None:
            msg = _sanitize_text(
                f"fixture app exit {proc_result['exit_code']}: {parse_err}", config
            )
            errors.append(msg)
            func_check = {"id": "app_functional_checks", "status": "FAIL", "detail": msg}
        else:
            functional_checks, check_errs = _normalize_functional_checks(parsed.get("checks"), config)
            telemetry = _normalize_telemetry(parsed.get("telemetry"), config)
            for raw_err in parsed.get("errors") or []:
                if isinstance(raw_err, str) and raw_err.strip():
                    errors.append(_sanitize_text(raw_err, config))
            for cerr in check_errs:
                errors.append(_sanitize_text(cerr, config))

            ops_present = {c["operation"] for c in functional_checks}
            missing_ops = [op for op in REQUIRED_PARITY_OPERATIONS if op not in ops_present]
            failed_ops = [c["operation"] for c in functional_checks if c["status"] == "FAIL"]
            incomplete_ops = [c["operation"] for c in functional_checks if c["status"] == "incomplete"]

            if check_errs or proc_result["exit_code"] != 0 or failed_ops:
                parts_msg = [f"exit {proc_result['exit_code']}"]
                if failed_ops:
                    parts_msg.append("failed: " + ", ".join(failed_ops))
                if missing_ops:
                    parts_msg.append("missing: " + ", ".join(missing_ops))
                detail = _sanitize_text(
                    "fixture app functional checks failed (" + "; ".join(parts_msg) + ")",
                    config,
                )
                if not errors:
                    errors.append(detail)
                func_check = {"id": "app_functional_checks", "status": "FAIL", "detail": detail}
            elif missing_ops or incomplete_ops:
                parts_msg = []
                if missing_ops:
                    parts_msg.append("missing required: " + ", ".join(missing_ops))
                if incomplete_ops:
                    parts_msg.append("incomplete: " + ", ".join(incomplete_ops))
                detail = _sanitize_text(
                    "fixture app functional checks incomplete (" + "; ".join(parts_msg) + ")",
                    config,
                )
                errors.append(detail)
                func_check = {"id": "app_functional_checks", "status": "incomplete", "detail": detail}
            else:
                functional_checks_passed = True
                detail = (
                    f"{len(functional_checks)}/{len(functional_checks)} functional checks PASS "
                    f"in {proc_result['elapsed']:.2f}s (telemetry={telemetry['status']})"
                )
                func_check = {"id": "app_functional_checks", "status": "PASS", "detail": detail}

    probe = host_network_probe or _observe_host_network
    try:
        host_network = probe(target_endpoint, target, config)
        if not isinstance(host_network, dict) or host_network.get("status") not in (
            "PASS",
            "FAIL",
            "incomplete",
        ):
            raise ValueError("invalid host_network probe output")
    except Exception as exc:  # noqa: BLE001
        host_network = {
            "status": "incomplete",
            "public_ip": None,
            "network_owner": None,
            "provenance": None,
            "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "detail": _sanitize_text(f"host network probe failed ({type(exc).__name__})", config),
        }

    # Sanitize every string inside host_network
    sanitized_host_net = {
        k: (_sanitize_text(v, config) if isinstance(v, str) else v)
        for k, v in host_network.items()
    }
    net_check = {
        "id": "host_network_observation",
        "status": sanitized_host_net["status"],
        "detail": sanitized_host_net.get("detail") or "host network observation status recorded",
    }

    checks = [hash_check, func_check, net_check]
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif all(s == "PASS" for s in statuses):
        overall = "PASS"
    else:
        overall = "incomplete"

    data = {
        "app_sha256_before": hash_before,
        "app_sha256_after": hash_after,
        "endpoint_changed": endpoint_changed,
        "functional_checks": functional_checks,
        "functional_checks_passed": functional_checks_passed,
        "ok": bool(functional_checks_passed and app_unchanged),
        "telemetry": telemetry,
        "exit_code": proc_result["exit_code"],
        "timed_out": proc_result["timed_out"],
        "host_network": sanitized_host_net,
    }
    return _envelope("run", "live", overall, checks, data, errors)


def run_app(workload: Path, target: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a run envelope recording unchanged-app execution against the target.

    ``target`` is the preceding ``choose`` envelope ``data`` object.
    Does not mutate inputs; ``stub=True`` performs no I/O, network, or process calls.
    """
    if not isinstance(workload, (Path, str)):
        raise ValueError("workload must be a pathlib.Path or str")
    _require_data_object(target, TARGET_KEYS, "target")
    _check_config(config)
    workload_path = Path(workload)

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

    return _live_run_app(workload_path, target, config=config)


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

    return _live_verify(data_map, target, config=config)


# ---------------------------------------------------------------------------
# Live Moto-before vs target-after parity suite (WS2-05)
# ---------------------------------------------------------------------------


def _parity_multipart_payload() -> bytes:
    """Deterministically build the 128 KiB synthetic multipart parity payload."""
    blocks = []
    for index in range(_PARITY_MULTIPART_RECORDS):
        header = f"SKYSHIFT-PARITY-{index:04d}:".encode("ascii")
        body = bytes(((index * 29 + offset) % 256) for offset in range(104))
        blocks.append(header + body + b"\n")
    return b"".join(blocks)


def _stream_body_sha256(body: Any, chunk_size: int = _PARITY_STREAM_CHUNK) -> tuple[str, int]:
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


def _s3_side_config(config: dict, ns: str) -> dict[str, str] | None:
    side = {
        "endpoint": _nonempty_str(config.get(f"{ns}_ENDPOINT_URL")),
        "key": _nonempty_str(config.get(f"{ns}_ACCESS_KEY_ID")),
        "secret": _nonempty_str(config.get(f"{ns}_SECRET_ACCESS_KEY")),
        "bucket": _nonempty_str(config.get(f"{ns}_BUCKET")),
        "region": _nonempty_str(config.get("AWS_DEFAULT_REGION")) or "eu-central-1",
    }
    if not all(side[k] for k in ("endpoint", "key", "secret", "bucket")):
        return None
    return side  # type: ignore[return-value]


def _build_s3_client(side: dict[str, str]) -> Any:
    import boto3  # lazy: importing skyshift.parity must not import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=side["endpoint"],
        aws_access_key_id=side["key"],
        aws_secret_access_key=side["secret"],
        region_name=side["region"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 1, "mode": "standard"},
        ),
    )


def _sanitize_exc(exc: BaseException, config: dict) -> str:
    code = None
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = (response.get("Error") or {}).get("Code")
    label = f"{type(exc).__name__}" + (
        f" ({code})" if isinstance(code, str) and code.isalnum() else ""
    )
    return _sanitize_text(label, config)


def _select_parity_operations(
    data_map: dict,
    *,
    config: dict,
    llm_complete: Callable[..., dict] | None = None,
) -> dict[str, Any]:
    """Deterministically build required operations and safely merge optional AI proposals."""
    required: set[str] = set(REQUIRED_PARITY_OPERATIONS)
    detected_raw: list[str] = []
    for call in data_map.get("calls") or []:
        if not isinstance(call, dict):
            continue
        if str(call.get("service") or "").lower() != "s3":
            continue
        op_name = _nonempty_str(call.get("operation"))
        if not op_name:
            continue
        detected_raw.append(op_name)
        mapped = _AST_OP_MAP.get(op_name)
        if mapped:
            required.add(mapped)

    ai_mode = "replay"
    ai_status = "incomplete"
    rejected: list[str] = []
    proposed_valid: set[str] = set()

    proposer = llm_complete
    if proposer is None:
        try:
            from skyshift.llm import complete as _default_complete

            proposer = _default_complete
        except Exception:  # noqa: BLE001
            proposer = None

    if proposer is not None:
        payload = {
            "required_operations": [op for op in KNOWN_PARITY_OPERATIONS if op in required],
            "detected_s3_calls": sorted(set(detected_raw)),
            "known_operations": list(KNOWN_PARITY_OPERATIONS),
        }
        try:
            res = proposer("parity_selection", payload, PARITY_SELECTION_SCHEMA, config=config)
        except Exception:  # noqa: BLE001 - advisory only
            res = None
        if isinstance(res, dict):
            mode_val = res.get("mode")
            if mode_val in ("live", "replay"):
                ai_mode = mode_val
            status_val = res.get("status")
            if status_val in ("ok", "incomplete"):
                ai_status = status_val
            proposed_data = res.get("data")
            if isinstance(proposed_data, dict) and isinstance(proposed_data.get("operations"), list):
                for item in proposed_data["operations"]:
                    if isinstance(item, str) and item in KNOWN_PARITY_OPERATIONS:
                        proposed_valid.add(item)
                    else:
                        rejected.append(_sanitize_text(str(item), config))
            elif status_val == "ok":
                ai_status = "incomplete"

    final_set = required | proposed_valid
    ordered = [op for op in KNOWN_PARITY_OPERATIONS if op in final_set]
    return {
        "source": "ast+required",
        "operations": ordered,
        "required_operations": [op for op in KNOWN_PARITY_OPERATIONS if op in required],
        "ai_mode": ai_mode,
        "ai_status": ai_status,
        "rejected_proposals": rejected,
    }


def _default_http_get(url: str, timeout: float = _PARITY_HTTP_TIMEOUT) -> tuple[int, bytes]:
    import urllib.request  # lazy: importing skyshift.parity must not import urllib.request

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("presigned URL must use http or https")
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - scheme validated
        status = getattr(resp, "status", 200)
        chunks = []
        total = 0
        while True:
            chunk = resp.read(_PARITY_STREAM_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > 4 * 1024 * 1024:
                raise ValueError("presigned response exceeded size limit")
            chunks.append(chunk)
        return int(status), b"".join(chunks)


def _execute_parity_suite(
    client: Any,
    bucket: str,
    operations: list[str],
    *,
    prefix: str,
    config: dict,
    side_label: str,
    http_get: Callable[[str, float], tuple[int, bytes]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run identical S3 parity operations on one side and clean up ONLY created synthetic keys."""
    clean_prefix = prefix.strip("/") + "/"
    smoke_key = f"{clean_prefix}smoke.json"
    multipart_key = f"{clean_prefix}multipart.bin"
    delete_key = f"{clean_prefix}delete-probe.txt"

    smoke_sha256 = hashlib.sha256(_PARITY_SMOKE_PAYLOAD).hexdigest()
    multipart_payload = _parity_multipart_payload()
    multipart_sha256 = hashlib.sha256(multipart_payload).hexdigest()

    created_keys: set[str] = set()
    results: dict[str, dict[str, Any]] = {}
    getter = http_get or _default_http_get

    try:
        for op in operations:
            if op == "put_object":
                try:
                    client.put_object(
                        Bucket=bucket,
                        Key=smoke_key,
                        Body=_PARITY_SMOKE_PAYLOAD,
                        ContentType="application/json",
                    )
                    created_keys.add(smoke_key)
                    results[op] = {
                        "status": "PASS",
                        "detail": f"{side_label}: put {len(_PARITY_SMOKE_PAYLOAD)} bytes",
                        "signature": {"bytes": len(_PARITY_SMOKE_PAYLOAD), "sha256": smoke_sha256},
                    }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: put_object failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "get_object":
                try:
                    resp = client.get_object(Bucket=bucket, Key=smoke_key)
                    got_sha, got_bytes = _stream_body_sha256(resp["Body"])
                    if got_sha == smoke_sha256 and got_bytes == len(_PARITY_SMOKE_PAYLOAD):
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: read {got_bytes} bytes SHA-256 verified",
                            "signature": {"bytes": got_bytes, "sha256": got_sha},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: get_object content/hash mismatch",
                            "signature": {"bytes": got_bytes, "sha256": got_sha},
                        }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: get_object failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "list_objects_v2":
                try:
                    found_keys: list[str] = []
                    token = None
                    pages = 0
                    while True:
                        pages += 1
                        if pages > 100:
                            raise ValueError("pagination bound exceeded")
                        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": clean_prefix}
                        if token:
                            kwargs["ContinuationToken"] = token
                        page = client.list_objects_v2(**kwargs)
                        for item in page.get("Contents") or []:
                            if "Key" in item:
                                found_keys.append(item["Key"])
                        if page.get("IsTruncated"):
                            token = page.get("NextContinuationToken")
                            if not token:
                                raise ValueError("truncated listing without continuation token")
                        else:
                            break
                    found = smoke_key in found_keys
                    if found:
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: listed {len(found_keys)} key(s) under synthetic prefix",
                            "signature": {"smoke_key_found": True},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: synthetic smoke key missing from listing",
                            "signature": {"smoke_key_found": False},
                        }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: list_objects_v2 failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "head_object":
                try:
                    resp = client.head_object(Bucket=bucket, Key=smoke_key)
                    length = int(resp.get("ContentLength", -1))
                    if length == len(_PARITY_SMOKE_PAYLOAD):
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: head_object ContentLength={length}",
                            "signature": {"content_length": length},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: head_object length mismatch ({length})",
                            "signature": {"content_length": length},
                        }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: head_object failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "multipart_upload":
                upload_id: str | None = None
                try:
                    created = client.create_multipart_upload(
                        Bucket=bucket,
                        Key=multipart_key,
                        ContentType="application/octet-stream",
                    )
                    upload_id = created["UploadId"]
                    part = client.upload_part(
                        Bucket=bucket,
                        Key=multipart_key,
                        UploadId=upload_id,
                        PartNumber=1,
                        Body=multipart_payload,
                    )
                    client.complete_multipart_upload(
                        Bucket=bucket,
                        Key=multipart_key,
                        UploadId=upload_id,
                        MultipartUpload={"Parts": [{"ETag": part["ETag"], "PartNumber": 1}]},
                    )
                    upload_id = None
                    created_keys.add(multipart_key)
                    resp = client.get_object(Bucket=bucket, Key=multipart_key)
                    got_sha, got_bytes = _stream_body_sha256(resp["Body"])
                    if got_sha == multipart_sha256 and got_bytes == len(multipart_payload):
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: multipart upload verified ({got_bytes} bytes)",
                            "signature": {"bytes": got_bytes, "sha256": got_sha},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: multipart readback SHA-256 mismatch",
                            "signature": {"bytes": got_bytes, "sha256": got_sha},
                        }
                except Exception as exc:  # noqa: BLE001
                    if upload_id is not None:
                        try:
                            client.abort_multipart_upload(
                                Bucket=bucket,
                                Key=multipart_key,
                                UploadId=upload_id,
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: multipart_upload failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "presigned_url":
                try:
                    url = client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket, "Key": smoke_key},
                        ExpiresIn=60,
                    )
                    if not isinstance(url, str) or not url:
                        raise ValueError("empty presigned URL")
                    status_code, body = getter(url, _PARITY_HTTP_TIMEOUT)
                    got_sha = hashlib.sha256(body).hexdigest()
                    if status_code == 200 and got_sha == smoke_sha256:
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: presigned GET returned 200 and matching SHA-256",
                            "signature": {"http_status": status_code, "bytes": len(body), "sha256": got_sha},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: presigned GET returned status {status_code}",
                            "signature": {"http_status": status_code, "bytes": len(body), "sha256": got_sha},
                        }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: presigned_url failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }

            elif op == "delete_object":
                try:
                    client.put_object(
                        Bucket=bucket,
                        Key=delete_key,
                        Body=b"delete-probe",
                        ContentType="text/plain",
                    )
                    created_keys.add(delete_key)
                    client.delete_object(Bucket=bucket, Key=delete_key)
                    created_keys.discard(delete_key)
                    page = client.list_objects_v2(Bucket=bucket, Prefix=delete_key)
                    remaining = [item["Key"] for item in (page.get("Contents") or []) if "Key" in item]
                    if delete_key not in remaining:
                        results[op] = {
                            "status": "PASS",
                            "detail": f"{side_label}: deleted synthetic probe key",
                            "signature": {"deleted": True},
                        }
                    else:
                        results[op] = {
                            "status": "FAIL",
                            "detail": f"{side_label}: synthetic probe key still present after delete",
                            "signature": {"deleted": False},
                        }
                except Exception as exc:  # noqa: BLE001
                    results[op] = {
                        "status": "FAIL",
                        "detail": f"{side_label}: delete_object failed ({_sanitize_exc(exc, config)})",
                        "signature": None,
                    }
    finally:
        # Clean up strictly and exclusively keys created inside our synthetic prefix.
        for key in sorted(created_keys):
            if not key.startswith(clean_prefix):
                continue
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception:  # noqa: BLE001
                pass

    return results


def _live_verify(
    data_map: dict,
    target: dict,
    *,
    config: dict,
    before_client: Any | None = None,
    after_client: Any | None = None,
    before_bucket: str | None = None,
    after_bucket: str | None = None,
    llm_complete: Callable[..., dict] | None = None,
    http_get: Callable[[str, float], tuple[int, bytes]] | None = None,
    allow_live_pass: bool = True,
    prefix: str | None = None,
) -> dict:
    """Run the same selected S3 parity operations on Moto (before) and target (after)."""
    selection = _select_parity_operations(data_map, config=config, llm_complete=llm_complete)
    selected_ops: list[str] = selection["operations"]

    src_side = _s3_side_config(config, "SKYSHIFT_SOURCE")
    dst_side = _s3_side_config(config, "SKYSHIFT_TARGET")

    # Resolve target (after) client first; without a real or injected target we stay incomplete.
    resolved_after_client = after_client
    resolved_after_bucket = after_bucket or (dst_side["bucket"] if dst_side else None)

    if resolved_after_client is None and dst_side is None:
        detail = "missing target configuration (SKYSHIFT_TARGET_*); Moto-vs-target parity not run"
        rows = [
            {
                "operation": op,
                "before": {"status": "incomplete", "detail": "not executed; target unavailable"},
                "after": {"status": "incomplete", "detail": detail},
                "equal": False,
            }
            for op in selected_ops
        ]
        checks = [
            {"id": "parity_suite", "status": "incomplete", "detail": detail},
            {"id": "parity_operations_equal", "status": "incomplete", "detail": detail},
        ]
        return _envelope("parity", "live", "incomplete", checks, {"operations": rows, "selection": selection}, [detail])

    moto_ctx = None
    resolved_before_client = before_client
    resolved_before_bucket = before_bucket or (src_side["bucket"] if src_side else None)
    before_label = "Moto baseline"
    after_label = f"target ({target.get('target_id') or 'configured-target'})"

    errors: list[str] = []
    try:
        if resolved_before_client is None:
            if src_side is not None:
                try:
                    resolved_before_client = _build_s3_client(src_side)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"before client setup failed: {_sanitize_exc(exc, config)}")
            else:
                try:
                    from moto import mock_aws  # lazy optional in-process fallback
                    import boto3

                    moto_ctx = mock_aws()
                    moto_ctx.start()
                    resolved_before_bucket = "skyshift-parity-moto"
                    resolved_before_client = boto3.client(
                        "s3",
                        region_name=_nonempty_str(config.get("AWS_DEFAULT_REGION")) or "eu-central-1",
                        aws_access_key_id="testing",
                        aws_secret_access_key="testing",
                    )
                    resolved_before_client.create_bucket(
                        Bucket=resolved_before_bucket,
                        CreateBucketConfiguration={
                            "LocationConstraint": _nonempty_str(config.get("AWS_DEFAULT_REGION")) or "eu-central-1"
                        },
                    )
                    before_label = "Moto in-process baseline"
                except Exception as exc:  # noqa: BLE001
                    if moto_ctx is not None:
                        try:
                            moto_ctx.stop()
                        except Exception:  # noqa: BLE001
                            pass
                        moto_ctx = None
                    errors.append(f"Moto baseline unavailable ({_sanitize_exc(exc, config)})")

        if resolved_after_client is None and dst_side is not None:
            try:
                resolved_after_client = _build_s3_client(dst_side)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"target client setup failed: {_sanitize_exc(exc, config)}")

        if (
            resolved_before_client is None
            or resolved_after_client is None
            or not resolved_before_bucket
            or not resolved_after_bucket
        ):
            reason = "; ".join(errors) if errors else "before or after client unavailable"
            rows = [
                {
                    "operation": op,
                    "before": {"status": "incomplete", "detail": reason},
                    "after": {"status": "incomplete", "detail": reason},
                    "equal": False,
                }
                for op in selected_ops
            ]
            checks = [
                {"id": "parity_suite", "status": "incomplete", "detail": reason},
                {"id": "parity_operations_equal", "status": "incomplete", "detail": reason},
            ]
            return _envelope(
                "parity",
                "live",
                "incomplete",
                checks,
                {"operations": rows, "selection": selection},
                errors or [reason],
            )

        run_prefix = prefix or f"skyshift-parity/{time.time_ns()}-{os.getpid()}/"
        before_results = _execute_parity_suite(
            resolved_before_client,
            resolved_before_bucket,
            selected_ops,
            prefix=run_prefix,
            config=config,
            side_label=before_label,
            http_get=http_get,
        )
        after_results = _execute_parity_suite(
            resolved_after_client,
            resolved_after_bucket,
            selected_ops,
            prefix=run_prefix,
            config=config,
            side_label=after_label,
            http_get=http_get,
        )
    finally:
        if moto_ctx is not None:
            try:
                moto_ctx.stop()
            except Exception:  # noqa: BLE001
                pass

    rows: list[dict[str, Any]] = []
    any_fail = False
    any_incomplete = False
    any_unequal = False
    passed_both = 0

    for op in selected_ops:
        b = before_results.get(op) or {
            "status": "incomplete",
            "detail": f"{before_label}: operation skipped",
            "signature": None,
        }
        a = after_results.get(op) or {
            "status": "incomplete",
            "detail": f"{after_label}: operation skipped",
            "signature": None,
        }
        b_status = b["status"]
        a_status = a["status"]
        b_detail = _sanitize_text(str(b.get("detail") or ""), config)
        a_detail = _sanitize_text(str(a.get("detail") or ""), config)

        if b_status == "incomplete" or a_status == "incomplete":
            equal = False
            any_incomplete = True
        elif b_status == "PASS" and a_status == "PASS":
            equal = b.get("signature") == a.get("signature")
            if equal:
                passed_both += 1
            else:
                any_unequal = True
        elif b_status == "FAIL" and a_status == "FAIL":
            # Both failing may agree in outcome, but NEVER produces overall PASS.
            equal = True
            any_fail = True
        else:
            equal = False
            any_fail = True
            any_unequal = True

        rows.append(
            {
                "operation": op,
                "before": {"status": b_status, "detail": b_detail},
                "after": {"status": a_status, "detail": a_detail},
                "equal": equal,
            }
        )

    if any_fail or any_unequal:
        failed_names = [
            r["operation"]
            for r in rows
            if r["before"]["status"] == "FAIL" or r["after"]["status"] == "FAIL" or not r["equal"]
        ]
        suite_check = {
            "id": "parity_suite",
            "status": "FAIL",
            "detail": f"{passed_both}/{len(rows)} operations passed on both sides; findings in: {', '.join(failed_names)}",
        }
        equal_check = {
            "id": "parity_operations_equal",
            "status": "FAIL",
            "detail": f"parity differences or failures detected in: {', '.join(failed_names)}",
        }
        errors.append(suite_check["detail"])
    elif any_incomplete or not rows or not allow_live_pass:
        reason = (
            "non-live/fallback execution; parity cannot claim live PASS"
            if not allow_live_pass
            else f"{passed_both}/{len(rows)} operations measured; incomplete or skipped operations present"
        )
        suite_check = {"id": "parity_suite", "status": "incomplete", "detail": reason}
        equal_check = {"id": "parity_operations_equal", "status": "incomplete", "detail": reason}
    else:
        suite_check = {
            "id": "parity_suite",
            "status": "PASS",
            "detail": f"{passed_both}/{len(rows)} operations passed on both Moto and target",
        }
        equal_check = {
            "id": "parity_operations_equal",
            "status": "PASS",
            "detail": f"all {len(rows)} required/selected operations matched between Moto and target",
        }

    checks = [suite_check, equal_check]
    statuses = [c["status"] for c in checks]
    overall = "FAIL" if "FAIL" in statuses else ("PASS" if all(s == "PASS" for s in statuses) else "incomplete")
    return _envelope(
        "parity",
        "live",
        overall,
        checks,
        {"operations": rows, "selection": selection},
        errors,
    )
