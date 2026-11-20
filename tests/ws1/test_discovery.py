"""Tests for live discovery (WS1-02): HCL/AST analysis, inventory and readiness.

Run from the repository root:
    python -B -m unittest discover -s tests/ws1 -p test_discovery.py -v
HCL tests need python-hcl2 and PyYAML; source inventory is mocked (no boto3/network).
Live read-only inventory test: SKYSHIFT_WS1_LIVE_TESTS=1 plus SKYSHIFT_SOURCE_* keys and
SKYSHIFT_WS1_EXPECTED_COUNT / SKYSHIFT_WS1_EXPECTED_BYTES (human-provided expectation).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import discover as disc  # noqa: E402

HAS_HCL = all(importlib.util.find_spec(m) for m in ("hcl2", "yaml"))
SECRET = "SENTINEL-SECRET-ws1-02-7d1e"
CREDS = {
    "SKYSHIFT_SOURCE_ACCESS_KEY_ID": "AKIA" + SECRET,
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": SECRET,
    "SKYSHIFT_SOURCE_ENDPOINT_URL": "http://127.0.0.1:9000",
}

MAIN_TF = f"""
provider "aws" {{
  region = "eu-central-1"
}}

variable "subnet" {{}}

resource "aws_security_group" "app" {{
  name = "app"
}}

resource "aws_instance" "app" {{
  ami                    = "ami-0123456789"
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.app.id]
  subnet_id              = var.subnet
  user_data              = "{SECRET}"
}}

resource "aws_s3_bucket" "demo" {{
  bucket = "demo-src"
}}

resource "aws_db_instance" "db" {{
  engine = "postgres"
}}
"""

APP_PY = '''
"""Synthetic app. Docs: https://docs.aws.amazon.com/ is a docstring, not a call."""
import os
import boto3 as b3
import requests
from boto3 import client as make_client

TELEMETRY_URL = "https://metrics.eu-west-1.amazonaws.com/v1/ingest"

s3 = b3.client("s3", endpoint_url="http://127.0.0.1:9000")
cw = make_client("cloudwatch")


def run():
    s3.put_object(Bucket="demo-src", Key="a.txt", Body=b"x")
    s3.get_object(Bucket="demo-src", Key="a.txt"); s3.get_object(Bucket="demo-src", Key="a.txt")
    s3.list_objects_v2(Bucket="demo-src")
    s3.select_object_content(Bucket="demo-src", Key="a.txt")
    s3.select_object_content(Bucket="demo-src", Key="b.txt")
    cw.put_metric_data(Namespace="app", MetricData=[])
    requests.post(os.environ.get("HOOK_URL"), json={})
    getattr(s3, os.environ["OP"])(Bucket="demo-src")
