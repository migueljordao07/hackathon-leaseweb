"""Unit tests for the bounded unchanged-application runner (WS2-04).

Run from the repository root:
    python -B -m unittest tests.ws2.test_run_app -v

Standard library only; exercises real bounded subprocess lifecycles against
temporary fake app scripts without modifying fixtures/aws_workload/app.py.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import parity as parity_mod  # noqa: E402
from skyshift.parity import _live_run_app, run_app  # noqa: E402

FIXTURE_APP = REPO_ROOT / "fixtures" / "aws_workload" / "app.py"
ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}
RUN_DATA_KEYS = {
    "app_sha256_before",
    "app_sha256_after",
    "endpoint_changed",
    "functional_checks",
    "host_network",
}

SYNTHETIC_TARGET = {
    "target_id": "leaseweb-native",
    "operator": "Leaseweb",
    "jurisdiction": "EU",
    "storage_mode": "native_s3",
    "criteria": [
        {
            "name": "operator_jurisdiction",
            "value": "EU",
            "source_url": "https://www.leaseweb.com/",
        }
    ],
    "prices": [
        {
            "item": "compute",
            "amount": None,
            "currency": "EUR",
            "unit": "hour",
            "source_url": None,
            "assumptions": "not verified",
        }
    ],
    "explanation": {"mode": "replay", "text": "Synthetic example"},
}

SENTINEL_SECRET = "SENTINEL-RUNAPP-SECRET-9f8e7d6c"
SENTINEL_OTHER_SECRET = "SENTINEL-LEASEWEB-API-KEY-123456"

BASE_CONFIG = {
    "SKYSHIFT_SOURCE_ENDPOINT_URL": "http://127.0.0.1:5000",
    "SKYSHIFT_SOURCE_ACCESS_KEY_ID": "SOURCE-ACCESS-123456",
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": "SOURCE-SECRET-123456789",
    "SKYSHIFT_TARGET_ENDPOINT_URL": "https://s3.leaseweb.example/bucket?X-Amz-Signature=deadbeef998877",
    "SKYSHIFT_TARGET_ACCESS_KEY_ID": "TARGET-ACCESS-123456",
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SENTINEL_SECRET,
    "SKYSHIFT_TARGET_BUCKET": "skyshift-demo-bucket",
    "AWS_DEFAULT_REGION": "eu-central-1",
    "LEASEWEB_API_KEY": SENTINEL_OTHER_SECRET,
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(16384)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _pass_host_network(endpoint: str, target: dict, config: dict) -> dict:
    return {
        "status": "PASS",
        "public_ip": "198.51.100.10",
        "network_owner": "Leaseweb (EU; declared by approved target)",
        "provenance": "test_probe",
        "observed_at": "2026-11-20T14:40:00+00:00",
        "target_endpoint_class": "public_global",
        "limitations": "unit test double",
        "detail": "test double public global observation",
    }


def _incomplete_host_network(endpoint: str, target: dict, config: dict) -> dict:
    return {
        "status": "incomplete",
        "public_ip": None,
        "network_owner": None,
        "provenance": None,
        "observed_at": "2026-11-20T14:40:00+00:00",
        "detail": "host network unavailable",
    }


def _write_fake_app(directory: Path, body: str) -> Path:
    app_path = directory / "app.py"
    app_path.write_text(body, encoding="utf-8")
    return app_path


class RunAppTest(unittest.TestCase):
    def setUp(self):
        self.fixture_hash = _sha256_file(FIXTURE_APP)

    def tearDown(self):
        self.assertEqual(
            _sha256_file(FIXTURE_APP),
            self.fixture_hash,
            "committed fixtures/aws_workload/app.py must never be modified by tests",
        )

    def test_success_path_and_contract_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            app_path = _write_fake_app(
                workload,
                """
