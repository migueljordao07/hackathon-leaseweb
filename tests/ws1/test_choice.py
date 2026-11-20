"""Offline tests for the deterministic Leaseweb target choice (WS1-03). No live calls."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skyshift.discover import (_live_choose, choose, load_targets, parse_gate_record,
                               select_target)

DATA_MAP = {"resources": [], "calls": [], "buckets": [], "readiness": {}}
GATE_TEXT = """# Human VM validation record
Provider choice: OpenStack (Leaseweb Public Cloud).

## 1. Moto and target put/get/list

Measured: Leaseweb bucket: put ok.
Result: **PASS**. Limitation: path-style.

## Human decision

go-with-fallback (4/5). Signed: A Human, 2026-11-20 14:20 UTC.
"""


def run(config, gate, targets=None):
    return _live_choose(config, gate=gate, targets=targets or load_targets(),
                        explain=lambda p, t, c: {"mode": "replay", "text": t})


class GateRecordTest(unittest.TestCase):
    def test_parse_signed_record(self):
        gate = parse_gate_record(GATE_TEXT)
        self.assertEqual(gate["decision"], "go-with-fallback")
        self.assertEqual(gate["provider"], "openstack")
        self.assertTrue(gate["native_storage_verified"])

    def test_unsigned_record_has_no_decision(self):
        gate = parse_gate_record(GATE_TEXT.replace("Signed: A Human", "pending"))
        self.assertIsNone(gate["decision"])

    def test_failed_check1_is_not_native(self):
        gate = parse_gate_record(GATE_TEXT.replace("**PASS**", "**FAIL**"))
        self.assertFalse(gate["native_storage_verified"])

    def test_repository_record_parses(self):
        gate = parse_gate_record(
            (Path(__file__).resolve().parents[2] / "tasks/WS0-setup/validation.md")
            .read_text(encoding="utf-8"))
        self.assertIn(gate["decision"], ("go", "go-with-fallback"))
        self.assertEqual(gate["provider"], "openstack")


class ChoiceTest(unittest.TestCase):
    def setUp(self):
        self.gate = parse_gate_record(GATE_TEXT)

    def test_native_preferred_when_accessible(self):
        rec = run({}, self.gate)
        self.assertEqual(rec["status"], "PASS")
        self.assertEqual(rec["data"]["target_id"], "leaseweb-native")
        self.assertEqual(rec["data"]["storage_mode"], "native_s3")

    def test_selfhost_fallback_only_when_verified(self):
        gate = dict(self.gate, native_storage_verified=False, selfhosted_verified=True)
        rec = run({}, gate)
        self.assertEqual(rec["data"]["target_id"], "leaseweb-selfhosted")
        gate = dict(self.gate, native_storage_verified=False, selfhosted_verified=False)
        rec = run({}, gate)
        self.assertEqual(rec["status"], "incomplete")
        self.assertIsNone(rec["data"]["target_id"])

    def test_unknown_or_unapproved_provider(self):
        rec = run({"SKYSHIFT_TARGET_PROVIDER": "aws"}, self.gate)
        self.assertEqual(rec["status"], "incomplete")
        self.assertIsNone(rec["data"]["target_id"])
        rec = run({}, dict(self.gate, decision=None))
        self.assertEqual(rec["status"], "incomplete")
        rec = run({}, {"decision": None, "provider": None, "native_storage_verified": False})
        self.assertIsNone(rec["data"]["target_id"])

    def test_matching_config_provider(self):
        rec = run({"SKYSHIFT_TARGET_PROVIDER": "OpenStack"}, self.gate)
        self.assertEqual(rec["status"], "PASS")

    def test_eu_region_alone_proves_nothing(self):
        dm = dict(DATA_MAP, resources=[{"id": "x", "type": "aws_s3_bucket",
                                        "region": "eu-central-1"}])
        gate = {"decision": None, "provider": None, "native_storage_verified": False}
        rec = _live_choose({}, gate=gate, targets=load_targets(),
                           explain=lambda p, t, c: {"mode": "replay", "text": t})
        self.assertEqual(rec["status"], "incomplete")
        self.assertIsNone(rec["data"]["jurisdiction"])
        del dm

    def test_only_leaseweb_and_prices_unknown(self):
        targets = load_targets()
        self.assertTrue(all(t["operator"] == "Leaseweb" for t in targets))
        rec = run({}, self.gate)
        self.assertTrue(rec["data"]["prices"])
        for price in rec["data"]["prices"]:
            self.assertIsNone(price["amount"])
        self.assertTrue(any("prices unverified" in i for i in rec["data"]["open_items"]))

    def test_numeric_price_needs_citation(self):
        targets = load_targets()
        bad = json.loads(json.dumps(targets))
        bad[0]["prices"][0]["amount"] = 0.1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.yaml"
            path.write_text(json.dumps({"schema_version": 1, "targets": bad}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_targets(path)
            bad[0]["operator"] = "OtherCloud"
            bad[0]["prices"][0]["source_url"] = "https://example.invalid/"
            path.write_text(json.dumps({"schema_version": 1, "targets": bad}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_targets(path)

    def test_deterministic(self):
        self.assertEqual(run({}, self.gate), run({}, self.gate))

    def test_secret_redaction(self):
        secret = "S3CRET-VALUE-0123456789abcdef"
        config = {"SKYSHIFT_TARGET_SECRET_ACCESS_KEY": secret, "LEASEWEB_API_KEY": secret}
        self.assertNotIn(secret, json.dumps(run(config, self.gate)))

    def test_select_target_pure(self):
        sel = select_target(load_targets(), self.gate, None)
        self.assertEqual(sel["provider"], "openstack")

    def test_stub_unchanged(self):
        rec = choose(DATA_MAP, config={}, stub=True)
        self.assertEqual((rec["mode"], rec["status"]), ("stub", "incomplete"))


if __name__ == "__main__":
    unittest.main()


class VariableResolutionTest(unittest.TestCase):
    def test_var_with_literal_default_is_resolvable(self):
        from skyshift.discover import _resolvable
        self.assertTrue(_resolvable('"${var.a}-sg"', {"a": "x"}))
        self.assertFalse(_resolvable("${var.missing}", {"a": "x"}))
        self.assertFalse(_resolvable('${upper(var.a)}', {"a": "x"}))
        self.assertFalse(_resolvable('${var.a}${local.b}', {"a": "x"}))
