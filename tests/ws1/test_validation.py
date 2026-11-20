"""Offline tests for the tofu validate step (WS1-05, no AI repair). Fake runner only."""

from __future__ import annotations

import json
import subprocess
import unittest

from skyshift import translate as tr
from tests.ws1.test_templates import translate


class FakeRunner:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def __call__(self, args, cwd, timeout):
        self.calls.append((args, cwd, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


OK_JSON = json.dumps({"valid": True, "error_count": 0, "diagnostics": []})
BAD_JSON = json.dumps({"valid": False, "diagnostics": [
    {"severity": "error", "summary": "Unsupported argument", "detail": "x"}]})


class ValidationTest(unittest.TestCase):
    def test_exact_args_and_pass(self):
        runner = FakeRunner((0, "ok", ""), (0, OK_JSON, ""))
        rec, out = translate(runner=runner, tofu="tofu")
        self.assertEqual(runner.calls[0][0], ["tofu", "init", "-backend=false", "-input=false",
                                              "-no-color"])
        self.assertEqual(runner.calls[1][0], ["tofu", "validate", "-json", "-no-color"])
        self.assertTrue(all(c[2] == 30 for c in runner.calls))
        self.assertEqual(runner.calls[0][1], out / "iac")
        v = rec["data"]["validation"]
        self.assertEqual((v["method"], v["init_exit"], v["validate_exit"], v["attempts"]),
                         ("tofu", 0, 0, 1))
        checks = {c["id"]: c["status"] for c in rec["checks"]}
        self.assertEqual(checks["iac_validated"], "PASS")
        self.assertEqual(rec["status"], "incomplete")  # manual rows remain

    def test_init_failure_skips_validate(self):
        runner = FakeRunner((1, "", "registry unreachable"))
        rec, _ = translate(runner=runner, tofu="tofu")
        self.assertEqual(len(runner.calls), 1)
        v = rec["data"]["validation"]
        self.assertEqual((v["init_exit"], v["validate_exit"]), (1, None))
        self.assertEqual(rec["status"], "FAIL")

    def test_validate_failure_keeps_diagnostics(self):
        runner = FakeRunner((0, "", ""), (1, BAD_JSON, ""))
        rec, _ = translate(runner=runner, tofu="tofu")
        self.assertEqual(rec["status"], "FAIL")
        self.assertTrue(any("Unsupported argument" in d
                            for d in rec["data"]["validation"]["diagnostics"]))

    def test_timeout_is_incomplete_not_zero(self):
        runner = FakeRunner(subprocess.TimeoutExpired(["tofu"], 30))
        rec, _ = translate(runner=runner, tofu="tofu")
        v = rec["data"]["validation"]
        self.assertIsNone(v["init_exit"])
        self.assertEqual({c["id"]: c["status"] for c in rec["checks"]}["iac_validated"],
                         "incomplete")

    def test_missing_tofu_offline_schema(self):
        rec, _ = translate(tofu="")
        v = rec["data"]["validation"]
        self.assertEqual((v["method"], v["init_exit"], v["validate_exit"]),
                         ("offline_schema", None, None))
        self.assertNotEqual(rec["status"], "PASS")

    def test_tofu_env_drops_secrets(self):
        import os
        os.environ["OS_APPLICATION_CREDENTIAL_SECRET"] = "secret-value-for-test"
        try:
            self.assertNotIn("OS_APPLICATION_CREDENTIAL_SECRET", tr._tofu_env())
        finally:
            del os.environ["OS_APPLICATION_CREDENTIAL_SECRET"]


if __name__ == "__main__":
    unittest.main()
