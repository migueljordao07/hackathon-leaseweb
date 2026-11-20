"""Evidence hash chain and qualified HTML report (WS4).

Contract: tasks/contracts.md (Python API ``build_evidence``, Evidence section).
Standard library only. Importing this module performs no I/O, network or service start.

Current state: minimal stub-path adapter (WS4-01). The SHA-256 chain follows the
contract exactly. The verdict policy is deliberately conservative (FAIL, then
incomplete, then PASS only for an all-live-PASS artifact set) until WS4-02 replaces
it with per-domain deterministic checks. The report is rendered with stdlib HTML
escaping, contains no scripts or external resources, and visibly qualifies stub,
replay and unmeasured material. Evidence never hashes itself or the HTML report.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1

CHAIN_STEPS = ("discover", "choose", "translate", "migrate", "run", "parity", "sever")
GENESIS_HASH = "0" * 64
ENVELOPE_KEYS = ("schema_version", "step", "mode", "status", "checks", "data", "errors")
MODES = ("live", "stub", "replay")
STATUSES = ("PASS", "FAIL", "incomplete")

REPORT_NAME = "report.html"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "report" / "report.html.j2"
_PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")

DISCLAIMER = (
    "This report supports an exit-plan test. It is not a certificate, a sovereignty "
    "determination or a DORA compliance determination."
)
STUB_QUALIFICATION = (
    "Synthetic stub run: no VM validation occurred. Every record was produced offline by "
    "contract stubs. No migration, OpenTofu validation, target parity, proxy enforcement, "
    "VM location, sovereignty or DORA compliance has been proven."
)


# --------------------------------------------------------------------------- files


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text via a sibling temp file and ``os.replace``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.chmod(tmp, 0o644)  # mkstemp creates 0600; outputs are shareable local artifacts
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------- chain


def canonical_bytes(record: dict) -> bytes:
    """Contract canonical form: sorted, compact, UTF-8 JSON without NaN."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def artifact_sha256(record: dict) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def chain_hash(previous_hash: str, artifact_hash: str) -> str:
    return hashlib.sha256(bytes.fromhex(previous_hash) + bytes.fromhex(artifact_hash)).hexdigest()


def _validate_records(records: object) -> None:
    if not isinstance(records, list) or len(records) != len(CHAIN_STEPS):
        raise ValueError(f"records must be a list of {len(CHAIN_STEPS)} step envelopes")
    for expected, record in zip(CHAIN_STEPS, records):
        if not isinstance(record, dict) or set(record) != set(ENVELOPE_KEYS):
            raise ValueError(f"{expected} record must have exactly the envelope keys")
        if record["step"] != expected:
            raise ValueError(f"records out of order: expected {expected}, got {record['step']!r}")
        if record["schema_version"] != SCHEMA_VERSION:
            raise ValueError(f"{expected} record has unsupported schema_version")
        if record["mode"] not in MODES or record["status"] not in STATUSES:
            raise ValueError(f"{expected} record has invalid mode or status")
        if not isinstance(record["checks"], list) or not isinstance(record["errors"], list):
            raise ValueError(f"{expected} record checks and errors must be lists")
        if not isinstance(record["data"], dict):
            raise ValueError(f"{expected} record data must be an object")


def build_chain(records: list[dict], *, output_dir: Path) -> list[dict]:
    """Return the seven chain links in contract order."""
    _validate_records(records)
    output_dir = Path(output_dir)
    previous = GENESIS_HASH
    links = []
    for record in records:
        artifact = artifact_sha256(record)
        link = chain_hash(previous, artifact)
        links.append({
            "step": record["step"],
            "path": (output_dir / f"{record['step']}.json").as_posix(),
            "artifact_sha256": artifact,
            "previous_hash": previous,
            "hash": link,
        })
        previous = link
    return links


def verify_chain(records: list[dict], evidence_data: dict) -> list[str]:
    """Recompute every link from ``records``; return problems (empty means verified)."""
    links = evidence_data.get("records") if isinstance(evidence_data, dict) else None
    if not isinstance(records, list) or not isinstance(links, list):
        return ["records and evidence links must be lists"]
    if len(records) != len(CHAIN_STEPS) or len(links) != len(CHAIN_STEPS):
        return [f"expected {len(CHAIN_STEPS)} records and links"]
    problems = []
    previous = GENESIS_HASH
    for step, record, link in zip(CHAIN_STEPS, records, links):
        if not isinstance(record, dict) or record.get("step") != step:
            problems.append(f"{step}: record missing or out of order")
        if not isinstance(link, dict) or link.get("step") != step:
            problems.append(f"{step}: link missing or out of order")
            link = {}
        try:
            artifact = artifact_sha256(record)
        except (TypeError, ValueError):
            problems.append(f"{step}: record is not canonical JSON")
            return problems
        expected = chain_hash(previous, artifact)
        if link.get("artifact_sha256") != artifact:
            problems.append(f"{step}: artifact_sha256 mismatch")
        if link.get("previous_hash") != previous:
            problems.append(f"{step}: previous_hash mismatch")
        if link.get("hash") != expected:
            problems.append(f"{step}: chain hash mismatch")
        previous = expected
    if evidence_data.get("final_hash") != previous:
        problems.append("final_hash mismatch")
    return problems


