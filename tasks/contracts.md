# SkyShift contracts v1

This is the portable implementation specification. No untracked root proposal or private machine context is required. Planning only: the signatures below are contracts, not existing product code.

## Scope and ownership

Python 3.10+, package `skyshift/`, invoked from the repository root. Pipeline: discover -> choose -> translate -> migrate -> run unchanged app -> parity -> sever -> evidence. Default: Leaseweb compute plus either Leaseweb object storage or a separately operated S3-compatible service on the supplied Linux VM. Provider choice (official Leaseweb provider versus OpenStack) is a human VM-gate decision, not an invented working deployment. No production data, IAM translation, Kubernetes, Azure/CloudFormation, eBPF, competitor ranking, or database migration in P0. The report supports exit planning; it does not certify sovereignty or DORA compliance.

| Workstream | Exclusive implementation paths | Reserved task home / IDs |
|---|---|---|
| WS0 | `tasks/WS0-setup/validation.md` (human record only) | `tasks/WS0-setup/WS0-01-*.md` |
| WS1 | `skyshift/discover.py`, `skyshift/translate.py`, `skyshift/catalogue/resources.yaml`, `skyshift/catalogue/targets.yaml`, `skyshift/templates/iac/`, `tests/ws1/` | `tasks/WS1-discover-translate/WS1-01` through `WS1-99` |
| WS2 | `skyshift/migrate.py`, `skyshift/parity.py`, `fixtures/aws_workload/`, `tests/ws2/` | `tasks/WS2-data-parity/WS2-01` through `WS2-99` |
| WS3 | `skyshift/sever.py`, `skyshift/llm.py`, `skyshift/catalogue/replacements.yaml`, `fixtures/llm/`, `fixtures/ip-ranges/`, `tests/ws3/` | `tasks/WS3-severance-ai/WS3-01` through `WS3-99` |
| WS4 | `skyshift/__init__.py`, `skyshift/cli.py`, `skyshift/evidence.py`, `skyshift/templates/report/`, `tests/__init__.py`, `tests/ws4/`, `README.md`, `LICENSE`, `requirements.txt`, `.gitignore`, `.env.example`, `demo/`, shared planning maintenance | `tasks/WS4-integration-delivery/WS4-01` through `WS4-99` |

All feature paths must be enumerated narrowly in task `files`; directory prefixes above are reservations, not permission to edit an entire directory. Shared files belong to WS4. Request changes through `tasks/comms/inbox-WS4.md`. Each stream's `-01` task is its stub task. WS1-01, WS2-01 and WS3-01 must have no dependency on the VM gate or on WS4-01; WS4-01 may depend on those three stubs. WS0-01 is the independent human VM gate. Planners allocate later IDs only in their reserved home; the final verifier reconciles reciprocal `blocks` links.

## Python API (JSON-compatible dicts, pathlib.Path)

Each function returns a complete envelope defined below, without writing its canonical JSON file. Functions consuming `data_map` or `target` receive the preceding envelope's `data` object, never the whole envelope. `output_dir` is the run root (normally out), not its iac subdirectory. The CLI alone serializes envelopes to `out/`. Functions may write their owned generated artifacts (IaC, report). Accept explicit keyword-only options; importing a module never starts services or network calls. `stub=True` is offline and must produce realistic synthetic data, not empty success. `config` maps the environment key names below to runtime values; secrets never enter returned records. Operational failures become FAIL/incomplete envelopes; corrupt programmer inputs raise ValueError. CLI converts exceptions into incomplete records and a nonzero exit.

