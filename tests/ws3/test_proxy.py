"""Offline tests for the allowlist egress proxy (WS3-03).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_proxy.py -v
Uses real loopback listeners only, an injected resolver (no DNS) and the
committed synthetic range fixture at a fixed time. No internet access. These
tests prove local proxy behaviour, not universal isolation or VM success.
"""

from __future__ import annotations

import socket
import sys
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import sever as sv  # noqa: E402

FRESH = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
TIMEOUT = 5.0
SECRET = "SENTINEL-SECRET-proxy-4d2a"

DNS = {
    "monitoring.amazonaws.com": ["192.0.2.10"],      # synthetic AWS range
    "rebind.example.test": ["127.0.0.1", "192.0.2.20"],  # allowlisted but one address in cloud range
    "echo.example.test": ["127.0.0.1"],
}


def resolver(host, port):
    if host not in DNS:
        raise OSError("NXDOMAIN (test resolver)")
    return DNS[host]


class Upstream:
    """Loopback echo or one-shot HTTP server used as the approved destination."""

    def __init__(self, http=False):
        self.http = http
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.sock.settimeout(TIMEOUT)
        self.port = self.sock.getsockname()[1]
        self.received = b""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            conn, _ = self.sock.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(TIMEOUT)
            if self.http:
                while b"\r\n\r\n" not in self.received:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    self.received += chunk
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
                return
            data = conn.recv(4096)
            self.received += data
            conn.sendall(b"echo:" + data)

    def close(self):
        self.sock.close()
        self.thread.join(TIMEOUT)


class RecordingConnector:
    def __init__(self):
        self.calls = []

    def __call__(self, ip, port, timeout):
        self.calls.append((ip, port))
        return socket.create_connection((ip, port), timeout=timeout)


def _proxy(allowlist, connector=None, **kwargs):
    return sv.EgressProxy(allowlist=frozenset(allowlist), ranges=sv.load_ranges(), resolver=resolver,
                          connector=connector or RecordingConnector(), clock=lambda: FRESH, **kwargs)


def _send(proxy, payload: bytes) -> tuple[socket.socket, bytes]:
    client = socket.create_connection(proxy.address, timeout=TIMEOUT)
    client.sendall(payload)
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = client.recv(4096)
        if not chunk:
            break
        data += chunk
    return client, data


def _read_all(sock) -> bytes:
    data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return data
        data += chunk