# --------------------------------------------------------------------------- verdict


def _overall(statuses: list[str]) -> str:
    if "FAIL" in statuses:
        return "FAIL"
    if "incomplete" in statuses:
        return "incomplete"
    return "PASS"


def _checks(records: list[dict], stub: bool) -> list[dict]:
    failed = [r["step"] for r in records if r["status"] == "FAIL"]
    not_live_pass = [r["step"] for r in records if r["mode"] != "live" or r["status"] != "PASS"]
    if failed:
        verdicts = {"id": "step_verdicts", "status": "FAIL",
                    "detail": "measured FAIL in: " + ", ".join(failed)}
    elif not_live_pass:
        verdicts = {"id": "step_verdicts", "status": "incomplete",
                    "detail": "not live PASS: " + ", ".join(not_live_pass)}
    else:
        verdicts = {"id": "step_verdicts", "status": "PASS",
                    "detail": "all seven step records are live PASS"}
    if stub:
        return [
            {"id": "artifact_set_complete", "status": "incomplete",
             "detail": "seven synthetic stub records present in contract order; not live evidence"},
            {"id": "hash_chain", "status": "incomplete",
             "detail": "SHA-256 chain computed over synthetic stub records; not live evidence"},
            verdicts,
        ]
    return [
        {"id": "artifact_set_complete", "status": "PASS",
         "detail": "seven step records present in contract order"},
        {"id": "hash_chain", "status": "PASS",
         "detail": "SHA-256 chain recomputed and verified from canonical record bytes"},
        verdicts,
    ]


def _open_items(records: list[dict], stub: bool) -> list[str]:
    items = []
    if stub:
        items.append("STUB RUN: synthetic records only; no VM validation occurred")
    for record in records:
        for check in record["checks"]:
            if isinstance(check, dict) and check.get("status") != "PASS":
                items.append(f"{record['step']}: {check.get('id')} {check.get('status')}: "
                             f"{check.get('detail')}")
        for error in record["errors"]:
            items.append(f"{record['step']}: error: {error}")
    return items


# --------------------------------------------------------------------------- report


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _status_cell(status: object) -> str:
    css = {"PASS": "pass", "FAIL": "fail"}.get(status, "incomplete")
    return f'<td class="status {css}">{_e(status)}</td>'


def _mode_cell(mode: object) -> str:
    css = "live" if mode == "live" else "qualified"
    label = mode if mode == "live" else f"{str(mode).upper()} (not measured live)"
    return f'<td class="mode {css}">{_e(label)}</td>'


