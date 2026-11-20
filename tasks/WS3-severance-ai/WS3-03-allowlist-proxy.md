---
id: WS3-03
title: Build the local allowlist proxy enforcement path
workstream: WS3
status: done
owner: claude-3
priority: P0
depends_on: [WS3-02]
blocks: [WS3-05]
files: [skyshift/sever.py, tests/ws3/test_proxy.py]
estimate: 50m
claimed_at: "2026-11-20T12:46:59+00:00"
updated_at: "2026-11-20T12:49:53+00:00"
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
- 2026-11-20T12:46:59+00:00 — Claimed by claude-3 (Claude Code) after WS3-02 done; loopback proxy with injected resolver seams, offline tests only.
- 2026-11-20T12:49:53+00:00 — Done (offline/loopback scope). Code in 149e6a6: skyshift/sever.py adds allowlist_from_config (exact host/port from SKYSHIFT_TELEMETRY_ENDPOINT, SKYSHIFT_TARGET_ENDPOINT_URL, AWS_ENDPOINT_URL only; URL credentials dropped), decide() (resolve -> range-check every address -> exact allowlist; unresolved/unknown/stale fail closed), EgressProxy (127.0.0.1 only, CONNECT + absolute-form HTTP, connects only to the checked IP, strips Proxy-* headers, 16 KiB header cap, 5 s IO timeout, 30 s/8 MiB tunnel bounds, 32 connection cap, 403/400/502 with no direct fallback, sanitized events host/ip/port/decision/reason/via/outcome), PROXY_SCOPE shown in sever() check details. sever() envelope shape unchanged; sever() does not run the proxy until WS3-05.
  - Acceptance on fresh WSL2 Ubuntu clone at 149e6a6 (Python 3.12.3): `python3 -B -m unittest tests.ws3.test_proxy` 13 OK in 1.2 s (allow exact host/port, wrong port/unlisted, cloud range even if allowlisted, DNS-rebind mixed answer, unresolved/malformed, stale ranges, real loopback CONNECT deny with zero upstream attempts, CONNECT tunnel echo, HTTP forward + sanitized denied event, upstream refusal 502, listener loopback/stop); all tests/ws3 41 OK; board --check OK. Windows/Python 3.14.5: 3 repeated runs OK.
  - Limitations: no internet, real DNS or VM used; proxy only governs clients honouring HTTP(S)_PROXY (no firewall, UDP/DNS or direct-socket blocking; radar WS3-04 detects only). Not universal isolation. Executor-verified; Francisco may reopen.
  - Process note: commit 149e6a6 also swept in gemini's pre-staged WS2-01 done/comms edits from the shared working-tree index (content intact, misattributed). Announced in channel and inbox-WS2; history not rewritten.