```python
# skyshift/discover.py (WS1)
def discover(workload: Path, *, config: dict, stub: bool = False) -> dict: ...
def choose(data_map: dict, *, config: dict, stub: bool = False) -> dict: ...
# skyshift/translate.py (WS1)
def translate(data_map: dict, target: dict, *, output_dir: Path, config: dict, stub: bool = False) -> dict: ...
# skyshift/migrate.py (WS2)
def migrate(data_map: dict, target: dict, *, config: dict, stub: bool = False) -> dict: ...
# skyshift/parity.py (WS2)
def run_app(workload: Path, target: dict, *, config: dict, stub: bool = False) -> dict: ...
def verify(data_map: dict, target: dict, *, config: dict, stub: bool = False) -> dict: ...
# skyshift/sever.py (WS3)
def sever(data_map: dict, target: dict, *, config: dict, max_attempts: int = 2, stub: bool = False) -> dict: ...
# skyshift/llm.py (WS3): never decides check verdicts
def complete(task: str, payload: dict, schema: dict, *, config: dict, replay: bool = False) -> dict: ...
# skyshift/evidence.py (WS4)
def build_evidence(records: list[dict], *, output_dir: Path, config: dict, stub: bool = False) -> dict: ...
# skyshift/cli.py (WS4)
def main(argv: list[str] | None = None) -> int: ...
```

`run_app` runs functional checks with a bounded process lifetime and always cleans up children. It records the unchanged fixture app hash before/after and config-only endpoint changes; it is not a permanent background daemon. `complete` returns `{"mode":"live|replay", "status":"ok|incomplete", "data":{}, "errors":[]}`; `data` must validate against the caller's JSON schema. Schema failure, timeout or sanitiser rejection yields incomplete. Only synthetic, locally sanitised fixture information may leave the VM; no raw environment, source data, credentials or private addresses. Replay must be visibly labelled, never passed off as a model call.

## Shared envelope and paths

Every step record has exactly these top-level keys (extension happens inside `data`):

```json
{"schema_version":1,"step":"discover","mode":"stub","status":"incomplete","checks":[{"id":"example","status":"incomplete","detail":"synthetic stub; no VM validation"}],"data":{},"errors":[]}
```

`step`: discover, choose, translate, migrate, run, parity, sever, evidence. `mode`: live, stub, replay. `status` and check status: PASS, FAIL, incomplete. `errors`: list of sanitized strings. Any failed required check => FAIL; otherwise missing checks, malformed model output, manual resources, offline validation only or stub results => incomplete; PASS requires all required checks measured. Replay applies only to model explanations; deterministic steps still execute live. No stub may produce a live PASS. Record each check's honest scope (e.g. proxy denial is not proof of all network isolation). Outputs contain no credentials or signed URL query strings.

| Step | Canonical output | Required data fields |
|---|---|---|
| discover | `out/discover.json` | resources, calls, buckets, readiness |
| choose | `out/choose.json` | target_id, operator, jurisdiction, storage_mode, criteria, prices, explanation |
| translate | `out/translate.json` | provider, files, resources, validation |
| migrate | `out/migrate.json` | objects, source_count, target_count, matched, missing, different, extra |
| run | `out/run.json` | app_sha256_before, app_sha256_after, endpoint_changed, functional_checks, host_network |
| parity | `out/parity.json` | operations, selection |
| sever | `out/sever.json` | attempts, max_attempts, final, radar_scope |
| evidence | `out/evidence.json` | records, final_hash, report_path, open_items |

Canonical generated IaC: `out/iac/main.tf`; human report: `out/report.html`. Outputs are local generated artifacts, ignored by Git. The CLI writes JSON atomically with UTF-8, sorted keys and no NaN, overwriting stale records on every run; downstream steps must not use outputs from an earlier run. Inputs are function return values, not assumed shared files across computers.

## Required JSON data shapes

Illustrative values below are synthetic types/examples, not measured results. All listed keys are required; arrays may be empty only when genuinely measured empty or explicitly incomplete. Additional per-object fields are permitted if sanitized.

### Data map (`discover.data`)

```json
{"resources":[{"id":"aws_s3_bucket.demo","type":"aws_s3_bucket","provider":"aws","region":"eu-central-1","supported":true}],"calls":[{"file":"fixtures/aws_workload/app.py","line":10,"service":"s3","operation":"put_object","bucket":"demo","endpoint_host":null}],"buckets":[{"name":"demo","provider":"aws","jurisdiction":"US-controlled","object_count":10,"total_bytes":1000}],"readiness":{"score":80,"formula":"max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)","proprietary":1,"unsupported":0,"us_calls":0}}
```

Score rule v1 is the displayed formula above, counts computed from parsed resources/calls and catalogue support, not AI. Unsupported S3 operations counted separately from proprietary unsupported resource types; duplicate AST calls deduplicated by file/line/service/operation. Unknown inventory => incomplete, never zero by assumption.

