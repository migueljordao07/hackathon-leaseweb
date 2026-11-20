---
id: WS1-04
title: Render known AWS resources into approved provider templates
workstream: WS1
status: in_progress
owner: claude-1
priority: P0
depends_on: [WS1-03, WS0-01]
blocks: [WS1-05]
files: [skyshift/translate.py, skyshift/catalogue/resources.yaml, skyshift/templates/iac/compute.tf.j2, skyshift/templates/iac/network.tf.j2, skyshift/templates/iac/storage.tf.j2, skyshift/templates/iac/provider.tf.j2, skyshift/templates/iac/provider-schema.json, tests/ws1/test_templates.py]
estimate: 50m
claimed_at: "2026-11-20T14:35:00+00:00"
updated_at: "2026-11-20T14:35:00+00:00"
---

## Goal
Replace translation's real-path placeholder with template-first IaC for the three P0 AWS resource types using the human-approved target provider.

## Context
Read tasks/contracts.md Python API, translated IaC, data map, environment and ownership sections; WS1-02 fixes resources.yaml, WS1-03 fixes target IDs. Original proposal sections 3 step 3, 4, 6, 8-11: catalogue/Jinja2 before AI, aws_instance/aws_security_group/aws_s3_bucket only, no auto-apply, provider decided with mentors. Executor claude-1, supervised by Ricardo; Diogo reviews source/target traceability.

Unavoidable cross-workstream dependency: WS0-01 is the human gate establishing go/switch and the actual provider/schema/registry path. Templates must not invent a Leaseweb resource API. WS1-01 remains independent and WS4 can integrate stubs before this gate. A human switch to Airlock means stop live SkyShift work and request an approved cut, not mark this task done. No live VM result is implied by this plan.

`translate(data_map: dict, target: dict, *, output_dir: Path, config: dict, stub: bool = False) -> dict` writes `output_dir/iac/main.tf`; inputs are data objects. Known template filenames are fixed by WS1-02. `provider-schema.json` stores an offline subset of the actual approved provider's resource schema plus provider source, version and provenance URL/retrieval date; no credentials. Only the chosen provider mode is P0; the other mode is manual, not fictional coverage.

## Steps
1. Follow Git-only claim/push protocol in tasks/README.md, read gate/channel/inbox, and verify dependencies done. Request Jinja2/PyYAML and any provider CLI setup through WS4/humans without editing shared files. Preserve stub=True offline behavior.
2. Obtain the selected provider source/version/resource schema from the human gate evidence and official provider documentation/`tofu providers schema -json` where available. Vendor only the required credential-free validation subset with provenance. If schema is unavailable, block rather than making up resource names/attributes.
3. Render provider.tf.j2 and known compute/network/storage templates with strict undefined values and HCL-safe serialization of literals; do not interpolate untrusted raw HCL or execute source input. Use stable source-ID-derived target labels and references, preserve dependency relationships, and never place config secret values or secrets from discovered attributes into generated files.
4. For aws_instance map verified image/flavor/network inputs; unresolved AMI-to-image or sizing conversions become manual with reason. Map security-group ingress/egress explicitly; never broaden a rule to make it valid. Map S3 bucket to actual approved storage capability; in self_hosted_s3 mode record separate service/bucket setup as a manual requirement unless a verified supported mapping exists. Do not invent a provider-managed bucket for a self-hosted service. Resource catalogue eligibility is not a promise every instance can translate automatically.
5. Include every discovered resource in translate.data.resources with source_id, target_type, method template/manual, status mapped/manual and manual_reason. Unsupported/dynamic/unresolved resources remain visible; one manual item forces incomplete. Resources become mapped only for actual valid rendered mappings. Return provider/files/resources/validation; pending real tofu validation uses offline_schema with null exit codes, never tofu success. Save diagnostics for WS1-05.
6. Add deterministic rendering/schema tests using temporary outputs and an injectable approved schema. Record mapping limits, schema provenance, template diff and actual tests in Log/WS1 inbox and push named-file commits. Shared contract changes require WS4 approval, not local edits.

## Acceptance criteria
- `python -B -m unittest discover -s tests/ws1 -p test_templates.py -v` exits 0. Test all three supported types against the approved schema, unresolved AMI conversion, explicit security rules, source references, unknown resource/manual preservation, malicious HCL literals, deterministic rerender, output path confinement, credential redaction and no auto-apply subprocess.
- `python -B -m unittest discover -s tests/ws1 -p 'test_*.py' -v` passes all default offline tests. No placeholder is counted as mapped solely because the resource type is known.
- On the human-approved Linux environment, generate `out/iac/main.tf` from sanitized fixture data through the function or landed CLI; inspect the exact provider version and mapping rows. Run `tofu -chdir=out/iac init -backend=false -input=false` then `tofu -chdir=out/iac validate -json`; record actual codes/diagnostics as baseline evidence for WS1-05, never run apply. If only offline validation is available, explicitly record incomplete and the human-approved fallback.
- `python tasks/board.py --check` succeeds after verifier reconciles gate blocks. Review/done follow Linux-like acceptance, origin/main and intact run-all protocol. Commit format `[WS1-04] feat: render approved provider templates (claude-1)`.

## Out of scope
Provisioning/apply/destroy, speculative provider modes, Kubernetes/IAM/database translation, changing the app, storage daemon deployment, model-client implementation, shared dependencies and report/CLI code.

## Fallback if blocked
Human-approved offline schema mode is incomplete with null tofu exit codes; retain manual mappings and output diagnostics. Missing provider schema or an unsafe mapping is a blocker, not permission to fabricate deployment. Notify inbox-humans/WS4 through Git; preserve early stubs. Cut optional provider modes before 14:30; no merges after 15:15.

## Log
- 2026-11-20: Planned only. Provider schema and all VM/OpenTofu execution remain unverified; gate remains human-only.
- 2026-11-20 14:35 UTC: Claimed by claude-1 under SPEED MODE (Miguel 14:30; WS1-03/04/05 claimed together, deps WS0-01/WS1-02 done per human decision).
