"""Offline tests for provenance-aware IP range matching (WS3-02).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_ip_ranges.py -v
Uses only the committed synthetic fixture and mocked feed transports; no network.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import sever as sv  # noqa: E402

FRESH = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
STALE = datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)


def _no_network(*_args, **_kwargs):
    raise AssertionError("network transport must be mocked")


class MatcherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ranges = sv.load_ranges()

    def match(self, ip, now=FRESH):
        return sv.match_ip(ip, self.ranges, now=now)

    def test_fixture_loads_all_providers_fresh_and_synthetic(self):
        self.assertEqual(self.ranges.errors, [])
        self.assertEqual(set(self.ranges.provider_status(FRESH).values()), {"fresh"})
        self.assertTrue(all(s["synthetic"] for s in self.ranges.sources.values()))

    def test_ipv4_in_range_denied_with_provenance(self):
        result = self.match("192.0.2.10")
        self.assertEqual((result["verdict"], result["deny"], result["provider"]), ("cloud_range", True, "aws"))
        self.assertEqual(result["prefix"], "192.0.2.0/25")
        self.assertTrue(result["synthetic"])

    def test_ipv4_prefix_boundaries(self):
        self.assertEqual(self.match("192.0.2.0")["prefix"], "192.0.2.0/25")
        self.assertEqual(self.match("192.0.2.127")["prefix"], "192.0.2.0/25")
        self.assertEqual(self.match("192.0.2.128")["prefix"], "192.0.2.128/25")
        self.assertEqual(self.match("203.0.113.191")["provider"], "cloudflare")
        outside = self.match("203.0.113.192")
        self.assertEqual((outside["verdict"], outside["deny"]), ("not_listed", False))

    def test_out_of_range_not_listed_but_not_allowed_blindly(self):
        result = self.match("127.0.0.1")
        self.assertEqual(result["verdict"], "not_listed")
        self.assertIn("allowlist", result["reason"])

    def test_ipv6_boundaries_and_mapped_ipv4(self):
        self.assertEqual(self.match("2001:db8:aa::")["verdict"], "cloud_range")
        self.assertEqual(self.match("2001:db8:aa:ffff:ffff:ffff:ffff:ffff")["verdict"], "cloud_range")
        self.assertEqual(self.match("[2001:db8:ab::1]")["verdict"], "not_listed")
        mapped = self.match("::ffff:192.0.2.5")
        self.assertEqual((mapped["verdict"], mapped["ip"]), ("cloud_range", "192.0.2.5"))

    def test_malformed_or_unresolved_address_fails_closed(self):
        for bad in ("not-an-ip", "192.0.2.300", "", None, "monitoring.amazonaws.com"):
            result = self.match(bad)
            self.assertEqual((result["verdict"], result["deny"]), ("unknown", True), bad)

    def test_stale_data_fails_closed(self):
        result = self.match("127.0.0.1", now=STALE)
        self.assertEqual((result["verdict"], result["deny"], result["coverage"]), ("unknown", True, "incomplete"))
        # Stale ranges are not trusted for a positive match either, but still deny.
        self.assertTrue(self.match("192.0.2.10", now=STALE)["deny"])

    def test_missing_and_malformed_provider_data_fails_closed(self):
        doc = json.loads(sv.RANGES_FIXTURE.read_text(encoding="utf-8"))
        doc["prefixes"] = [p for p in doc["prefixes"] if p["provider"] != "azure"]
        missing = sv.ranges_from_document(doc)
        self.assertEqual(missing.provider_status(FRESH)["azure"], "missing")
        self.assertEqual(sv.match_ip("127.0.0.1", missing, now=FRESH)["verdict"], "unknown")

        doc = json.loads(sv.RANGES_FIXTURE.read_text(encoding="utf-8"))
        doc["prefixes"].append({"ip_prefix": "192.0.2.1/24", "provider": "google"})  # host bits set
        broken = sv.ranges_from_document(doc)
        self.assertEqual(broken.provider_status(FRESH)["google"], "invalid")
        self.assertTrue(broken.errors)
        self.assertEqual(sv.match_ip("127.0.0.1", broken, now=FRESH)["verdict"], "unknown")

        unreadable = sv.load_ranges(REPO_ROOT / "fixtures" / "ip-ranges" / "does-not-exist.json")
        self.assertEqual(sv.match_ip("127.0.0.1", unreadable, now=FRESH)["verdict"], "unknown")

    def test_classify_addresses_denies_if_any_address_denied(self):
        mixed = sv.classify_addresses(["127.0.0.1", "192.0.2.10"], self.ranges, now=FRESH)
        self.assertEqual((mixed["deny"], mixed["verdict"]), (True, "cloud_range"))
        self.assertTrue(sv.classify_addresses([], self.ranges, now=FRESH)["deny"])
        clean = sv.classify_addresses(["127.0.0.1"], self.ranges, now=FRESH)
        self.assertFalse(clean["deny"])

    def test_naive_now_rejected(self):
        with self.assertRaises(ValueError):
            sv.match_ip("127.0.0.1", self.ranges, now=datetime(2026, 11, 20))


class FeedLoaderTest(unittest.TestCase):
    AWS_FEED = json.dumps({
        "syncToken": "1", "createDate": "2026-11-20-00-00-00",
        "prefixes": [{"ip_prefix": "192.0.2.0/24", "region": "us-east-1", "service": "AMAZON"}],
        "ipv6_prefixes": [{"ipv6_prefix": "2001:db8:cc::/48", "region": "us-east-1", "service": "AMAZON"}],
    }).encode()

    def test_mocked_aws_feed_replaces_fixture_provider_with_provenance(self):
        calls = []

        def fetch(url, *, timeout, max_bytes):
            calls.append((url, timeout, max_bytes))
            return self.AWS_FEED

        live = sv.load_published_feed("aws", approved_urls=sv.PUBLISHED_FEEDS["aws"], fetch=fetch, now=FRESH)
        self.assertEqual(live.errors, [])
        self.assertEqual(calls[0][0], "https://ip-ranges.amazonaws.com/ip-ranges.json")
        self.assertFalse(live.sources["aws"]["synthetic"])
        merged = sv.load_ranges().merge(live)
        self.assertEqual(sv.match_ip("2001:db8:cc::1", merged, now=FRESH)["provider"], "aws")
        self.assertFalse(sv.match_ip("2001:db8:cc::1", merged, now=FRESH)["synthetic"])
        self.assertEqual(sv.match_ip("2001:db8:aa::1", merged, now=FRESH)["verdict"], "not_listed")
        expired = FRESH + sv.FEED_MAX_AGE
        self.assertEqual(merged.provider_status(expired)["aws"], "stale")

    def test_cloudflare_google_azure_formats(self):
        bodies = {
            "https://www.cloudflare.com/ips-v4": b"203.0.113.128/26\n",
            "https://www.cloudflare.com/ips-v6": b"2001:db8:dd::/48\n",
            "https://www.gstatic.com/ipranges/cloud.json": json.dumps({"prefixes": [
                {"ipv4Prefix": "203.0.113.0/25", "service": "Google Cloud", "scope": "europe-west1"},
                {"ipv6Prefix": "2001:db8:ee::/48", "service": "Google Cloud", "scope": "europe-west1"}]}).encode(),
            "https://example.invalid/azure-servicetags.json": json.dumps({"values": [
                {"name": "AzureMonitor", "properties": {"region": "", "addressPrefixes": ["198.51.100.0/24"]}}]}).encode(),
        }

        def fetch(url, **_):
            return bodies[url]

        for provider, urls in (("cloudflare", sv.PUBLISHED_FEEDS["cloudflare"]),
                               ("google", sv.PUBLISHED_FEEDS["google"]),
                               ("azure", ["https://example.invalid/azure-servicetags.json"])):
            result = sv.load_published_feed(provider, approved_urls=urls, fetch=fetch, now=FRESH)
            self.assertEqual(result.errors, [], provider)
            self.assertGreaterEqual(len(result.entries), 1, provider)

    def test_feed_failures_fail_closed(self):
        def boom(url, **_):
            raise OSError("unreachable")

        cases = [
            ("aws", sv.PUBLISHED_FEEDS["aws"], boom),
            ("aws", sv.PUBLISHED_FEEDS["aws"], lambda url, **_: b"{not json"),
            ("aws", sv.PUBLISHED_FEEDS["aws"], lambda url, **_: json.dumps({"prefixes": [{"ip_prefix": "1.2.3.4/33"}]}).encode()),
            ("aws", sv.PUBLISHED_FEEDS["aws"], lambda url, max_bytes, **_: b"x" * (max_bytes + 1)),
            ("azure", sv.PUBLISHED_FEEDS["azure"], _no_network),  # no approved URL
        ]
        for provider, urls, fetch in cases:
            result = sv.load_published_feed(provider, approved_urls=urls, fetch=fetch, now=FRESH, max_bytes=1024)
            self.assertIn(provider, result.invalid_providers)
            merged = sv.load_ranges().merge(result)
            self.assertEqual(sv.match_ip("127.0.0.1", merged, now=FRESH)["verdict"], "unknown")

    def test_default_transport_rejects_plain_http_without_network(self):
        with self.assertRaises(ValueError):
            sv._default_fetch("http://example.invalid/feed", timeout=1, max_bytes=10)

    def test_snapshot_written_to_out_not_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = sv.save_snapshot(sv.load_ranges(), Path(tmp))
            reloaded = sv.load_ranges(path)
            self.assertEqual(len(reloaded.entries), len(sv.load_ranges().entries))
            self.assertEqual(reloaded.provider_status(FRESH), sv.load_ranges().provider_status(FRESH))
        with self.assertRaises(ValueError):
            sv.save_snapshot(sv.load_ranges(), REPO_ROOT / "fixtures")


if __name__ == "__main__":
    unittest.main()
