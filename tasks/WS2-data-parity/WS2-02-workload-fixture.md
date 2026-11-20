---
id: WS2-02
title: Reproducible AWS workload and seed fixture
workstream: WS2
status: todo
owner: null
priority: P0
depends_on: [WS2-01]
blocks: [WS2-03, WS2-04]
files: [fixtures/aws_workload/main.tf, fixtures/aws_workload/app.py, fixtures/aws_workload/seed_data/customer-001.json, fixtures/aws_workload/seed_data/customer-002.json, fixtures/aws_workload/seed_data/readme.txt, fixtures/aws_workload/seed_data/multipart.bin, tests/ws2/test_fixture.py]
estimate: 45m
claimed_at: null
updated_at: null
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
