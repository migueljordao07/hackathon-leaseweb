"""Offline regression checks for the planning board; no product or VM tests."""
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import board


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.task = {
            "id": "WS1-01", "title": "Offline stub", "workstream": "WS1",
            "status": "todo", "owner": None, "priority": "P0", "depends_on": [],
            "blocks": [], "files": ["skyshift/discover.py"], "estimate": "30m",
            "claimed_at": None, "updated_at": None,
            "_path": Path("WS1-discover-translate/WS1-01-stub.md"),
            "_body": "\n".join("## " + s for s in board.SECTIONS),
        }

    def second(self):
        task = copy.deepcopy(self.task)
        task.update(id="WS2-01", workstream="WS2", files=["skyshift/migrate.py"],
                    _path=Path("WS2-data-parity/WS2-01-stub.md"))
        return task

    def test_valid_task(self):
        self.assertEqual(board.validate([self.task]), [])

    def test_duplicate_id(self):
        self.assertTrue(any("duplicate id" in e for e in board.validate([self.task, copy.deepcopy(self.task)])))

    def test_unknown_dependency(self):
        self.task["depends_on"] = ["WS4-99"]
        self.assertTrue(any("unknown depends_on" in e for e in board.validate([self.task])))

    def test_cycle(self):
        other = self.second()
        for task, ref in ((self.task, "WS2-01"), (other, "WS1-01")):
            task["depends_on"] = [ref]
            task["blocks"] = [ref]
        self.assertTrue(any("cycle" in e for e in board.validate([self.task, other])))

    def test_file_overlap(self):
        other = self.second()
        other["files"] = self.task["files"][:]
        self.assertTrue(any("ownership conflict" in e for e in board.validate([self.task, other])))

    def test_reciprocal_blocks(self):
        other = self.second()
        other["depends_on"] = ["WS1-01"]
        self.assertTrue(any("reciprocal" in e for e in board.validate([self.task, other])))
        self.task["blocks"] = ["WS2-01"]
        self.assertEqual(board.validate([self.task, other]), [])

    def test_status_owner_estimate_timestamp(self):
        for field, value in (("status", "running"), ("owner", "human"),
                             ("estimate", "90m"), ("updated_at", "2026-11-20")):
            with self.subTest(field=field):
                task = copy.deepcopy(self.task)
                task[field] = value
                self.assertTrue(board.validate([task]))

    def test_active_claim_requires_owner(self):
        self.task["status"] = "claimed"
        self.assertTrue(board.validate([self.task]))
        self.task.update(owner="claude-1", claimed_at="2026-11-20T12:00:00Z")
        self.assertEqual(board.validate([self.task]), [])

    def test_reassigned_claude_owner(self):
        self.task.update(owner="claude-3", status="claimed", claimed_at="2026-11-20T12:00:00Z")
        self.assertEqual(board.validate([self.task]), [])
        self.task["owner"] = "codex"
        self.assertTrue(any("invalid owner" in e for e in board.validate([self.task])))

    def test_unsafe_paths(self):
        for file in ("../README.md", "/etc/passwd", "C:/private", "skyshift/*", ".env", ".env.local", "skyshift/"):
            with self.subTest(file=file):
                self.task["files"] = [file]
                self.assertTrue(any("unsafe" in e for e in board.validate([self.task])))

    def test_missing_section(self):
        self.task["_body"] = ""
        self.assertEqual(sum("missing body section" in e for e in board.validate([self.task])), len(board.SECTIONS))

    def test_parse_lists_and_missing_fields(self):
        text = "---\n" + "\n".join(
            f"{key}: " + ("null" if self.task[key] is None else str(self.task[key]))
            for key in sorted(board.FIELDS)) + "\n---\n" + self.task["_body"]
        text = text.replace("files: ['skyshift/discover.py']", "files:\n  - skyshift/discover.py")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "WS1-01-stub.md"
            path.write_text(text, encoding="utf-8")
            parsed = board.parse_task(path)
            self.assertEqual(parsed["files"], ["skyshift/discover.py"])
            self.assertEqual(parsed["depends_on"], [])
            path.write_text(text.replace("owner: null\n", ""), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing fields"):
                board.parse_task(path)

    def test_render_deterministic(self):
        other = self.second()
        self.assertEqual(board.render([self.task, other]), board.render([other, self.task]))
        self.assertIn("## WS4", board.render([self.task]))
        self.assertTrue(board.render([self.task]).endswith("\n"))
        self.assertFalse(board.render([self.task]).endswith("\n\n"))

    def run_cli(self, tasks, args):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "board.py"
            snapshot = Path(directory) / "BOARD.md"
            snapshot.write_text("sentinel", encoding="utf-8")
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(board, "__file__", str(script)), patch.object(board, "load_tasks", return_value=tasks), redirect_stdout(output), redirect_stderr(errors):
                code = board.main(args)
            return code, output.getvalue(), errors.getvalue(), snapshot.read_text(encoding="utf-8")

    def test_check_is_read_only(self):
        code, output, errors, snapshot = self.run_cli([self.task], ["--check"])
        self.assertEqual(code, 0)
        self.assertIn("1 tasks", output)
        self.assertEqual(errors, "")
        self.assertEqual(snapshot, "sentinel")

    def test_cli_regenerates_board(self):
        code, _, _, snapshot = self.run_cli([self.task], [])
        self.assertEqual(code, 0)
        self.assertEqual(snapshot, board.render([self.task]))

    def test_ready_waits_for_done_not_cut_or_review(self):
        other = self.second()
        other["depends_on"] = [self.task["id"]]
        self.task["blocks"] = [other["id"]]
        for status in ("todo", "blocked", "cut", "review", "done"):
            with self.subTest(status=status):
                self.task.update(status=status, owner="claude-1", claimed_at="2026-11-20T12:00:00Z")
                code, output, _, snapshot = self.run_cli([self.task, other], ["--ready", "WS2"])
                self.assertEqual(code, 0)
                self.assertEqual("WS2-01 P0" in output, status == "done")
                self.assertEqual(snapshot, "sentinel")

    def test_ready_human_gate_label(self):
        self.task.update(id="WS0-01", workstream="WS0", files=["tasks/WS0-setup/validation.md"],
                         _path=Path("WS0-setup/WS0-01-gate.md"))
        code, output, _, _ = self.run_cli([self.task], ["--ready", "WS0"])
        self.assertEqual(code, 0)
        self.assertIn("[human-only]", output)

    def test_invalid_graph_does_not_overwrite_board(self):
        self.task["depends_on"] = ["WS2-99"]
        code, _, errors, snapshot = self.run_cli([self.task], [])
        self.assertEqual(code, 1)
        self.assertIn("unknown depends_on", errors)
        self.assertEqual(snapshot, "sentinel")

    def test_cross_stream_prefix_collision(self):
        other = self.second()
        other["files"] = ["skyshift/discover.py/child"]
        self.assertTrue(any("ownership conflict" in e for e in board.validate([self.task, other])))

    def test_unknown_and_duplicate_front_matter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "WS1-01-stub.md"
            for text in ("---\nid: WS1-01\nid: WS1-01\n---\n", "---\nexecutor: codex\n---\n"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "unknown or duplicate"):
                    board.parse_task(path)


if __name__ == "__main__":
    unittest.main()
