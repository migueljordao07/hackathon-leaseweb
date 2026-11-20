"""Offline tests for OpenStack template rendering (WS1-04). No tofu, no network."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skyshift import translate as tr

U = lambda e: {"unresolved": True, "expression": e}  # noqa: E731
SG = {"id": "aws_security_group.app", "type": "aws_security_group", "references": [],
      "attributes": {"name": U('"${var.project_name}-sg"'), "description": "demo",
                     "ingress": [{"from_port": 443, "to_port": 443, "protocol": "tcp",
                                  "cidr_blocks": ["192.0.2.0/24"], "description": "https"}],
                     "egress": [{"from_port": 0, "to_port": 0, "protocol": "-1",
                                 "cidr_blocks": ["192.0.2.0/24"]}],
                     "tags": {"Name": "sg"}}}
VM = {"id": "aws_instance.app", "type": "aws_instance", "references": ["aws_security_group.app"],
      "attributes": {"ami": U("${var.ami_id}"), "instance_type": "t3.micro",
                     "tags": {"Name": U('"${var.project_name}-app"'),
                              "Bucket": U("${aws_s3_bucket.demo.bucket}")}}}
BUCKET = {"id": "aws_s3_bucket.demo", "type": "aws_s3_bucket", "references": [],
          "attributes": {"bucket": U("${var.bucket_name}")}}
DATA_MAP = {"resources": [BUCKET, SG, VM], "calls": [], "buckets": [], "readiness": {}}
TARGET = {"target_id": "leaseweb-native", "operator": "Leaseweb", "jurisdiction": "EU",
          "storage_mode": "native_s3", "criteria": [], "prices": [], "explanation": {},
          "provider": "openstack"}


def translate(data_map=DATA_MAP, target=TARGET, config=None, runner=None, tofu=""):
    out = Path(tempfile.mkdtemp())
    rec = tr._live_translate(data_map, target, output_dir=out, config=config or {},
                             tofu=tofu, runner=runner, find=lambda: None)
    return rec, out


class TemplateTest(unittest.TestCase):
    def test_three_types_rendered(self):
        rec, out = translate()
        text = (out / "iac" / "main.tf").read_text(encoding="utf-8")
        self.assertIn('resource "openstack_networking_secgroup_v2" "app"', text)
        self.assertIn('resource "openstack_compute_instance_v2" "app"', text)
        self.assertIn("terraform-provider-openstack/openstack", text)
        rows = {r["source_id"]: r for r in rec["data"]["resources"]}
        self.assertEqual(rows["aws_security_group.app"]["status"], "mapped")
        self.assertEqual(rows["aws_instance.app"]["status"], "manual")  # AMI unresolved
        self.assertIn("AMI", rows["aws_instance.app"]["manual_reason"])
        self.assertEqual(rows["aws_s3_bucket.demo"]["status"], "manual")
        self.assertEqual(rec["status"], "incomplete")
        self.assertEqual([r["source_id"] for r in rec["data"]["resources"]],
                         [r["id"] for r in DATA_MAP["resources"]])

    def test_rules_explicit_never_broadened(self):
        _, out = translate()
        text = (out / "iac" / "main.tf").read_text(encoding="utf-8")
        self.assertIn("delete_default_rules = true", text)
        self.assertIn("port_range_min    = 443", text)
        self.assertNotIn("0.0.0.0/0", text)
        self.assertEqual(text.count('remote_ip_prefix  = "192.0.2.0/24"'), 2)

    def test_source_references(self):
        _, out = translate()
        text = (out / "iac" / "main.tf").read_text(encoding="utf-8")
        self.assertIn("security_groups = [openstack_networking_secgroup_v2.app.name]", text)
        self.assertIn('variable "project_name"', text)
        self.assertNotIn("aws_s3_bucket.demo.bucket", text.split("# aws_s3_bucket")[0])

    def test_unknown_resource_manual(self):
        dm = dict(DATA_MAP, resources=[{"id": "aws_db_instance.db", "type": "aws_db_instance",
                                        "attributes": {}}])
        rec, _ = translate(dm)
        self.assertEqual(rec["data"]["resources"][0]["status"], "manual")

    def test_malicious_literals_escaped(self):
        sg = json.loads(json.dumps(SG))
        sg["attributes"]["description"] = 'x" }\nresource "evil" "e" { ${file("/etc/passwd")} %{if}'
        rec, out = translate(dict(DATA_MAP, resources=[sg]))
        text = (out / "iac" / "main.tf").read_text(encoding="utf-8")
        self.assertNotIn('resource "evil"\n', text.replace('\\"', ""))
        self.assertIn("$${file", text)
        self.assertIn("%%{if}", text)
        self.assertNotIn("\n" + 'resource "evil"', text)

    def test_disallowed_expression_rejected(self):
        with self.assertRaises(tr.Unresolvable):
            tr.hcl_value(U('${file("/etc/passwd")}'), set())

    def test_deterministic(self):
        _, a = translate()
        _, b = translate()
        self.assertEqual((a / "iac/main.tf").read_text(), (b / "iac/main.tf").read_text())

    def test_output_confined(self):
        _, out = translate()
        files = [p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()]
        self.assertEqual(files, ["iac/main.tf"])

    def test_credentials_not_written(self):
        secret = "S3CRET-0123456789abcdefXYZ"
        cfg = {"OS_APPLICATION_CREDENTIAL_SECRET": secret, "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": secret}
        rec, out = translate(config=cfg)
        self.assertNotIn(secret, (out / "iac/main.tf").read_text())
        self.assertNotIn(secret, json.dumps(rec))

    def test_unapproved_provider_incomplete(self):
        rec, out = translate(target=dict(TARGET, provider="aws"))
        self.assertEqual(rec["status"], "incomplete")
        self.assertFalse((out / "iac").exists())

    def test_no_apply_in_source(self):
        src = Path(tr.__file__).read_text(encoding="utf-8")
        for verb in ('"apply"', '"plan"', '"destroy"'):
            self.assertNotIn(verb, src)

    def test_stub_unchanged(self):
        out = Path(tempfile.mkdtemp())
        rec = tr.translate(DATA_MAP, TARGET, output_dir=out, config={}, stub=True)
        self.assertEqual((rec["mode"], rec["status"]), ("stub", "incomplete"))


if __name__ == "__main__":
    unittest.main()
