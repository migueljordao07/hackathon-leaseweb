"""Offline tests for the single LLM client, sanitizer and replay (WS3-06).

Run from the repository root:
    python -B -m unittest discover -s tests/ws3 -p test_llm_client.py -v
A recording fake transport replaces the HTTP adapter; no external API or
network access. Passing tests do not imply any successful live model call.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skyshift import llm  # noqa: E402

SECRET = "SENTINEL-SECRET-llm-8c3f"
SIGNATURE = "deadbeefcafe0123456789signature"
LIVE = {
    "SKYSHIFT_LLM_BASE_URL": "https://llm.example.test/v1",
    "SKYSHIFT_LLM_API_KEY": SECRET,
    "SKYSHIFT_LLM_MODEL": "example-model",
    "SKYSHIFT_SOURCE_SECRET_ACCESS_KEY": "wJalrXUtnFEMI-source-secret-value",
}
SCHEMA = {
    "type": "object",
    "required": ["replacement_id", "rationale", "config_keys"],
    "properties": {
        "replacement_id": {"type": "string", "enum": ["local-otel"]},
        "rationale": {"type": "string", "minLength": 1},
        "config_keys": {"type": "array", "items": {"type": "string", "enum": ["SKYSHIFT_TELEMETRY_ENDPOINT"]}},
    },
}
DIRTY_PAYLOAD = {
    "blocked_hosts": ["monitoring.eu-central-1.amazonaws.com"],
    "note": f"app on 10.0.0.5 and fd00::12 used key {SECRET} and AKIAABCDEFGHIJKLMNOP",
    "env": f"SKYSHIFT_SOURCE_SECRET_ACCESS_KEY=wJalrXUtnFEMI-source-secret-value HOME=/root",
    "presigned": f"https://bucket.s3.amazonaws.com/obj?X-Amz-Signature={SIGNATURE}&X-Amz-Credential=AKIAXYZ",
    "Authorization": "Bearer abcdefghijklmnop",
    "nested": [{"aws_secret_access_key": "x" * 12, "public_ip": "8.8.8.8"}],
}
GOOD = {"replacement_id": "local-otel", "rationale": "Route telemetry locally.", "config_keys": ["SKYSHIFT_TELEMETRY_ENDPOINT"]}


def chat_response(content) -> bytes:
    text = content if isinstance(content, str) else json.dumps(content)
    return json.dumps({"choices": [{"message": {"role": "assistant", "content": text}}]}).encode()


class RecordingTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "body": body, "timeout": timeout})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _forbidden_in(text: str):
    return [m for m in (SECRET, SIGNATURE, "10.0.0.5", "fd00::12", "AKIAABCDEFGHIJKLMNOP",
                        "wJalrXUtnFEMI-source-secret-value", "abcdefghijklmnop", "x" * 12) if m in text]


class SanitizerTest(unittest.TestCase):
    def test_redacts_secrets_env_signed_queries_and_private_addresses(self):
        clean, report = llm.sanitize(DIRTY_PAYLOAD, LIVE)
        text = json.dumps(clean)
        self.assertEqual(_forbidden_in(text), [])
        self.assertIn("monitoring.eu-central-1.amazonaws.com", text)  # public, non-secret context kept
        self.assertIn("8.8.8.8", text)  # global address kept
        self.assertIn("https://bucket.s3.amazonaws.com/obj?[REDACTED]", text)
        for category in ("config-value", "credential-pattern", "env-assignment", "private-address",
                         "sensitive-key", "url-query-or-userinfo"):
            self.assertIn(category, report)

    def test_sanitizer_is_deterministic_and_does_not_mutate(self):
        snapshot = json.dumps(DIRTY_PAYLOAD, sort_keys=True)
        first = llm.sanitize(DIRTY_PAYLOAD, LIVE)
        second = llm.sanitize(DIRTY_PAYLOAD, LIVE)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(DIRTY_PAYLOAD, sort_keys=True), snapshot)


class LiveClientTest(unittest.TestCase):
    def test_transport_receives_only_sanitized_payload(self):
        transport = RecordingTransport([chat_response(GOOD)])
        with mock.patch.object(llm, "_transport", transport):
            result = llm.complete("replacement_proposal", DIRTY_PAYLOAD, SCHEMA, config=LIVE)
        self.assertEqual((result["mode"], result["status"], result["data"]), ("live", "ok", GOOD))
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        self.assertEqual(call["url"], "https://llm.example.test/v1/chat/completions")
        self.assertLessEqual(call["timeout"], llm.REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(_forbidden_in(call["body"].decode()), [])
        self.assertEqual(call["headers"]["Authorization"], f"Bearer {SECRET}")  # key only in auth header
        self.assertEqual(_forbidden_in(json.dumps(result)), [])
        self.assertTrue(any("sanitizer redacted" in e for e in result["errors"]))

    def test_fenced_json_output_is_parsed(self):
        transport = RecordingTransport([chat_response("```json\n" + json.dumps(GOOD) + "\n```")])
        with mock.patch.object(llm, "_transport", transport):
            result = llm.complete("replacement_proposal", {}, SCHEMA, config=LIVE)
        self.assertEqual(result["status"], "ok")

    def test_schema_failure_and_malformed_output_are_incomplete(self):
        for body in (chat_response({"replacement_id": "attacker", "rationale": "x", "config_keys": []}),
                     chat_response("not json at all"), b"<html>gateway</html>"):
            transport = RecordingTransport([body])
            with mock.patch.object(llm, "_transport", transport):
                result = llm.complete("replacement_proposal", {"k": SECRET}, SCHEMA, config=LIVE)
            self.assertEqual((result["mode"], result["status"], result["data"]), ("live", "incomplete", {}))
            self.assertEqual(_forbidden_in(json.dumps(result)), [])

    def test_transport_failure_is_bounded_and_falls_back_to_labelled_replay(self):
        transport = RecordingTransport([TimeoutError("slow"), OSError(f"refused {SECRET}"), chat_response(GOOD)])
        with mock.patch.object(llm, "_transport", transport):
            result = llm.complete("replacement_proposal", {"k": SECRET}, SCHEMA, config=LIVE)
        self.assertEqual(len(transport.calls), llm.MAX_TRANSPORT_ATTEMPTS)
        self.assertEqual((result["mode"], result["status"]), ("replay", "incomplete"))
        self.assertEqual(result["data"]["replacement_id"], "local-otel")
        self.assertIn("live model transport failed: TimeoutError", result["errors"])
        self.assertNotIn(SECRET, json.dumps(result))

    def test_missing_credentials_never_call_transport(self):
        transport = RecordingTransport([])
        partial = {k: v for k, v in LIVE.items() if k != "SKYSHIFT_LLM_MODEL"}
        with mock.patch.object(llm, "_transport", transport):
            result = llm.complete("replacement_proposal", {}, SCHEMA, config=partial)
        self.assertEqual(transport.calls, [])
        self.assertEqual((result["mode"], result["status"]), ("replay", "incomplete"))
        self.assertTrue(any("SKYSHIFT_LLM_MODEL" in e and "no model call was made" in e for e in result["errors"]))
        self.assertNotIn(SECRET, json.dumps(result))

    def test_insecure_or_credentialed_base_url_rejected_without_call(self):
        transport = RecordingTransport([])
        for base in ("http://llm.example.test/v1", "https://user:pw@llm.example.test/v1", "https://llm.example.test/v1?key=1"):
            with mock.patch.object(llm, "_transport", transport):
                result = llm.complete("replacement_proposal", {}, SCHEMA, config={**LIVE, "SKYSHIFT_LLM_BASE_URL": base})
            self.assertEqual(result["mode"], "replay")
        self.assertEqual(transport.calls, [])
        self.assertEqual(llm._endpoint("http://127.0.0.1:8080/v1"), "http://127.0.0.1:8080/v1/chat/completions")

    def test_oversized_payload_rejected_before_transport(self):
        transport = RecordingTransport([])
        with mock.patch.object(llm, "_transport", transport):
            result = llm.complete("replacement_proposal", {"blob": "a b " * llm.MAX_PAYLOAD_BYTES}, SCHEMA, config=LIVE)
        self.assertEqual(transport.calls, [])
        self.assertTrue(any("sanitizer rejected" in e for e in result["errors"]))


class ReplayTest(unittest.TestCase):
    def test_replay_is_deterministic_labelled_and_never_ok(self):
        transport = RecordingTransport([])
        with mock.patch.object(llm, "_transport", transport):
            first = llm.complete("replacement_proposal", DIRTY_PAYLOAD, SCHEMA, config=LIVE, replay=True)
            second = llm.complete("replacement_proposal", DIRTY_PAYLOAD, SCHEMA, config=LIVE, replay=True)
            env_replay = llm.complete("replacement_proposal", {}, SCHEMA, config={**LIVE, "SKYSHIFT_LLM_REPLAY": "1"})
        self.assertEqual(first, second)
        self.assertEqual(transport.calls, [])
        for result in (first, env_replay):
            self.assertEqual((result["mode"], result["status"]), ("replay", "incomplete"))
            self.assertEqual(set(result), set(llm.COMPLETION_KEYS))
            self.assertNotEqual(result["status"], "PASS")
            self.assertEqual(_forbidden_in(json.dumps(result)), [])

    def test_unknown_task_replay_is_empty_incomplete(self):
        result = llm.complete("no_such_task", {}, SCHEMA, config={}, replay=True)
        self.assertEqual((result["mode"], result["status"], result["data"]), ("replay", "incomplete", {}))


if __name__ == "__main__":
    unittest.main()
