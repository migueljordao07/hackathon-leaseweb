"""Offline tests for the replacement catalogue and bounded severance loop (WS3-05).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_replacement_loop.py -v
A fake app runner stands in for the unchanged fixture app (WS2 run_app is wired
at WS3-07). Real loopback proxy and receiver; injected resolver and radar
reader; synthetic ranges at a fixed time. No internet, DNS, model or VM.
"""

from __future__ import annotations

import ipaddress
import socket
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import sever as sv  # noqa: E402
from skyshift.llm import complete  # noqa: E402

FRESH = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
TIMEOUT = 5.0
AWS_TELEMETRY = "https://monitoring.eu-central-1.amazonaws.com"
DNS = {
    "monitoring.eu-central-1.amazonaws.com": ["192.0.2.10"],   # synthetic AWS range
    "telemetry.unknown-vendor.example": ["203.0.113.10"],      # synthetic Google range, not catalogued
}
DATA_MAP = {"resources": [], "calls": [], "buckets": [], "readiness": {}}
TARGET = {"target_id": "leaseweb-selfhosted", "operator": "Leaseweb"}


def resolver(host, port):
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        pass
    if host not in DNS:
        raise OSError("NXDOMAIN (test resolver)")
    return DNS[host]


def _proxy_request(proxy_url: str, payload: bytes) -> int:
    parts = urlsplit(proxy_url)
    with socket.create_connection((parts.hostname, parts.port), timeout=TIMEOUT) as sock:
        sock.sendall(payload)
        head = b""
        while b"\r\n" not in head:
            chunk = sock.recv(1024)
            if not chunk:
                return 0
            head += chunk
    return int(head.split(b" ")[1])


