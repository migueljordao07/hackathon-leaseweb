---
id: WS0-01
title: Human VM validation and go or Airlock switch
workstream: WS0
status: done
owner: null
priority: P0
depends_on: []
blocks: [WS1-04, WS2-03, WS2-04, WS3-07, WS4-05]
files: [tasks/WS0-setup/validation.md]
estimate: 30m
claimed_at: null
updated_at: "2026-11-20T14:33:00+00:00"
---

## Goal

A human tests the real supplied Linux VM within 30 minutes and records go, go-with-fallback, or switch-to-Airlock. Only a human can mark this gate done. No product implementation is authorized by this planning card.

## Context

Original proposal sections 3, 4, 6 and 9–11: the pipeline relies on two S3 endpoints, rclone, a usable target IaC provider, an EU-hosted model and a blocking proxy. See ../contracts.md for scope, environment key names and incomplete-result semantics. These are unverified capabilities, not completed checks. Ricardo confirms official Leaseweb provider versus OpenStack with mentors; Miguel coordinates VM access; no credentials are committed. Stubs proceed offline without this gate; live feature tasks depend on it, never the other way around.

## Steps

1. Human records start time, sanitized Linux/tool versions, available runtime (Docker or user-space), provider choice and access availability in validation.md. Agents may assist with commands but must not provide a human signature. Stop the test after 30 minutes.
2. Start Moto and the chosen S3-compatible server on the actual VM. Use boto3 clients explicitly pointed at both endpoints. Run put/get/list and compare returned bytes. Record exact commands, sanitized output, exit codes and time for check 1.
3. Seed 10 synthetic objects, run rclone between disposable endpoints, stream both copies through hashlib.sha256, and verify 10/10 objects/counts/sizes/hashes. Record check 2. No ETag substitution and no production buckets.
4. Write a minimal roughly 10-line Terraform probe for the human-selected provider in a disposable VM directory. Run tofu init and tofu validate; record registry access and actual exit codes as check 3. No apply. If registry blocked, explicitly record offline-schema fallback, not a successful tofu check.
5. Make one sanitised EU-hosted model request for three resources. Check JSON schema and elapsed time under 10 seconds as check 4. Cached JSON is a fallback labelled replay, not a live API pass.
6. Run a probe with HTTPS_PROXY pointing to a local allowlist proxy. A request resolving to a published AWS IP must be denied and logged; an approved local target must remain reachable. Record commands/denial and range provenance as check 5. Socket radar detection is not enforcement. Use a throwaway probe if product proxy does not exist yet; gate never waits on WS3-01.
7. Human signs decision: go for five passes; go-with-fallback for four passes plus a documented tested fallback for the fifth; otherwise switch to Airlock. Append a sanitized notice to tasks/comms/channel.md and tasks/comms/inbox-humans.md. Never mark done merely because the planning framework or offline stubs pass.

## Acceptance criteria

- Run `python tasks/board.py --check` from the repository root: exit 0 before and after updating gate status.
- validation.md has exactly five numbered check records, each with actual VM commands, timestamps, exit codes/results, pass/fail and any fallback, plus a human-attributed decision/signature. No fabricated terminal output or secret values.
- Check 1 measures put/get/list on both servers; check 2 measures SHA-256 equality for all 10 seeded objects; check 3 measures actual tofu init/validate; check 4 measures schema-valid JSON for three resources within 10 seconds; check 5 measures AWS denial/logging with approved-target connectivity. Tests not run are explicitly not run.
- Human go is supported by 5/5, or 4/5 with explicit tested fallback. Otherwise record switch, cut dependent SkyShift live tasks with human approval and do not treat this as a SkyShift live go. The gate can be done after a human switch decision, but dependent SkyShift tasks must be cut/replanned before execution.
- Commit only sanitized validation.md, own task status/Log and append-only comms; human signs final Log. Real VM acceptance commands are recorded by the human when access exists, not invented by this planner.

## Out of scope

No automatic deployment, production data, published credentials, claims of universal isolation/compliance or autonomous go decision. No edits to product modules or shared requirements. No claim that a probe validates the eventual implementation.

## Fallback if blocked

If Docker is unavailable, try user-space services/binaries. If only model fails, use clearly labelled cached responses; if only registry fails, use vendored/offline schema with an explicit incomplete IaC result. If fewer than four checks pass, switch to Airlock: rehearse an AI agent plan on a disposable copy, deterministically block changes when invariants break; no S3 servers/registry required. Airlock is a human-approved separate replan, not code to implement here. Post access/decision requests to tasks/comms/inbox-humans.md without secrets. Gate remains todo/blocked until the human records evidence.

## Log

- 2026-11-20 12:01 UTC — Planning record: no VM access or live checks have been performed by this task. owner and timestamps remain null until actual activity. Human-only completion.
- 2026-11-20 14:33 UTC — Human decision signed by Miguel Jordão at 14:20 UTC: go-with-fallback (4/5), recorded in tasks/WS0-setup/validation.md (abad861); live check 4 addendum 7b85ba5. Status set to done by claude-3 on Miguel's explicit instruction.
