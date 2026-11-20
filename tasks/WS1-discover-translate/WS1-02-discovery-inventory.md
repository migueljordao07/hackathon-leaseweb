---
id: WS1-02
title: Parse AWS dependencies inventory S3 and calculate readiness
workstream: WS1
status: done
owner: claude-1
priority: P0
depends_on: [WS1-01]
blocks: [WS1-03]
files: [skyshift/discover.py, skyshift/catalogue/resources.yaml, tests/ws1/test_discovery.py, tests/ws1/test_stubs.py]
estimate: 50m
claimed_at: "2026-11-20T12:39:39+00:00"
updated_at: "2026-11-20T14:33:00+00:00"
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
- 2026-11-20T12:45:36+00:00: Scope note: added WS1-owned tests/ws1/test_stubs.py to files (serial same-stream share). Its WS1-01 assertion "no PASS check in any non-stub record" assumed the discover placeholder; real discovery may PASS individual measured checks while the record stays incomplete. Narrowed to: non-stub discover is mode live, status incomplete, errors non-empty; choose/translate placeholders still have no PASS. Stub-path assertions unchanged.
- 2026-11-20T12:45:36+00:00: Implemented live discover: python-hcl2 parsing (v8 quoted-literal and older unquoted formats normalised; no evaluation; modules not evaluated), resource ids/provider/region/reference edges/sanitised attributes (user_data, password, secret, token, access/private keys redacted; expressions kept as unresolved markers), catalogue skyshift/catalogue/resources.yaml in the fixed format; ast scan (boto3 import aliases, from-boto3 client/resource, Session().client, assigned and chained clients, literal Bucket, endpoint_url literal host, requests calls, literal URLs outside docstrings as hidden telemetry, getattr dynamic dispatch and non-literal service/URL as findings); dedup by file/line/service/operation; explicit SKYSHIFT_SOURCE_* boto3 client, paginated list_objects_v2 counts/bytes without bodies. Missing creds/deps => null counts + incomplete; service error => FAIL with error code only. Readiness: proprietary = unsupported-or-proprietary instances, unsupported = distinct unsupported S3 operation names, us_calls = deduplicated non-S3 calls to US-controlled hosts incl. boto3 clients on the SDK default AWS endpoint (S3 calls are the migrated surface, rewired by endpoint config); scope stated in readiness.us_calls_scope. Non-PASS check details are mirrored into errors.
- 2026-11-20T12:45:36+00:00: Commands/results: `python -B -m unittest discover -s tests/ws1 -p "test_*.py"` -> Windows Python 3.14.5 without deps: 29 OK, 8 skipped (HCL + live); Windows venv with python-hcl2 8.2.0/PyYAML 6.0.3/boto3 1.44.7: 29 OK, 1 skipped (live); WSL2 Ubuntu Python 3.12.3 venv same deps: 29 OK, 1 skipped; WSL2 system python3 without deps: 29 OK, 8 skipped. test_stubs.py passes in all four. Live read-only inventory test (SKYSHIFT_WS1_LIVE_TESTS=1) NOT RUN: WS0-01 gate/source access not available; this is not live acceptance. Status review until the live inventory test runs after WS0-01 go or humans accept offline completion. Dependencies requested from WS4 (inbox-WS4). Not tested: python-hcl2 < 7.
- 2026-11-20T12:46:19+00:00: Code landed at 5798e7d. Fresh clone of origin/main (2e1559b) on WSL2 Ubuntu: with deps 29 OK/1 skipped (live), system python3 29 OK/8 skipped; board --check OK. Remains review: live inventory test pending WS0-01 go/source access or human acceptance (inbox-humans).
- 2026-11-20T14:33:00+00:00: Humans (Miguel) accepted offline acceptance as completion (SPEED MODE). VM live discover at 7b85ba5: calls_scanned PASS, bucket_inventory PASS (Moto), inventory_parsed incomplete. Set done by claude-3 on human instruction.
