"""Offline unit tests for the reproducible AWS workload and seed fixture (WS2-02).

Run from the repository root:
    python -B -m unittest discover -s tests/ws2 -p test_fixture.py -v
Or after WS4 creates tests/__init__.py:
    python -m unittest tests.ws2.test_fixture -v

Standard library only; no AWS, Moto, Docker, target storage, or credentials.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fixtures.aws_workload import app as workload_app  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "fixtures" / "aws_workload"
MAIN_TF = FIXTURE_DIR / "main.tf"
APP_PY = FIXTURE_DIR / "app.py"
SEED_DIR = FIXTURE_DIR / "seed_data"

CONTRACT_ENV_NAMES = frozenset(
    {
        "AWS_ENDPOINT_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "SKYSHIFT_SOURCE_ENDPOINT_URL",
        "SKYSHIFT_SOURCE_ACCESS_KEY_ID",
        "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY",
        "SKYSHIFT_SOURCE_BUCKET",
        "SKYSHIFT_TARGET_ENDPOINT_URL",
        "SKYSHIFT_TARGET_ACCESS_KEY_ID",
        "SKYSHIFT_TARGET_SECRET_ACCESS_KEY",
        "SKYSHIFT_TARGET_BUCKET",
        "SKYSHIFT_TARGET_PROVIDER",
        "SKYSHIFT_LLM_BASE_URL",
        "SKYSHIFT_LLM_API_KEY",
        "SKYSHIFT_LLM_MODEL",
        "SKYSHIFT_LLM_REPLAY",
        "SKYSHIFT_TELEMETRY_ENDPOINT",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "OS_AUTH_URL",
        "OS_APPLICATION_CREDENTIAL_ID",
        "OS_APPLICATION_CREDENTIAL_SECRET",
        "OS_REGION_NAME",
        "LEASEWEB_API_KEY",
    }
)

EXPECTED_SEED_FILES = {
    "customer-001.json": (
        147,
        "c1ae14a8020977c90fcc30ac98a1ff879c321f02f9bd8d5206738dc66a5902e5",
    ),
    "customer-002.json": (
        144,
        "4c27c678017888d0b472c14d648f227de180d07cddc30b4cd5461f94e6b49c57",
    ),
    "multipart.bin": (
        131072,
        "fd90a13fcdf5f41de1d69731735b7ba4fec3bc2b38d890d9a5234fff85c99ab6",
    ),
    "readme.txt": (
        166,
        "e36d52a4dc048f85060c4115950cd2a732dabcc3c25b38af82f5052e9a9b4c6b",
    ),
}

AWS_KEY_LITERAL_RE = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
ACCOUNT_ID_RE = re.compile(r"\b\d{12}\b")
RFC1918_RE = re.compile(r"\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b")
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
ISO_TIMESTAMP_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(16384)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class _FakeS3Client:
    """In-memory S3 test double supporting put/get/list and multipart uploads."""

    def __init__(self, *, fail_on: str | None = None):
        self.fail_on = fail_on
        self.objects: dict[tuple[str, str], bytes] = {}
        self.uploads: dict[str, tuple[str, str, dict[int, tuple[str, bytes]]]] = {}
        self.aborted: list[str] = []
        self._next_upload = 0

    def _maybe_fail(self, op: str) -> None:
        if self.fail_on == op:
            raise RuntimeError(f"injected failure in {op}")

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **kwargs):
        self._maybe_fail("put_object")
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": f'"{hashlib.md5(Body).hexdigest()}"'}

    def get_object(self, *, Bucket: str, Key: str):
        self._maybe_fail("get_object")
        if (Bucket, Key) not in self.objects:
            raise KeyError(f"missing object: {Bucket}/{Key}")
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def list_objects_v2(self, *, Bucket: str, Prefix: str = ""):
        self._maybe_fail("list_objects_v2")
        contents = [
            {"Key": key, "Size": len(body)}
            for (bucket, key), body in sorted(self.objects.items())
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": contents, "IsTruncated": False}

    def create_multipart_upload(self, *, Bucket: str, Key: str, **kwargs):
        self._maybe_fail("create_multipart_upload")
        self._next_upload += 1
        upload_id = f"upload-{self._next_upload}"
        self.uploads[upload_id] = (Bucket, Key, {})
        return {"UploadId": upload_id}

    def upload_part(self, *, Bucket: str, Key: str, UploadId: str, PartNumber: int, Body: bytes):
        self._maybe_fail("upload_part")
        bucket, key, parts = self.uploads[UploadId]
        assert bucket == Bucket and key == Key
        raw = bytes(Body)
        etag = f'"{hashlib.md5(raw).hexdigest()}"'
        parts[PartNumber] = (etag, raw)
        return {"ETag": etag}

    def complete_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str, MultipartUpload: dict):
        self._maybe_fail("complete_multipart_upload")
        bucket, key, parts = self.uploads.pop(UploadId)
        assert bucket == Bucket and key == Key
        ordered = []
        for entry in MultipartUpload["Parts"]:
            part_num = entry["PartNumber"]
            etag, raw = parts[part_num]
            assert etag == entry["ETag"]
            ordered.append(raw)
        self.objects[(Bucket, Key)] = b"".join(ordered)
        return {"ETag": '"multipart-complete"'}

    def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str):
        self.uploads.pop(UploadId, None)
        self.aborted.append(UploadId)
        return {}


class _FakeCloudWatchClient:
    """In-memory CloudWatch telemetry test double."""

    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.metrics: list[dict] = []

    def put_metric_data(self, *, Namespace: str, MetricData: list[dict]):
        if self.should_fail:
            raise ConnectionError("telemetry endpoint blocked")
        self.metrics.append({"Namespace": Namespace, "MetricData": MetricData})
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


class TerraformFixtureTest(unittest.TestCase):
    def test_required_terraform_resource_types_exact(self):
        text = MAIN_TF.read_text(encoding="utf-8")
        resources = re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', text)
        types_found = [rtype for rtype, _ in resources]
        self.assertEqual(
            sorted(types_found),
            ["aws_instance", "aws_s3_bucket", "aws_security_group"],
        )
        self.assertEqual(len(resources), 3)

    def test_terraform_has_no_credentials_account_ids_or_private_ips(self):
        text = MAIN_TF.read_text(encoding="utf-8")
        self.assertIsNone(AWS_KEY_LITERAL_RE.search(text))
        self.assertIsNone(ACCOUNT_ID_RE.search(text))
        self.assertIsNone(RFC1918_RE.search(text))
        self.assertNotIn("secret_key", text.lower())
        self.assertNotIn("access_key", text.lower())
        self.assertNotIn("password", text.lower())


class AppStaticInspectionTest(unittest.TestCase):
    def setUp(self):
        self.source = APP_PY.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source, filename=str(APP_PY))

    def test_ast_exposes_s3_and_aws_cloudwatch_telemetry_calls(self):
        client_services: set[str] = set()
        method_calls: set[str] = set()
        string_literals: list[str] = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_literals.append(node.value)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_calls.add(node.func.attr)
                if (
                    node.func.attr == "client"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "boto3"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    client_services.add(node.args[0].value)

        self.assertIn("s3", client_services)
        self.assertIn("cloudwatch", client_services)
        self.assertTrue(
            {
                "put_object",
                "get_object",
                "list_objects_v2",
                "create_multipart_upload",
                "upload_part",
                "complete_multipart_upload",
                "put_metric_data",
            }
            <= method_calls
        )
        self.assertTrue(
            any("monitoring.eu-central-1.amazonaws.com" in s for s in string_literals),
            "default AWS-controlled telemetry endpoint must be statically visible",
        )
        self.assertTrue(
            workload_app.DEFAULT_TELEMETRY_ENDPOINT.endswith(".amazonaws.com")
        )

    def test_only_contract_environment_names_used(self):
        referenced_envs: set[str] = set()
        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, (ast.Name, ast.Attribute))
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                owner = ast.unparse(node.func.value)
                if owner in {"os.environ", "cfg"}:
                    referenced_envs.add(node.args[0].value)

        self.assertTrue(referenced_envs)
        self.assertTrue(
            referenced_envs <= CONTRACT_ENV_NAMES,
            f"non-contract env names referenced: {sorted(referenced_envs - CONTRACT_ENV_NAMES)}",
        )
        self.assertIn("AWS_ENDPOINT_URL", referenced_envs)
        self.assertIn("SKYSHIFT_TELEMETRY_ENDPOINT", referenced_envs)

    def test_bounded_timeouts_and_no_credential_literals(self):
        self.assertGreater(workload_app.CONNECT_TIMEOUT_SECONDS, 0)
        self.assertLessEqual(workload_app.CONNECT_TIMEOUT_SECONDS, 10)
        self.assertGreater(workload_app.READ_TIMEOUT_SECONDS, 0)
        self.assertLessEqual(workload_app.READ_TIMEOUT_SECONDS, 15)
        self.assertEqual(workload_app.MAX_RETRY_ATTEMPTS, 1)

        self.assertIsNone(AWS_KEY_LITERAL_RE.search(self.source))
        self.assertIsNone(ACCOUNT_ID_RE.search(self.source))
        self.assertNotIn("X-Amz-Signature", self.source)

    def test_import_has_no_network_or_client_side_effects(self):
        code = (
            "import socket, sys, threading, types\n"
            "try:\n"
            "    import ssl\n"
            "    import botocore.config\n"
            "except ImportError:\n"
            "    pass\n"
            "def _forbid(*a, **kw):\n"
            "    raise AssertionError('unexpected call during import')\n"
            "class _ForbiddenSocket(socket.socket):\n"
            "    def __init__(self, *a, **kw):\n"
            "        raise AssertionError('unexpected socket creation during import')\n"
            "socket.socket = _ForbiddenSocket\n"
            "socket.create_connection = _forbid\n"
            "socket.getaddrinfo = _forbid\n"
            "fake_boto3 = types.ModuleType('boto3')\n"
            "fake_boto3.client = _forbid\n"
            "fake_boto3.resource = _forbid\n"
            "sys.modules['boto3'] = fake_boto3\n"
            "import fixtures.aws_workload.app\n"
            "assert threading.active_count() == 1\n"
        )
        env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
        result = subprocess.run(
            [sys.executable, "-B", "-c", code],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


class SeedDataTest(unittest.TestCase):
    def test_seed_files_have_stable_expected_sha256_and_no_dynamic_values(self):
        actual_names = sorted(p.name for p in SEED_DIR.iterdir() if p.is_file())
        self.assertEqual(actual_names, sorted(EXPECTED_SEED_FILES.keys()))

        for name, (expected_size, expected_sha256) in EXPECTED_SEED_FILES.items():
            path = SEED_DIR / name
            self.assertEqual(path.stat().st_size, expected_size, name)
            self.assertEqual(_sha256_file(path), expected_sha256, name)

        for json_name in ("customer-001.json", "customer-002.json"):
            raw_text = (SEED_DIR / json_name).read_text(encoding="utf-8")
            parsed = json.loads(raw_text)
            self.assertIsInstance(parsed, dict)
            self.assertIs(parsed.get("synthetic"), True)
            self.assertIsNone(UUID_RE.search(raw_text))
            self.assertIsNone(ISO_TIMESTAMP_RE.search(raw_text))
            self.assertIsNone(AWS_KEY_LITERAL_RE.search(raw_text))

        readme_text = (SEED_DIR / "readme.txt").read_text(encoding="utf-8")
        self.assertIsNone(UUID_RE.search(readme_text))
        self.assertIsNone(ISO_TIMESTAMP_RE.search(readme_text))
        self.assertIsNone(AWS_KEY_LITERAL_RE.search(readme_text))

        generated = workload_app.generate_multipart_payload()
        self.assertEqual(generated, (SEED_DIR / "multipart.bin").read_bytes())
        self.assertEqual(len(generated), 131072)


class AppFunctionalBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.app_hash_before = _sha256_file(APP_PY)

    def tearDown(self):
        self.assertEqual(
            _sha256_file(APP_PY),
            self.app_hash_before,
            "fixtures/aws_workload/app.py bytes must never change during tests",
        )

    def test_run_workload_passes_with_local_test_doubles_and_multipart_chunking(self):
        fake_s3 = _FakeS3Client()
        fake_cw = _FakeCloudWatchClient()
        sentinel_secret = "SENTINEL-FIXTURE-SECRET-99aa"
        env = {
            "AWS_ENDPOINT_URL": f"http://127.0.0.1:9000/path?X-Amz-Signature={sentinel_secret}",
            "AWS_ACCESS_KEY_ID": "SYNTHETIC_ACCESS",
            "AWS_SECRET_ACCESS_KEY": sentinel_secret,
            "AWS_DEFAULT_REGION": "eu-central-1",
            "SKYSHIFT_TARGET_BUCKET": "synthetic-bucket",
            "SKYSHIFT_TELEMETRY_ENDPOINT": "http://127.0.0.1:4318",
        }

        result, exit_code = workload_app.run_workload(
            env=env,
            s3_client=fake_s3,
            telemetry_client=fake_cw,
            seed_dir=SEED_DIR,
            part_size=65536,  # exercises 2 parts for 128 KiB multipart.bin
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["endpoint_host"], "127.0.0.1:9000")
        self.assertEqual(result["telemetry"]["endpoint_host"], "127.0.0.1:4318")
        self.assertEqual(result["telemetry"]["status"], "PASS")
        self.assertEqual(len(fake_cw.metrics), 1)

        ops = {c["operation"]: c for c in result["checks"]}
        self.assertEqual(
            set(ops.keys()),
            {"put_object", "get_object", "list_objects_v2", "multipart_upload"},
        )
        for check in ops.values():
            self.assertEqual(check["status"], "PASS")
        self.assertIn("2 part(s)", ops["multipart_upload"]["detail"])

        dumped = json.dumps(result, sort_keys=True, allow_nan=False)
        self.assertNotIn(sentinel_secret, dumped)
        self.assertNotIn("X-Amz-Signature", dumped)

    def test_telemetry_failure_is_visible_and_fast(self):
        fake_s3 = _FakeS3Client()
        fake_cw = _FakeCloudWatchClient(should_fail=True)
        env = {
            "AWS_ENDPOINT_URL": "http://127.0.0.1:9000",
            "SKYSHIFT_TARGET_BUCKET": "synthetic-bucket",
        }

        result, exit_code = workload_app.run_workload(
            env=env,
            s3_client=fake_s3,
            telemetry_client=fake_cw,
            seed_dir=SEED_DIR,
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["telemetry"]["status"], "FAIL")
        self.assertEqual(
            result["telemetry"]["endpoint_host"],
            "monitoring.eu-central-1.amazonaws.com",
        )

        # With require_telemetry=True, telemetry failure forces nonzero exit.
        result_req, exit_code_req = workload_app.run_workload(
            env=env,
            s3_client=fake_s3,
            telemetry_client=fake_cw,
            seed_dir=SEED_DIR,
            require_telemetry=True,
        )
        self.assertEqual(exit_code_req, 1)
        self.assertEqual(result_req["status"], "FAIL")
        self.assertTrue(result_req["errors"])

    def test_s3_failure_returns_nonzero_and_aborts_multipart(self):
        fake_s3 = _FakeS3Client(fail_on="upload_part")
        fake_cw = _FakeCloudWatchClient()
        result, exit_code = workload_app.run_workload(
            env={"SKYSHIFT_TARGET_BUCKET": "synthetic-bucket"},
            s3_client=fake_s3,
            telemetry_client=fake_cw,
            seed_dir=SEED_DIR,
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(fake_s3.aborted), 1)
        self.assertTrue(result["errors"])

    def test_configuration_routes_both_clients_to_local_endpoints(self):
        recorded_calls: list[tuple[str, dict]] = []

        def _fake_client(service_name: str, **kwargs):
            recorded_calls.append((service_name, kwargs))
            return _FakeS3Client() if service_name == "s3" else _FakeCloudWatchClient()

        fake_boto3 = types.ModuleType("boto3")
        fake_boto3.client = _fake_client

        env = {
            "AWS_ENDPOINT_URL": "http://127.0.0.1:19000",
            "AWS_DEFAULT_REGION": "eu-central-1",
            "AWS_ACCESS_KEY_ID": "test-access",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "SKYSHIFT_TELEMETRY_ENDPOINT": "http://127.0.0.1:14318",
        }
        with mock.patch.object(workload_app, "boto3", fake_boto3):
            workload_app.build_s3_client(env)
            _, cw_url = workload_app.build_telemetry_client(env)
            _, default_cw_url = workload_app.build_telemetry_client({"AWS_DEFAULT_REGION": "eu-central-1"})

        self.assertEqual(cw_url, "http://127.0.0.1:14318")
        self.assertEqual(default_cw_url, "https://monitoring.eu-central-1.amazonaws.com")
        self.assertEqual(recorded_calls[0][0], "s3")
        self.assertEqual(recorded_calls[0][1]["endpoint_url"], "http://127.0.0.1:19000")
        self.assertEqual(recorded_calls[1][0], "cloudwatch")
        self.assertEqual(recorded_calls[1][1]["endpoint_url"], "http://127.0.0.1:14318")
        self.assertEqual(recorded_calls[2][0], "cloudwatch")
        self.assertEqual(
            recorded_calls[2][1]["endpoint_url"],
            "https://monitoring.eu-central-1.amazonaws.com",
        )


if __name__ == "__main__":
    unittest.main()