import json, os, sys
result = {
    "status": "PASS",
    "checks": [
        {"operation": "put_object", "status": "PASS", "detail": "ok put"},
        {"operation": "get_object", "status": "PASS", "detail": "ok get"},
        {"operation": "list_objects_v2", "status": "PASS", "detail": "ok list"},
        {"operation": "multipart_upload", "status": "PASS", "detail": "ok mp"},
    ],
    "telemetry": {
        "operation": "put_metric_data",
        "endpoint_host": "monitoring.eu-central-1.amazonaws.com",
        "status": "FAIL",
        "detail": "telemetry metric failed (ClientError)",
    },
    "errors": [],
}
print(json.dumps(result))
sys.exit(0)
""",
            )
            expected_hash = _sha256_file(app_path)
            cfg_copy = copy.deepcopy(BASE_CONFIG)
            target_copy = copy.deepcopy(SYNTHETIC_TARGET)

            record = _live_run_app(
                workload,
                target_copy,
                config=cfg_copy,
                host_network_probe=_pass_host_network,
            )

            self.assertEqual(set(record.keys()), ENVELOPE_KEYS)
            self.assertEqual(record["schema_version"], 1)
            self.assertEqual(record["step"], "run")
            self.assertEqual(record["mode"], "live")
            self.assertEqual(record["status"], "PASS")
            self.assertEqual(record["errors"], [])
            self.assertTrue(RUN_DATA_KEYS <= set(record["data"].keys()))
            self.assertEqual(record["data"]["app_sha256_before"], expected_hash)
            self.assertEqual(record["data"]["app_sha256_after"], expected_hash)
            self.assertIs(record["data"]["functional_checks_passed"], True)
            self.assertIs(record["data"]["ok"], True)
            self.assertEqual(record["data"]["exit_code"], 0)
            self.assertIs(record["data"]["timed_out"], False)
            self.assertEqual(record["data"]["telemetry"]["status"], "FAIL")

            ep = record["data"]["endpoint_changed"]
            self.assertIs(ep["changed"], True)
            self.assertIs(ep["config_only"], True)
            self.assertEqual(ep["env_var"], "AWS_ENDPOINT_URL")
            self.assertEqual(ep["source_identity"], "127.0.0.1:5000")
            self.assertEqual(ep["target_identity"], "s3.leaseweb.example")

            dumped = json.dumps(record, sort_keys=True, allow_nan=False)
            self.assertNotIn(SENTINEL_SECRET, dumped)
            self.assertNotIn(SENTINEL_OTHER_SECRET, dumped)
            self.assertNotIn("X-Amz-Signature", dumped)
            self.assertEqual(cfg_copy, BASE_CONFIG)
            self.assertEqual(target_copy, SYNTHETIC_TARGET)
            # No temp files left behind
            self.assertEqual([p.name for p in workload.iterdir()], ["app.py"])

    def test_committed_fixture_sha256_matches_direct_hash(self):
        # Verify the runner hashes the committed fixture identically to direct SHA-256.
        record = run_app(FIXTURE_APP.parent, SYNTHETIC_TARGET, config={})
        self.assertEqual(record["status"], "incomplete")
        self.assertEqual(record["data"]["app_sha256_before"], self.fixture_hash)
        self.assertIsNone(record["data"]["app_sha256_after"])
        self.assertTrue(record["errors"])

    def test_proxy_and_telemetry_env_forwarding_and_secret_isolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(
                workload,
                """
import json, os, sys
seen = {
    "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
    "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
    "NO_PROXY": os.environ.get("NO_PROXY"),
    "SKYSHIFT_TELEMETRY_ENDPOINT": os.environ.get("SKYSHIFT_TELEMETRY_ENDPOINT"),
    "AWS_ENDPOINT_URL": os.environ.get("AWS_ENDPOINT_URL"),
    "SKYSHIFT_TARGET_BUCKET": os.environ.get("SKYSHIFT_TARGET_BUCKET"),
    "HAS_LEASEWEB_KEY": "LEASEWEB_API_KEY" in os.environ,
    "HAS_SOURCE_SECRET": "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY" in os.environ,
}
assert seen["HTTPS_PROXY"] == "http://127.0.0.1:18080", seen
assert seen["HTTP_PROXY"] == "http://127.0.0.1:18080", seen
assert seen["NO_PROXY"] == "", seen
assert seen["SKYSHIFT_TELEMETRY_ENDPOINT"] == "http://127.0.0.1:14318", seen
assert seen["SKYSHIFT_TARGET_BUCKET"] == "skyshift-demo-bucket", seen
assert not seen["HAS_LEASEWEB_KEY"], seen
assert not seen["HAS_SOURCE_SECRET"], seen
print(json.dumps({
    "status": "PASS",
    "checks": [
        {"operation": "put_object", "status": "PASS", "detail": "ok"},
        {"operation": "get_object", "status": "PASS", "detail": "ok"},
        {"operation": "list_objects_v2", "status": "PASS", "detail": "ok"},
    ],
    "telemetry": {
        "operation": "put_metric_data",
        "endpoint_host": "127.0.0.1:14318",
        "status": "PASS",
        "detail": "accepted",
    },
    "errors": [],
}))
""",
            )
            cfg = dict(
                BASE_CONFIG,
                HTTPS_PROXY="http://127.0.0.1:18080",
                HTTP_PROXY="http://127.0.0.1:18080",
                NO_PROXY="",
                SKYSHIFT_TELEMETRY_ENDPOINT="http://127.0.0.1:14318",
            )
            record = run_app(workload, SYNTHETIC_TARGET, config=cfg)
            self.assertIs(record["data"]["functional_checks_passed"], True)
            self.assertIs(record["data"]["ok"], True)
            self.assertEqual(record["data"]["telemetry"]["status"], "PASS")
            # Under active proxy, host_network probe skips direct lookup -> incomplete (not PASS)
            self.assertEqual(record["data"]["host_network"]["status"], "incomplete")
            self.assertEqual(record["status"], "incomplete")

    def test_functional_failure_preserved_and_secrets_redacted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(
                workload,
                f"""
