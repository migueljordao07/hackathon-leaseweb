---
id: WS2-02
title: Reproducible AWS workload and seed fixture
workstream: WS2
status: done
owner: gemini
priority: P0
depends_on: [WS2-01]
blocks: [WS2-03, WS2-04]
files: [fixtures/aws_workload/main.tf, fixtures/aws_workload/app.py, fixtures/aws_workload/seed_data/customer-001.json, fixtures/aws_workload/seed_data/customer-002.json, fixtures/aws_workload/seed_data/readme.txt, fixtures/aws_workload/seed_data/multipart.bin, tests/ws2/test_fixture.py]
estimate: 45m
claimed_at: "2026-11-20T12:49:52+00:00"
updated_at: "2026-11-20T13:00:00+00:00"
---

## Goal

Create a small deterministic workload that exposes AWS infrastructure, normal S3 behavior, and a hidden AWS telemetry dependency while remaining safe to run only against synthetic endpoints.

## Context

Original proposal sections 3, 6, 7, 9–11 require Terraform for EC2, a security group, and S3; an original `app.py` that later runs unchanged; synthetic seed objects; and a realistic hidden call to an AWS telemetry endpoint that discovery reveals before severance blocks it. The fixture must support the data-map, migration, run, parity, and severance contracts in `tasks/contracts.md` without requiring the untracked proposal.

`app.py` is the baseline artifact. Later tasks may change only environment configuration, never its bytes. It uses explicit endpoint/credential configuration, bounded timeouts, and S3 put/get/list behavior. It also creates a CloudWatch-style telemetry client whose default endpoint is an AWS-controlled host and whose only supported remediation is `SKYSHIFT_TELEMETRY_ENDPOINT`; this makes the dependency statically visible to WS1 discovery and blockable by WS3 without editing the app. The fixture handles telemetry failure visibly and quickly rather than hanging. It contains no real credentials, account IDs, private addresses, or production data.

Future executor: `gemini`. Carolina approves Terraform/application realism and the parity operations; Miguel approves seed-data suitability for checksum migration. The executor assignment preserves Claude Code for WS1 and WS4 integration.

## Steps

1. Write valid, intentionally AWS-specific Terraform declaring one `aws_instance`, one `aws_security_group`, and one `aws_s3_bucket`; use variables or synthetic defaults only and never apply it from this task.
2. Write a minimal deterministic application with import-safe functions and a bounded CLI entry point. Configure S3 through `AWS_ENDPOINT_URL` and telemetry through `SKYSHIFT_TELEMETRY_ENDPOINT`, which defaults to an AWS telemetry endpoint.
3. Exercise put, get, list, and a deterministic multipart-sized payload path. Emit structured sanitized results and return nonzero for required functional failures.
4. Add two small JSON objects, one text object, and a reproducibly generated binary payload. Record no timestamps, random UUIDs, secrets, or host-specific values in seed content.
5. Test Terraform resource presence, AST-visible `boto3` S3 and telemetry operations, endpoint environment names, bounded timeouts, deterministic seed hashes, and absence of credential literals.
6. Test that running the app through a fake/local client does not alter `app.py`; record its SHA-256 before and after the test.

## Acceptance criteria

- `python -m unittest tests.ws2.test_fixture -v` exits 0 offline without AWS, Moto, Docker, target storage, or credentials.
- The test parses text/AST and finds exactly the required Terraform resource types plus S3 put/get/list and a CloudWatch-style telemetry operation whose default host is AWS-controlled.
- The app reads endpoint and credential names only from the contract, sets bounded connection/read behavior, avoids import-time clients/network calls, and can point both S3 and telemetry at local test doubles through configuration.
- SHA-256 of `fixtures/aws_workload/app.py` is identical before and after every functional fixture test. Seed files have stable expected SHA-256 values asserted by the test; `multipart.bin` is generated deterministically and is large enough to exercise multipart logic without bloating Git.
- `tofu fmt -check fixtures/aws_workload/main.tf` exits 0 when OpenTofu is available. This task does not run `tofu init`, `tofu validate`, or apply; missing OpenTofu is recorded, not represented as a pass.
- `python tasks/board.py --check` exits 0 after all planned task files are present.