def render(template: str, values: dict[str, str]) -> str:
    """Single-pass ``{{ name }}`` substitution of pre-escaped HTML fragments."""
    def substitute(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            raise ValueError(f"report template placeholder has no value: {name}")
        return values[name]
    return _PLACEHOLDER.sub(substitute, template)


METHOD_LABELS = {
    "template": "template (OpenTofu)",
    "model": "model-proposed (OpenTofu)",
    "adopted_existing": "adopted existing resource, not managed by OpenTofu",
    "manual": "manual action needed",
}
NOTE_KEYS = ("note", "notes", "flavor_note", "manual_reason")


def _translate_section(records: list[dict]) -> str:
    """Escaped rows for every translated resource with its method label and notes."""
    record = next((r for r in records if isinstance(r, dict) and r.get("step") == "translate"),
                  None)
    data = record.get("data") if isinstance(record, dict) else None
    resources = data.get("resources") if isinstance(data, dict) else None
    rows = []
    for res in resources if isinstance(resources, list) else []:
        if not isinstance(res, dict):
            continue
        method = res.get("method")
        label = METHOD_LABELS.get(method, str(method))
        notes = []
        for key in NOTE_KEYS:
            value = res.get(key)
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            if value and str(value) not in notes:
                notes.append(str(value))
        rows.append(
            f"<tr><td>{_e(res.get('source_id'))}</td><td>{_e(res.get('target_type'))}</td>"
            f"<td>{_e(label)}</td><td>{_e(res.get('status'))}</td>"
            f"<td>{_e(' | '.join(notes) or '-')}</td></tr>")
    return "\n".join(rows) or "<tr><td colspan=\"5\">no translated resources recorded</td></tr>"


def _sever_section(records: list[dict]) -> tuple[str, str, str]:
    """Escaped rows for every severance attempt, preserving red -> fix -> green history."""
    sever = next((r for r in records if isinstance(r, dict) and r.get("step") == "sever"), None)
    data = sever.get("data") if isinstance(sever, dict) else None
    if not isinstance(data, dict):
        return "incomplete", "no severance record", "<tr><td colspan=\"6\">no attempts recorded</td></tr>"
    rows = []
    for attempt in data.get("attempts") or []:
        if not isinstance(attempt, dict):
            continue
        events = attempt.get("events") or []
        conns = "; ".join(
            f"{e.get('host')}:{e.get('port')} {e.get('decision')} via {e.get('via')}"
            for e in events if isinstance(e, dict)) or "none recorded"
        repl = attempt.get("replacement")
        repl_text = (f"{repl.get('id')} ({repl.get('mode')})" if isinstance(repl, dict)
                     else "none")
        bypasses = attempt.get("bypasses") or []
        rows.append(
            f"<tr><td>{_e(attempt.get('number'))}</td>{_status_cell(attempt.get('status'))}"
            f"<td>{_e(attempt.get('blocked'))}</td><td>{_e(conns)}</td>"
            f"<td>{_e(repl_text)}</td><td>{_e(len(bypasses))}</td></tr>")
    return (str(data.get("final")), str(data.get("radar_scope") or "not stated"),
            "\n".join(rows) or "<tr><td colspan=\"6\">no attempts recorded</td></tr>")


def render_report(records: list[dict], evidence: dict, *, stub: bool,
                  template_path: Path = TEMPLATE_PATH) -> str:
    data = evidence["data"]
    status = evidence["status"]
    if stub:
        banner, banner_css, qualification = (
            "STUB / INCOMPLETE / NOT VM VALIDATED", "incomplete", STUB_QUALIFICATION)
    elif status == "PASS":
        banner, banner_css, qualification = (
            "PASS: all required checks measured live", "pass",
            "Every step record is live PASS and the hash chain verifies.")
    elif status == "FAIL":
        banner, banner_css, qualification = (
            "FAIL: at least one measured check failed", "fail",
            "See the failing checks below; failures are findings, not hidden.")
    else:
        banner, banner_css, qualification = (
            "INCOMPLETE: not all required checks were measured", "incomplete",
            "Unmeasured, stubbed, replayed or offline-only results remain open items.")

    links = {link["step"]: link for link in data["records"]}
    step_rows = []
    check_rows = []
    for record in records + [evidence]:
        step = record["step"]
        link = links.get(step)
        step_rows.append(
            f"<tr><td>{_e(step)}</td>{_mode_cell(record['mode'])}{_status_cell(record['status'])}"
            f"<td class=\"hash\">{_e(link['artifact_sha256'] if link else 'not chained')}</td>"
            f"<td class=\"hash\">{_e(link['hash'] if link else 'not chained')}</td></tr>")
        for check in record["checks"]:
            if not isinstance(check, dict):
                continue
            check_rows.append(
                f"<tr><td>{_e(step)}</td><td>{_e(check.get('id'))}</td>"
                f"{_status_cell(check.get('status'))}<td>{_e(check.get('detail'))}</td></tr>")
    open_items = "".join(f"<li>{_e(item)}</li>" for item in data["open_items"])
    sever_final, sever_scope, sever_rows = _sever_section(records)
    translate_rows = _translate_section(records)

    values = {
        "banner": _e(banner),
        "banner_class": banner_css,
        "qualification": _e(qualification),
        "disclaimer": _e(DISCLAIMER),
        "overall_status": _e(status),
        "final_hash": _e(data["final_hash"]),
        "genesis_hash": _e(GENESIS_HASH),
        "step_rows": "\n".join(step_rows),
        "check_rows": "\n".join(check_rows),
        "open_items": open_items or "<li>none</li>",
        "sever_final": _e(sever_final),
        "sever_scope": _e(sever_scope),
        "sever_rows": sever_rows,
        "translate_rows": translate_rows,
    }
    return render(Path(template_path).read_text(encoding="utf-8"), values)


# --------------------------------------------------------------------------- API


def build_evidence(records: list[dict], *, output_dir: Path, config: dict,
                   stub: bool = False) -> dict:
    """Return the evidence envelope and write ``<output_dir>/report.html``.

    ``records`` are the seven step envelopes in contract order. Secrets in
    ``config`` are never read into the record or the report.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a dict of environment names to values")
    output_dir = Path(output_dir)
    links = build_chain(records, output_dir=output_dir)
    checks = _checks(records, stub)
    report_path = output_dir / REPORT_NAME
    data = {
        "records": links,
        "final_hash": links[-1]["hash"],
        "report_path": report_path.as_posix(),
        "open_items": _open_items(records, stub),
    }
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "step": "evidence",
        "mode": "stub" if stub else "live",
        # Stub checks are always incomplete, so a stub run can never reach PASS.
        "status": _overall([c["status"] for c in checks]),
        "checks": checks,
        "data": data,
        "errors": [],
    }
    atomic_write_text(report_path, render_report(records, evidence, stub=stub))
    return evidence
