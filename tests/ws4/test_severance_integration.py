"""Offline severance report checks (WS4-06); injected records, not live acceptance."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skyshift import cli, evidence


def _record(step: str, data: dict | None = None) -> dict:
    return {"schema_version": 1, "step": step, "mode": "live", "status": "PASS",
            "checks": [{"id": "measured", "status": "PASS", "detail": "injected"}],
            "data": data if data is not None else dict(cli.EMPTY_DATA[step]), "errors": []}


SEVER = {"attempts": [
    {"number": 1, "status": "FAIL", "blocked": 1, "bypasses": [], "replacement": None,
     "events": [{"host": "monitoring.<b>amazonaws</b>.com", "port": 443, "decision": "deny",
                 "via": "proxy"}]},
    {"number": 2, "status": "PASS", "blocked": 0, "bypasses": [],
     "replacement": {"id": "local-otel", "mode": "replay"},
     "events": [{"host": "127.0.0.1", "port": 4318, "decision": "allow", "via": "proxy"}]}],
    "max_attempts": 2, "final": "green", "radar_scope": "socket detection only"}


class SeveranceReportTest(unittest.TestCase):
    def test_report_keeps_red_attempt_and_escapes(self):
        records = [_record(s) for s in cli.STEPS[:-2]] + [_record("sever", SEVER)]
        with tempfile.TemporaryDirectory() as tmp:
            result = evidence.build_evidence(records, output_dir=Path(tmp), config={})
            html = (Path(tmp) / evidence.REPORT_NAME).read_text(encoding="utf-8")
        self.assertEqual(result["status"], "PASS")
        self.assertIn("Severance drill", html)
        self.assertIn("deny via proxy", html)
        self.assertIn("local-otel (replay)", html)
        self.assertIn("&lt;b&gt;amazonaws", html)
        self.assertNotIn("<b>amazonaws", html)
        self.assertIn("not proof of zero leakage", html)

    def test_missing_attempts_render_placeholder(self):
        records = [_record(s) for s in cli.STEPS[:-1]]
        with tempfile.TemporaryDirectory() as tmp:
            evidence.build_evidence(records, output_dir=Path(tmp), config={})
            html = (Path(tmp) / evidence.REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("no attempts recorded", html)


if __name__ == "__main__":
    unittest.main()
