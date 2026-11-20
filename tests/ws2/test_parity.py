"""Unit tests for the Moto-before versus target-after parity suite (WS2-05).

Run from the repository root:
    python -B -m unittest tests.ws2.test_parity -v

Standard library only; exercises the identical operation suite against explicit
in-memory S3 doubles, verifying operation selection, failure preservation,
presigned URL sanitization, cleanup isolation, and deterministic output.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import parity as parity_mod  # noqa: E402
from skyshift.parity import _live_verify, verify  # noqa: E402

ENVELOPE_KEYS = {"schema_version", "step", "mode", "status", "checks", "data", "errors"}

SYNTHETIC_TARGET = {
    "target_id": "leaseweb-native",
    "operator": "Leaseweb",
    "jurisdiction": "EU",
    "storage_mode": "native_s3",
    "criteria": [
        {
            "name": "operator_jurisdiction",
            "value": "EU",
            "source_url": "https://www.leaseweb.com/",
        }
    ],
    "prices": [
        {
            "item": "compute",
            "amount": None,
            "currency": "EUR",
            "unit": "hour",
            "source_url": None,
            "assumptions": "not verified",
        }
    ],
    "explanation": {"mode": "replay", "text": "Synthetic example"},
}

DATA_MAP_WITH_MULTIPART = {
    "resources": [
        {
            "id": "aws_s3_bucket.demo",
            "type": "aws_s3_bucket",
            "provider": "aws",
            "region": "eu-central-1",
            "supported": True,
        }
    ],
    "calls": [
        {"file": "fixtures/aws_workload/app.py", "line": 216, "service": "s3", "operation": "put_object", "bucket": "demo", "endpoint_host": None},
        {"file": "fixtures/aws_workload/app.py", "line": 236, "service": "s3", "operation": "get_object", "bucket": "demo", "endpoint_host": None},
        {"file": "fixtures/aws_workload/app.py", "line": 258, "service": "s3", "operation": "list_objects_v2", "bucket": "demo", "endpoint_host": None},
        {"file": "fixtures/aws_workload/app.py", "line": 282, "service": "s3", "operation": "create_multipart_upload", "bucket": "demo", "endpoint_host": None},
        {"file": "fixtures/aws_workload/app.py", "line": 294, "service": "s3", "operation": "upload_part", "bucket": "demo", "endpoint_host": None},
        {"file": "fixtures/aws_workload/app.py", "line": 305, "service": "s3", "operation": "complete_multipart_upload", "bucket": "demo", "endpoint_host": None},
    ],
    "buckets": [{"name": "demo", "provider": "aws", "jurisdiction": "US-controlled", "object_count": 4, "total_bytes": 131529}],
    "readiness": {"score": 100, "formula": "f", "proprietary": 0, "unsupported": 0, "us_calls": 0},
}

DATA_MAP_WITH_PRESIGNED = copy.deepcopy(DATA_MAP_WITH_MULTIPART)
DATA_MAP_WITH_PRESIGNED["calls"].append(
    {"file": "fixtures/aws_workload/app.py", "line": 340, "service": "s3", "operation": "generate_presigned_url", "bucket": "demo", "endpoint_host": None}
)

SENTINEL_SECRET = "SENTINEL-PARITY-SECRET-aabbccdd"
SIGNED_QUERY = "X-Amz-Signature=deadbeef1234567890&AWSAccessKeyId=AKIAEXAMPLE123"


class _InMemoryS3:
    """In-memory S3 double tracking calls and deleted keys for cleanup assertions."""

    def __init__(self, *, fail_ops: set[str] | None = None, preseed: dict[tuple[str, str], bytes] | None = None):
        self.fail_ops = set(fail_ops or ())
        self.objects: dict[tuple[str, str], bytes] = dict(preseed or {})
        self.uploads: dict[str, tuple[str, str, dict[int, tuple[str, bytes]]]] = {}
        self.deleted_keys: list[str] = []
        self.ops_called: list[str] = []
        self._next_id = 0

    def _check_fail(self, op: str):
        self.ops_called.append(op)
        if op in self.fail_ops:
            raise RuntimeError(f"injected {op} failure with {SENTINEL_SECRET}")

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **kwargs):
        self._check_fail("put_object")
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": f'"{hashlib.md5(Body).hexdigest()}"'}

    def get_object(self, *, Bucket: str, Key: str):
        self._check_fail("get_object")
        if (Bucket, Key) not in self.objects:
            raise KeyError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def head_object(self, *, Bucket: str, Key: str):
        self._check_fail("head_object")
        if (Bucket, Key) not in self.objects:
            raise KeyError("NoSuchKey")
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def list_objects_v2(self, *, Bucket: str, Prefix: str = "", ContinuationToken: str | None = None):
        self._check_fail("list_objects_v2")
        keys = [
            {"Key": key, "Size": len(body)}
            for (b, key), body in sorted(self.objects.items())
            if b == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": keys, "IsTruncated": False}

    def create_multipart_upload(self, *, Bucket: str, Key: str, **kwargs):
        self._check_fail("create_multipart_upload")
        self._next_id += 1
        uid = f"mp-{self._next_id}"
        self.uploads[uid] = (Bucket, Key, {})
        return {"UploadId": uid}

    def upload_part(self, *, Bucket: str, Key: str, UploadId: str, PartNumber: int, Body: bytes):
        self._check_fail("upload_part")
        _, _, parts = self.uploads[UploadId]
        raw = bytes(Body)
        etag = f'"{hashlib.md5(raw).hexdigest()}"'
        parts[PartNumber] = (etag, raw)
        return {"ETag": etag}

    def complete_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str, MultipartUpload: dict):
        self._check_fail("complete_multipart_upload")
        _, _, parts = self.uploads.pop(UploadId)
        chunks = [parts[entry["PartNumber"]][1] for entry in MultipartUpload["Parts"]]
        self.objects[(Bucket, Key)] = b"".join(chunks)
        return {"ETag": '"done"'}

    def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str):
        self.uploads.pop(UploadId, None)
        return {}

    def generate_presigned_url(self, ClientMethod: str, Params: dict, ExpiresIn: int = 60):
        self._check_fail("generate_presigned_url")
        return f"https://s3.leaseweb.example/{Params['Bucket']}/{Params['Key']}?{SIGNED_QUERY}"

    def delete_object(self, *, Bucket: str, Key: str):
        self._check_fail("delete_object")
        self.deleted_keys.append(Key)
        self.objects.pop((Bucket, Key), None)
        return {}


def _replay_llm(ops: list[str], *, mode: str = "replay", status: str = "incomplete"):
    def _complete(task, payload, schema, *, config, replay=False):
        return {"mode": mode, "status": status, "data": {"operations": ops}, "errors": []}

    return _complete


class ParitySuiteTest(unittest.TestCase):
    def test_both_sides_pass_identical_inputs_and_clean_only_synthetic_namespace(self):
        protected = {("dst-bucket", "seed_data/customer-001.json"): b"keep-me"}
        before = _InMemoryS3(preseed={("src-bucket", "seed_data/customer-001.json"): b"keep-me"})
        after = _InMemoryS3(preseed=protected)
        cfg = {
            "SKYSHIFT_SOURCE_ENDPOINT_URL": "http://127.0.0.1:5000",
            "SKYSHIFT_SOURCE_ACCESS_KEY_ID": "SOURCE-ACCESS-1234",
            "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": SENTINEL_SECRET,
            "SKYSHIFT_SOURCE_BUCKET": "src-bucket",
            "SKYSHIFT_TARGET_ENDPOINT_URL": "https://s3.leaseweb.example",
            "SKYSHIFT_TARGET_ACCESS_KEY_ID": "TARGET-ACCESS-1234",
            "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SENTINEL_SECRET,
            "SKYSHIFT_TARGET_BUCKET": "dst-bucket",
        }
        record = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config=cfg,
            before_client=before,
            after_client=after,
            before_bucket="src-bucket",
            after_bucket="dst-bucket",
            llm_complete=_replay_llm(["put_object", "get_object", "list_objects_v2"]),
            prefix="skyshift-parity/test-run/",
        )
        self.assertEqual(set(record.keys()), ENVELOPE_KEYS)
        self.assertEqual(record["step"], "parity")
        self.assertEqual(record["mode"], "live")
        self.assertEqual(record["status"], "PASS")
        self.assertEqual(record["errors"], [])

        ops = [row["operation"] for row in record["data"]["operations"]]
        self.assertEqual(ops, ["put_object", "get_object", "list_objects_v2", "multipart_upload"])
        for row in record["data"]["operations"]:
            self.assertEqual(row["before"]["status"], "PASS")
            self.assertEqual(row["after"]["status"], "PASS")
            self.assertIs(row["equal"], True)

        # Protected seed key untouched on both sides; only synthetic prefix keys deleted.
        self.assertIn(("dst-bucket", "seed_data/customer-001.json"), after.objects)
        self.assertIn(("src-bucket", "seed_data/customer-001.json"), before.objects)
        self.assertTrue(after.deleted_keys)
        self.assertTrue(all(k.startswith("skyshift-parity/test-run/") for k in after.deleted_keys))
        self.assertTrue(all(k.startswith("skyshift-parity/test-run/") for k in before.deleted_keys))

        # Determinism & no secrets
        dumped = json.dumps(record, sort_keys=True, allow_nan=False)
        self.assertNotIn(SENTINEL_SECRET, dumped)
        record2 = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config=cfg,
            before_client=_InMemoryS3(),
            after_client=_InMemoryS3(),
            before_bucket="src-bucket",
            after_bucket="dst-bucket",
            llm_complete=_replay_llm(["put_object", "get_object", "list_objects_v2"]),
            prefix="skyshift-parity/test-run/",
        )
        self.assertEqual(record, record2)

    def test_model_cannot_remove_required_or_add_unknown_operations(self):
        before = _InMemoryS3()
        after = _InMemoryS3()
        # Model tries to drop everything except put_object and inject an unknown op
        bad_llm = _replay_llm(["put_object", "drop_all_buckets", "head_object"], mode="live", status="ok")
        record = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config={},
            before_client=before,
            after_client=after,
            before_bucket="src",
            after_bucket="dst",
            llm_complete=bad_llm,
            prefix="skyshift-parity/sel/",
        )
        sel = record["data"]["selection"]
        self.assertEqual(
            sel["operations"],
            ["put_object", "get_object", "list_objects_v2", "head_object", "multipart_upload"],
        )
        self.assertNotIn("drop_all_buckets", sel["operations"])
        self.assertIn("drop_all_buckets", sel["rejected_proposals"])
        self.assertEqual(record["status"], "PASS")

    def test_one_side_failure_is_finding_not_crash(self):
        before = _InMemoryS3()
        after = _InMemoryS3(fail_ops={"upload_part"})
        record = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config={"SKYSHIFT_TARGET_SECRET_ACCESS_KEY": SENTINEL_SECRET},
            before_client=before,
            after_client=after,
            before_bucket="src",
            after_bucket="dst",
            llm_complete=_replay_llm([]),
            prefix="skyshift-parity/onefail/",
        )
        self.assertEqual(record["status"], "FAIL")
        rows = {r["operation"]: r for r in record["data"]["operations"]}
        self.assertEqual(rows["multipart_upload"]["before"]["status"], "PASS")
        self.assertEqual(rows["multipart_upload"]["after"]["status"], "FAIL")
        self.assertIs(rows["multipart_upload"]["equal"], False)
        self.assertEqual(rows["put_object"]["before"]["status"], "PASS")
        self.assertEqual(rows["put_object"]["after"]["status"], "PASS")
        dumped = json.dumps(record, sort_keys=True, allow_nan=False)
        self.assertNotIn(SENTINEL_SECRET, dumped)

    def test_both_sides_failing_never_produces_overall_pass(self):
        before = _InMemoryS3(fail_ops={"get_object"})
        after = _InMemoryS3(fail_ops={"get_object"})
        record = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config={},
            before_client=before,
            after_client=after,
            before_bucket="src",
            after_bucket="dst",
            llm_complete=_replay_llm([]),
            prefix="skyshift-parity/bothfail/",
        )
        rows = {r["operation"]: r for r in record["data"]["operations"]}
        self.assertEqual(rows["get_object"]["before"]["status"], "FAIL")
        self.assertEqual(rows["get_object"]["after"]["status"], "FAIL")
        self.assertIs(rows["get_object"]["equal"], True)
        self.assertEqual(record["status"], "FAIL")

    def test_presigned_url_included_when_detected_and_query_sanitized(self):
        before = _InMemoryS3()
        after = _InMemoryS3()

        def _fake_http_get(url: str, timeout: float):
            self.assertIn("X-Amz-Signature=", url)
            return 200, parity_mod._PARITY_SMOKE_PAYLOAD

        record = _live_verify(
            DATA_MAP_WITH_PRESIGNED,
            SYNTHETIC_TARGET,
            config={},
            before_client=before,
            after_client=after,
            before_bucket="src",
            after_bucket="dst",
            llm_complete=_replay_llm([]),
            http_get=_fake_http_get,
            prefix="skyshift-parity/presign/",
        )
        self.assertEqual(record["status"], "PASS")
        rows = {r["operation"]: r for r in record["data"]["operations"]}
        self.assertIn("presigned_url", rows)
        self.assertEqual(rows["presigned_url"]["before"]["status"], "PASS")
        self.assertEqual(rows["presigned_url"]["after"]["status"], "PASS")
        dumped = json.dumps(record, sort_keys=True, allow_nan=False)
        self.assertNotIn("X-Amz-Signature", dumped)
        self.assertNotIn("deadbeef1234567890", dumped)
        self.assertNotIn("AKIAEXAMPLE123", dumped)

    def test_skipped_or_fallback_execution_is_incomplete(self):
        before = _InMemoryS3()
        after = _InMemoryS3()
        # Simulate allow_live_pass=False (e.g. fake/fallback client run)
        record = _live_verify(
            DATA_MAP_WITH_MULTIPART,
            SYNTHETIC_TARGET,
            config={},
            before_client=before,
            after_client=after,
            before_bucket="src",
            after_bucket="dst",
            llm_complete=_replay_llm([]),
            allow_live_pass=False,
            prefix="skyshift-parity/fallback/",
        )
        self.assertEqual(record["status"], "incomplete")

        # Simulate a skipped operation returned from suite execution
        with mock.patch.object(
            parity_mod,
            "_execute_parity_suite",
            return_value={
                "put_object": {"status": "PASS", "detail": "ok", "signature": {"bytes": 1}},
                # get_object intentionally omitted (skipped)
                "list_objects_v2": {"status": "PASS", "detail": "ok", "signature": {"smoke_key_found": True}},
            },
        ):
            rec_skip = _live_verify(
                DATA_MAP_WITH_MULTIPART,
                SYNTHETIC_TARGET,
                config={},
                before_client=before,
                after_client=after,
                before_bucket="src",
                after_bucket="dst",
                llm_complete=_replay_llm([]),
                prefix="skyshift-parity/skip/",
            )
            self.assertEqual(rec_skip["status"], "incomplete")

    def test_missing_target_config_returns_incomplete(self):
        record = verify(DATA_MAP_WITH_MULTIPART, SYNTHETIC_TARGET, config={})
        self.assertEqual(record["mode"], "live")
        self.assertEqual(record["status"], "incomplete")
        self.assertTrue(record["errors"])
        self.assertEqual(
            record["data"]["selection"]["operations"],
            ["put_object", "get_object", "list_objects_v2", "multipart_upload"],
        )


if __name__ == "__main__":
    unittest.main()
