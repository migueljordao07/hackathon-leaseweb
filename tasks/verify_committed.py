"""Verify only committed planning files in a disposable Git archive, not a VM."""
import io
from pathlib import Path, PurePosixPath
import re
import runpy
import subprocess
import sys
import tempfile
import zipfile


def main():
    repo = Path(__file__).resolve().parent.parent
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "--format=zip", revision, "tasks"], cwd=repo)
    with tempfile.TemporaryDirectory(prefix="skyshift-planning-") as directory:
        root = Path(directory)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for member in bundle.infolist():
                path = PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts or path.parts[0] != "tasks":
                    raise ValueError("unsafe planning archive path")
            bundle.extractall(root)
        api = runpy.run_path(str(root / "tasks/board.py"))
        tasks = api["load_tasks"](root / "tasks")
        assert not api["validate"](tasks), "invalid committed graph"
        assert (root / "tasks/BOARD.md").read_text(encoding="utf-8") == api["render"](tasks), "stale board snapshot"
        for task in tasks:
            headings = re.findall(r"^## (.+)$", task["_body"], re.M)
            assert headings == list(api["SECTIONS"]), f"wrong section order/count: {task['id']}"
        for name in ("channel", "inbox-WS1", "inbox-WS2", "inbox-WS3", "inbox-WS4", "inbox-humans"):
            assert (root / f"tasks/comms/{name}.md").is_file(), f"missing comms: {name}"
        for document in (root / "tasks").rglob("*.md"):
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" not in target and not target.startswith("#"):
                    assert (document.parent / target.split("#")[0]).exists(), f"broken link: {document}: {target}"
        for args in (["test_board.py", "-v"], ["board.py", "--check"],
                     *(["board.py", "--ready", ws] for ws in api["HOMES"]), ["summarize.py"]):
            subprocess.run([sys.executable, "-B", str(root / "tasks" / args[0]), *args[1:]], cwd=root, check=True, timeout=60)
        assert not (root / "ideia-final.md").exists(), "archive unexpectedly contains untracked proposal"
        print(f"Committed planning archive verified: {revision}")
        print(f"{len(tasks)} task documents; exact sections, comms, links and board snapshot valid.")
        print("No untracked proposal, product module, service, credential or VM was used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
