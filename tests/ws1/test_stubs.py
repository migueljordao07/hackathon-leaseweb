"""Offline tests for the WS1 discover/choose/translate stubs (WS1-01).

Run from the repository root:
    python -B -m unittest discover -s tests/ws1 -p test_stubs.py -v
Standard library only; no credentials, network, tofu, fixtures or CLI.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift.discover import choose, discover  # noqa: E402
from skyshift.translate import translate  # noqa: E402

ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}
SECRET = "SENTINEL-SECRET-do-not-leak-9f3c"
CONFIG = {
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": SECRET,
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SECRET,
    "SKYSHIFT_LLM_API_KEY": SECRET,
    "LEASEWEB_API_KEY": SECRET,
}


def _walk_statuses(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "status":
                yield value
            yield from _walk_statuses(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_statuses(item)


class StubPipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.workload = tmp / "workload"
        self.workload.mkdir()
        (self.workload / "app.py").write_text("import boto3\n", encoding="utf-8")
        (self.workload / "main.tf").write_text('resource "aws_s3_bucket" "demo" {}\n',
                                               encoding="utf-8")
        self.run_root = tmp / "out"
        self.disc = discover(self.workload, config=CONFIG, stub=True)
        self.choice = choose(self.disc["data"], config=CONFIG, stub=True)
        self.trans = translate(self.disc["data"], self.choice["data"],
                               output_dir=self.run_root, config=CONFIG, stub=True)
        self.records = [self.disc, self.choice, self.trans]

    def tearDown(self):
        self._tmp.cleanup()

    def assertEnvelope(self, record, step):
        self.assertEqual(set(record), ENVELOPE_KEYS)
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["step"], step)
        self.assertEqual(record["mode"], "stub")
        self.assertEqual(record["status"], "incomplete")
        self.assertIsInstance(record["errors"], list)
        self.assertTrue(record["checks"])
        for check in record["checks"]:
            self.assertEqual(set(check), {"id", "status", "detail"})
            self.assertIn(check["status"], {"PASS", "FAIL", "incomplete"})
        # Records must be JSON-serializable with the CLI's strict settings.
        json.dumps(record, sort_keys=True, allow_nan=False)

    def test_envelopes(self):
        for record, step in zip(self.records, ("discover", "choose", "translate")):
            with self.subTest(step=step):
                self.assertEnvelope(record, step)

    def test_no_pass_anywhere(self):
        for record in self.records:
            self.assertNotIn("PASS", list(_walk_statuses(record)))

    def test_discover_data_map(self):
        data = self.disc["data"]
        self.assertTrue({"resources", "calls", "buckets", "readiness"} <= set(data))
        types = {r["type"] for r in data["resources"]}
        self.assertTrue({"aws_instance", "aws_security_group", "aws_s3_bucket"} <= types)
        for r in data["resources"]:
            self.assertTrue({"id", "type", "provider", "region", "supported"} <= set(r))
        for c in data["calls"]:
            self.assertTrue({"file", "line", "service", "operation", "bucket",
                             "endpoint_host"} <= set(c))
        ops = {c["operation"] for c in data["calls"] if c["service"] == "s3"}
        self.assertTrue({"put_object", "get_object", "list_objects_v2"} <= ops)
        telemetry = [c for c in data["calls"]
                     if (c["endpoint_host"] or "").endswith("amazonaws.com")
                     and c["service"] != "s3"]
        self.assertTrue(telemetry, "telemetry dependency must be visible")
        self.assertEqual(len(data["buckets"]), 1)
        bucket = data["buckets"][0]
        self.assertTrue({"name", "provider", "jurisdiction", "object_count",
                         "total_bytes"} <= set(bucket))
        self.assertGreater(bucket["object_count"], 0)
        self.assertTrue(bucket["synthetic"])

    def test_readiness_computed(self):
        r = self.disc["data"]["readiness"]
        self.assertEqual(r["formula"],
                         "max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)")
        expected = max(0, 100 - 20 * r["proprietary"] - 10 * r["unsupported"]
                       - 5 * r["us_calls"])
        self.assertEqual(r["score"], expected)
        self.assertEqual(r["proprietary"],
                         sum(1 for x in self.disc["data"]["resources"] if not x["supported"]))
        self.assertGreaterEqual(r["us_calls"], 1)

    def test_choice(self):
        data = self.choice["data"]
        self.assertTrue({"target_id", "operator", "jurisdiction", "storage_mode", "criteria",
                         "prices", "explanation"} <= set(data))
        self.assertEqual(data["operator"], "Leaseweb")
        self.assertEqual(data["storage_mode"], "self_hosted_s3")
        for price in data["prices"]:
            self.assertTrue({"item", "amount", "currency", "unit", "source_url",
                             "assumptions"} <= set(price))
            self.assertIsNone(price["amount"])
        self.assertIn("SYNTHETIC", data["explanation"]["text"])

    def test_translate(self):
        data = self.trans["data"]
        self.assertTrue({"provider", "files", "resources", "validation"} <= set(data))
        main_tf = self.run_root / "iac" / "main.tf"
        self.assertTrue(main_tf.is_file())
        self.assertEqual(data["files"], [main_tf.as_posix()])
        self.assertIn("NON-DEPLOYABLE", main_tf.read_text(encoding="utf-8"))
        # Only the IaC artifact is written; no canonical JSON records.
        written = sorted(p.relative_to(self.run_root).as_posix()
                         for p in self.run_root.rglob("*") if p.is_file())
        self.assertEqual(written, ["iac/main.tf"])
        v = data["validation"]
        self.assertEqual(v["method"], "offline_schema")
        self.assertIsNone(v["init_exit"])
        self.assertIsNone(v["validate_exit"])
        self.assertEqual(v["attempts"], 0)
        self.assertTrue(v["diagnostics"])
        statuses = {m["source_id"]: m for m in data["resources"]}
        self.assertEqual(statuses["aws_s3_bucket.demo"]["target_type"], "self_hosted_s3")
        self.assertEqual(statuses["aws_instance.app"]["method"], "template")
        manual = [m for m in data["resources"] if m["status"] == "manual"]
        self.assertTrue(all(m["manual_reason"] for m in manual))
        for m in data["resources"]:
            self.assertTrue({"source_id", "target_type", "method", "status",
                             "manual_reason"} <= set(m))

    def test_secret_absent(self):
        for record in self.records:
            self.assertNotIn(SECRET, json.dumps(record))
        for path in self.run_root.rglob("*"):
            if path.is_file():
                self.assertNotIn(SECRET, path.read_text(encoding="utf-8"))

    def test_envelope_inputs_rejected(self):
        with self.assertRaises(ValueError):
            choose(self.disc, config=CONFIG, stub=True)
        with self.assertRaises(ValueError):
            translate(self.disc["data"], self.choice, output_dir=self.run_root,
                      config=CONFIG, stub=True)
        with self.assertRaises(ValueError):
            choose({"resources": []}, config=CONFIG, stub=True)

    def test_non_stub_is_incomplete_not_live_pass(self):
        # Live choose/translate are real since WS1-03/04 (see test_choice.py and
        # test_templates.py); only discover without credentials is checked here.
        live = [discover(self.workload, config=CONFIG)]
        for record in live:
            self.assertEqual(set(record), ENVELOPE_KEYS)
            self.assertEqual(record["mode"], "live")
            # No credentials/coverage: never an overall live PASS (individual measured
            # checks may PASS once discovery is real, WS1-02).
            self.assertEqual(record["status"], "incomplete")
            self.assertTrue(record["errors"])
        self.assertFalse((Path(self._tmp.name) / "live").exists())


class ImportSideEffectTest(unittest.TestCase):
    def test_import_starts_nothing(self):
        code = (
            "import sys, threading\n"
            "import skyshift.discover, skyshift.translate\n"
            "bad = {'boto3', 'botocore', 'requests', 'urllib.request', 'http.client',"
            " 'subprocess', 'socket', 'yaml'} & set(sys.modules)\n"
            "assert not bad, bad\n"
            "assert threading.active_count() == 1\n"
        )
        env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(REPO_ROOT),
                                env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
