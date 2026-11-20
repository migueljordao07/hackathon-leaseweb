---
id: WS1-02
title: Parse AWS dependencies inventory S3 and calculate readiness
workstream: WS1
status: claimed
owner: claude-1
priority: P0
depends_on: [WS1-01]
blocks: [WS1-03]
files: [skyshift/discover.py, skyshift/catalogue/resources.yaml, tests/ws1/test_discovery.py]
estimate: 50m
claimed_at: "2026-11-20T12:39:39+00:00"
updated_at: "2026-11-20T12:39:39+00:00"
---

## Goal
Replace discover's non-stub placeholder with deterministic HCL/Python analysis, paginated source inventory and an auditable readiness score.

## Context
Read tasks/contracts.md Python API, data map and environment names, plus tasks/README.md. Original proposal sections 3 step 1, 4, 6, 7, 8-11 require python-hcl2, ast, source bucket counts/bytes and a code-calculated displayed formula; a European AWS region is still US-controlled. No private proposal is needed. Executor claude-1; Diogo reviews discovery/scoring, Ricardo reviews mappings. Signature remains `discover(workload: Path, *, config: dict, stub: bool = False) -> dict`; output data has resources, calls, buckets, readiness. Do not change choose's interface or earlier stub.

The WS1-owned resources.yaml format is fixed here for later tasks: root schema_version: 1, resources: mapping keyed by AWS resource type, and s3_operations: mapping keyed by operation name to supported boolean. Each resource entry has supported (boolean), proprietary (boolean), target_kind (string or null), template (relative filename or null). Known resources are aws_instance -> compute.tf.j2, aws_security_group -> network.tf.j2, aws_s3_bucket -> storage.tf.j2, all supported/non-proprietary; aws_db_instance is unsupported/proprietary with no template. Unknown types default unsupported/proprietary; unknown S3 operations unsupported. This is mapping eligibility, not a claim of measured target API compatibility. Catalogue support must be corrected to match the human-approved provider before real translation.

## Steps
1. Follow Git claim/push race protocol in tasks/README.md with claude-1; only claim after WS1-01 is done. Read channel/inbox after every pull. Request python-hcl2, boto3 and PyYAML declaration from WS4 via its inbox; never edit requirements.txt.
2. Parse workload .tf files with python-hcl2 without evaluating HCL or executing app source. Extract stable resource IDs, provider/region, reference edges and sanitized attributes needed by translation. Use null/explicit unresolved markers for expressions; never invent resolved bucket/region values. Preserve resource list order deterministically and do not expose credentials, user_data, signed queries or raw environment. Malformed input raises ValueError; unresolvable expressions produce incomplete findings.
3. Use ast for common boto3 import aliases, boto3.client/resource service literals, assigned clients, bucket literals and client method calls. Also surface literal/configured telemetry hosts (requests calls included) as calls with service/operation and source file/line. Do not execute Python. Deduplicate by file/line/service/operation; unsupported dynamic dispatch and unresolved endpoints remain visible incomplete findings rather than guessed coverage.
4. Use an explicit boto3 source client from SKYSHIFT_SOURCE_* keys, never a target/global app client. List every relevant source bucket with list_objects_v2 pagination, including empty pages; calculate object_count and total_bytes without downloading object bodies. Credentials are runtime only; unknown/unreachable inventory has null counts and incomplete status, not assumed zero. Read-only source access only. A measured service failure is FAIL; missing credentials/coverage is incomplete.
5. Calculate score `max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)`. proprietary counts unsupported/proprietary resource instances; unsupported counts distinct unsupported S3 operation names; us_calls counts deduplicated calls whose literal/resolved host is a known US-controlled endpoint. A missing endpoint is not a proven zero: preserve incomplete scope. Display formula and counters exactly in readiness. No AI scoring or inference that an EU AWS region changes provider control.
6. Build temporary HCL/Python inputs and mocked boto3 paginators in the owned test file; do not change WS2 fixtures. Add integration-test mode enabled only by SKYSHIFT_WS1_LIVE_TESTS=1; it reads human-supplied config, never writes source objects, and asserts source count/bytes against a human-provided sanitized expectation. Hand off schema/examples, dependencies needed and sanitized results via Log/WS1 inbox in Git.

## Acceptance criteria
- `python -B -m unittest discover -s tests/ws1 -p test_discovery.py -v` exits 0. Cover three supported resources, unsupported database and S3 operation, alias calls, deduplication, hidden telemetry, unresolved expressions, invalid HCL/Python, absent credentials, paginated counts/bytes, genuine empty bucket, and denied inventory. Assert formula/counters against expected values and no secret sentinel leakage.
- `python -B -m unittest discover -s tests/ws1 -p test_stubs.py -v` still exits 0 with optional dependencies absent from the stub path.
- Only after human WS0-01 go/access: `SKYSHIFT_WS1_LIVE_TESTS=1 python -B -m unittest discover -s tests/ws1 -p test_discovery.py -v` performs the read-only inventory test. Record measured bucket totals and environment, not credentials. A skipped live test is explicitly not live acceptance and cannot justify a full pipeline PASS.
- `python tasks/board.py --check` succeeds before review; Log lists actual commands/results, coverage limitations and commit. Done follows tasks/README.md Linux-like review, origin/main and run-all requirements. Named-file commits such as `[WS1-02] feat: discover source dependencies (claude-1)` only.

## Out of scope
Bucket mutation, data migration/hashing, executing source code, IAM, database migration, recursive HCL module evaluation, target selection, CLI and global dependency files. No change to WS2 fixture or WS3 telemetry implementation.

## Fallback if blocked
Offline mocked tests and static analysis remain usable without VM access; inventory must stay incomplete. Request human source access through inbox-humans with key names only. Missing shared dependencies go to inbox-WS4. Preserve stub path, mark blocked work honestly, and never fabricate a bucket count or silently drop an unknown resource.

## Log
- 2026-11-20: Planned only. Offline parsing can proceed without the VM gate; real source calls require the human go/access record.
- 2026-11-20T12:39:39+00:00: Claimed by claude-1 after WS1-01 done (5f7bce8).