## Out of scope

No AWS or Leaseweb deployment, real bucket, production data, IAM design, database, server daemon, product migration/parity implementation, proxy enforcement, app remediation, shared requirements, or VM-gate decision.

## Fallback if blocked

If OpenTofu is absent, retain static fixture tests and defer real validation to the human gate. If multipart storage would make the repository large, generate `multipart.bin` from a short documented byte pattern in the task and assert the generated hash; do not download a fixture. If telemetry APIs cannot run locally, use a fake client while preserving the AST-visible call and explicit incomplete status.

## Log

- 2026-11-20 12:07 UTC — Planned fixture only. AWS, OpenTofu, and VM behavior remain unverified.
- 2026-11-20T12:49:52+00:00 — Claimed by gemini. Re-read channel.md and inbox-WS2.md after WS2-01 landed. Implementation starts after claim push is accepted.
- 2026-11-20T12:57:20+00:00 — Implemented synthetic workload fixture: `fixtures/aws_workload/main.tf` (exact 3 AWS resources: `aws_instance.app`, `aws_security_group.app`, `aws_s3_bucket.demo`, RFC 5737 `192.0.2.0/24` CIDR, synthetic defaults only), unchanged baseline `fixtures/aws_workload/app.py` (import-safe, contract-only env vars, bounded timeouts 3s/5s/1 attempt, S3 put/get/list/multipart, CloudWatch `put_metric_data` defaulting to `https://monitoring.eu-central-1.amazonaws.com` and overridable via `SKYSHIFT_TELEMETRY_ENDPOINT`), 4 deterministic seed files (`customer-001.json` 147B `c1ae14a8...`, `customer-002.json` 144B `4c27c678...`, `readme.txt` 166B `e36d52a4...`, `multipart.bin` 131072B `fd90a13f...`), and offline tests `tests/ws2/test_fixture.py`.
- 2026-11-20T12:57:20+00:00 — Review acceptance: `python -B -m unittest discover -s tests/ws2 -v` 23 tests OK (11 fixture + 12 stub) on Windows 11 / Python 3.14.5 and on WSL2 Ubuntu (Linux 6.6.87.2-microsoft-standard-WSL2) / Python 3.12.3; `app.py` SHA-256 identical before and after functional tests (`71dd360d6193a1b1464da29c761160664c88143617eb31f06c48710607cef4ed`, LF). `skyshift.discover.scan_python` cleanly detects all S3 calls and `cloudwatch.put_metric_data` on `monitoring.eu-central-1.amazonaws.com` with 0 findings. `python tasks/board.py --check` OK. Limitations: `tofu` is not installed on Windows or WSL2 so `tofu fmt -check fixtures/aws_workload/main.tf` was NOT RUN (deferred to VM/WS0 gate); dotted `tests.ws2.test_fixture` waits on WS4 `tests/__init__.py`; no AWS, Moto, target storage, or VM validation performed.
- 2026-11-20T13:00:00+00:00 — Done. Verified commit `040747e` on origin/main in a fresh git archive on WSL2 Ubuntu (Linux 6.6.87.2-microsoft-standard-WSL2, Python 3.12.3): `python3 -B -m unittest discover -s tests/ws2 -v` 23 tests OK in 0.095s; `sha256sum fixtures/aws_workload/app.py` identical before and after (`71dd360d6193a1b1464da29c761160664c88143617eb31f06c48710607cef4ed`); `python3 tasks/board.py --check` OK. Verified by executor gemini (human supervisors Carolina/Miguel may reopen to review). `tofu` absent locally so `tofu fmt -check` remains NOT RUN; no AWS, Moto, target storage, or VM check claimed.
