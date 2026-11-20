"""Offline distribution checks for the public repository (WS4-03)."""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from skyshift import cli

ROOT = Path(__file__).resolve().parents[2]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class DistributionTest(unittest.TestCase):
    def test_license_is_apache_2(self):
        text = _read("LICENSE")
        self.assertIn("Apache License", text)
        self.assertIn("Version 2.0, January 2004", text)
        self.assertIn("TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION", text)
        self.assertIn("END OF TERMS AND CONDITIONS", text)

    def test_readme_documents_commands_and_honesty(self):
        text = _read("README.md")
        for needle in ("pip install -r requirements.txt", "python -m skyshift.cli --help",
                       "run-all --workload fixtures/aws_workload --out out --stub",
                       "out/report.html", "Apache License 2.0", "OpenTofu", "rclone",
                       "Ollama", "replay", "incomplete"):
            self.assertIn(needle, text)
        self.assertNotRegex(text, r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b(?<!127\.0\.0\.1)")

    def test_env_example_lists_contract_names_without_values(self):
        lines = [l for l in _read(".env.example").splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
        names = []
        for line in lines:
            name, sep, value = line.partition("=")
            self.assertEqual(sep, "=", line)
            self.assertEqual(value, "", f"{name} must have an empty value")
            names.append(name)
        contract = re.findall(r"`([A-Z][A-Z0-9_]+)`",
                              _read("tasks/contracts.md").split("## Environment names only")[1]
                              .split("Only provider-appropriate")[0])
        self.assertEqual(sorted(names), sorted(set(contract)))
        self.assertEqual(sorted(names), sorted(cli.ENV_NAMES))

    def test_requirements_declare_runtime_packages(self):
        text = _read("requirements.txt").lower()
        for package in ("boto3", "python-hcl2", "pyyaml", "moto[server]"):
            self.assertIn(package, text)

    @unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "git checkout needed")
    def test_ignore_boundaries(self):
        def ignored(path: str) -> bool:
            return subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0
        for path in (".env", "vm.env", "out/evidence.json", "skyshift/__pycache__/x.pyc"):
            self.assertTrue(ignored(path), path)
        for path in (".env.example", "fixtures/aws_workload/app.py", "tasks/contracts.md",
                     "requirements.txt"):
            self.assertFalse(ignored(path), path)


if __name__ == "__main__":
    unittest.main()
