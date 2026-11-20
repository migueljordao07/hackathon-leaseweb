"""Validate the limited task front matter and render the Git-only board (stdlib)."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
from pathlib import Path, PurePosixPath
import re
import sys

HOMES = {
    "WS0": "WS0-setup",
    "WS1": "WS1-discover-translate",
    "WS2": "WS2-data-parity",
    "WS3": "WS3-severance-ai",
    "WS4": "WS4-integration-delivery",
}
FIELDS = {"id", "title", "workstream", "status", "owner", "priority", "depends_on",
          "blocks", "files", "estimate", "claimed_at", "updated_at"}
LISTS = {"depends_on", "blocks", "files"}
STATUSES = {"todo", "claimed", "in_progress", "blocked", "review", "done", "cut"}
OWNERS = {None, "claude-1", "claude-2", "codex", "gemini"}
SECTIONS = ("Goal", "Context", "Steps", "Acceptance criteria", "Out of scope",
            "Fallback if blocked", "Log")
ID = re.compile(r"WS[0-4]-(?:0[1-9]|[1-9][0-9])\Z")


def scalar(text: str):
    text = text.strip()
    if text == "null":
        return None
    if not text:
        raise ValueError("empty scalar; use null or [] explicitly")
    if text[0] in "\"'":
        value = ast.literal_eval(text)
        if not isinstance(value, str):
            raise ValueError("expected a string scalar")
        return value
    if any(c in text for c in "{}[]#"):
        raise ValueError("unsupported scalar syntax")
    return text


def inline_list(text: str) -> list:
    if not (text.startswith("[") and text.endswith("]")):
        raise ValueError("list must use [...] or indented - entries")
    inside = text[1:-1].strip()
    if not inside:
        return []
    # Paths/IDs cannot contain commas; quoted scalar values remain supported.
    return [scalar(item) for item in inside.split(",")]


def parse_task(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening front-matter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing front-matter delimiter") from exc
    task = {}
    active = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.startswith("  - "):
            if active not in LISTS:
                raise ValueError("list item without list field")
            task[active].append(scalar(line[4:]))
            continue
        match = re.fullmatch(r"([a-z_]+):(?:\s+(.*))?", line)
        if not match:
            raise ValueError(f"unsupported front-matter line: {line}")
        key, value = match.groups()
        if key not in FIELDS or key in task:
            raise ValueError(f"unknown or duplicate field: {key}")
        active = key if key in LISTS else None
        task[key] = (inline_list(value.strip()) if value else []) if active else scalar(value or "")
    if set(task) != FIELDS:
        raise ValueError(f"missing fields: {', '.join(sorted(FIELDS - set(task)))}")
    task["_path"] = path
    task["_body"] = "\n".join(lines[end + 1:])
    return task


def validate(tasks: list[dict]) -> list[str]:
    errors = []
    by_id = {}
    paths = []
    for task in tasks:
        label = str(task["_path"])
        def error(message):
            errors.append(f"{label}: {message}")
        task_id, ws = task["id"], task["workstream"]
        if not isinstance(task_id, str) or not ID.fullmatch(task_id):
            error("invalid id")
            continue
        if task_id in by_id:
            error(f"duplicate id {task_id}")
        by_id[task_id] = task
        if ws not in HOMES or not task_id.startswith(ws + "-"):
            error("invalid workstream/id combination")
        elif task["_path"].parent.name != HOMES[ws]:
            error("task is in the wrong home")
        if not task["_path"].name.startswith(task_id + "-"):
            error("filename must start with id followed by a slug")
        if not isinstance(task["title"], str) or not task["title"].strip():
            error("title must be nonempty")
        if task["status"] not in STATUSES:
            error("invalid status")
        if task["owner"] not in OWNERS:
            error("invalid owner")
        if task["priority"] not in {"P0", "P1", "P2"}:
            error("invalid priority")
        if not isinstance(task["estimate"], str) or not re.fullmatch(r"(?:[2-5][0-9]|60)m", task["estimate"]):
            error("estimate must be 20m through 60m")
        for key in ("claimed_at", "updated_at"):
            value = task[key]
            if value is not None:
                try:
                    if not isinstance(value, str) or "T" not in value or datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
                        raise ValueError("timezone required")
                except (ValueError, TypeError):
                    error(f"{key} must be null or a timezone-qualified ISO timestamp")
        if ws != "WS0" and task["status"] in {"claimed", "in_progress", "review"}:
            if task["owner"] is None or task["claimed_at"] is None:
                error("active task requires owner and claimed_at")
        for key in LISTS:
            value = task[key]
            if not isinstance(value, list) or not all(isinstance(x, str) and x for x in value):
                error(f"{key} must be a string list")
            elif len(set(value)) != len(value):
                error(f"{key} has duplicate entries")
        for name in SECTIONS:
            if not re.search(r"^## " + re.escape(name) + r"\s*$", task["_body"], re.M):
                error(f"missing body section {name}")
        if not task["files"]:
            error("files must be nonempty and narrowly scoped")
        for file in task["files"]:
            if not isinstance(file, str):
                continue
            p = PurePosixPath(file)
            if (not file or p.is_absolute() or ".." in p.parts or "\\" in file
                    or ":" in file or any(c in file for c in "*?[]") or file.endswith("/")
                    or str(p) != file or p.name in {".env", ".git"} or ".git" in p.parts
                    or (p.name.startswith(".env.") and p.name != ".env.example")):
                error(f"unsafe or non-exact file path {file!r}")
            else:
                paths.append((file, ws, task_id))
    for task in tasks:
        task_id = task["id"]
        for field in ("depends_on", "blocks"):
            for ref in task[field]:
                if ref not in by_id:
                    errors.append(f"{task_id}: unknown {field} reference {ref}")
                elif ref == task_id:
                    errors.append(f"{task_id}: self dependency")
                else:
                    reverse = "blocks" if field == "depends_on" else "depends_on"
                    if task_id not in by_id[ref][reverse]:
                        errors.append(f"{task_id}: {field} {ref} missing reciprocal {reverse}")
        for ref in task["depends_on"]:
            dep = by_id.get(ref)
            if dep and dep["workstream"] != task["workstream"] and not ref.endswith("-01"):
                if "Unavoidable cross-workstream dependency" not in task["_body"]:
                    errors.append(f"{task_id}: non-stub cross-stream dependency {ref} needs justification")
    for i, (file, ws, task_id) in enumerate(paths):
        for other, other_ws, other_id in paths[:i]:
            if ws != other_ws and (file == other or file.startswith(other + "/") or other.startswith(file + "/")):
                errors.append(f"ownership conflict: {task_id} and {other_id}: {file} / {other}")
    visiting, visited = set(), set()
    def visit(task_id):
        if task_id in visiting:
            errors.append(f"dependency cycle at {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for ref in by_id[task_id]["depends_on"]:
            if ref in by_id:
                visit(ref)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in sorted(by_id):
        visit(task_id)
    return errors


def load_tasks(root: Path) -> list[dict]:
    tasks = []
    # Do not hide malformed filenames by filtering only valid IDs.
    for home in HOMES.values():
        for path in sorted((root / home).glob("*.md")):
            if path.name == "validation.md":
                continue  # Human VM record is not an executable task.
            tasks.append(parse_task(path))
    return tasks


def render(tasks: list[dict]) -> str:
    lines = ["# SkyShift task board", "", "Generated by `python tasks/board.py`; task files are authoritative.",
             "Planning estimates are not measured durations. Read README.md and contracts.md before claiming.", ""]
    for ws in HOMES:
        lines += [f"## {ws}", "", "| id | title | status | owner | priority | depends_on |",
                  "|---|---|---|---|---|---|"]
        for task in sorted(tasks, key=lambda t: t["id"]):
            if task["workstream"] == ws:
                title = task["title"].replace("|", "\\|")
                link = f'[{task["id"]}]({HOMES[ws]}/{task["_path"].name})'
                cells = [link, title, task["status"], task["owner"] or "—", task["priority"], ", ".join(task["depends_on"]) or "—"]
                lines.append("| " + " | ".join(cells) + " |")
        lines += [""]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate without changing BOARD.md")
    mode.add_argument("--ready", choices=HOMES, help="list claimable todo tasks")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        tasks = load_tasks(root)
        errors = validate(tasks)
    except (ValueError, TypeError, OSError, SyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.ready:
        by_id = {t["id"]: t for t in tasks}
        ready = [t for t in tasks if t["workstream"] == args.ready and t["status"] == "todo"
                 and all(by_id[ref]["status"] == "done" for ref in t["depends_on"])]
        for task in sorted(ready, key=lambda t: (t["priority"], t["id"])):
            note = " [human-only]" if task["workstream"] == "WS0" else ""
            print(f'{task["id"]} {task["priority"]} {task["title"]}{note}')
        if not ready:
            print(f"No ready tasks for {args.ready}.")
    elif args.check:
        print(f"OK: {len(tasks)} tasks; schema, graph and ownership valid.")
    else:
        (root / "BOARD.md").write_text(render(tasks), encoding="utf-8")
        print(f"Generated tasks/BOARD.md from {len(tasks)} tasks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
