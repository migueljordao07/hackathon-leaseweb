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

    def test_report_labels_adopted_existing_and_notes(self):
        translate = dict(cli.EMPTY_DATA["translate"])
        translate["resources"] = [
            {"source_id": "aws_s3_bucket.demo", "target_type": "leaseweb_object_storage",
             "method": "adopted_existing", "status": "mapped", "manual_reason": None,
             "note": "migrate+parity PASS on this bucket"},
            {"source_id": "aws_instance.app", "target_type": "openstack_compute_instance_v2",
             "method": "template", "status": "mapped", "manual_reason": None,
             "note": "flavor lsw.c7a.medium is the smallest available, not an exact <match>"}]
        records = [_record(s) for s in ("discover", "choose")] + [_record("translate", translate)]
        records += [_record(s) for s in ("migrate", "run", "parity")] + [_record("sever", SEVER)]
        with tempfile.TemporaryDirectory() as tmp:
            evidence.build_evidence(records, output_dir=Path(tmp), config={})
            html = (Path(tmp) / evidence.REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("adopted existing resource, not managed by OpenTofu", html)
        self.assertIn("lsw.c7a.medium", html)
        self.assertIn("&lt;match&gt;", html)

    def test_missing_attempts_render_placeholder(self):
        records = [_record(s) for s in cli.STEPS[:-1]]
        with tempfile.TemporaryDirectory() as tmp:
            evidence.build_evidence(records, output_dir=Path(tmp), config={})
            html = (Path(tmp) / evidence.REPORT_NAME).read_text(encoding="utf-8")
        self.assertIn("no attempts recorded", html)


if __name__ == "__main__":
    unittest.main()
