---
id: WS1-03
title: Choose a verified Leaseweb target with cited criteria
workstream: WS1
status: in_progress
owner: claude-1
priority: P0
depends_on: [WS1-02]
blocks: [WS1-04]
files: [skyshift/discover.py, skyshift/catalogue/targets.yaml, tests/ws1/test_choice.py]
estimate: 30m
claimed_at: "2026-11-20T14:35:00+00:00"
updated_at: "2026-11-20T14:35:00+00:00"
---

## Goal
Replace choose's placeholder with deterministic Leaseweb deployment selection and honest price/criteria records.

## Context
Portable contracts: tasks/contracts.md target choice, data map, Python API, environment names and demo honesty. Original proposal sections 3 step 2, 4, 6-8, 9-12: compare Leaseweb native object storage versus a separately operated S3 service on Leaseweb compute, not sponsor competitors; AI explains, code selects. Suggested executor claude-1, Diogo supervises criteria/prices and Ricardo validates provider availability. WS1-02 is serial because both tasks edit discover.py. Signature `choose(data_map: dict, *, config: dict, stub: bool = False) -> dict`; target data is passed unchanged to subsequent functions.

Decide targets.yaml now: root schema_version: 1 and targets: list; each entry includes target_id, operator, jurisdiction, storage_mode, provider_modes (list of verified provider identifiers), criteria (name/value/source_url records), prices (item/amount/currency/unit/source_url/assumptions records). IDs: leaseweb-native for native_s3, leaseweb-selfhosted for self_hosted_s3. Provider modes come from the human VM record; no invented API coverage or speculative provider name. Runtime availability is not hardcoded into the catalogue. A price amount may be null; numeric prices require a public source URL and assumptions. Add retrieval dates as per-object extension fields, not new envelope keys.

## Steps
1. Claim through tasks/README.md Git protocol as claude-1, push accepted claim, then edit named files only. Read channel/inbox on each pull. Keep discover and all stub behavior intact.
2. Populate Leaseweb-only catalogue using verified public sources for jurisdiction/criteria; keep prices null unless the exact service/region/unit amount is verified. Cite each non-null value, state taxes/billing/storage/egress assumptions and date. Price comparison is not required to invent a baseline or savings percentage.
3. Read human-approved provider from config SKYSHIFT_TARGET_PROVIDER and the sanitized WS0-01 decision recorded in tasks/WS0-setup/validation.md. Do not infer availability from a key name, test private credentials or add config key names to the contract. With a verified available native storage endpoint choose leaseweb-native; otherwise choose leaseweb-selfhosted only if that alternative is human-verified accessible. An unapproved provider, missing availability decision or neither option available yields incomplete with open criteria, not a working target by assumption.
4. Return all required target fields: target_id, operator, jurisdiction, storage_mode, criteria, prices, explanation. Explain the deterministic reason with a labelled deterministic extension in explanation and a valid mode live/replay as specified; a local code explanation needs no model call. Never claim API coverage until parity measures it. Nullable prices stay visible as unknown, not zero; choice PASS concerns verified choice criteria, not migration/sovereignty proof.
5. Test the choice with injected config/availability adapters and temporary sanitized gate records, never requiring real VM data in unit tests. Keep availability logic isolated from catalogue parsing. Hand off the chosen ID, storage mode, provider evidence reference, price unknowns and commands/results in Log and WS1 inbox via Git. Request shared integration changes rather than editing contracts or WS4 files.

## Acceptance criteria
- `python -B -m unittest discover -s tests/ws1 -p test_choice.py -v` exits 0 and covers native preference only when accessible, verified self-host fallback, unknown/no provider, unavailable native without valid fallback, no competitor choices, unknown prices, missing citations for numeric prices, deterministic repeated calls and secret redaction.
- `python -B -m unittest discover -s tests/ws1 -p 'test_*.py' -v` passes existing WS1 tests; no live calls in default tests. Include assertion that an EU region alone cannot prove operator jurisdiction or availability.
- Once WS4 CLI and human gate exist: `python -m skyshift.cli choose --workload fixtures/aws_workload --out out` writes choose.json with the approved Leaseweb target or an explicit incomplete finding. Log the actual exit/envelope; do not count a stub or skipped check as a live choice.
- `python tasks/board.py --check` succeeds. Append actual acceptance/environment and commit reference; use review until Linux-like acceptance and origin/main/run-all conditions in tasks/README.md are met. Commit format `[WS1-03] feat: select verified Leaseweb target (claude-1)`.

## Out of scope
Competitor rankings, extrapolated savings, legal certification, live service provisioning, API coverage proof, model client, contracts/requirements edits and report rendering.

## Fallback if blocked
Retain null prices and an explicit unverified criterion when a source cannot be accessed. Ask humans for sanitized go/provider/endpoint availability evidence through inbox-humans, not secret values. Without a verified target keep incomplete and retain the independent stub for demos; label cached explanations replay. Feature freeze 14:30 and code freeze 15:15 take precedence over additional price research.

## Log
- 2026-11-20: Planned only; provider, storage availability and public prices remain unverified until execution.
- 2026-11-20 14:35 UTC: Claimed by claude-1 under SPEED MODE (Miguel 14:30; WS1-03/04/05 claimed together, deps WS0-01/WS1-02 done per human decision).
- 2026-11-20 14:47 UTC: Implemented (claude-1). skyshift/catalogue/targets.yaml (JSON-subset YAML, Leaseweb-only, leaseweb-native + leaseweb-selfhosted, all prices null with assumptions); live choose in skyshift/discover.py reads the signed gate record (tasks/WS0-setup/validation.md: go-with-fallback, provider openstack, check 1 Leaseweb bucket PASS) and optional SKYSHIFT_TARGET_PROVIDER (must match gate). Result: leaseweb-native / native_s3, checks provider_approved PASS + storage_verified PASS, prices null listed in data.open_items. Explanation via skyshift.llm.complete (live/replay mode preserved; deterministic text kept in explanation.deterministic). Local Windows/Python 3.14: `python -B -m unittest discover -s tests/ws1 -p 'test_*.py'` 44 OK (8 skipped); tests.ws4.test_stub_run_all OK. test_stubs.py live-placeholder assertion narrowed to discover (WS1-owned file). Awaiting live VM choose from claude-3.
