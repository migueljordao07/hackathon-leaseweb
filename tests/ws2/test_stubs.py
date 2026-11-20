"""Offline unit tests for WS2 migrate, run_app, and verify stubs (WS2-01).

Run from the repository root before WS4 creates tests/__init__.py:
    python -B -m unittest discover -s tests/ws2 -p test_stubs.py -v
And after WS4 creates tests/__init__.py:
    python -m unittest tests.ws2.test_stubs -v

Standard library only; no network, subprocess, boto3, fixtures, VM, or CLI.
"""

from __future__ import annotations

import copy
import inspect
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift.migrate import migrate  # noqa: E402
from skyshift.parity import run_app, verify  # noqa: E402

ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}
CHECK_KEYS = {"id", "status", "detail"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SENTINEL_SECRET = "SENTINEL-WS2-SECRET-do-not-leak-7e4b"
SENTINEL_SIGNATURE = "X-Amz-Signature=deadbeefcafebabe0123456789"
CONFIG_WITH_SECRETS = {
    "AWS_ACCESS_KEY_ID": "AKIA-SYNTHETIC-TEST",
    "AWS_SECRET_ACCESS_KEY": SENTINEL_SECRET,
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": SENTINEL_SECRET,
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SENTINEL_SECRET,
    "SKYSHIFT_TARGET_ENDPOINT_URL": f"https://example.invalid/bucket?{SENTINEL_SIGNATURE}",
    "SKYSHIFT_LLM_API_KEY": SENTINEL_SECRET,
    "LEASEWEB_API_KEY": SENTINEL_SECRET,
    "OS_APPLICATION_CREDENTIAL_SECRET": SENTINEL_SECRET,
}

SYNTHETIC_DATA_MAP = {
    "resources": [
        {
            "id": "aws_s3_bucket.demo",
            "type": "aws_s3_bucket",
            "provider": "aws",
            "region": "eu-central-1",
            "supported": True,
        }
    ],
    "calls": [
        {
            "file": "fixtures/aws_workload/app.py",
            "line": 10,
            "service": "s3",
            "operation": "put_object",
            "bucket": "demo",
            "endpoint_host": None,
        }
    ],
    "buckets": [
        {
            "name": "demo",
            "provider": "aws",
            "jurisdiction": "US-controlled",
            "object_count": 1,
            "total_bytes": 128,
        }
    ],
    "readiness": {
        "score": 100,
        "formula": "max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)",
        "proprietary": 0,
        "unsupported": 0,
        "us_calls": 0,
    },
}

SYNTHETIC_TARGET = {
    "target_id": "leaseweb-selfhosted",
    "operator": "Leaseweb",
    "jurisdiction": "EU",
    "storage_mode": "self_hosted_s3",
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


def _walk_statuses(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "status":
                yield value
            yield from _walk_statuses(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_statuses(item)


def _walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield from _walk_strings(key)
            yield from _walk_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_strings(item)


class ContractSignatureAndImportTest(unittest.TestCase):
    def test_exact_contract_signatures(self):
        migrate_params = list(inspect.signature(migrate).parameters.values())
        self.assertEqual([p.name for p in migrate_params], ["data_map", "target", "config", "stub"])
        self.assertEqual(migrate_params[2].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(migrate_params[3].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(migrate_params[3].default, False)

        run_params = list(inspect.signature(run_app).parameters.values())
        self.assertEqual([p.name for p in run_params], ["workload", "target", "config", "stub"])
        self.assertEqual(run_params[2].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(run_params[3].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(run_params[3].default, False)

        verify_params = list(inspect.signature(verify).parameters.values())
        self.assertEqual([p.name for p in verify_params], ["data_map", "target", "config", "stub"])
        self.assertEqual(verify_params[2].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(verify_params[3].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(verify_params[3].default, False)

    def test_import_has_no_network_process_or_thread_side_effects(self):
        code = (
            "import sys, threading\n"
            "import skyshift.migrate, skyshift.parity\n"
            "forbidden = {'boto3', 'botocore', 'requests', 'urllib.request', 'http.client', "
            "'subprocess', 'socket'}\n"
            "loaded = forbidden & set(sys.modules)\n"
            "assert not loaded, f'unexpected modules imported: {sorted(loaded)}'\n"
            "assert threading.active_count() == 1, f'threads started: {threading.active_count()}'\n"
        )
        env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


class WS2StubsTest(unittest.TestCase):
    def setUp(self):
        self.workload = Path("fixtures/aws_workload")

    def assertStubEnvelope(self, record: dict, expected_step: str) -> None:
        self.assertEqual(set(record.keys()), ENVELOPE_KEYS)
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["step"], expected_step)
        self.assertEqual(record["mode"], "stub")
        self.assertEqual(record["status"], "incomplete")
        self.assertIsInstance(record["checks"], list)
        self.assertTrue(record["checks"], "checks must be nonempty")
        for check in record["checks"]:
            self.assertEqual(set(check.keys()), CHECK_KEYS)
            self.assertIsInstance(check["id"], str)
            self.assertTrue(check["id"])
            self.assertEqual(check["status"], "incomplete")
            self.assertIsInstance(check["detail"], str)
            self.assertTrue(check["detail"])
        self.assertIsInstance(record["errors"], list)
        for err in record["errors"]:
            self.assertIsInstance(err, str)
        self.assertNotIn("PASS", list(_walk_statuses(record)))
        serialized = json.dumps(record, sort_keys=True, allow_nan=False)
        self.assertIsInstance(serialized, str)

    def test_migrate_stub_contract_and_data(self):
        record = migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertStubEnvelope(record, "migrate")

        data = record["data"]
        required = {"objects", "source_count", "target_count", "matched", "missing", "different", "extra"}
        self.assertTrue(required <= set(data.keys()))
        self.assertEqual(len(data["objects"]), 1)
        obj = data["objects"][0]
        self.assertTrue(
            {"key", "source_bytes", "target_bytes", "source_sha256", "target_sha256", "status"}
            <= set(obj.keys())
        )
        self.assertEqual(obj["status"], "matched")
        self.assertEqual(obj["source_bytes"], obj["target_bytes"])
        self.assertRegex(obj["source_sha256"], SHA256_RE)
        self.assertRegex(obj["target_sha256"], SHA256_RE)
        self.assertEqual(obj["source_sha256"], obj["target_sha256"])

        self.assertEqual(data["source_count"], 1)
        self.assertEqual(data["target_count"], 1)
        self.assertEqual(data["matched"], 1)
        self.assertEqual(data["missing"], 0)
        self.assertEqual(data["different"], 0)
        self.assertEqual(data["extra"], 0)

    def test_run_app_stub_contract_and_data(self):
        record = run_app(self.workload, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertStubEnvelope(record, "run")

        data = record["data"]
        required = {
            "app_sha256_before",
            "app_sha256_after",
            "endpoint_changed",
            "functional_checks",
            "host_network",
        }
        self.assertTrue(required <= set(data.keys()))
        self.assertRegex(data["app_sha256_before"], SHA256_RE)
        self.assertRegex(data["app_sha256_after"], SHA256_RE)
        self.assertEqual(data["app_sha256_before"], data["app_sha256_after"])

        endpoint = data["endpoint_changed"]
        self.assertIsInstance(endpoint, dict)
        self.assertTrue(endpoint.get("config_only"))
        self.assertEqual(endpoint.get("env_var"), "AWS_ENDPOINT_URL")

        self.assertIsInstance(data["functional_checks"], list)
        self.assertTrue(data["functional_checks"])
        ops = {item["operation"] for item in data["functional_checks"]}
        self.assertTrue({"put_object", "get_object", "list_objects_v2"} <= ops)
        for item in data["functional_checks"]:
            self.assertEqual(item["status"], "incomplete")

        host_net = data["host_network"]
        self.assertIsInstance(host_net, dict)
        self.assertEqual(host_net["status"], "incomplete")
        self.assertIsNone(host_net["public_ip"])
        self.assertIsNone(host_net["network_owner"])

    def test_verify_stub_contract_and_data(self):
        record = verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertStubEnvelope(record, "parity")

        data = record["data"]
        self.assertTrue({"operations", "selection"} <= set(data.keys()))
        ops = data["operations"]
        self.assertIsInstance(ops, list)
        names = [row["operation"] for row in ops]
        self.assertEqual(names, ["put_object", "get_object", "list_objects_v2"])
        for row in ops:
            self.assertTrue({"operation", "before", "after", "equal"} <= set(row.keys()))
            self.assertEqual(row["before"]["status"], "incomplete")
            self.assertEqual(row["after"]["status"], "incomplete")
            self.assertIs(row["equal"], False)

        selection = data["selection"]
        self.assertTrue({"source", "operations", "ai_mode"} <= set(selection.keys()))
        self.assertEqual(selection["operations"], ["put_object", "get_object", "list_objects_v2"])
        self.assertIn("stub", selection["source"])
        self.assertEqual(selection["ai_mode"], "replay")

    def test_deterministic_outputs_and_no_shared_mutable_state(self):
        m1 = migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        m2 = migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertEqual(m1, m2)
        self.assertEqual(
            json.dumps(m1, sort_keys=True, allow_nan=False),
            json.dumps(m2, sort_keys=True, allow_nan=False),
        )
        m1["data"]["objects"].clear()
        self.assertEqual(len(migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)["data"]["objects"]), 1)

        r1 = run_app(self.workload, SYNTHETIC_TARGET, config={}, stub=True)
        r2 = run_app(self.workload, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertEqual(r1, r2)
        self.assertEqual(
            json.dumps(r1, sort_keys=True, allow_nan=False),
            json.dumps(r2, sort_keys=True, allow_nan=False),
        )

        v1 = verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        v2 = verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
        self.assertEqual(v1, v2)
        self.assertEqual(
            json.dumps(v1, sort_keys=True, allow_nan=False),
            json.dumps(v2, sort_keys=True, allow_nan=False),
        )

    def test_inputs_are_not_mutated(self):
        data_map = copy.deepcopy(SYNTHETIC_DATA_MAP)
        target = copy.deepcopy(SYNTHETIC_TARGET)
        config = copy.deepcopy(CONFIG_WITH_SECRETS)

        migrate(data_map, target, config=config, stub=True)
        run_app(self.workload, target, config=config, stub=True)
        verify(data_map, target, config=config, stub=True)

        self.assertEqual(data_map, SYNTHETIC_DATA_MAP)
        self.assertEqual(target, SYNTHETIC_TARGET)
        self.assertEqual(config, CONFIG_WITH_SECRETS)

    def test_no_credentials_or_signed_queries_in_output(self):
        records = [
            migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=True),
            run_app(self.workload, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=True),
            verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=True),
            migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=False),
            run_app(self.workload, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=False),
            verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config=CONFIG_WITH_SECRETS, stub=False),
        ]
        for record in records:
            dumped = json.dumps(record, sort_keys=True, allow_nan=False)
            self.assertNotIn(SENTINEL_SECRET, dumped)
            self.assertNotIn(SENTINEL_SIGNATURE, dumped)
            self.assertNotIn("AKIA-SYNTHETIC-TEST", dumped)
            for text in _walk_strings(record):
                self.assertNotIn("X-Amz-Signature", text)

    def test_offline_boundaries_fail_if_network_subprocess_or_boto3_called(self):
        def _forbid(*args, **kwargs):
            raise AssertionError("Stub must not invoke network, subprocess, or boto3 boundaries")

        fake_boto3 = types.ModuleType("boto3")
        fake_boto3.client = _forbid
        fake_boto3.resource = _forbid
        fake_boto3.Session = _forbid

        with (
            mock.patch.object(socket, "socket", side_effect=_forbid),
            mock.patch.object(socket, "create_connection", side_effect=_forbid),
            mock.patch.object(socket, "getaddrinfo", side_effect=_forbid),
            mock.patch.object(subprocess, "Popen", side_effect=_forbid),
            mock.patch.object(subprocess, "run", side_effect=_forbid),
            mock.patch.object(subprocess, "check_output", side_effect=_forbid),
            mock.patch.dict(sys.modules, {"boto3": fake_boto3}),
        ):
            m = migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
            r = run_app(self.workload, SYNTHETIC_TARGET, config={}, stub=True)
            v = verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
            self.assertStubEnvelope(m, "migrate")
            self.assertStubEnvelope(r, "run")
            self.assertStubEnvelope(v, "parity")

    def test_no_files_written_by_stubs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workload = Path(tmpdir) / "workload"
            workload.mkdir()
            migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
            run_app(workload, SYNTHETIC_TARGET, config={}, stub=True)
            verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={}, stub=True)
            self.assertEqual(list(Path(tmpdir).rglob("*")), [workload])

    def test_corrupt_inputs_raise_value_error(self):
        whole_envelope = {
            "schema_version": 1,
            "step": "discover",
            "mode": "stub",
            "status": "incomplete",
            "checks": [],
            "data": SYNTHETIC_DATA_MAP,
            "errors": [],
        }
        with self.assertRaises(ValueError):
            migrate(whole_envelope, SYNTHETIC_TARGET, config={}, stub=True)
        with self.assertRaises(ValueError):
            migrate(SYNTHETIC_DATA_MAP, whole_envelope, config={}, stub=True)
        with self.assertRaises(ValueError):
            migrate({"resources": []}, SYNTHETIC_TARGET, config={}, stub=True)
        with self.assertRaises(ValueError):
            migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config="bad", stub=True)
        with self.assertRaises(ValueError):
            run_app(123, SYNTHETIC_TARGET, config={}, stub=True)
        with self.assertRaises(ValueError):
            run_app(self.workload, whole_envelope, config={}, stub=True)
        with self.assertRaises(ValueError):
            verify(whole_envelope, SYNTHETIC_TARGET, config={}, stub=True)
        with self.assertRaises(ValueError):
            verify(SYNTHETIC_DATA_MAP, {"target_id": "only-one-key"}, config={}, stub=True)

    def test_non_stub_is_incomplete_not_live_pass(self):
        records = [
            ("migrate", migrate(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={})),
            ("run", run_app(self.workload, SYNTHETIC_TARGET, config={})),
            ("parity", verify(SYNTHETIC_DATA_MAP, SYNTHETIC_TARGET, config={})),
        ]
        for step, record in records:
            self.assertEqual(set(record.keys()), ENVELOPE_KEYS)
            self.assertEqual(record["step"], step)
            self.assertEqual(record["mode"], "live")
            self.assertEqual(record["status"], "incomplete")
            self.assertTrue(record["checks"])
            self.assertTrue(record["errors"])
            self.assertNotIn("PASS", list(_walk_statuses(record)))
            json.dumps(record, sort_keys=True, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
