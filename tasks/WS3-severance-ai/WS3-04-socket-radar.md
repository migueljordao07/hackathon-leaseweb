---
id: WS3-04
title: Add Linux socket radar with explicit detection limits
workstream: WS3
status: done
owner: claude-3
priority: P0
depends_on: [WS3-01]
blocks: [WS3-05]
files: [skyshift/sever.py, tests/ws3/test_socket_radar.py]
estimate: 35m
claimed_at: "2026-11-20T12:50:10+00:00"
updated_at: "2026-11-20T12:53:17+00:00"
---

## Goal
Add a bounded Linux socket-radar check that identifies connections not observed through the proxy and reports detection scope without implying enforcement.

## Context
Follow `tasks/contracts.md` headings Python API and Severance: radar reads `/proc/net/tcp` or `ss -ntp`, only detects, and must disclose coverage limitations and possible bypasses. Root proposal sections 3, 6, 7 and 10 identify proxy bypass as a risk. This task can proceed from WS3-01's stub independently of the live VM gate; unit tests must be portable through injected proc/command input.

## Steps
1. Implement a parser for `/proc/net/tcp` (and `/proc/net/tcp6` if supported) or a bounded `ss -ntp` adapter behind an injectable reader.
2. Compare observed sockets with the proxy-observed set and produce sanitized bypass candidates without process secrets.
3. Return radar scope and collection errors in the severance data; never convert detection into a blocking claim.
4. Test parsing, empty/unreadable input, matching proxy-observed sockets and detection of an unmatched socket using fixtures.

## Acceptance criteria
- `python -m unittest tests.ws3.test_socket_radar` exits 0 with at least four deterministic fixture-based cases.
- No test requires Linux `/proc`, root, live sockets or `ss`; a bounded timeout is used for any command adapter test.
- Output explicitly states that the radar detects only and does not enforce network isolation.

## Out of scope
eBPF, firewalling, killing processes, claims of complete socket visibility, host-wide network changes and cross-stream integration files.

## Fallback if blocked
Use only the fixture parser and return incomplete coverage with a clear reason; do not silently omit radar evidence.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
- 2026-11-20T12:50:10+00:00 — Claimed by claude-3 (Claude Code); detection-only radar with fixture-driven offline tests.
- 2026-11-20T12:53:17+00:00 — Done (detection only). Code in 3ce02a6: skyshift/sever.py adds parse_proc_net_tcp (IPv4/IPv6 little-endian words, IPv4-mapped normalised), parse_ss (ss -ntH, no -p so no process data), _default_radar_reader (/proc/net/tcp{,6}, else ss with 3 s timeout; never raises), radar_scan (ESTABLISHED/SYN_SENT to non-loopback peers not matching proxy allow events and not inbound to a listening port; dedup; samples bounded 1..50; returns enforces False, coverage partial/unavailable, collection_errors, limitations). RADAR_SCOPE now states radar does not enforce. sever() wiring is WS3-05.
  - Acceptance on fresh WSL2 Ubuntu clone at 3ce02a6 (Python 3.12.3): `python3 -B -m unittest tests.ws3.test_socket_radar` 12 OK (proc v4/v6 decoding, ss parsing, empty input, unmatched detection vs proxied/loopback/inbound, sanitized fields, unreadable reader, detection-only wording, sample bound/dedup, ss fallback timeout/no -p via mocks, no proc + no ss); all tests/ws3 53 OK; board --check OK. Extra smoke (not acceptance): default reader on WSL /proc returned coverage partial, 0 errors.
  - Limitations: snapshot sampling misses short-lived connections; TCP only; current network namespace only; no process attribution; not run on the supplied VM. Executor-verified; Francisco may reopen.
