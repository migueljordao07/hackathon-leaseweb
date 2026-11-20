"""SkyShift command line: run the eight-step pipeline and write canonical records (WS4).

Contract: tasks/contracts.md (CLI contract, shared envelope and paths).
Standard library only. Importing this module or printing ``--help`` performs no
file writes, network calls or service starts.

Every invocation clears the canonical outputs under ``--out`` first, recomputes all
prerequisite steps in-process and passes return values (never files from an earlier
run) downstream. Step exceptions, malformed envelopes, non-JSON values and records
that would leak a secret become sanitized ``incomplete`` records; steps that need
the missing data are skipped as ``incomplete``. Exit codes: 0 only when every
produced record is live PASS, 1 for any FAIL, 2 otherwise (always for ``--stub``).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

from skyshift import discover as discover_mod
from skyshift import evidence as evidence_mod
from skyshift import migrate as migrate_mod
from skyshift import parity as parity_mod
from skyshift import sever as sever_mod
from skyshift import translate as translate_mod

SCHEMA_VERSION = 1

STEPS = ("discover", "choose", "translate", "migrate", "run", "parity", "sever", "evidence")
ENVELOPE_KEYS = ("schema_version", "step", "mode", "status", "checks", "data", "errors")
MODES = ("live", "stub", "replay")
STATUSES = ("PASS", "FAIL", "incomplete")

# Upstream records whose data each step consumes (evidence consumes all seven records).
NEEDS = {
    "discover": (),
    "choose": ("discover",),
    "translate": ("discover", "choose"),
    "migrate": ("discover", "choose"),
    "run": ("choose",),
    "parity": ("discover", "choose"),
    "sever": ("discover", "choose"),
    "evidence": (),
}
# Steps whose live behaviour is driven by configuration (endpoints, buckets, app) and
# can still be measured without usable upstream data. They run with the contract's
# placeholder data, but such a record can never be PASS (capped at incomplete).
# translate and choose stay hard dependencies: without resources/target they would
# measure nothing meaningful.
SOFT_NEEDS = frozenset({"migrate", "run", "parity", "sever"})

COMMANDS = {
    "discover": ("discover",),
    "choose": ("discover", "choose"),
    "translate": ("discover", "choose", "translate"),
    "migrate": ("discover", "choose", "migrate"),
    "verify": ("discover", "choose", "run", "parity"),
    "sever": ("discover", "choose", "sever"),
    "report": STEPS,
    "run-all": STEPS,
}

COMMAND_HELP = {
    "discover": "map AWS resources, calls and buckets",
    "choose": "choose a Leaseweb target (runs discover first)",
    "translate": "generate out/iac/main.tf (runs discover, choose first)",
    "migrate": "copy and hash objects (runs discover, choose first)",
    "verify": "run the unchanged app and parity suite; emits run and parity",
    "sever": "severance test (runs discover, choose first)",
    "report": "evidence chain and HTML report (runs all steps)",
    "run-all": "run all eight steps in order",
}

# Required data keys per step; used only for placeholder records with no result.
EMPTY_DATA = {
    "discover": {"resources": [], "calls": [], "buckets": [], "readiness": None},
    "choose": {"target_id": None, "operator": None, "jurisdiction": None, "storage_mode": None,
               "criteria": [], "prices": [], "explanation": None},
    "translate": {"provider": None, "files": [], "resources": [], "validation": None},
    "migrate": {"objects": [], "source_count": None, "target_count": None, "matched": None,
                "missing": None, "different": None, "extra": None},
    "run": {"app_sha256_before": None, "app_sha256_after": None, "endpoint_changed": None,
            "functional_checks": [], "host_network": None},
    "parity": {"operations": [], "selection": None},
    "sever": {"attempts": [], "max_attempts": 2, "final": "incomplete", "radar_scope": None},
    "evidence": {"records": [], "final_hash": None, "report_path": None, "open_items": []},
}

ENV_NAMES = (
    "AWS_ENDPOINT_URL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION",
    "SKYSHIFT_SOURCE_ENDPOINT_URL", "SKYSHIFT_SOURCE_ACCESS_KEY_ID",
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY", "SKYSHIFT_SOURCE_BUCKET",
    "SKYSHIFT_TARGET_ENDPOINT_URL", "SKYSHIFT_TARGET_ACCESS_KEY_ID",
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY", "SKYSHIFT_TARGET_BUCKET", "SKYSHIFT_TARGET_PROVIDER",
    "SKYSHIFT_LLM_BASE_URL", "SKYSHIFT_LLM_API_KEY", "SKYSHIFT_LLM_MODEL", "SKYSHIFT_LLM_REPLAY",
    "SKYSHIFT_TELEMETRY_ENDPOINT", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
    "OS_AUTH_URL", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET",
    "OS_REGION_NAME", "LEASEWEB_API_KEY",
)
SECRET_ENV_NAMES = (
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
    "SKYSHIFT_SOURCE_ACCESS_KEY_ID", "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY",
    "SKYSHIFT_TARGET_ACCESS_KEY_ID", "SKYSHIFT_TARGET_SECRET_ACCESS_KEY",
    "SKYSHIFT_LLM_API_KEY", "OS_APPLICATION_CREDENTIAL_ID", "OS_APPLICATION_CREDENTIAL_SECRET",
    "LEASEWEB_API_KEY",
)
# Shorter values (e.g. Moto's "testing") are local placeholders, not secrets; matching
# them would withhold honest records that happen to contain the same word.
MIN_SECRET_LENGTH = 8
MAX_ERROR_CHARS = 300
REDACTED = "[REDACTED]"

_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
_URL_QUERY = re.compile(r"(?i)(\bhttps?://[^\s?#'\"<>]*)\?[^\s'\"<>]*")
_SIGNED_PARAM = re.compile(r"(?i)\b(X-Amz-[A-Za-z-]+|Signature|AWSAccessKeyId)=[^\s&'\"<>]+")

OUTPUT_FILES = tuple(f"{step}.json" for step in STEPS) + (evidence_mod.REPORT_NAME, "iac/main.tf")


# --------------------------------------------------------------------------- config


def build_config(environ: dict | None = None) -> dict:
    """Map documented environment names to their non-empty values (never logged)."""
    environ = os.environ if environ is None else environ
    return {name: environ[name] for name in ENV_NAMES if environ.get(name)}


def _secret_values(config: dict) -> list[str]:
    values = {config.get(name) for name in SECRET_ENV_NAMES}
    return sorted((v for v in values if isinstance(v, str) and len(v) >= MIN_SECRET_LENGTH),
                  key=len, reverse=True)


def sanitize(text: str, config: dict) -> str:
    """Redact secret values, URL credentials and signed query strings; bound length."""
    for value in _secret_values(config):
        text = text.replace(value, REDACTED)
    text = _URL_USERINFO.sub(rf"\1{REDACTED}@", text)
    text = _URL_QUERY.sub(rf"\1?{REDACTED}", text)
    text = _SIGNED_PARAM.sub(rf"\1={REDACTED}", text)
    text = " ".join(text.split())
    return text if len(text) <= MAX_ERROR_CHARS else text[: MAX_ERROR_CHARS - 3] + "..."


# --------------------------------------------------------------------------- records


def _placeholder(step: str, mode: str, check_id: str, detail: str, error: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "step": step,
        "mode": mode,
        "status": "incomplete",
        "checks": [{"id": check_id, "status": "incomplete", "detail": detail}],
        "data": copy.deepcopy(EMPTY_DATA[step]),
        "errors": [error],
    }


def _malformed(step: str, envelope: object) -> str | None:
    if not isinstance(envelope, dict) or set(envelope) != set(ENVELOPE_KEYS):
        return "step returned a malformed envelope (top-level keys differ from contract)"
    if envelope["schema_version"] != SCHEMA_VERSION or envelope["step"] != step:
        return "step returned the wrong schema_version or step name"
    if envelope["mode"] not in MODES or envelope["status"] not in STATUSES:
        return "step returned an invalid mode or status"
    if not isinstance(envelope["checks"], list) or not isinstance(envelope["errors"], list):
        return "step returned non-list checks or errors"
    if not isinstance(envelope["data"], dict):
        return "step returned non-object data"
    return None


def _accept(step: str, envelope: object, mode: str, config: dict) -> tuple[dict, bool]:
    """Return (JSON-normalised valid leak-free envelope, True) or (placeholder, False)."""
    problem = _malformed(step, envelope)
    if problem is None:
        try:
            text = evidence_mod.canonical_bytes(envelope).decode("utf-8")
        except (TypeError, ValueError):
            problem = "step returned non-JSON values (for example NaN); record withheld"
        else:
            if any(value in text for value in _secret_values(config)):
                problem = "step output contained a configuration secret; record withheld"
            else:
                return json.loads(text), True
    return _placeholder(step, mode, "record_valid", "no valid record; result not measured",
                        problem), False


def _invoke(step: str, records: dict, *, workload: Path, out: Path, config: dict,
            stub: bool) -> object:
    # Functions are looked up at call time so tests can inject doubles per module.
    def data(name: str) -> dict:
        if name not in records:  # dependency not run in this command
            return copy.deepcopy(EMPTY_DATA[name])
        return copy.deepcopy(records[name]["data"])

    if step == "discover":
        return discover_mod.discover(workload, config=config, stub=stub)
    if step == "choose":
        return discover_mod.choose(data("discover"), config=config, stub=stub)
    if step == "translate":
        return translate_mod.translate(data("discover"), data("choose"), output_dir=out,
                                       config=config, stub=stub)
    if step == "migrate":
        return migrate_mod.migrate(data("discover"), data("choose"), config=config, stub=stub)
    if step == "run":
        # The app runs with its own directory as cwd; an absolute path keeps a relative
        # --workload valid there. Other steps keep the relative path so records do not
        # expose host directories.
        return parity_mod.run_app(Path(workload).resolve(), data("choose"), config=config,
                                  stub=stub)
    if step == "parity":
        return parity_mod.verify(data("discover"), data("choose"), config=config, stub=stub)
    if step == "sever":
        return sever_mod.sever(data("discover"), data("choose"), config=config, stub=stub)
    if step == "evidence":
        chain = [copy.deepcopy(records[name]) for name in STEPS[:-1]]
        return evidence_mod.build_evidence(chain, output_dir=out, config=config, stub=stub)
    raise ValueError(f"unknown step: {step}")


def run_steps(steps: tuple[str, ...], *, workload: Path, out: Path, config: dict,
              stub: bool) -> dict:
    """Run ``steps`` in order; return {step: record} for every step attempted."""
    mode = "stub" if stub else "live"
    records: dict[str, dict] = {}
    usable: set[str] = set()
    for step in steps:
        missing = [name for name in NEEDS[step] if name not in usable]
        soft = bool(missing) and step in SOFT_NEEDS
        # Inputs view: unusable upstream data is replaced by contract placeholders
        # (never stale files); the hashed records themselves are left untouched.
        inputs = {name: records[name] for name in usable}
        inputs.update({name: {"data": copy.deepcopy(EMPTY_DATA[name])} for name in missing})
        if step == "evidence":
            inputs = records
        if missing and not soft:
            record = _placeholder(
                step, mode, "upstream_available",
                f"not run: upstream {', '.join(missing)} produced no usable data",
                f"skipped: upstream {', '.join(missing)} unavailable")
        else:
            try:
                result = _invoke(step, inputs, workload=workload, out=out, config=config,
                                 stub=stub)
            except Exception as exc:  # converted to an incomplete record by contract
                record = _placeholder(step, mode, "step_completed",
                                      "step raised an exception; result not measured",
                                      sanitize(f"{type(exc).__name__}: {exc}", config))
            else:
                record, valid = _accept(step, result, mode, config)
                if valid:
                    usable.add(step)
                    if soft:
                        record = _cap_without_upstream(record, missing)
        if step == "evidence" and step not in usable:
            # A report must never outlive the evidence record it was rendered from.
            (out / evidence_mod.REPORT_NAME).unlink(missing_ok=True)
        records[step] = record
        evidence_mod.atomic_write_text(out / f"{step}.json", _pretty(record))
    return records


def _cap_without_upstream(record: dict, missing: list[str]) -> dict:
    """A step measured without usable upstream data is never PASS; FAIL stays FAIL."""
    names = ", ".join(missing)
    record["checks"].append({"id": "upstream_available", "status": "incomplete",
                             "detail": f"ran with placeholder data: upstream {names} unusable"})
    record["errors"].append(f"upstream {names} unavailable; result capped at incomplete")
    if record["status"] == "PASS":
        record["status"] = "incomplete"
    return record


def _pretty(record: dict) -> str:
    return json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def exit_code(records: list[dict]) -> int:
    """0 only if every record is live PASS; 1 for any FAIL; otherwise 2."""
    if not records:
        return 2
    if any(isinstance(r, dict) and r.get("status") == "FAIL" for r in records):
        return 1
    if all(isinstance(r, dict) and r.get("mode") == "live" and r.get("status") == "PASS"
           for r in records):
        return 0
    return 2


def clear_outputs(out: Path) -> None:
    """Remove only canonical outputs so nothing from an earlier run survives."""
    for name in OUTPUT_FILES:
        (out / name).unlink(missing_ok=True)


# --------------------------------------------------------------------------- CLI


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workload", type=Path, default=Path("fixtures/aws_workload"),
                        help="workload directory (default: fixtures/aws_workload)")
    common.add_argument("--out", type=Path, default=Path("out"),
                        help="run root for canonical outputs (default: out)")
    common.add_argument("--stub", action="store_true",
                        help="offline synthetic stubs; always exits 2, never live proof")
    parser = argparse.ArgumentParser(
        prog="python -m skyshift.cli",
        description="SkyShift exit-plan test: discover -> choose -> translate -> migrate -> "
                    "run -> parity -> sever -> evidence. Configuration comes from documented "
                    "environment variable names; values are never printed.",
        epilog="Exit codes: 0 live PASS, 1 measured FAIL, 2 incomplete or stub.")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for command, text in COMMAND_HELP.items():
        sub.add_parser(command, parents=[common], help=text, description=text)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help exits 0, usage errors exit 2
        return exc.code if isinstance(exc.code, int) else 2
    if args.command is None:
        parser.print_help()
        return 2

    config = build_config()
    out = args.out
    try:
        out.mkdir(parents=True, exist_ok=True)
        clear_outputs(out)
    except OSError as exc:
        print(f"error: cannot prepare output directory: {sanitize(str(exc), config)}",
              file=sys.stderr)
        return 2

    records = run_steps(COMMANDS[args.command], workload=args.workload, out=out,
                        config=config, stub=args.stub)
    for step, record in records.items():
        print(f"{step:<10} {record['mode']:<7} {record['status']:<11} "
              f"{(out / f'{step}.json').as_posix()}")
    code = exit_code(list(records.values()))
    label = {0: "PASS", 1: "FAIL", 2: "INCOMPLETE"}[code]
    if args.stub:
        label += " (STUB: synthetic records, not VM validated)"
    print(f"overall: {label} (exit {code})")
    return code


if __name__ == "__main__":
    sys.exit(main())