### Target choice (`choose.data`)

```json
{"target_id":"leaseweb-selfhosted","operator":"Leaseweb","jurisdiction":"EU","storage_mode":"self_hosted_s3","criteria":[{"name":"operator_jurisdiction","value":"EU","source_url":"https://www.leaseweb.com/"}],"prices":[{"item":"compute","amount":null,"currency":"EUR","unit":"hour","source_url":null,"assumptions":"not verified"}],"explanation":{"mode":"replay","text":"Synthetic example"}}
```

Only Leaseweb choices; deterministic selection uses human-approved provider availability, then native storage if verified accessible, otherwise self-hosted storage. Unknown prices remain null with open items; no invented savings or assumed API coverage. Actual prices need cited public URLs per value and explicit assumptions. Human gate fixes provider mode; no key means no real provider apply.

### Translated IaC (`translate.data`)

```json
{"provider":"openstack","files":["out/iac/main.tf"],"resources":[{"source_id":"aws_s3_bucket.demo","target_type":"self_hosted_s3","method":"template","status":"mapped","manual_reason":null}],"validation":{"method":"tofu","init_exit":0,"validate_exit":0,"attempts":1,"diagnostics":[]}}
```

Resource method: template, model, adopted_existing, manual. Status: mapped, manual. `adopted_existing` (human decision, Miguel, 15:07 UTC) marks an existing, human-provisioned target resource; it is allowed only when migrate and parity measured PASS on that same resource in the same run, uses status mapped, carries a `note` with the evidence, and never counts as `template` or as created by OpenTofu. Optional per-resource `note` (string) carries sanitized operator notes such as an approximate flavor match. Known mappings: aws_instance, aws_security_group, aws_s3_bucket. Templates first; schema-constrained AI only for gaps; at most one correction after validation failure. Unresolved resources remain visible as manual. Offline schema validation uses method `offline_schema`, nullable exit codes, and incomplete overall status, never claims `tofu validate` ran. No automatic apply in P0.

### Migration (`migrate.data`)

```json
{"objects":[{"key":"sample.txt","source_bytes":100,"target_bytes":100,"source_sha256":"<64 lowercase hex>","target_sha256":"<64 lowercase hex>","status":"matched"}],"source_count":1,"target_count":1,"matched":1,"missing":0,"different":0,"extra":0}
```

Stream every object's bytes through SHA-256 on both sides; ETag is not a checksum substitute. Object status: matched, missing, different, extra. Missing-side size/hash is null. Counts computed from complete listings (pagination included); nonzero missing/different/extra => FAIL. Use rclone copy/sync only against disposable synthetic target buckets with explicit human approval for deletion; prefer copy by default. Command failures and incomplete listing => FAIL or incomplete, never PASS.

### Parity (`parity.data`)

```json
{"operations":[{"operation":"put_object","before":{"status":"PASS","detail":"Moto synthetic fixture"},"after":{"status":"PASS","detail":"target check"},"equal":true}],"selection":{"source":"ast+required","operations":["put_object","get_object","list_objects_v2"],"ai_mode":"replay"}}
```

Same suite before (Moto) and after (target). Include detected operations, put/get/list and app checks; multipart and presigned URL when used. Model selection cannot drop required/detected operations; validate proposals against a bounded known-operation schema. Differences are findings, not process crashes. equal only means the measured results agree; both failing never makes overall PASS. Missing/skipped operations => incomplete.

### Severance (`sever.data`)

```json
{"attempts":[{"number":1,"events":[{"host":"monitoring.amazonaws.com","ip":"192.0.2.1","port":443,"decision":"deny","reason":"published cloud range","via":"proxy"}],"blocked":1,"bypasses":[],"replacement":{"id":"local-otel","mode":"replay","applied_config_keys":["SKYSHIFT_TELEMETRY_ENDPOINT"]},"status":"FAIL"}],"max_attempts":2,"final":"blocked","radar_scope":"socket detection only; proxy enforces requests using it"}
```

