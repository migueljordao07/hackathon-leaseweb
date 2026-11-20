"""WS3-07 demo-path tests: offline by default; SKYSHIFT_WS3_LIVE_TESTS=1 runs live sever on the VM."""
import os
import unittest

from skyshift import sever

DATA_MAP = {"resources": [], "calls": [], "buckets": [], "readiness": {}}
TARGET = {k: None for k in ("target_id", "operator", "jurisdiction", "storage_mode", "criteria", "prices", "explanation")}


class OfflineDemoPathTest(unittest.TestCase):
    def test_live_without_target_config_is_incomplete_and_measures_nothing(self):
        rec = sever.sever(DATA_MAP, TARGET, config={})
        self.assertEqual((rec["mode"], rec["status"]), ("live", "incomplete"))
        self.assertEqual(rec["data"]["attempts"], [])
        self.assertTrue(all(c["status"] == "incomplete" for c in rec["checks"]))

    def test_severance_config_maps_target_to_app_names_only(self):
        cfg = {"SKYSHIFT_TARGET_ENDPOINT_URL": "https://t", "SKYSHIFT_TARGET_ACCESS_KEY_ID": "k",
               "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": "s", "SKYSHIFT_TELEMETRY_ENDPOINT": "http://x"}
        out = sever._severance_config(cfg)
        self.assertEqual(out["AWS_ENDPOINT_URL"], "https://t")
        self.assertEqual(out["AWS_ACCESS_KEY_ID"], "k")
        self.assertNotIn("SKYSHIFT_TELEMETRY_ENDPOINT", out)  # first attempt uses the app default

    def test_radar_baseline_excludes_preexisting_sockets(self):
        old = {"state": "ESTABLISHED", "local_port": 50000, "remote_ip": "198.51.100.7", "remote_port": 22}
        new = {"state": "ESTABLISHED", "local_port": 50001, "remote_ip": "198.51.100.8", "remote_port": 443}
        calls = iter([([old], []), ([old, new], []), ([old, new], [])])
        sampler = sever._RadarSampler(None)
        sampler.reader = lambda: next(calls, ([old, new], []))
        with sampler:
            pass
        result = sampler.result([])
        self.assertEqual(result["preexisting_excluded"], 1)
        self.assertEqual([b["port"] for b in result["bypasses"]], [443])

    def test_app_runner_hash_recorded(self):
        runner = sever.fixture_app_runner({})
        self.assertRegex(runner.hash_before or "", r"^[0-9a-f]{64}$")


@unittest.skipUnless(os.environ.get("SKYSHIFT_WS3_LIVE_TESTS") == "1", "live VM test (opt-in)")
class LiveDemoPathTest(unittest.TestCase):
    def test_live_red_then_green(self):
        from skyshift.cli import build_config
        rec = sever.sever(DATA_MAP, TARGET, config=build_config())
        attempts = rec["data"]["attempts"]
        self.assertGreaterEqual(len(attempts), 1)
        self.assertTrue(any(e["decision"] == "deny" for e in attempts[0]["events"]))
        self.assertEqual(rec["data"]["app_sha256_before"], rec["data"]["app_sha256_after"])
        self.assertIn(rec["data"]["final"], ("green", "blocked", "incomplete"))


if __name__ == "__main__":
    unittest.main()
