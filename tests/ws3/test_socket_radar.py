"""Offline tests for the detection-only socket radar (WS3-04).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_socket_radar.py -v
Fixture text only: no Linux /proc, root, live sockets or ss binary required.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import sever as sv  # noqa: E402

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode"
TAIL = "00000000:00000000 00:00000000 00000000  1000        0 12345 1 0000000000000000 20 4 30 10 -1"
PROC_TCP = "\n".join([
    HEADER,
    f"   0: 00000000:1F90 00000000:0000 0A {TAIL}",   # LISTEN 0.0.0.0:8080
    f"   1: 0100007F:C350 0100007F:0C38 01 {TAIL}",   # app -> proxy on loopback 127.0.0.1:3128
    f"   2: 0500000A:D431 C87100CB:01BB 01 {TAIL}",   # proxy upstream -> 203.0.113.200:443 (proxied)
    f"   3: 0500000A:D432 0A0200C0:01BB 01 {TAIL}",   # direct -> 192.0.2.10:443 (BYPASS)
    f"   4: 0500000A:1F90 096433C6:C738 01 {TAIL}",   # inbound 198.51.100.9 -> listening 8080
    f"   5: 0500000A:D433 057100CB:0050 02 {TAIL}",   # SYN_SENT -> 203.0.113.5:80 (BYPASS)
    f"   6: 0500000A:D434 0B0200C0:01BB 06 {TAIL}",   # TIME_WAIT ignored
    "   7: ZZZZ:not-hex",
])
PROC_TCP6 = "\n".join([
    HEADER,
    f"   0: 00000000000000000000000001000000:0016 00000000000000000000000000000000:0000 0A {TAIL}",
    f"   1: 0000000000000000FFFF00000500000A:D435 B80D0120000000000000000001000000:01BB 01 {TAIL}",
    f"   2: 0000000000000000FFFF00000500000A:D436 0000000000000000FFFF00000A0200C0:01BB 01 {TAIL}",
])
SS_OUT = "\n".join([
    "LISTEN 0      128          0.0.0.0:22         0.0.0.0:*",
    "ESTAB  0      0           10.0.0.5:51234   192.0.2.10:443",
    "ESTAB  0      0    [::ffff:10.0.0.5]:51235 [2001:db8::1]:443",
    "ESTAB  0      0          127.0.0.1:50000    127.0.0.1:3128",
    "garbage",
])
PROXY_EVENTS = [
    {"host": "s3.target.example.test", "ip": "203.0.113.200", "port": 443, "decision": "allow", "via": "proxy"},
    {"host": "monitoring.amazonaws.com", "ip": "192.0.2.10", "port": 443, "decision": "deny", "via": "proxy"},
]


def _reader(*texts):
    def read():
        sockets, errors = [], []
        for text, family in texts:
            found, bad = sv.parse_proc_net_tcp(text, family=family)
            sockets += found
            errors += bad
        return sockets, errors
    return read


class ParserTest(unittest.TestCase):
    def test_proc_ipv4_decoding_and_states(self):
        sockets, errors = sv.parse_proc_net_tcp(PROC_TCP)
        self.assertEqual(len(sockets), 7)
        self.assertEqual(errors, ["tcp: unparsable line 8"])
        listen = sockets[0]
        self.assertEqual((listen["local_ip"], listen["local_port"], listen["state"]), ("0.0.0.0", 8080, "LISTEN"))
        bypass = sockets[3]
        self.assertEqual((bypass["local_ip"], bypass["remote_ip"], bypass["remote_port"]), ("10.0.0.5", "192.0.2.10", 443))
        self.assertEqual(sockets[5]["state"], "SYN_SENT")
        self.assertEqual(sockets[6]["state"], "OTHER")

    def test_proc_ipv6_and_mapped_ipv4(self):
        sockets, errors = sv.parse_proc_net_tcp(PROC_TCP6, family="tcp6")
        self.assertEqual(errors, [])
        self.assertEqual((sockets[0]["local_ip"], sockets[0]["local_port"]), ("::1", 22))
        self.assertEqual((sockets[1]["remote_ip"], sockets[1]["remote_port"]), ("2001:db8::1", 443))
        self.assertEqual(sockets[2]["remote_ip"], "192.0.2.10")
        self.assertEqual(sockets[2]["local_ip"], "10.0.0.5")

    def test_ss_parser(self):
        sockets, errors = sv.parse_ss(SS_OUT)
        self.assertEqual(errors, ["ss: unparsable line 4"])
        self.assertEqual([s["state"] for s in sockets], ["LISTEN", "ESTABLISHED", "ESTABLISHED", "ESTABLISHED"])
        self.assertEqual(sockets[2]["remote_ip"], "2001:db8::1")
        self.assertEqual(sockets[2]["local_ip"], "10.0.0.5")

    def test_empty_input(self):
        self.assertEqual(sv.parse_proc_net_tcp(""), ([], []))
        self.assertEqual(sv.parse_ss(""), ([], []))


class RadarTest(unittest.TestCase):
    def test_detects_unmatched_and_ignores_proxied_loopback_inbound(self):
        result = sv.radar_scan(proxy_events=PROXY_EVENTS, reader=_reader((PROC_TCP, "tcp"), (PROC_TCP6, "tcp6")))
        found = [(b["ip"], b["port"]) for b in result["bypasses"]]
        # 192.0.2.10:443 seen over IPv4 and IPv4-mapped IPv6 is reported once; the proxy's
        # deny event does not whitelist a direct socket.
        self.assertEqual(found, [("192.0.2.10", 443), ("2001:db8::1", 443), ("203.0.113.5", 80)])
        self.assertNotIn(("203.0.113.200", 443), found)
        self.assertNotIn(("198.51.100.9", 51000), found)
        self.assertTrue(all(b["via"] == "radar" and "not blocked" in b["reason"] for b in result["bypasses"]))
        self.assertEqual(result["coverage"], "partial")
        self.assertEqual(result["collection_errors"], ["tcp: unparsable line 8"])

    def test_bypass_records_are_sanitized(self):
        result = sv.radar_scan(proxy_events=[], reader=_reader((PROC_TCP, "tcp")))
        for bypass in result["bypasses"]:
            self.assertEqual(set(bypass), {"ip", "port", "state", "family", "via", "reason"})
        self.assertNotIn("uid", repr(result))
        self.assertNotIn("inode", repr(result))

    def test_unreadable_input_is_reported_not_hidden(self):
        def broken():
            raise PermissionError("denied")

        result = sv.radar_scan(reader=broken)
        self.assertEqual((result["coverage"], result["bypasses"]), ("unavailable", []))
        self.assertEqual(result["collection_errors"], ["reader failed: PermissionError"])
        empty = sv.radar_scan(reader=lambda: ([], ["tcp: /proc/net/tcp unreadable"]))
        self.assertEqual(empty["coverage"], "unavailable")

    def test_states_detection_only_never_enforcement(self):
        result = sv.radar_scan(reader=_reader((PROC_TCP, "tcp")))
        self.assertIs(result["enforces"], False)
        self.assertIn("radar detects only and does not enforce network isolation", result["limitations"])
        self.assertIn("does not enforce", sv.RADAR_SCOPE)
        record = sv.sever({"calls": []}, {}, config={}, stub=True)
        self.assertIn("does not enforce", record["data"]["radar_scope"])

    def test_multiple_samples_bounded_and_deduplicated(self):
        result = sv.radar_scan(proxy_events=PROXY_EVENTS, reader=_reader((PROC_TCP, "tcp")), samples=3)
        self.assertEqual(len(result["bypasses"]), 2)
        unproxied = sv.radar_scan(reader=_reader((PROC_TCP, "tcp")))
        self.assertIn(("203.0.113.200", 443), [(b["ip"], b["port"]) for b in unproxied["bypasses"]])
        self.assertEqual(result["observed_connections"], 15)  # 5 active sockets x 3 samples
        with self.assertRaises(ValueError):
            sv.radar_scan(reader=_reader(), samples=sv.RADAR_MAX_SAMPLES + 1)


class CommandAdapterTest(unittest.TestCase):
    def test_ss_fallback_uses_bounded_timeout(self):
        with mock.patch.object(Path, "read_text", side_effect=OSError("no proc")), \
             mock.patch("shutil.which", return_value="/usr/bin/ss"), \
             mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ss", 3)) as run:
            result = sv.radar_scan()
        self.assertEqual(run.call_args.kwargs["timeout"], sv.RADAR_COMMAND_TIMEOUT)
        self.assertLessEqual(sv.RADAR_COMMAND_TIMEOUT, 5)
        self.assertNotIn("-p", run.call_args.args[0])
        self.assertEqual(result["coverage"], "unavailable")
        self.assertIn("ss: TimeoutExpired", result["collection_errors"])

    def test_ss_fallback_parses_output(self):
        completed = subprocess.CompletedProcess(["ss", "-ntH"], 0, stdout=SS_OUT, stderr="")
        with mock.patch.object(Path, "read_text", side_effect=OSError("no proc")), \
             mock.patch("shutil.which", return_value="/usr/bin/ss"), \
             mock.patch("subprocess.run", return_value=completed):
            result = sv.radar_scan(proxy_events=PROXY_EVENTS)
        self.assertEqual([(b["ip"], b["port"]) for b in result["bypasses"]], [("192.0.2.10", 443), ("2001:db8::1", 443)])
        self.assertEqual(result["coverage"], "partial")

    def test_no_proc_and_no_ss(self):
        with mock.patch.object(Path, "read_text", side_effect=OSError("no proc")), \
             mock.patch("shutil.which", return_value=None):
            result = sv.radar_scan()
        self.assertEqual(result["coverage"], "unavailable")
        self.assertIn("ss: command not available", result["collection_errors"])


if __name__ == "__main__":
    unittest.main()
