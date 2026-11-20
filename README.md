# SkyShift

**Test your cloud exit plan before you need it.** SkyShift takes a small AWS-style workload (Terraform + an S3-using Python app), moves it to a European operator (Leaseweb), proves the data and the unchanged app still work there, and then cuts the hidden ties back to US-controlled cloud ranges, producing a hash-chained evidence report.

Built in one day for Hackathon Portugal 2026 — InfraHack: AI for Cloud Infrastructure (Leaseweb × Velv).

## Problem

Exit plans (for example under DORA-style operational-resilience expectations) usually live in documents nobody runs. The hard questions — *what exactly depends on AWS? does the data arrive intact? does the app still run unchanged? is anything still calling home?* — are only answered when it is too late. SkyShift turns the exit plan into an executable, repeatable test whose verdicts come from measurements, not from an AI model.

## The 8 steps

| # | Step | What it measures | Output |
|---|------|------------------|--------|
| 1 | discover | Terraform resources, boto3 calls (static AST scan), source buckets, readiness score | `out/discover.json` |
| 2 | choose | Leaseweb target selection from human-approved availability; prices stay `null` unless cited | `out/choose.json` |
| 3 | translate | AWS resources → OpenTofu for the target (templates first), `tofu init/validate` | `out/translate.json`, `out/iac/main.tf` |
| 4 | migrate | Copy synthetic objects source → target, streaming SHA-256 on both sides, complete listings | `out/migrate.json` |
| 5 | run | Run the **unchanged** fixture app against the target (config-only change), app hash before/after | `out/run.json` |
| 6 | parity | Same S3 operation suite before (Moto) and after (target) | `out/parity.json` |
| 7 | sever | Allowlist proxy denies published AWS/Azure/Google/Cloudflare ranges; red → config-only fix → green (max 2 attempts); socket radar for detection | `out/sever.json` |
| 8 | evidence | SHA-256 hash chain over the seven records + HTML report with open items | `out/evidence.json`, `out/report.html` |

AI (an OpenAI-compatible endpoint such as a local Ollama model) only drafts explanations and proposals validated against a JSON schema; it never decides a verdict, cost or hash. Cached model answers are always labelled `replay`.

## Status (honest)

Status at the time of writing; each record states its own `mode` (`live`, `stub`, `replay`) and `status` (`PASS`, `FAIL`, `incomplete`).

| Step | Live on the demo VM | Notes |
|------|---------------------|-------|
| discover | partial | Terraform + boto3 calls + live source bucket listing measured |
| choose | in progress | |
| translate | in progress | `tofu init/validate` verified manually on the VM; authenticated `tofu plan` failed (provider account domain), so **no apply** |
| migrate | in progress | rclone copy with 10/10 SHA-256 matches verified manually on the VM |
| run / parity | in progress | Moto source + Leaseweb S3 target put/get/list verified manually on the VM |
| sever | in progress | proxy denial of AWS ranges and allow of Leaseweb S3 verified manually on the VM |
| evidence | live | hash chain and report built from whatever records exist; incomplete steps listed as open items |

A step that is not yet measured is reported `incomplete` and the run exits 2. Nothing is presented as passing unless it was measured.

## Requirements

- Linux, Python 3.10+ (tested with 3.13/3.14), `git`.
- Python packages in [requirements.txt](requirements.txt): `boto3`, `python-hcl2`, `PyYAML`, `moto[server]`.
- External tools for the live run (not Python packages, installed separately):
  - [OpenTofu](https://opentofu.org/) (`tofu`) — IaC validation (MPL-2.0).
  - [rclone](https://rclone.org/) — optional object copy tool (MIT).
  - [Ollama](https://ollama.com/) or any OpenAI-compatible endpoint — optional; without it explanations use labelled replay (MIT).
  - An S3-compatible target: Leaseweb Object Storage, or a self-hosted S3 service you operate (it keeps its own license).

## Build and run from a fresh clone

```bash
git clone <this repository> skyshift && cd skyshift
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt
python -m skyshift.cli --help
```

### 1. Offline stub run (no network, no credentials)

```bash
python -m skyshift.cli run-all --workload fixtures/aws_workload --out out --stub
echo $?   # 2 = incomplete: synthetic records, NOT live proof
```

Produces the eight JSON records, `out/iac/main.tf` and `out/report.html`.

### 2. Live run

```bash
# local S3-compatible source with synthetic data
moto_server -H 127.0.0.1 -p 5000 &
cp .env.example .env      # fill values privately; .env is git-ignored
set -a; . ./.env; set +a
python -m skyshift.cli run-all --workload fixtures/aws_workload --out out
```

Exit codes: **0** every step live PASS · **1** a measured FAIL · **2** incomplete or stub. Open `out/report.html` for the evidence report. Individual steps: `discover`, `choose`, `translate`, `migrate`, `verify` (run + parity), `sever`, `report`.

### Tests

```bash
python -B -m unittest discover -s tests -t . -v
```

## Safety and limits

- Synthetic fixture data only; no production data, no database migration, no IAM translation.
- No automatic `tofu apply`; provider choice is a human decision.
- Secrets come only from the environment and are redacted from every record; `.env`/`vm.env` are git-ignored.
- Proxy and radar results are scoped evidence (what was measured), not proof of zero leakage. The report uses DORA-style headings but is **not** a compliance certification.

## Project structure

```
skyshift/            Python package
  cli.py             eight-step CLI and exit codes
  discover.py        discover + choose
  translate.py       AWS -> OpenTofu translation and validation
  migrate.py         object copy with per-object SHA-256
  parity.py          unchanged app run + before/after parity
  sever.py           allowlist proxy, range matcher, radar, severance loop
  llm.py             schema-validated model client with labelled replay
  evidence.py        hash chain + HTML report
  catalogue/         resource, target and replacement catalogues
fixtures/            synthetic AWS workload, model replay, published IP ranges
tests/               offline unit tests per workstream
tasks/               team task board and coordination log
```

## License

[Apache License 2.0](LICENSE). Third-party tools and services keep their own licenses.
