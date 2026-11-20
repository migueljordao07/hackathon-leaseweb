"""Offline tests for the WS3 severance and LLM stubs (WS3-01).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_contract_stubs.py -v
Standard library only; no credentials, network, proxy, radar, model or CLI.
"""

from __future__ import annotations

import inspect
import ipaddress
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift.llm import complete, validate  # noqa: E402
from skyshift.sever import sever  # noqa: E402

ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}
COMPLETION_KEYS = {"mode", "status", "data", "errors"}
SEVER_DATA_KEYS = {"attempts", "max_attempts", "final", "radar_scope"}
EVENT_KEYS = {"host", "ip", "port", "decision", "reason", "via"}
SECRET = "SENTINEL-SECRET-do-not-leak-7b1e"
CONFIG = {"SKYSHIFT_LLM_API_KEY": SECRET, "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SECRET}
DOC_NETS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32", "127.0.0.0/8")
]
DATA_MAP = {
    "resources": [],
    "calls": [
        {"file": "app.py", "line": 12, "service": "cloudwatch", "operation": "put_metric_data",
         "bucket": None, "endpoint_host": "monitoring.amazonaws.com"}
    ],
    "buckets": [],
    "readiness": {},
}
TARGET = {"target_id": "leaseweb-selfhosted", "operator": "Leaseweb"}
PROPOSAL_SCHEMA = {
    "type": "object",
    "required": ["replacement_id", "rationale", "config_keys"],
    "additionalProperties": False,
    "properties": {
        "replacement_id": {"type": "string", "enum": ["local-otel"]},
        "rationale": {"type": "string", "minLength": 1},
        "config_keys": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    },
}


def _statuses(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("status", "final"):
                yield value
            yield from _statuses(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _statuses(item)


class ImportSafetyTest(unittest.TestCase):
    def test_imports_open_no_sockets_or_processes(self):
        code = (
            "import socket, subprocess, sys\n"
            "def boom(*a, **k): raise RuntimeError('side effect at import')\n"
            "socket.socket = boom; socket.create_connection = boom; socket.getaddrinfo = boom\n"
            "subprocess.Popen = boom\n"
            f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
            "import skyshift.sever, skyshift.llm\n"
            "print('ok')\n"
        )
        proc = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "ok")


class SignatureTest(unittest.TestCase):
    def test_sever_signature(self):
        params = inspect.signature(sever).parameters
        self.assertEqual(list(params), ["data_map", "target", "config", "max_attempts", "stub"])
        for name in ("config", "max_attempts", "stub"):
            self.assertEqual(params[name].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual(params["max_attempts"].default, 2)
        self.assertIs(params["stub"].default, False)

    def test_complete_signature(self):
        params = inspect.signature(complete).parameters
        self.assertEqual(list(params), ["task", "payload", "schema", "config", "replay"])
        for name in ("config", "replay"):
            self.assertEqual(params[name].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(params["replay"].default, False)


class SeverStubTest(unittest.TestCase):
    def setUp(self):
        self.record = sever(DATA_MAP, TARGET, config=CONFIG, stub=True)

    def test_envelope_shape(self):
        self.assertEqual(set(self.record), ENVELOPE_KEYS)
        self.assertEqual(self.record["step"], "sever")
        self.assertEqual(self.record["mode"], "stub")
        self.assertEqual(self.record["status"], "incomplete")
        self.assertEqual(set(self.record["data"]), SEVER_DATA_KEYS)
        json.dumps(self.record, allow_nan=False)

    def test_synthetic_history_is_nonempty_and_realistic(self):
        data = self.record["data"]
        self.assertEqual(len(data["attempts"]), 2)
        first, second = data["attempts"]
        self.assertEqual(first["events"][0]["decision"], "deny")
        self.assertEqual(first["events"][0]["host"], "monitoring.amazonaws.com")
        self.assertEqual(second["replacement"]["id"], "local-otel")
        self.assertEqual(second["replacement"]["applied_config_keys"], ["SKYSHIFT_TELEMETRY_ENDPOINT"])
        for attempt in data["attempts"]:
            for event in attempt["events"]:
                self.assertEqual(set(event), EVENT_KEYS)
                ip = ipaddress.ip_address(event["ip"])
                self.assertTrue(any(ip in net for net in DOC_NETS), event["ip"])
        self.assertTrue(self.record["checks"])

    def test_never_pass_or_green(self):
        for kwargs in ({"stub": True}, {"stub": True, "max_attempts": 1}, {"stub": False}):
            record = sever(DATA_MAP, TARGET, config=CONFIG, **kwargs)
            statuses = set(_statuses(record))
            self.assertNotIn("PASS", statuses)
            self.assertNotIn("green", statuses)
            self.assertEqual(record["status"], "incomplete")
            self.assertEqual(record["data"]["final"], "incomplete")
            self.assertNotIn(SECRET, json.dumps(record))

    def test_non_stub_is_explicitly_unimplemented(self):
        record = sever(DATA_MAP, TARGET, config=CONFIG)
        self.assertEqual(record["data"]["attempts"], [])
        self.assertTrue(record["errors"])

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sever([], TARGET, config=CONFIG, stub=True)
        with self.assertRaises(ValueError):
            sever(DATA_MAP, TARGET, config=CONFIG, max_attempts=0, stub=True)


class CompleteStubTest(unittest.TestCase):
    def test_replay_is_labelled_and_incomplete(self):
        for replay in (True, False):
            result = complete("replacement_proposal", {"host": "x"}, PROPOSAL_SCHEMA, config=CONFIG, replay=replay)
            self.assertEqual(set(result), COMPLETION_KEYS)
            self.assertEqual(result["mode"], "replay")
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(validate(result["data"], PROPOSAL_SCHEMA), [])
            self.assertEqual(result["data"]["replacement_id"], "local-otel")
            self.assertTrue(any("no model call" in e for e in result["errors"]))
            self.assertNotIn(SECRET, json.dumps(result))

    def test_schema_failure_and_unknown_task_yield_empty_incomplete(self):
        strict = {"type": "object", "required": ["missing_key"]}
        for task, schema in (("replacement_proposal", strict), ("unknown_task", PROPOSAL_SCHEMA)):
            result = complete(task, {}, schema, config=CONFIG, replay=True)
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(result["data"], {})
            self.assertGreaterEqual(len(result["errors"]), 2)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            complete("", {}, {}, config=CONFIG)
        with self.assertRaises(ValueError):
            complete("x", {}, "not-a-schema", config=CONFIG)


class FixtureTest(unittest.TestCase):
    def test_ip_range_fixture_is_documentation_only(self):
        doc = json.loads((REPO_ROOT / "fixtures/ip-ranges/ranges.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["synthetic"])
        self.assertTrue(doc["provenance"])
        prefixes = [p["ip_prefix"] for p in doc["prefixes"]] + [p["ipv6_prefix"] for p in doc["ipv6_prefixes"]]
        self.assertTrue(prefixes)
        for prefix in prefixes:
            net = ipaddress.ip_network(prefix)
            self.assertTrue(any(net.subnet_of(d) for d in DOC_NETS if d.version == net.version), prefix)

    def test_replacement_catalogue_is_config_only(self):
        doc = json.loads((REPO_ROOT / "skyshift/catalogue/replacements.yaml").read_text(encoding="utf-8"))
        entries = {e["id"]: e for e in doc["replacements"]}
        self.assertIn("local-otel", entries)
        self.assertIs(entries["local-otel"]["code_change"], False)
        self.assertTrue(set(entries["local-otel"]["applied_config_keys"]) <= set(entries["local-otel"]["config"]))


if __name__ == "__main__":
    unittest.main()