'''


class FakePaginator:
    def __init__(self, pages=None, error=None):
        self.pages, self.error = pages or [], error

    def paginate(self, **kwargs):
        if self.error:
            raise self.error
        yield from self.pages


class FakeClient:
    def __init__(self, paginator):
        self._paginator = paginator

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self._paginator


class DeniedError(Exception):
    def __init__(self):
        super().__init__(f"Access Denied for {SECRET}")
        self.response = {"Error": {"Code": "AccessDenied", "Message": f"leak {SECRET}"}}


def _workload(tmp: Path, tf: str | None = MAIN_TF, py: str | None = APP_PY) -> Path:
    workload = tmp / "workload"
    workload.mkdir()
    if tf is not None:
        (workload / "main.tf").write_text(tf, encoding="utf-8")
    if py is not None:
        (workload / "app.py").write_text(py, encoding="utf-8")
    return workload


class PythonScanTest(unittest.TestCase):
    """AST scanning needs only the standard library."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workload = _workload(Path(self._tmp.name), tf=None)
        self.calls, self.findings = disc.scan_python(self.workload, "wl")

    def tearDown(self):
        self._tmp.cleanup()

    def ops(self, service):
        return [c["operation"] for c in self.calls if c["service"] == service]

    def test_alias_calls_detected(self):
        self.assertEqual(self.ops("s3"), ["put_object", "get_object", "list_objects_v2",
                                          "select_object_content", "select_object_content"])
        self.assertEqual(self.ops("cloudwatch"), ["put_metric_data"])
        put = next(c for c in self.calls if c["operation"] == "put_object")
        self.assertEqual(put["bucket"], "demo-src")
        self.assertEqual(put["endpoint_host"], "127.0.0.1")
        self.assertEqual(put["file"], "wl/app.py")

    def test_same_line_deduplicated(self):
        self.assertEqual(self.ops("s3").count("get_object"), 1)

    def test_hidden_telemetry_visible(self):
        literal = [c for c in self.calls if c["operation"] == "literal_url"]
        self.assertEqual([c["endpoint_host"] for c in literal],
                         ["metrics.eu-west-1.amazonaws.com"])
        self.assertTrue(literal[0]["us_controlled"])
        # Docstring URLs and the boto3 endpoint literal are not separate calls.
        hosts = {c["endpoint_host"] for c in self.calls}
        self.assertNotIn("docs.aws.amazon.com", hosts)

    def test_dynamic_findings_visible(self):
        kinds = sorted(f["kind"] for f in self.findings)
        self.assertEqual(kinds, ["dynamic_dispatch", "unresolved_endpoint"])
        http = [c for c in self.calls if c["service"] == "http" and c["operation"] == "post"]
        self.assertEqual(len(http), 1)
        self.assertIsNone(http[0]["endpoint_host"])

    def test_readiness_counters(self):
        resources = [{"supported": True}, {"supported": False, "proprietary": True}]
        r = disc.compute_readiness(resources, self.calls, frozenset({
            "put_object", "get_object", "list_objects_v2"}))
        # proprietary: db; unsupported: select_object_content (distinct name);
        # us_calls: cloudwatch on SDK default endpoint + literal amazonaws.com telemetry.
        self.assertEqual((r["proprietary"], r["unsupported"], r["us_calls"]), (1, 1, 2))
        self.assertEqual(r["score"], 60)
        self.assertEqual(r["formula"],
                         "max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)")

    def test_invalid_python_raises(self):
        (self.workload / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            disc.scan_python(self.workload, "wl")


class InventoryTest(unittest.TestCase):
    """Source inventory with a mocked paginator (no boto3 or network)."""

    def run_inventory(self, paginator, config=CREDS):
        with mock.patch.object(disc, "_source_client", return_value=FakeClient(paginator)):
            return disc.inventory_buckets(["demo-src"], dict(config))

    def test_paginated_counts_and_bytes(self):
        pages = [{"Contents": [{"Size": 10}, {"Size": 5}]}, {"KeyCount": 0}, {"Contents": [
            {"Size": 7}]}]
        buckets, check = self.run_inventory(FakePaginator(pages))
        self.assertEqual(check["status"], "PASS")
        self.assertEqual((buckets[0]["object_count"], buckets[0]["total_bytes"]), (3, 22))
        self.assertEqual(buckets[0]["jurisdiction"], "US-controlled")

    def test_genuine_empty_bucket(self):
        buckets, check = self.run_inventory(FakePaginator([{"KeyCount": 0}]))
        self.assertEqual(check["status"], "PASS")
        self.assertEqual((buckets[0]["object_count"], buckets[0]["total_bytes"]), (0, 0))

    def test_denied_inventory_is_fail(self):
        buckets, check = self.run_inventory(FakePaginator(error=DeniedError()))
        self.assertEqual(check["status"], "FAIL")
        self.assertIn("AccessDenied", check["detail"])
        self.assertIsNone(buckets[0]["object_count"])
        self.assertNotIn(SECRET, json.dumps([buckets, check]))

    def test_absent_credentials_incomplete(self):
        with mock.patch.object(disc, "_source_client") as factory:
            buckets, check = disc.inventory_buckets(["demo-src"], {})
        factory.assert_not_called()
        self.assertEqual(check["status"], "incomplete")
        self.assertIsNone(buckets[0]["object_count"])
        self.assertIsNone(buckets[0]["total_bytes"])


@unittest.skipUnless(HAS_HCL, "python-hcl2 and PyYAML required for HCL discovery tests")
class LiveDiscoverOfflineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workload = _workload(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def discover(self, config, paginator=None):
        paginator = paginator or FakePaginator([{"Contents": [{"Size": 4}, {"Size": 6}]}])
        with mock.patch.object(disc, "_source_client", return_value=FakeClient(paginator)):
            return disc.discover(self.workload, config=dict(config))

    def test_full_data_map(self):
        record = self.discover(CREDS)
        self.assertEqual(set(record), {"schema_version", "step", "mode", "status", "checks",
                                       "data", "errors"})
        self.assertEqual((record["step"], record["mode"]), ("discover", "live"))
        data = record["data"]
        by_id = {r["id"]: r for r in data["resources"]}
        self.assertEqual(list(by_id), ["aws_security_group.app", "aws_instance.app",
                                       "aws_s3_bucket.demo", "aws_db_instance.db"])
        for rid in ("aws_security_group.app", "aws_instance.app", "aws_s3_bucket.demo"):
            self.assertTrue(by_id[rid]["supported"])
            self.assertEqual(by_id[rid]["region"], "eu-central-1")
        self.assertEqual(by_id["aws_instance.app"]["template"], "compute.tf.j2")
        self.assertFalse(by_id["aws_db_instance.db"]["supported"])
        self.assertTrue(by_id["aws_db_instance.db"]["proprietary"])
        self.assertEqual(by_id["aws_instance.app"]["references"], ["aws_security_group.app"])
        self.assertEqual(by_id["aws_instance.app"]["attributes"]["user_data"], {"redacted": True})
        self.assertTrue(by_id["aws_instance.app"]["attributes"]["subnet_id"]["unresolved"])
        self.assertEqual(data["buckets"][0]["name"], "demo-src")
        self.assertEqual((data["buckets"][0]["object_count"], data["buckets"][0]["total_bytes"]),
                         (2, 10))
        r = data["readiness"]
        self.assertEqual((r["proprietary"], r["unsupported"], r["us_calls"], r["score"]),
                         (1, 1, 2, 60))
        checks = {c["id"]: c["status"] for c in record["checks"]}
        self.assertEqual(checks["bucket_inventory"], "PASS")
        self.assertEqual(checks["inventory_parsed"], "incomplete")  # var.subnet unresolved
        self.assertEqual(checks["calls_scanned"], "incomplete")     # dynamic findings
        self.assertEqual(record["status"], "incomplete")
        json.dumps(record, sort_keys=True, allow_nan=False)

    def test_no_secret_leak(self):
        for paginator in (None, FakePaginator(error=DeniedError())):
            record = self.discover(CREDS, paginator)
            self.assertNotIn(SECRET, json.dumps(record))

    def test_denied_inventory_fails_record(self):
        record = self.discover(CREDS, FakePaginator(error=DeniedError()))
        self.assertEqual(record["status"], "FAIL")
        self.assertTrue(any("AccessDenied" in e for e in record["errors"]))

    def test_absent_credentials(self):
        record = self.discover({})
        self.assertEqual(record["status"], "incomplete")
        self.assertIsNone(record["data"]["buckets"][0]["object_count"])

    def test_unresolved_region(self):
        tf = MAIN_TF.replace('region = "eu-central-1"', "region = var.region")
        (self.workload / "main.tf").write_text(tf, encoding="utf-8")
        record = self.discover(CREDS)
        self.assertTrue(all(r["region"] is None for r in record["data"]["resources"]))
        kinds = {f["kind"] for f in record["data"]["findings"]}
        self.assertIn("unresolved_region", kinds)

    def test_invalid_hcl_raises(self):
        (self.workload / "broken.tf").write_text('resource "aws_s3_bucket" {\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            disc.discover(self.workload, config={})

    def test_clean_workload_can_pass(self):
        tf = MAIN_TF.replace("  subnet_id              = var.subnet\n", "")
        tf = tf.replace('resource "aws_db_instance" "db" {\n  engine = "postgres"\n}\n', "")
        (self.workload / "main.tf").write_text(tf, encoding="utf-8")
        (self.workload / "app.py").write_text(
            'import boto3\ns3 = boto3.client("s3")\ns3.put_object(Bucket="demo-src")\n',
            encoding="utf-8")
        record = self.discover(CREDS)
        self.assertEqual(record["status"], "PASS", record["checks"])
        self.assertEqual(record["data"]["readiness"]["score"], 100)


class StubPathTest(unittest.TestCase):
    def test_stub_never_imports_optional_libraries(self):
        code = (
            "import sys, pathlib, tempfile\n"
            "from skyshift.discover import discover, choose\n"
            "from skyshift.translate import translate\n"
            "d = discover(pathlib.Path('wl'), config={}, stub=True)\n"
            "c = choose(d['data'], config={}, stub=True)\n"
            "translate(d['data'], c['data'], output_dir=pathlib.Path(tempfile.mkdtemp()),"
            " config={}, stub=True)\n"
            "bad = {'hcl2', 'yaml', 'boto3', 'botocore', 'lark'} & set(sys.modules)\n"
            "assert not bad, bad\n"
        )
        env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(REPO_ROOT),
                                env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(os.environ.get("SKYSHIFT_WS1_LIVE_TESTS") == "1",
                     "live read-only inventory: set SKYSHIFT_WS1_LIVE_TESTS=1 after WS0-01 go")
class LiveInventoryTest(unittest.TestCase):
    """Read-only; never writes source objects. Skipped runs are not live acceptance."""

    def test_source_inventory_matches_expectation(self):
        keys = ("SKYSHIFT_SOURCE_ENDPOINT_URL", "SKYSHIFT_SOURCE_ACCESS_KEY_ID",
                "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY", "SKYSHIFT_SOURCE_BUCKET",
                "AWS_DEFAULT_REGION")
        config = {k: os.environ[k] for k in keys if os.environ.get(k)}
        bucket = config.get("SKYSHIFT_SOURCE_BUCKET")
        self.assertTrue(bucket, "SKYSHIFT_SOURCE_BUCKET required")
        buckets, check = disc.inventory_buckets([bucket], config)
        self.assertEqual(check["status"], "PASS", check["detail"])
        self.assertEqual(buckets[0]["object_count"],
                         int(os.environ["SKYSHIFT_WS1_EXPECTED_COUNT"]))
        self.assertEqual(buckets[0]["total_bytes"],
                         int(os.environ["SKYSHIFT_WS1_EXPECTED_BYTES"]))
        print(f"\nlive inventory: {buckets[0]['object_count']} objects, "
              f"{buckets[0]['total_bytes']} bytes")


if __name__ == "__main__":
    unittest.main()