Published AWS/Azure/Google/Cloudflare ranges must have provenance and freshness; unresolved destinations fail closed at proxy. Allowlist exact approved hosts/ports; resolve and check addresses at connect time to avoid DNS rebinding, reject any denied range. Radar uses /proc/net/tcp or ss on Linux, reports coverage limitations and bypasses but does not enforce. Fixture contains telemetry dependency visible in discover; app unchanged, remediation config-only from replacement catalogue. Final: green, blocked, incomplete. Record red -> fix -> green as separate attempts; initial failure remains evidence. Max two attempts by default; blocked after exhaustion. A successful final retry must not erase the initial denial; evidence evaluates final checks and preserves history.

### Evidence (`evidence.data`)

```json
{"records":[{"step":"discover","path":"out/discover.json","artifact_sha256":"<64 lowercase hex>","previous_hash":"<64 lowercase hex>","hash":"<64 lowercase hex>"}],"final_hash":"<64 lowercase hex>","report_path":"out/report.html","open_items":[]}
```

Hash order: discover, choose, translate, migrate, run, parity, sever. Canonical artifact bytes: `json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`. artifact_sha256 = SHA256(canonical bytes).hexdigest(). First previous_hash = 64 ASCII zero characters. Chain hash = SHA256(bytes.fromhex(previous_hash) + bytes.fromhex(artifact_sha256)).hexdigest(). Evidence does not hash itself or the mutable HTML report. Recompute chain to verify; changing one artifact must fail verification. Evidence required checks cover complete artifact set, live measured migration/parity, unchanged app, validated IaC and final severance. Stub/replay qualifications and offline-only validation stay explicit; history red does not fail a verified final green. Report uses DORA-style headings but no certification claim. AI may draft narrative, never calculate verdicts, costs or hashes.

## Environment names only

WS4 creates `.env.example` listing these names without values. No real `.env` is read during planning, tracked or logged. Runtime secret values are supplied privately by humans. Never put values in comms.

`AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `SKYSHIFT_SOURCE_ENDPOINT_URL`, `SKYSHIFT_SOURCE_ACCESS_KEY_ID`, `SKYSHIFT_SOURCE_SECRET_ACCESS_KEY`, `SKYSHIFT_SOURCE_BUCKET`, `SKYSHIFT_TARGET_ENDPOINT_URL`, `SKYSHIFT_TARGET_ACCESS_KEY_ID`, `SKYSHIFT_TARGET_SECRET_ACCESS_KEY`, `SKYSHIFT_TARGET_BUCKET`, `SKYSHIFT_TARGET_PROVIDER`, `SKYSHIFT_LLM_BASE_URL`, `SKYSHIFT_LLM_API_KEY`, `SKYSHIFT_LLM_MODEL`, `SKYSHIFT_LLM_REPLAY`, `SKYSHIFT_TELEMETRY_ENDPOINT`, `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`, `OS_AUTH_URL`, `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET`, `OS_REGION_NAME`, `LEASEWEB_API_KEY`.

Only provider-appropriate keys are required after the human gate; no speculative provider-specific API usage. CLI builds boto3 clients explicitly for source and target to avoid global endpoint confusion. The unchanged app alone receives AWS_ENDPOINT_URL and AWS credentials; proxy settings must not bypass the tested telemetry destination via NO_PROXY.

## CLI contract and demo honesty

Future commands: `python -m skyshift.cli discover|choose|translate|migrate|verify|sever|report|run-all --workload fixtures/aws_workload --out out [--stub]`. `verify` emits both run and parity. `run-all` performs all eight steps in order. Exit 0 only for live overall PASS; 1 for measured FAIL; 2 for incomplete/stub. Stub acceptance expects exit 2 with all eight valid JSON records and HTML, not successful live proof. Integration tests explicitly accept this exit code. No product commands exist yet.

Before lunch (12:30): real discover/translate/migrate/parity; 14:00 severance/report; 14:30 feature freeze and two rehearsals/backup; 15:15 code freeze, no merges. These are targets, not claims of completed checks. Cut features rather than fabricate live results. Backup video and cached responses are labelled replay; deterministic copy/checksum/parity/proxy still run live where available. Pitch <= five minutes. Claims limited to measured checks and blocked connections, never mathematical guarantees, universal isolation, certification, invented savings or global novelty.
