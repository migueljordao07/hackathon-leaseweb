"""Offline integration tests for the WS4-01 stub run-all pipeline.

Run from the repository root:
    python -B -m unittest tests.ws4.test_stub_run_all -v

Standard library only. Every run writes to a temporary output directory; in-process
runs block sockets so any network attempt fails the test. No VM, provider or model.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import cli, evidence  # noqa: E402
from skyshift import discover as discover_mod  # noqa: E402
from skyshift import migrate as migrate_mod  # noqa: E402
from skyshift import parity as parity_mod  # noqa: E402
from skyshift import sever as sever_mod  # noqa: E402
from skyshift import translate as translate_mod  # noqa: E402

WORKLOAD = REPO_ROOT / "fixtures" / "aws_workload"
STEPS = ("discover", "choose", "translate", "migrate", "run", "parity", "sever", "evidence")
ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}
REQUIRED_DATA = {
    "discover": {"resources", "calls", "buckets", "readiness"},
    "choose": {"target_id", "operator", "jurisdiction", "storage_mode", "criteria", "prices",
               "explanation"},
    "translate": {"provider", "files", "resources", "validation"},
    "migrate": {"objects", "source_count", "target_count", "matched", "missing", "different",
                "extra"},
    "run": {"app_sha256_before", "app_sha256_after", "endpoint_changed", "functional_checks",
            "host_network"},
    "parity": {"operations", "selection"},
    "sever": {"attempts", "max_attempts", "final", "radar_scope"},
    "evidence": {"records", "final_hash", "report_path", "open_items"},
}
OUTPUTS = [f"{s}.json" for s in STEPS] + ["iac/main.tf", "report.html"]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

SECRET = "SENTINEL-WS4-SECRET-do-not-leak-91c2"
SECRET_ENV = {name: f"{SECRET}-{name}" for name in cli.SECRET_ENV_NAMES}
STALE = "STALE-MARKER-from-an-earlier-run"

# Real stub functions, captured before any test patches their modules.
REAL_DISCOVER = discover_mod.discover
REAL_MIGRATE = migrate_mod.migrate
REAL_VERIFY = parity_mod.verify


def _no_network(*_args, **_kwargs):
    raise AssertionError("network access attempted during an offline test")


class StubRunAllTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "out"
        for target in ("socket.socket.connect", "socket.create_connection", "socket.getaddrinfo"):
            patcher = mock.patch(target, side_effect=_no_network)
            patcher.start()
            self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, SECRET_ENV)
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main([*args, "--workload", str(WORKLOAD), "--out", str(self.out), "--stub"])
        return code, stdout.getvalue()

    def load(self, step: str) -> dict:
        return json.loads((self.out / f"{step}.json").read_text(encoding="utf-8"))

    def all_text(self) -> str:
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(self.out.rglob("*"))
                         if p.is_file())

    # ------------------------------------------------------------------ happy path

    def test_run_all_stub_writes_eight_incomplete_records_and_exits_2(self):
        code, stdout = self.run_cli("run-all")
        self.assertEqual(code, 2)
        self.assertIn("exit 2", stdout)
        found = sorted(p.relative_to(self.out).as_posix() for p in self.out.rglob("*")
                       if p.is_file())
        self.assertEqual(found, sorted(OUTPUTS))
        for step in STEPS:
            text = (self.out / f"{step}.json").read_text(encoding="utf-8")
            record = json.loads(text)
            self.assertEqual(set(record), ENVELOPE_KEYS, step)
            self.assertEqual(record["schema_version"], 1)
            self.assertEqual(record["step"], step)
            self.assertEqual(record["mode"], "stub", step)
            self.assertEqual(record["status"], "incomplete", step)
            self.assertTrue(record["checks"], step)
            for check in record["checks"]:
                self.assertEqual(check["status"], "incomplete", (step, check))
            self.assertTrue(REQUIRED_DATA[step] <= set(record["data"]), step)
            self.assertNotIn("NaN", text)
            self.assertNotIn("Infinity", text)
            # Sorted keys, UTF-8, exactly what the CLI's formatter produces.
            self.assertEqual(text, json.dumps(record, sort_keys=True, indent=2,
                                              ensure_ascii=False) + "\n")

    def test_report_is_qualified_and_self_contained(self):
        self.run_cli("run-all")
        report = (self.out / "report.html").read_text(encoding="utf-8")
        self.assertIn("STUB / INCOMPLETE / NOT VM VALIDATED", report)
        self.assertIn("no VM validation occurred", report)
        self.assertIn("not a certificate", report)
        self.assertNotIn("<script", report.lower())
        self.assertNotIn("http://", report)
        self.assertNotIn("https://", report)
        self.assertNotRegex(report, r"\{\{.*\}\}")
        self.assertIn(self.load("evidence")["data"]["final_hash"], report)
        for item in self.load("evidence")["data"]["open_items"]:
            self.assertTrue(item)
        self.assertTrue(self.load("evidence")["data"]["open_items"][0].startswith("STUB RUN"))

    def test_call_order_and_data_flow(self):
        calls = []
        real = {
            "discover": discover_mod.discover, "choose": discover_mod.choose,
            "translate": translate_mod.translate, "migrate": migrate_mod.migrate,
            "run_app": parity_mod.run_app, "verify": parity_mod.verify,
            "sever": sever_mod.sever, "build_evidence": evidence.build_evidence,
        }

        def recorder(name):
            def wrapper(*args, **kwargs):
                calls.append((name, args, kwargs))
                return real[name](*args, **kwargs)
            return wrapper

        targets = {
            "discover": (discover_mod, "discover"), "choose": (discover_mod, "choose"),
            "translate": (translate_mod, "translate"), "migrate": (migrate_mod, "migrate"),
            "run_app": (parity_mod, "run_app"), "verify": (parity_mod, "verify"),
            "sever": (sever_mod, "sever"), "build_evidence": (evidence, "build_evidence"),
        }
        with contextlib.ExitStack() as stack:
            for name, (module, attr) in targets.items():
                stack.enter_context(mock.patch.object(module, attr, recorder(name)))
            self.assertEqual(self.run_cli("run-all")[0], 2)

        self.assertEqual([c[0] for c in calls], list(targets))
        for _, _, kwargs in calls:
            self.assertIs(kwargs["stub"], True)
            self.assertIsInstance(kwargs["config"], dict)
        data = {step: self.load(step)["data"] for step in STEPS}
        by_name = {name: (args, kwargs) for name, args, kwargs in calls}
        self.assertEqual(by_name["discover"][0], (WORKLOAD,))
        self.assertEqual(by_name["choose"][0], (data["discover"],))
        self.assertEqual(by_name["translate"][0], (data["discover"], data["choose"]))
        self.assertEqual(by_name["translate"][1]["output_dir"], self.out)
        self.assertEqual(by_name["migrate"][0], (data["discover"], data["choose"]))
        self.assertEqual(by_name["run_app"][0], (WORKLOAD, data["choose"]))
        self.assertEqual(by_name["verify"][0], (data["discover"], data["choose"]))
        self.assertEqual(by_name["sever"][0], (data["discover"], data["choose"]))
        chain_input = by_name["build_evidence"][0][0]
        self.assertEqual([r["step"] for r in chain_input], list(STEPS[:-1]))
        self.assertEqual(chain_input, [self.load(step) for step in STEPS[:-1]])

    def test_verify_command_emits_run_and_parity_only(self):
        code, _ = self.run_cli("verify")
        self.assertEqual(code, 2)
        found = sorted(p.name for p in self.out.iterdir() if p.is_file())
        self.assertEqual(found, ["choose.json", "discover.json", "parity.json", "run.json"])

    # ------------------------------------------------------------------ evidence chain

    def test_chain_recomputes_from_canonical_bytes_and_detects_mutation(self):
        self.run_cli("run-all")
        ev = self.load("evidence")
        records = [self.load(step) for step in STEPS[:-1]]
        previous = "0" * 64
        self.assertEqual(ev["data"]["records"][0]["previous_hash"], previous)
        for record, link in zip(records, ev["data"]["records"]):
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False, allow_nan=False).encode("utf-8")
            artifact = hashlib.sha256(canonical).hexdigest()
            self.assertEqual(link["artifact_sha256"], artifact)
            self.assertEqual(link["previous_hash"], previous)
            previous = hashlib.sha256(bytes.fromhex(previous) + bytes.fromhex(artifact)).hexdigest()
            self.assertEqual(link["hash"], previous)
            self.assertEqual(link["path"], (self.out / f"{record['step']}.json").as_posix())
            for value in (link["artifact_sha256"], link["previous_hash"], link["hash"]):
                self.assertRegex(value, SHA256_RE)
        self.assertEqual(ev["data"]["final_hash"], previous)
        self.assertEqual(evidence.verify_chain(records, ev["data"]), [])

        mutated = json.loads(json.dumps(records))
        mutated[3]["data"]["matched"] += 1
        problems = evidence.verify_chain(mutated, ev["data"])
        self.assertIn("migrate: artifact_sha256 mismatch", problems)
        self.assertIn("final_hash mismatch", problems)
        swapped = records[:]
        swapped[2], swapped[3] = swapped[3], swapped[2]
        self.assertTrue(evidence.verify_chain(swapped, ev["data"]))
        self.assertTrue(evidence.verify_chain(records[:-1], ev["data"]))

    def test_rerun_is_byte_identical(self):
        self.run_cli("run-all")
        first = {p: (self.out / p).read_bytes() for p in OUTPUTS}
        self.run_cli("run-all")
        second = {p: (self.out / p).read_bytes() for p in OUTPUTS}
        self.assertEqual(first, second)

    # ------------------------------------------------------------------ stale outputs

    def test_stale_outputs_are_replaced_and_unrelated_files_kept(self):
        (self.out / "iac").mkdir(parents=True)
        for name in OUTPUTS:
            (self.out / name).write_text(STALE, encoding="utf-8")
        (self.out / "notes.txt").write_text("keep me", encoding="utf-8")
        self.run_cli("run-all")
        self.assertNotIn(STALE, "\n".join((self.out / p).read_text(encoding="utf-8")
                                          for p in OUTPUTS))
        self.assertEqual((self.out / "notes.txt").read_text(encoding="utf-8"), "keep me")

    def test_partial_command_clears_outputs_of_other_steps(self):
        self.run_cli("run-all")
        self.run_cli("discover")
        found = sorted(p.relative_to(self.out).as_posix() for p in self.out.rglob("*")
                       if p.is_file())
        self.assertEqual(found, ["discover.json"])

    # ------------------------------------------------------------------ failure handling

    def test_forced_exception_is_sanitized_incomplete_and_skips_dependents(self):
        (self.out / "iac").mkdir(parents=True)
        for name in OUTPUTS:
            (self.out / name).write_text(STALE, encoding="utf-8")
        message = (f"boom {SECRET_ENV['AWS_SECRET_ACCESS_KEY']} "
                   "https://user:pw@bucket.example/key?X-Amz-Signature=abcdef0123")
        choose = mock.Mock(wraps=discover_mod.choose)
        with mock.patch.object(discover_mod, "discover", side_effect=RuntimeError(message)), \
                mock.patch.object(discover_mod, "choose", choose):
            code, _ = self.run_cli("run-all")
        self.assertEqual(code, 2)
        choose.assert_not_called()
        record = self.load("discover")
        self.assertEqual(record["status"], "incomplete")
        self.assertEqual(record["checks"][0]["id"], "step_completed")
        self.assertTrue(record["errors"][0].startswith("RuntimeError: boom [REDACTED]"))
        text = self.all_text()
        self.assertNotIn(SECRET, text)
        self.assertNotIn("abcdef0123", text)
        self.assertNotIn("user:pw", text)
        self.assertNotIn(STALE, text)
        for step in ("choose", "translate", "migrate", "run", "parity", "sever"):
            dependent = self.load(step)
            self.assertEqual(dependent["status"], "incomplete")
            self.assertEqual(dependent["checks"][0]["id"], "upstream_available", step)
            self.assertTrue(REQUIRED_DATA[step] <= set(dependent["data"]), step)
        self.assertFalse((self.out / "iac" / "main.tf").exists())
        self.assertEqual(self.load("evidence")["status"], "incomplete")
        self.assertTrue((self.out / "report.html").exists())

    def test_midstream_exception_only_skips_steps_that_need_it(self):
        with mock.patch.object(translate_mod, "translate", side_effect=ValueError("bad map")):
            code, _ = self.run_cli("run-all")
        self.assertEqual(code, 2)
        self.assertEqual(self.load("translate")["errors"], ["ValueError: bad map"])
        for step in ("migrate", "run", "parity", "sever"):
            self.assertEqual(self.load(step)["errors"], [], step)
            self.assertEqual(self.load(step)["mode"], "stub", step)

    def test_record_leaking_a_secret_is_withheld(self):
        def leaky(*args, **kwargs):
            record = REAL_MIGRATE(*args, **kwargs)
            record["data"]["objects"][0]["key"] = SECRET_ENV["SKYSHIFT_TARGET_SECRET_ACCESS_KEY"]
            return record
        with mock.patch.object(migrate_mod, "migrate", leaky):
            self.assertEqual(self.run_cli("run-all")[0], 2)
        record = self.load("migrate")
        self.assertEqual(record["checks"][0]["id"], "record_valid")
        self.assertIn("secret", record["errors"][0])
        self.assertNotIn(SECRET, self.all_text())

    def test_nan_and_malformed_envelopes_become_incomplete(self):
        def nan_parity(*args, **kwargs):
            record = REAL_VERIFY(*args, **kwargs)
            record["data"]["score"] = float("nan")
            return record
        with mock.patch.object(parity_mod, "verify", nan_parity), \
                mock.patch.object(sever_mod, "sever", return_value={"step": "sever"}):
            self.assertEqual(self.run_cli("run-all")[0], 2)
        self.assertIn("NaN", self.load("parity")["errors"][0])
        self.assertEqual(self.load("sever")["checks"][0]["id"], "record_valid")
        self.assertTrue((self.out / "report.html").exists())
        for step in STEPS:
            text = (self.out / f"{step}.json").read_text(encoding="utf-8")
            self.assertNotIn(": NaN", text)

    def test_failed_evidence_step_leaves_no_report(self):
        (self.out).mkdir(parents=True)
        (self.out / "report.html").write_text(STALE, encoding="utf-8")
        with mock.patch.object(evidence, "build_evidence", side_effect=ValueError("bad chain")):
            self.assertEqual(self.run_cli("run-all")[0], 2)
        self.assertEqual(self.load("evidence")["errors"], ["ValueError: bad chain"])
        self.assertFalse((self.out / "report.html").exists())

    def test_report_escapes_record_content(self):
        hostile = '<script>alert("x")</script>{{ banner }}'

        def hostile_discover(*args, **kwargs):
            record = REAL_DISCOVER(*args, **kwargs)
            record["checks"][0]["detail"] = hostile
            return record
        with mock.patch.object(discover_mod, "discover", hostile_discover):
            self.run_cli("run-all")
        report = (self.out / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;{{ banner }}", report)

    # ------------------------------------------------------------------ exit codes and CLI

    def test_exit_code_mapping(self):
        def rec(mode, status):
            return {"mode": mode, "status": status}
        self.assertEqual(cli.exit_code([rec("live", "PASS")] * 8), 0)
        self.assertEqual(cli.exit_code([rec("live", "PASS")] * 7 + [rec("live", "FAIL")]), 1)
        self.assertEqual(cli.exit_code([rec("stub", "FAIL"), rec("stub", "incomplete")]), 1)
        self.assertEqual(cli.exit_code([rec("live", "PASS")] * 7 + [rec("stub", "PASS")]), 2)
        self.assertEqual(cli.exit_code([rec("live", "PASS")] * 7 + [rec("replay", "PASS")]), 2)
        self.assertEqual(cli.exit_code([rec("live", "PASS"), rec("live", "incomplete")]), 2)
        self.assertEqual(cli.exit_code([]), 2)

    def test_help_exits_zero_without_files(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(cli.main(["--help"]), 0)
                self.assertEqual(cli.main(["run-all", "--help"]), 0)
        finally:
            os.chdir(cwd)
        self.assertIn("run-all", stdout.getvalue())
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_config_uses_documented_names_and_never_prints_values(self):
        config = cli.build_config({"AWS_SECRET_ACCESS_KEY": "x" * 12, "UNRELATED": "y",
                                   "SKYSHIFT_TARGET_BUCKET": ""})
        self.assertEqual(config, {"AWS_SECRET_ACCESS_KEY": "x" * 12})
        _, stdout = self.run_cli("run-all")
        self.assertNotIn(SECRET, stdout)
        self.assertNotIn(SECRET, self.all_text())


class SubprocessTest(unittest.TestCase):
    """The documented commands, exactly as a user runs them."""

    def _env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k not in cli.ENV_NAMES}
        env["PYTHONPATH"] = str(REPO_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def test_module_help_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-B", "-m", "skyshift.cli", "--help"],
                                    cwd=tmp, env=self._env(), capture_output=True, text=True,
                                    timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_module_run_all_stub_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            result = subprocess.run(
                [sys.executable, "-B", "-m", "skyshift.cli", "run-all", "--workload",
                 "fixtures/aws_workload", "--out", str(out), "--stub"],
                cwd=REPO_ROOT, env=self._env(), capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 2, result.stderr)
            for name in OUTPUTS:
                self.assertTrue((out / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