class DecisionTest(unittest.TestCase):
    def setUp(self):
        self.ranges = sv.load_ranges()

    def decide(self, host, port, allowlist):
        return sv.decide(host, port, allowlist=frozenset(allowlist), ranges=self.ranges, resolver=resolver, now=FRESH)

    def test_allowed_exact_host_and_port(self):
        event = self.decide("echo.example.test", 4318, {("echo.example.test", 4318)})
        self.assertEqual((event["decision"], event["connect_ip"]), ("allow", "127.0.0.1"))

    def test_wrong_port_or_unlisted_host_denied(self):
        self.assertEqual(self.decide("echo.example.test", 4319, {("echo.example.test", 4318)})["reason"],
                         "not on allowlist")
        self.assertEqual(self.decide("echo.example.test", 4318, set())["decision"], "deny")

    def test_provider_range_denied_even_if_allowlisted(self):
        event = self.decide("monitoring.amazonaws.com", 443, {("monitoring.amazonaws.com", 443)})
        self.assertEqual((event["decision"], event["ip"]), ("deny", "192.0.2.10"))
        self.assertIn("published cloud range (aws, synthetic fixture)", event["reason"])
        rebind = self.decide("rebind.example.test", 443, {("rebind.example.test", 443)})
        self.assertEqual((rebind["decision"], rebind["ip"]), ("deny", "192.0.2.20"))

    def test_unknown_resolution_and_malformed_fail_closed(self):
        self.assertEqual(self.decide("nx.example.test", 443, {("nx.example.test", 443)})["reason"],
                         "unresolved destination; fail closed")
        self.assertEqual(self.decide("", 443, set())["decision"], "deny")
        self.assertEqual(self.decide("echo.example.test", 70000, set())["decision"], "deny")

    def test_stale_ranges_fail_closed(self):
        stale = datetime(2026, 11, 22, tzinfo=timezone.utc)
        event = sv.decide("echo.example.test", 4318, allowlist=frozenset({("echo.example.test", 4318)}),
                          ranges=self.ranges, resolver=resolver, now=stale)
        self.assertEqual(event["decision"], "deny")
        self.assertIn("fail closed", event["reason"])

    def test_allowlist_from_config_only_keeps_host_port(self):
        config = {"SKYSHIFT_TELEMETRY_ENDPOINT": "http://127.0.0.1:4318/v1/metrics",
                  "SKYSHIFT_TARGET_ENDPOINT_URL": f"https://user:{SECRET}@s3.target.example.test",
                  "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SECRET}
        allow = sv.allowlist_from_config(config)
        self.assertEqual(allow, frozenset({("127.0.0.1", 4318), ("s3.target.example.test", 443)}))
        self.assertNotIn(SECRET, repr(allow))


class ProxyIntegrationTest(unittest.TestCase):
    def test_denied_connect_logged_and_no_upstream_attempt(self):
        connector = RecordingConnector()
        with _proxy({("monitoring.amazonaws.com", 443)}, connector) as proxy:
            client, reply = _send(proxy, b"CONNECT monitoring.amazonaws.com:443 HTTP/1.1\r\n"
                                         b"Host: monitoring.amazonaws.com:443\r\n\r\n")
            client.close()
            events = proxy.events
        self.assertTrue(reply.startswith(b"HTTP/1.1 403"))
        self.assertEqual(connector.calls, [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["decision"], "deny")
        self.assertEqual(events[0]["via"], "proxy")
        self.assertEqual(events[0]["outcome"], "blocked")

    def test_allowed_connect_tunnel_reaches_checked_address(self):
        upstream = Upstream()
        connector = RecordingConnector()
        try:
            with _proxy({("echo.example.test", upstream.port)}, connector) as proxy:
                client, reply = _send(proxy, f"CONNECT echo.example.test:{upstream.port} HTTP/1.1\r\n\r\n".encode())
                self.assertTrue(reply.startswith(b"HTTP/1.1 200"))
                client.sendall(b"hello")
                self.assertEqual(client.recv(4096), b"echo:hello")
                client.close()
                events = proxy.events
        finally:
            upstream.close()
        self.assertEqual(connector.calls, [("127.0.0.1", upstream.port)])
        self.assertEqual((events[0]["decision"], events[0]["outcome"]), ("allow", "tunnel"))

    def test_plain_http_forward_and_sanitized_denied_event(self):
        upstream = Upstream(http=True)
        try:
            with _proxy({("echo.example.test", upstream.port)}) as proxy:
                client, head = _send(proxy, f"GET http://echo.example.test:{upstream.port}/v1/metrics HTTP/1.1\r\n"
                                            f"Host: echo.example.test\r\nProxy-Authorization: Basic {SECRET}\r\n\r\n".encode())
                body = head + _read_all(client)
                self.assertTrue(body.startswith(b"HTTP/1.1 200"))
                client.close()
                denied, reply = _send(proxy, f"GET http://monitoring.amazonaws.com/put?token={SECRET} HTTP/1.1\r\n"
                                             f"Authorization: Bearer {SECRET}\r\n\r\n".encode())
                denied.close()
                events = proxy.events
        finally:
            upstream.close()
        self.assertTrue(body.endswith(b"ok"))
        self.assertTrue(upstream.received.startswith(b"GET /v1/metrics HTTP/1.1"))
        self.assertNotIn(SECRET.encode(), upstream.received)  # Proxy-* headers stripped
        self.assertTrue(reply.startswith(b"HTTP/1.1 403"))
        self.assertEqual([e["outcome"] for e in events], ["forwarded", "blocked"])
        self.assertNotIn(SECRET, repr(events))
        self.assertEqual(set(events[1]), {"host", "ip", "port", "decision", "reason", "via", "outcome"})

    def test_malformed_and_unresolved_requests_rejected(self):
        connector = RecordingConnector()
        with _proxy(set(), connector) as proxy:
            bad, reply_bad = _send(proxy, b"NONSENSE\r\n\r\n")
            bad.close()
            nx, reply_nx = _send(proxy, b"CONNECT nx.example.test:443 HTTP/1.1\r\n\r\n")
            nx.close()
            ftp, reply_ftp = _send(proxy, b"GET ftp://echo.example.test/ HTTP/1.1\r\n\r\n")
            ftp.close()
            events = proxy.events
        self.assertTrue(reply_bad.startswith(b"HTTP/1.1 400"))
        self.assertTrue(reply_nx.startswith(b"HTTP/1.1 403"))
        self.assertTrue(reply_ftp.startswith(b"HTTP/1.1 400"))
        self.assertEqual(connector.calls, [])
        self.assertEqual([e["reason"] for e in events], ["unresolved destination; fail closed"])

    def test_upstream_failure_does_not_fall_back(self):
        def refuse(ip, port, timeout):
            raise ConnectionRefusedError("refused")

        with _proxy({("echo.example.test", 9)}, refuse) as proxy:
            client, reply = _send(proxy, b"CONNECT echo.example.test:9 HTTP/1.1\r\n\r\n")
            client.close()
            events = proxy.events
        self.assertTrue(reply.startswith(b"HTTP/1.1 502"))
        self.assertEqual(events[0]["outcome"], "upstream_error")

    def test_listener_is_loopback_and_stops(self):
        proxy = _proxy(set()).start()
        try:
            self.assertEqual(proxy.address[0], "127.0.0.1")
            self.assertTrue(proxy.url.startswith("http://127.0.0.1:"))
        finally:
            proxy.stop()
        with self.assertRaises(OSError):
            socket.create_connection(proxy.address, timeout=1).close()

    def test_scope_is_explicit_in_severance_record(self):
        record = sv.sever({"calls": []}, {}, config={})
        detail = " ".join(c["detail"] for c in record["checks"])
        self.assertIn("does not block direct sockets", detail)
        self.assertEqual(record["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