def send_telemetry(env: dict, endpoint: str) -> int:
    """What the unchanged app does: POST telemetry to the configured endpoint via the proxy."""
    url = urlsplit(endpoint)
    if url.scheme == "https":
        return _proxy_request(env["HTTPS_PROXY"], f"CONNECT {url.hostname}:443 HTTP/1.1\r\n\r\n".encode())
    body = b'{"metric":"orders","value":1}'
    request = (f"POST http://{url.hostname}:{url.port}/v1/metrics HTTP/1.1\r\nHost: {url.hostname}\r\n"
               f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body
    return _proxy_request(env["HTTP_PROXY"], request)


def fake_app(env):
    code = send_telemetry(env, env.get("SKYSHIFT_TELEMETRY_ENDPOINT") or AWS_TELEMETRY)
    return {"ok": True, "detail": f"storage checks ok (fake); telemetry HTTP {code}"}


fake_app.label = "test-fake-app"


def stubborn_app(env):
    """Ignores the telemetry setting: config-only remediation cannot fix it."""
    code = send_telemetry(env, AWS_TELEMETRY)
    return {"ok": True, "detail": f"telemetry HTTP {code}"}


def unknown_vendor_app(env):
    code = send_telemetry(env, "https://telemetry.unknown-vendor.example")
    return {"ok": True, "detail": f"telemetry HTTP {code}"}


def clean_radar():
    return [], []


def run(app, **kwargs):
    options = {"config": {}, "app_runner": app, "resolver": resolver, "clock": lambda: FRESH,
               "radar_reader": clean_radar, "proposer": complete}
    options.update(kwargs)
    return sv.run_severance(DATA_MAP, TARGET, **options)


class CatalogueTest(unittest.TestCase):
    def test_catalogue_is_config_only_and_selects_deterministically(self):
        catalogue = sv.load_catalogue()
        self.assertEqual([e["id"] for e in catalogue], ["local-otel"])
        self.assertIn("not a deployed OpenTelemetry collector", catalogue[0]["description"])
        self.assertEqual(sv.select_replacement("monitoring.eu-central-1.amazonaws.com", catalogue)["id"], "local-otel")
        self.assertIsNone(sv.select_replacement("telemetry.unknown-vendor.example", catalogue))

    def test_receiver_counts_post_on_loopback_only(self):
        with sv.TelemetryReceiver() as receiver:
            self.assertTrue(receiver.endpoint.startswith("http://127.0.0.1:"))
            with socket.create_connection(("127.0.0.1", receiver.port), timeout=TIMEOUT) as sock:
                sock.sendall(b"POST /v1/metrics?k=v HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\n\r\n{}")
                self.assertTrue(sock.recv(1024).startswith(b"HTTP/1.0 200"))
            receipts = receiver.receipts
        self.assertEqual(receipts, [{"path": "/v1/metrics", "bytes": 2}])


class LoopTest(unittest.TestCase):
    def test_red_then_config_only_fix_then_green_preserves_denial(self):
        record = run(fake_app)
        data = record["data"]
        self.assertEqual(set(record), {"schema_version", "step", "mode", "status", "checks", "data", "errors"})
        self.assertEqual((record["step"], record["mode"]), ("sever", "live"))
        self.assertEqual([a["status"] for a in data["attempts"]], ["FAIL", "PASS"])
        first, second = data["attempts"]
        self.assertEqual(first["events"][0]["decision"], "deny")
        self.assertEqual(first["events"][0]["host"], "monitoring.eu-central-1.amazonaws.com")
        self.assertTrue(first["events"][0]["reason"].startswith("published cloud range"))
        self.assertIsNone(first["replacement"])
        self.assertEqual(second["replacement"]["id"], "local-otel")
        self.assertEqual(second["replacement"]["applied_config_keys"], ["SKYSHIFT_TELEMETRY_ENDPOINT"])
        self.assertEqual(second["replacement"]["mode"], "replay")
        self.assertEqual(second["replacement"]["proposal_status"], "agrees")
        self.assertEqual(second["receiver_receipts"], 1)
        self.assertEqual(second["blocked"], 0)
        self.assertEqual(data["final"], "green")
        self.assertEqual(record["status"], "PASS")
        self.assertEqual(data["runner"], "test-fake-app")
        self.assertIn("does not enforce", data["radar_scope"])

    def test_exhaustion_reports_blocked(self):
        one = run(fake_app, max_attempts=1)
        self.assertEqual((one["data"]["final"], one["status"]), ("blocked", "FAIL"))
        self.assertEqual(len(one["data"]["attempts"]), 1)
        self.assertIn("replacement local-otel available but attempts exhausted", one["data"]["manual"])
        stubborn = run(stubborn_app)
        self.assertEqual([a["status"] for a in stubborn["data"]["attempts"]], ["FAIL", "FAIL"])
        self.assertEqual(stubborn["data"]["final"], "blocked")
        self.assertEqual(stubborn["data"]["attempts"][0]["events"][0]["decision"], "deny")

    def test_unknown_dependency_is_manual_and_blocked(self):
        record = run(unknown_vendor_app)
        self.assertEqual(len(record["data"]["attempts"]), 1)
        self.assertEqual(record["data"]["final"], "blocked")
        self.assertIn("no catalogued replacement for telemetry.unknown-vendor.example; manual remediation required",
                      record["data"]["manual"])

    def test_invalid_attempt_limits(self):
        for bad in (0, -1, sv.MAX_ATTEMPTS_LIMIT + 1, True, "2", 1.5):
            with self.assertRaises(ValueError, msg=repr(bad)):
                run(fake_app, max_attempts=bad)
        with self.assertRaises(ValueError):
            run(None)

    def test_model_cannot_choose_or_inject_destinations(self):
        def rogue(task, payload, schema, *, config):
            return {"mode": "live", "status": "ok", "errors": [],
                    "data": {"replacement_id": "attacker", "rationale": "send to http://evil.example",
                             "config_keys": ["SKYSHIFT_TELEMETRY_ENDPOINT"]}}

        def broken(task, payload, schema, *, config):
            raise TimeoutError("model timeout")

        for proposer, expected in ((rogue, "disagrees (deterministic selection kept)"), (broken, "incomplete (TimeoutError)"),
                                   (None, "not_requested")):
            record = run(fake_app, proposer=proposer)
            second = record["data"]["attempts"][1]
            self.assertEqual(second["replacement"]["id"], "local-otel")
            self.assertEqual(second["replacement"]["proposal_status"], expected)
            self.assertEqual(record["data"]["final"], "green")
            self.assertNotIn("evil.example", repr(record))

    def test_radar_bypass_fails_and_is_not_fixed_by_config(self):
        bypass = [{"local_ip": "10.0.0.5", "local_port": 50001, "remote_ip": "198.51.100.50",
                   "remote_port": 443, "state": "ESTABLISHED", "family": "tcp"}]
        record = run(fake_app, radar_reader=lambda: (bypass, []))
        self.assertEqual(record["data"]["final"], "blocked")
        self.assertEqual(len(record["data"]["attempts"]), 1)
        radar_check = next(c for c in record["checks"] if c["id"] == "radar_bypass_detection")
        self.assertEqual(radar_check["status"], "FAIL")

    def test_unmeasurable_runs_stay_incomplete(self):
        def crashing(env):
            raise RuntimeError("app did not start")

        record = run(crashing)
        self.assertEqual((record["data"]["final"], record["status"]), ("incomplete", "incomplete"))
        no_radar = run(fake_app, radar_reader=lambda: ([], ["tcp: /proc/net/tcp unreadable"]))
        self.assertEqual(no_radar["data"]["final"], "incomplete")
        self.assertEqual(no_radar["status"], "incomplete")
        self.assertIn("tcp: /proc/net/tcp unreadable", no_radar["errors"])

    def test_sever_entry_point_unchanged_and_honest(self):
        stub = sv.sever(DATA_MAP, TARGET, config={}, stub=True)
        self.assertEqual((stub["mode"], stub["status"], stub["data"]["final"]), ("stub", "incomplete", "incomplete"))
        live = sv.sever(DATA_MAP, TARGET, config={})
        self.assertEqual(live["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
