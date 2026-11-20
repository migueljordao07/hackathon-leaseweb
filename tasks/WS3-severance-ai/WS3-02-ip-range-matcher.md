---
id: WS3-02
title: Implement provenance-aware IP range matching
workstream: WS3
status: done
owner: claude-3
priority: P0
depends_on: [WS3-01]
blocks: [WS3-03]
files: [skyshift/sever.py, fixtures/ip-ranges/ranges.json, tests/ws3/test_ip_ranges.py]
estimate: 35m
claimed_at: "2026-11-20T12:43:35+00:00"
updated_at: "2026-11-20T12:46:46+00:00"
---

## Goal
Implement deterministic matching of IP addresses against fixture-backed AWS, Azure, Google and Cloudflare ranges, with freshness/provenance and fail-closed handling for unknown destinations.

## Context
Follow `tasks/contracts.md` heading Severance: published range data needs provenance/freshness, unresolved destinations fail closed, and proxy decisions must avoid DNS-rebinding gaps by checking the resolved address at connect time. Root proposal sections 3, 6, 7, 9 and 10 describe the severance checks. Keep the fixture synthetic/documented and suitable for offline tests; do not claim it is a current provider feed. Depends on WS3-01 stub; WS3-03 consumes this matcher.

## Steps
1. Define a small pure matcher using Python `ipaddress` and fixture schema with explicit source, retrieval/fixture time, and address prefixes.
2. Match IPv4 and IPv6 addresses, including boundary addresses; classify missing, malformed or stale range data as unknown.
3. Expose the match result to the proxy path without changing the public `sever()` envelope. Add a bounded loader for human-approved published AWS/Azure/Google/Cloudflare feeds, with source URL/retrieval date/expiry and validated IPv4/IPv6 prefixes. Keep live snapshots in ignored out/, never replace the committed synthetic fixture or treat it as current. Live refresh is opt-in only after the human VM go; missing/stale/malformed provider data yields unknown/deny and incomplete coverage. Mock all feed transports in default tests.
4. Add unit tests for in-range, out-of-range, prefix boundaries, IPv6, malformed input and stale/unknown data.

## Acceptance criteria
- `python -m unittest tests.ws3.test_ip_ranges` exits 0 and covers at least six cases, including fail-closed unknown/stale data and IPv4/IPv6 boundaries.
- Tests use only the committed synthetic fixture and standard-library `ipaddress`; they make no network calls.
- `python tasks/board.py --check` exits 0 after the task is marked done and its dependent links are updated by the framework verifier.

## Out of scope
Unapproved network fetches, DNS resolution, proxy enforcement, firewall rules, socket radar and claims of complete network isolation. The bounded approved-feed loader is in scope; current feed availability is measured only at WS3-07.

## Fallback if blocked
Treat unavailable or invalid range information as unknown/deny, retain the synthetic fixture, and report the limitation through the WS3 inbox.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20T12:43:35+00:00 — Claimed by claude-3 (Claude Code) after WS3-01 done; offline matcher and mocked feed loader only, no live fetch.
- 2026-11-20T12:46:46+00:00 — Done (offline scope). Code in 2e1559b: skyshift/sever.py adds load_ranges, ranges_from_document, match_ip, classify_addresses (deny if any resolved address is cloud_range/unknown, for connect-time checks by WS3-03), RangeSet.merge/provider_status, load_published_feed (opt-in, explicit approved URLs, https-only, 20 s timeout, 16 MiB bound; AWS/Google/Cloudflare/Azure formats; any failure marks provider invalid), save_snapshot (writes <out>/ip-ranges/snapshot.json, refuses the fixture dir). sever() envelope unchanged. Fixture provenance gains retrieved_at/expires_at (hackathon-day window); Cloudflare synthetic prefix narrowed to /26 so 203.0.113.192/26 is unlisted test space.
  - Acceptance on fresh WSL2 Ubuntu clone at 494feb6 (Python 3.12.3): `python3 -B -m unittest tests.ws3.test_ip_ranges` 15 OK (IPv4/IPv6 boundaries, mapped IPv4, malformed/hostname input, stale, missing, malformed provider data, unreadable file, mocked feeds incl. failure/oversize/no-URL, snapshot path); `tests.ws3.test_contract_stubs` 13 OK; board --check OK; clean tree. Also 28 OK on Windows/Python 3.14.5.
  - Limitations: no live feed fetched (all transports mocked); Azure URL must be supplied by a human; synthetic fixture is not a current provider feed and goes stale after 2026-11-21T00:00Z (fail closed). No DNS resolution or proxy enforcement here. Executor-verified; Francisco may reopen.