import json, sys
print(json.dumps({{
    "status": "FAIL",
    "checks": [
        {{"operation": "put_object", "status": "PASS", "detail": "ok"}},
        {{"operation": "get_object", "status": "FAIL", "detail": "err with {SENTINEL_SECRET} and https://user:pw@s3.example/k?X-Amz-Signature=abc123"}},
        {{"operation": "list_objects_v2", "status": "PASS", "detail": "ok"}},
    ],
    "telemetry": {{"operation": "put_metric_data", "endpoint_host": "monitoring.eu-central-1.amazonaws.com", "status": "FAIL", "detail": "blocked"}},
    "errors": ["failed with {SENTINEL_SECRET} and X-Amz-Signature=xyz789"],
}}))
sys.exit(1)
""",
            )
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(record["status"], "FAIL")
            self.assertIs(record["data"]["functional_checks_passed"], False)
            self.assertIs(record["data"]["ok"], False)
            self.assertEqual(record["data"]["exit_code"], 1)
            ops = {c["operation"]: c["status"] for c in record["data"]["functional_checks"]}
            self.assertEqual(ops["get_object"], "FAIL")

            dumped = json.dumps(record, sort_keys=True, allow_nan=False)
            self.assertNotIn(SENTINEL_SECRET, dumped)
            self.assertNotIn("user:pw@", dumped)
            self.assertNotIn("abc123", dumped)
            self.assertNotIn("xyz789", dumped)

    def test_malformed_child_json_fails_never_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(workload, "print('not-json-at-all')\n")
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(record["status"], "FAIL")
            self.assertIs(record["data"]["functional_checks_passed"], False)
            self.assertIs(record["data"]["ok"], False)
            self.assertTrue(record["errors"])

    def test_timeout_escalation_reaps_child_and_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            # Child ignores SIGTERM (where supported) and sleeps so terminate -> kill triggers.
            _write_fake_app(
                workload,
                """
import signal, time
try:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
except (AttributeError, OSError, ValueError):
    pass
time.sleep(30)
""",
            )
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                timeout=0.3,
                grace_timeout=0.2,
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(record["status"], "FAIL")
            self.assertIs(record["data"]["timed_out"], True)
            self.assertIs(record["data"]["functional_checks_passed"], False)
            self.assertIs(record["data"]["ok"], False)
            self.assertTrue(any("timed out" in e for e in record["errors"]))

    def test_app_mutation_during_execution_returns_fail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            app_path = _write_fake_app(
                workload,
                """
import json, pathlib
p = pathlib.Path(__file__)
p.write_text(p.read_text(encoding="utf-8") + "\\n# mutated\\n", encoding="utf-8")
print(json.dumps({
    "status": "PASS",
    "checks": [
        {"operation": "put_object", "status": "PASS", "detail": "ok"},
        {"operation": "get_object", "status": "PASS", "detail": "ok"},
        {"operation": "list_objects_v2", "status": "PASS", "detail": "ok"},
    ],
    "telemetry": {"operation": "put_metric_data", "endpoint_host": None, "status": "PASS", "detail": "ok"},
    "errors": [],
}))
""",
            )
            hash_before = _sha256_file(app_path)
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(record["status"], "FAIL")
            self.assertEqual(record["data"]["app_sha256_before"], hash_before)
            self.assertNotEqual(record["data"]["app_sha256_after"], hash_before)
            self.assertIs(record["data"]["ok"], False)
            checks = {c["id"]: c["status"] for c in record["checks"]}
            self.assertEqual(checks["app_unchanged_sha256"], "FAIL")

    def test_incomplete_host_network_cannot_yield_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(
                workload,
                """
