"""Offline tests for live migrate (WS2-03): fake paginated clients and fake rclone."""
import copy
import hashlib
import io
import json
import subprocess
import unittest

from skyshift import migrate as m

P = m.SCOPE_PREFIX


class StrictBody:
    """Body that refuses unbounded read() to prove streaming."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    def read(self, size=-1):
        if size is None or size < 0:
            raise AssertionError("unbounded read")
        return self._buf.read(size)


class FakeS3:
    def __init__(self, objects: dict, page_size: int = 2, fail_get: bool = False):
        self.objects = dict(objects)
        self.page_size = page_size
        self.fail_get = fail_get
        self.list_calls = 0

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):
        self.list_calls += 1
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        start = int(ContinuationToken or 0)
        page = keys[start:start + self.page_size]
        resp = {"Contents": [{"Key": k, "ETag": '"bogus"'} for k in page]}
        if start + self.page_size < len(keys):
            resp.update(IsTruncated=True, NextContinuationToken=str(start + self.page_size))
        return resp

    def get_object(self, Bucket, Key):
        if self.fail_get:
            raise OSError("connection reset")
        return {"Body": StrictBody(self.objects[Key])}


SRC = {P + "a.txt": b"alpha", P + "b.bin": b"\x00" * 200000, P + "c.json": b"{}", "skyshift-workload-check/x": b"z"}
CONFIG = {
    "SKYSHIFT_SOURCE_ENDPOINT_URL": "http://127.0.0.1:5000", "SKYSHIFT_SOURCE_ACCESS_KEY_ID": "AKSRC",
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": "src-secret-value", "SKYSHIFT_SOURCE_BUCKET": "src",
    "SKYSHIFT_TARGET_ENDPOINT_URL": "https://target.example", "SKYSHIFT_TARGET_ACCESS_KEY_ID": "AKTGT",
    "SKYSHIFT_TARGET_SECRET_ACCESS_KEY": "tgt-secret-value", "SKYSHIFT_TARGET_BUCKET": "tgt",
}
OK_COPY = lambda s, d: {"status": "PASS", "detail": "rclone copy exit 0"}  # noqa: E731


def run(target_objects, rclone=OK_COPY, src=SRC, fail_get=False, config=CONFIG):
    clients = {"src": FakeS3(src), "tgt": FakeS3(target_objects, fail_get=fail_get)}
    return m._live_migrate(config, client_factory=lambda side: clients[side["bucket"]], rclone=rclone)


class LiveMigrateTest(unittest.TestCase):
    def test_all_matched_pass_with_real_hashes(self):
        rec = run({k: v for k, v in SRC.items() if k.startswith(P)})
        self.assertEqual(rec["status"], "PASS")
        d = rec["data"]
        self.assertEqual((d["source_count"], d["target_count"], d["matched"], d["missing"], d["different"], d["extra"]), (3, 3, 3, 0, 0, 0))
        row = next(r for r in d["objects"] if r["key"] == "a.txt")
        self.assertEqual(row["source_sha256"], hashlib.sha256(b"alpha").hexdigest())
        self.assertEqual([r["key"] for r in d["objects"]], sorted(r["key"] for r in d["objects"]))
        json.dumps(rec, allow_nan=False)

    def test_different_missing_extra_fail(self):
        tgt = {P + "a.txt": b"alphA", P + "c.json": b"{}", P + "new.txt": b"n"}
        rec = run(tgt)
        d = rec["data"]
        self.assertEqual(rec["status"], "FAIL")
        self.assertEqual((d["matched"], d["different"], d["missing"], d["extra"]), (1, 1, 1, 1))
        extra = next(r for r in d["objects"] if r["status"] == "extra")
        self.assertIsNone(extra["source_sha256"])

    def test_read_failure_never_pass(self):
        rec = run({k: v for k, v in SRC.items() if k.startswith(P)}, fail_get=True)
        self.assertEqual(rec["status"], "FAIL")

    def test_rclone_failure_is_fail_even_if_hashes_match(self):
        rec = run({k: v for k, v in SRC.items() if k.startswith(P)}, rclone=lambda s, d: {"status": "FAIL", "detail": "rclone copy exit 1"})
        self.assertEqual(rec["status"], "FAIL")

    def test_empty_source_incomplete(self):
        self.assertEqual(run({}, src={})["status"], "incomplete")

    def test_missing_config_incomplete(self):
        rec = m._live_migrate({}, client_factory=None, rclone=OK_COPY)
        self.assertEqual(rec["status"], "incomplete")

    def test_pagination_complete(self):
        many = {f"{P}k{i:03d}": bytes([i]) for i in range(7)}
        src = FakeS3(many, page_size=3)
        self.assertEqual(len(m.list_and_hash(src, "b")), 7)
        self.assertEqual(src.list_calls, 3)

    def test_truncated_without_token_raises(self):
        class Bad(FakeS3):
            def list_objects_v2(self, **kw):
                return {"Contents": [], "IsTruncated": True}
        with self.assertRaises(ValueError):
            m.list_and_hash(Bad({}), "b")

    def test_no_secrets_in_record_and_inputs_unchanged(self):
        cfg = copy.deepcopy(CONFIG)
        rec = run({k: v for k, v in SRC.items() if k.startswith(P)}, config=cfg)
        self.assertEqual(cfg, CONFIG)
        text = json.dumps(rec)
        for secret in ("src-secret-value", "tgt-secret-value", "AKSRC", "AKTGT", "target.example"):
            self.assertNotIn(secret, text)


class RcloneTest(unittest.TestCase):
    src = {"endpoint": "http://127.0.0.1:5000", "key": "k", "secret": "s3cr3t", "bucket": "src", "region": "r"}
    dst = {"endpoint": "https://t", "key": "k2", "secret": "s3cr3t2", "bucket": "tgt", "region": "r"}

    def test_sync_rejected_without_both_flags(self):
        with self.assertRaises(ValueError):
            m.rclone_args("rclone", "a", "b", mode="sync")
        with self.assertRaises(ValueError):
            m.rclone_args("rclone", "a", "b", mode="sync", disposable_target=True)
        self.assertEqual(m.rclone_args("rclone", "a", "b", mode="sync", disposable_target=True, human_approved=True)[1], "sync")

    def test_copy_argument_list_without_shell(self):
        seen = {}

        def runner(args, **kw):
            seen.update(args=args, **kw)
            return subprocess.CompletedProcess(args, 0, b"", b"")
        res = m.run_rclone(self.src, self.dst, runner=runner, which=lambda n: "/usr/bin/rclone")
        self.assertEqual(res["status"], "PASS")
        self.assertIsInstance(seen["args"], list)
        self.assertEqual(seen["args"][1], "copy")
        self.assertFalse(seen["shell"])
        self.assertNotIn("s3cr3t", " ".join(seen["args"]))
        self.assertNotIn("s3cr3t", res["detail"])

    def test_timeout_and_nonzero_fail(self):
        def slow(args, **kw):
            raise subprocess.TimeoutExpired(args, 1)
        self.assertEqual(m.run_rclone(self.src, self.dst, runner=slow, which=lambda n: "x")["status"], "FAIL")
        bad = lambda a, **kw: subprocess.CompletedProcess(a, 3, b"", b"secret stderr")  # noqa: E731
        res = m.run_rclone(self.src, self.dst, runner=bad, which=lambda n: "x")
        self.assertEqual(res["status"], "FAIL")
        self.assertNotIn("secret", res["detail"])

    def test_missing_binary_incomplete(self):
        self.assertEqual(m.run_rclone(self.src, self.dst, which=lambda n: None)["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
