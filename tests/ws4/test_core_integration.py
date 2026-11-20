"""Offline core-integration checks for live run-all wiring (WS4-05).

Injected doubles stand in for the live modules; nothing here is live acceptance.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from skyshift import cli
from skyshift import discover as discover_mod
from skyshift import migrate as migrate_mod
from skyshift import parity as parity_mod
from skyshift import sever as sever_mod
from skyshift import translate as translate_mod

WORKLOAD = Path(__file__).resolve().parents[2] / "fixtures" / "aws_workload"


def _live(step: str, status: str = "PASS") -> dict:
    return {"schema_version": 1, "step": step, "mode": "live", "status": status,
            "checks": [{"id": "measured", "status": status, "detail": "injected double"}],
            "data": dict(cli.EMPTY_DATA[step]), "errors": []}


class CoreIntegrationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "out"
        env = mock.patch.dict(os.environ, {"SKYSHIFT_TARGET_SECRET_ACCESS_KEY": "s3cr3t-value-xyz",
                                           "SKYSHIFT_TARGET_BUCKET": "demo-target"}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self, *args: str) -> int:
        with redirect_stdout(io.StringIO()):
            return cli.main([*args, "--workload", str(WORKLOAD), "--out", str(self.out)])

    def load(self, step: str) -> dict:
        return json.loads((self.out / f"{step}.json").read_text(encoding="utf-8"))

    def test_config_comes_from_environment_without_leaking(self):
        seen = {}

        def migrate(data_map, target, *, config, stub=False):
            seen.update(config)
            return _live("migrate")

        with mock.patch.object(migrate_mod, "migrate", migrate):
            self.run_cli("migrate")
        self.assertEqual(seen["SKYSHIFT_TARGET_BUCKET"], "demo-target")
        self.assertNotIn("s3cr3t-value-xyz", (self.out / "migrate.json").read_text("utf-8"))

    def test_failed_discover_does_not_block_config_driven_steps(self):
        calls = []

        def double(step):
            def fn(*args, **kwargs):
                calls.append(step)
                return _live(step)
            return fn

        with mock.patch.object(discover_mod, "discover", side_effect=RuntimeError("down")), \
                mock.patch.object(discover_mod, "choose", double("choose")), \
                mock.patch.object(translate_mod, "translate", double("translate")), \
                mock.patch.object(migrate_mod, "migrate", double("migrate")), \
                mock.patch.object(parity_mod, "run_app", double("run")), \
                mock.patch.object(parity_mod, "verify", double("parity")), \
                mock.patch.object(sever_mod, "sever", double("sever")):
            code = self.run_cli("run-all")
        self.assertEqual(code, 2)
        self.assertEqual(calls, ["migrate", "run", "parity", "sever"])
        for step in ("migrate", "run", "parity", "sever"):
            record = self.load(step)
            self.assertEqual(record["status"], "incomplete", step)  # PASS capped
            self.assertEqual(record["checks"][-1]["id"], "upstream_available", step)
        self.assertEqual(self.load("translate")["checks"][0]["id"], "upstream_available")

    def test_measured_fail_without_upstream_stays_fail(self):
        with mock.patch.object(discover_mod, "discover", side_effect=RuntimeError("down")), \
                mock.patch.object(migrate_mod, "migrate", return_value=_live("migrate", "FAIL")):
            code = self.run_cli("run-all")
        self.assertEqual(code, 1)
        self.assertEqual(self.load("migrate")["status"], "FAIL")

    def test_incomplete_upstream_record_still_feeds_later_steps(self):
        seen = []

        def migrate(data_map, target, *, config, stub=False):
            seen.append(target["target_id"])
            return _live("migrate")

        choose = _live("choose", "incomplete")
        choose["data"]["target_id"] = "leaseweb-selfhosted"
        with mock.patch.object(discover_mod, "discover", return_value=_live("discover")), \
                mock.patch.object(discover_mod, "choose", return_value=choose), \
                mock.patch.object(migrate_mod, "migrate", migrate):
            self.run_cli("migrate")
        self.assertEqual(seen, ["leaseweb-selfhosted"])
        self.assertEqual(self.load("migrate")["status"], "PASS")

    def test_all_live_pass_exits_zero(self):
        doubles = {"discover": (discover_mod, "discover"), "choose": (discover_mod, "choose"),
                   "translate": (translate_mod, "translate"), "migrate": (migrate_mod, "migrate"),
                   "run": (parity_mod, "run_app"), "parity": (parity_mod, "verify"),
                   "sever": (sever_mod, "sever")}
        patches = [mock.patch.object(m, a, return_value=_live(s)) for s, (m, a) in doubles.items()]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        records = cli.run_steps(cli.STEPS[:-1], workload=WORKLOAD, out=self.out.parent,
                                config={}, stub=False)
        self.assertEqual(cli.exit_code(list(records.values())), 0)


if __name__ == "__main__":
    unittest.main()
