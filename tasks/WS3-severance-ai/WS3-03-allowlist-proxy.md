---
id: WS3-03
title: Build the local allowlist proxy enforcement path
workstream: WS3
status: todo
owner: null
priority: P0
depends_on: [WS3-02]
blocks: [WS3-05]
files: [skyshift/sever.py, tests/ws3/test_proxy.py]
estimate: 50m
claimed_at: null
updated_at: null
---

## Goal
Implement the local allowlist proxy decision/enforcement path that allows only explicitly approved host/port destinations and denies/logs prohibited or unresolved destinations.

## Context
Use `tasks/contracts.md` headings Python API, Severance, and Environment names only. Proxy policy is the enforcement mechanism; published AWS/Azure/Google/Cloudflare ranges are denied, exact approved hosts/ports are allowed, and resolved addresses must be checked at connection time. Unknown resolution/range status fails closed. The radar is detection-only. Root proposal sections 3, 6, 7, 9 and 10 frame the demo and the proxy-bypass risk. This task depends on the matcher implemented by WS3-02; contract-level offline stubs remain usable before the human gate.

## Steps
1. Implement a local, bounded HTTP proxy with HTTPS CONNECT support, explicit allowlist configuration and structured sanitized events. Local integration tests must exercise an actual loopback listener/CONNECT tunnel and denied upstream connection, not only a policy function. Bind loopback only, bound tunnel lifetime/bytes, and always close sockets/children. Endpoint/allowlist configuration derives from the approved target/telemetry config, never model-created destinations.
2. Invoke WS3-02 matching on resolved addresses immediately before connect/forward; deny unknown and prohibited destinations and record reason/via.
3. Bound request/connect handling and ensure errors cannot accidentally fall back to direct access; do not start a listener on module import.
4. Add deterministic tests using injected resolver/transport seams, checking allowed host+port, blocked provider-range address, unknown resolution, and sanitized log event.

## Acceptance criteria
- `python -m unittest tests.ws3.test_proxy` exits 0 and covers at least four allow/deny/error cases without internet access.
- An integration-style local test confirms a denied request is logged and no upstream connection is attempted; test has a timeout of at most 5 seconds.
- No test claims universal isolation or live VM success; proxy scope/limitations are explicit in returned severance evidence.

## Out of scope
System firewall configuration, changing `NO_PROXY` globally, production proxy deployment, fetching provider ranges, run-all integration and real cloud credentials.

## Fallback if blocked
Keep the proxy API fail-closed and run deterministic decision tests only; mark live enforcement incomplete and notify WS4 through `tasks/comms/inbox-WS4.md` if integration requires a shared change.

## Log
- 2026-11-20 — Planned; no implementation or VM validation performed.