import json
print(json.dumps({
    "status": "PASS",
    "checks": [
        {"operation": "put_object", "status": "PASS", "detail": "ok"},
        {"operation": "get_object", "status": "PASS", "detail": "ok"},
        {"operation": "list_objects_v2", "status": "PASS", "detail": "ok"},
    ],
    "telemetry": {"operation": "put_metric_data", "endpoint_host": None, "status": "PASS", "detail": "ok"},
    "errors": [],
}))
""",
            )
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                host_network_probe=_incomplete_host_network,
            )
            self.assertEqual(record["status"], "incomplete")
            self.assertIs(record["data"]["functional_checks_passed"], True)
            self.assertIs(record["data"]["ok"], True)
            checks = {c["id"]: c["status"] for c in record["checks"]}
            self.assertEqual(checks["app_unchanged_sha256"], "PASS")
            self.assertEqual(checks["app_functional_checks"], "PASS")
            self.assertEqual(checks["host_network_observation"], "incomplete")

    def test_loopback_target_yields_incomplete_host_network(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(
                workload,
                """
import json
print(json.dumps({
    "status": "PASS",
    "checks": [
        {"operation": "put_object", "status": "PASS", "detail": "ok"},
        {"operation": "get_object", "status": "PASS", "detail": "ok"},
        {"operation": "list_objects_v2", "status": "PASS", "detail": "ok"},
    ],
    "telemetry": {"operation": "put_metric_data", "endpoint_host": None, "status": "PASS", "detail": "ok"},
    "errors": [],
}))
""",
            )
            cfg = dict(BASE_CONFIG, SKYSHIFT_TARGET_ENDPOINT_URL="http://127.0.0.1:9000")
            record = run_app(workload, SYNTHETIC_TARGET, config=cfg)
            self.assertEqual(record["status"], "incomplete")
            self.assertEqual(record["data"]["host_network"]["target_endpoint_class"], "loopback")
            self.assertEqual(record["data"]["host_network"]["status"], "incomplete")

    def test_subprocess_uses_argument_list_never_shell(self):
        captured: dict = {}

        class _FakeProc:
            returncode = 0

            def communicate(self, timeout=None):
                payload = json.dumps(
                    {
                        "status": "PASS",
                        "checks": [
                            {"operation": "put_object", "status": "PASS", "detail": "ok"},
                            {"operation": "get_object", "status": "PASS", "detail": "ok"},
                            {"operation": "list_objects_v2", "status": "PASS", "detail": "ok"},
                        ],
                        "telemetry": {
                            "operation": "put_metric_data",
                            "endpoint_host": None,
                            "status": "PASS",
                            "detail": "ok",
                        },
                        "errors": [],
                    }
                )
                return payload + "\n", ""

            def terminate(self):
                pass

            def kill(self):
                pass

            def wait(self):
                return 0

        def _fake_popen(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return _FakeProc()

        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(workload, "pass\n")
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                popen_factory=_fake_popen,
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(record["status"], "PASS")
            self.assertIsInstance(captured["argv"], list)
            self.assertIs(captured["kwargs"].get("shell"), False)

    def test_timeout_escalation_calls_terminate_then_kill(self):
        calls: list[str] = []

        class _StubbornProc:
            returncode = -9

            def __init__(self):
                self._comm_calls = 0

            def communicate(self, timeout=None):
                self._comm_calls += 1
                if self._comm_calls <= 2:
                    raise subprocess.TimeoutExpired(cmd=["python"], timeout=timeout or 1)
                return "", ""

            def terminate(self):
                calls.append("terminate")

            def kill(self):
                calls.append("kill")

            def wait(self):
                calls.append("wait")
                return -9

        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir)
            _write_fake_app(workload, "pass\n")
            record = _live_run_app(
                workload,
                SYNTHETIC_TARGET,
                config=BASE_CONFIG,
                timeout=0.1,
                grace_timeout=0.1,
                popen_factory=lambda *a, **kw: _StubbornProc(),
                host_network_probe=_pass_host_network,
            )
            self.assertEqual(calls, ["terminate", "kill"])
            self.assertEqual(record["status"], "FAIL")
            self.assertIs(record["data"]["timed_out"], True)
            self.assertIn("terminate+kill", record["errors"][0])


if __name__ == "__main__":
    unittest.main()
