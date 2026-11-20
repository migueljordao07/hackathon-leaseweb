"""Severance test: deny hyperscaler egress, detect bypasses, retry with replacements (WS3).

Contract: tasks/contracts.md (Python API ``sever``, shared envelope, severance).
The proxy enforces; the socket radar only detects; the model never decides a
verdict. Standard library only. Importing this module performs no I/O, network,
socket or process activity.

Current state: offline stub (WS3-01). ``stub=True`` returns a realistic
synthetic red -> config-only fix -> retry history labelled ``mode: stub`` with
overall ``status: incomplete``. Synthetic events use RFC 5737 documentation
addresses. Non-stub calls return an explicit not-implemented incomplete
envelope until WS3-02..WS3-05 land; no proxy or radar is started. No stub ever
reports PASS or a ``green`` final.
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

SCHEMA_VERSION = 1

REPO_ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS_PATH = REPO_ROOT / "skyshift" / "catalogue" / "replacements.yaml"
RANGES_FIXTURE = REPO_ROOT / "fixtures" / "ip-ranges" / "ranges.json"

SEVER_DATA_KEYS = ("attempts", "max_attempts", "final", "radar_scope")
FINAL_STATES = ("green", "blocked", "incomplete")
RADAR_SCOPE = (
    "socket detection only; proxy enforces requests using it. Radar does not enforce; it samples TCP "
    "sockets in this network namespace and misses short-lived, UDP/DNS and other-namespace traffic"
)


# ---------------------------------------------------------------------------
# IP range matching (WS3-02)
#
# Pure, deterministic and offline. The proxy (WS3-03) resolves a destination,
# then calls ``classify_addresses`` on the exact addresses it will connect to,
# so a DNS answer that changes between check and connect cannot slip through.
# Verdicts: ``cloud_range`` (deny), ``unknown`` (deny, fail closed) and
# ``not_listed`` (not in any fresh published range; the proxy allowlist still
# decides). Missing, malformed or stale provider data makes every unmatched
# address ``unknown``.
# ---------------------------------------------------------------------------

REQUIRED_PROVIDERS = ("aws", "azure", "google", "cloudflare")

# Public feeds a human may approve after the VM gate. Azure publishes a weekly
# file whose URL changes, so its URL must be supplied explicitly by a human.
PUBLISHED_FEEDS: dict[str, tuple[str, ...]] = {
    "aws": ("https://ip-ranges.amazonaws.com/ip-ranges.json",),
    "google": ("https://www.gstatic.com/ipranges/cloud.json",),
    "cloudflare": ("https://www.cloudflare.com/ips-v4", "https://www.cloudflare.com/ips-v6"),
    "azure": (),
}
FEED_MAX_BYTES = 16 * 1024 * 1024
FEED_TIMEOUT_SECONDS = 20
FEED_MAX_AGE = timedelta(days=7)


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now


@dataclass(frozen=True)
class RangeEntry:
    network: ipaddress.IPv4Network | ipaddress.IPv6Network
    provider: str
    service: str | None = None
    region: str | None = None


@dataclass
class RangeSet:
    """Validated prefixes plus per-provider provenance and freshness."""

    entries: list[RangeEntry] = field(default_factory=list)
    sources: dict[str, dict] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    invalid_providers: set[str] = field(default_factory=set)

    def provider_status(self, now: datetime | None = None) -> dict[str, str]:
        """Map each required provider to fresh, stale, missing or invalid."""
        current = _now(now)
        status = {}
        for provider in REQUIRED_PROVIDERS:
            source = self.sources.get(provider)
            if provider in self.invalid_providers:
                status[provider] = "invalid"
            elif source is None or not any(e.provider == provider for e in self.entries):
                status[provider] = "missing"
            else:
                retrieved = _parse_time(source.get("retrieved_at"))
                expires = _parse_time(source.get("expires_at"))
                if retrieved is None or expires is None or retrieved > current or current >= expires:
                    status[provider] = "stale"
                else:
                    status[provider] = "fresh"
        return status

    def merge(self, other: "RangeSet") -> "RangeSet":
        """Combine sets; a provider present in ``other`` replaces this one's data."""
        replaced = set(other.sources) | other.invalid_providers
        return RangeSet(
            entries=[e for e in self.entries if e.provider not in replaced] + list(other.entries),
            sources={**{k: v for k, v in self.sources.items() if k not in replaced}, **other.sources},
            errors=self.errors + other.errors,
            invalid_providers=(self.invalid_providers - replaced) | other.invalid_providers,
        )


def _network(prefix):
    if not isinstance(prefix, str):
        raise ValueError("prefix is not a string")
    return ipaddress.ip_network(prefix.strip(), strict=True)


def ranges_from_document(doc) -> RangeSet:
    """Build a RangeSet from the fixture/snapshot schema in fixtures/ip-ranges/ranges.json.

    Any malformed prefix marks its provider invalid (fail closed) instead of
    silently dropping it.
    """
    result = RangeSet()
    if not isinstance(doc, dict):
        result.errors.append("range document is not an object")
        result.invalid_providers.update(REQUIRED_PROVIDERS)
        return result
    synthetic = bool(doc.get("synthetic", False))
    for source in doc.get("provenance", []) or []:
        if isinstance(source, dict) and isinstance(source.get("provider"), str):
            result.sources[source["provider"]] = {
                "source_url": source.get("source_url"),
                "retrieved_at": source.get("retrieved_at"),
                "expires_at": source.get("expires_at"),
                "synthetic": synthetic,
            }
    rows = [(row, "ip_prefix") for row in doc.get("prefixes", []) or []]
    rows += [(row, "ipv6_prefix") for row in doc.get("ipv6_prefixes", []) or []]
    for row, key in rows:
        provider = row.get("provider") if isinstance(row, dict) else None
        if not isinstance(provider, str):
            result.errors.append("range row without provider")
            continue
        try:
            network = _network(row.get(key))
        except ValueError:
            result.errors.append(f"malformed {provider} prefix")
            result.invalid_providers.add(provider)
            continue
        result.entries.append(RangeEntry(network, provider, row.get("service"), row.get("region")))
    return result


def load_ranges(path: Path = RANGES_FIXTURE) -> RangeSet:
    """Load a committed fixture or an ignored ``out/`` snapshot. Never fetches."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result = RangeSet(errors=[f"range data unavailable: {type(exc).__name__}"])
        result.invalid_providers.update(REQUIRED_PROVIDERS)
        return result
    return ranges_from_document(doc)


def _normalise_address(address):
    if isinstance(address, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
        ip = address
    else:
        if not isinstance(address, str):
            raise ValueError("address is not a string")
        text = address.strip().strip("[]")
        ip = ipaddress.ip_address(text.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped (::ffff:a.b.c.d) and 6to4-style embeddings must match IPv4 ranges.
        if ip.ipv4_mapped is not None:
            return ip.ipv4_mapped
    return ip


def match_ip(address, ranges: RangeSet, *, now: datetime | None = None) -> dict:
    """Classify one address. ``deny`` is True for cloud_range and unknown."""
    status = ranges.provider_status(now)
    coverage = "complete" if all(v == "fresh" for v in status.values()) else "incomplete"
    base = {"ip": None, "verdict": "unknown", "deny": True, "provider": None, "prefix": None,
            "service": None, "synthetic": False, "coverage": coverage, "provider_status": status}
    try:
        ip = _normalise_address(address)
    except ValueError:
        return {**base, "reason": "malformed or unresolved address; fail closed"}
    base["ip"] = str(ip)

    best = None
    for entry in ranges.entries:
        if entry.network.version == ip.version and ip in entry.network:
            if status.get(entry.provider, "fresh") != "fresh" and entry.provider in REQUIRED_PROVIDERS:
                continue
            if best is None or entry.network.prefixlen > best.network.prefixlen:
                best = entry
    if best is not None:
        source = ranges.sources.get(best.provider, {})
        return {**base, "verdict": "cloud_range", "provider": best.provider, "prefix": str(best.network),
                "service": best.service, "synthetic": bool(source.get("synthetic")),
                "reason": f"published {best.provider} range"}

    if coverage != "complete":
        bad = sorted(p for p, v in status.items() if v != "fresh")
        return {**base, "reason": "range data not fresh for " + ", ".join(bad) + "; fail closed"}
    synthetic = any(ranges.sources.get(p, {}).get("synthetic") for p in REQUIRED_PROVIDERS)
    return {**base, "verdict": "not_listed", "deny": False, "synthetic": synthetic,
            "reason": "not in any fresh published range; allowlist still applies"}


def classify_addresses(addresses: Iterable, ranges: RangeSet, *, now: datetime | None = None) -> dict:
    """Classify every address a connection may use; deny if any is denied or none given."""
    results = [match_ip(a, ranges, now=now) for a in (addresses or [])]
    if not results:
        return {"deny": True, "verdict": "unknown", "reason": "no resolved address; fail closed", "matches": []}
    for verdict in ("cloud_range", "unknown"):
        hit = next((r for r in results if r["verdict"] == verdict), None)
        if hit is not None:
            return {"deny": True, "verdict": verdict, "reason": hit["reason"], "matches": results}
    return {"deny": False, "verdict": "not_listed", "reason": results[0]["reason"], "matches": results}


# --- Bounded approved-feed loading (opt-in, live only after the human VM go) ---

def _parse_feed(provider: str, bodies: list[bytes]) -> list[tuple[str, str | None, str | None]]:
    """Parse published feed bodies into (prefix, service, region). Raises ValueError."""
    rows: list[tuple[str, str | None, str | None]] = []
    if provider == "cloudflare":
        for body in bodies:
            for line in body.decode("utf-8").splitlines():
                if line.strip():
                    rows.append((line.strip(), "Cloudflare", None))
        return rows
    if len(bodies) != 1:
        raise ValueError("expected exactly one feed document")
    doc = json.loads(bodies[0].decode("utf-8"))
    if provider == "aws":
        for p in doc["prefixes"]:
            rows.append((p["ip_prefix"], p.get("service"), p.get("region")))
        for p in doc.get("ipv6_prefixes", []):
            rows.append((p["ipv6_prefix"], p.get("service"), p.get("region")))
    elif provider == "google":
        for p in doc["prefixes"]:
            rows.append((p.get("ipv4Prefix") or p["ipv6Prefix"], p.get("service"), p.get("scope")))
    elif provider == "azure":
        for value in doc["values"]:
            props = value.get("properties", {})
            for prefix in props.get("addressPrefixes", []):
                rows.append((prefix, value.get("name"), props.get("region") or None))
    else:
        raise ValueError("unsupported provider")
    if not rows:
        raise ValueError("feed contained no prefixes")
    return rows


def _default_fetch(url: str, *, timeout: float, max_bytes: int) -> bytes:
    """HTTPS GET with timeout and size bound. Imported lazily; never runs at import."""
    import urllib.request

    if not url.startswith("https://"):
        raise ValueError("feed URL must use https")
    request = urllib.request.Request(url, headers={"User-Agent": "skyshift-range-loader"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https enforced)
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("feed exceeds size bound")
    return body


def load_published_feed(
    provider: str,
    *,
    approved_urls: Iterable[str],
    fetch: Callable[..., bytes] | None = None,
    now: datetime | None = None,
    max_age: timedelta = FEED_MAX_AGE,
    max_bytes: int = FEED_MAX_BYTES,
) -> RangeSet:
    """Fetch one human-approved published feed into a RangeSet.

    Opt-in only: callers pass the approved URLs explicitly. Any transport,
    size, parse or prefix error marks the provider invalid, so unmatched
    addresses become unknown/deny. Tests inject ``fetch``.
    """
    if provider not in REQUIRED_PROVIDERS:
        raise ValueError("unknown provider")
    urls = list(approved_urls)
    current = _now(now)
    transport = fetch or _default_fetch
    result = RangeSet()
    if not urls:
        result.errors.append(f"{provider}: no approved feed URL")
        result.invalid_providers.add(provider)
        return result
    try:
        bodies = [transport(url, timeout=FEED_TIMEOUT_SECONDS, max_bytes=max_bytes) for url in urls]
        if any(len(body) > max_bytes for body in bodies):
            raise ValueError("feed exceeds size bound")
        rows = _parse_feed(provider, bodies)
        entries = [RangeEntry(_network(prefix), provider, service, region) for prefix, service, region in rows]
    except Exception as exc:  # noqa: BLE001 - any feed failure must fail closed
        result.errors.append(f"{provider}: feed unavailable or invalid ({type(exc).__name__})")
        result.invalid_providers.add(provider)
        return result
    result.entries = entries
    result.sources[provider] = {
        "source_url": urls[0] if len(urls) == 1 else urls,
        "retrieved_at": current.isoformat(),
        "expires_at": (current + max_age).isoformat(),
        "synthetic": False,
    }
    return result


def ranges_to_document(ranges: RangeSet) -> dict:
    """Serialise a RangeSet to the fixture schema (for ignored ``out/`` snapshots)."""
    return {
        "synthetic": any(s.get("synthetic") for s in ranges.sources.values()),
        "provenance": [{"provider": p, **{k: v for k, v in s.items() if k != "synthetic"}}
                       for p, s in sorted(ranges.sources.items())],
        "prefixes": [{"ip_prefix": str(e.network), "provider": e.provider, "service": e.service, "region": e.region}
                     for e in ranges.entries if e.network.version == 4],
        "ipv6_prefixes": [{"ipv6_prefix": str(e.network), "provider": e.provider, "service": e.service,
                           "region": e.region} for e in ranges.entries if e.network.version == 6],
    }


def save_snapshot(ranges: RangeSet, out_dir: Path) -> Path:
    """Write a live snapshot under ``<out_dir>/ip-ranges/`` (ignored). Never touches the fixture."""
    target_dir = Path(out_dir) / "ip-ranges"
    if target_dir.resolve() == RANGES_FIXTURE.parent.resolve():
        raise ValueError("refusing to overwrite the committed synthetic fixture")
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "snapshot.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ranges_to_document(ranges), sort_keys=True, indent=1), encoding="utf-8")
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Allowlist egress proxy (WS3-03)
#
# Local, loopback-only HTTP proxy with HTTPS CONNECT. Policy: a destination is
# allowed only if its exact (host, port) is on the allowlist derived from the
# approved target/telemetry configuration AND every resolved address passes the
# range matcher. The proxy then connects to the exact address it checked (no
# second resolution), so DNS rebinding between check and connect cannot reach a
# denied range. Every failure path closes the client; there is no direct-access
# fallback. Nothing listens until ``EgressProxy.start()`` is called.
# ---------------------------------------------------------------------------

PROXY_SCOPE = (
    "proxy enforcement applies only to clients that use HTTP(S)_PROXY; it does not block "
    "direct sockets, UDP or DNS (radar detects, firewall out of scope)"
)
ALLOWLIST_CONFIG_KEYS = ("SKYSHIFT_TELEMETRY_ENDPOINT", "SKYSHIFT_TARGET_ENDPOINT_URL", "AWS_ENDPOINT_URL")
PROXY_MAX_HEADER_BYTES = 16 * 1024
PROXY_IO_TIMEOUT = 5.0
PROXY_TUNNEL_MAX_SECONDS = 30.0
PROXY_TUNNEL_MAX_BYTES = 8 * 1024 * 1024
PROXY_MAX_CONNECTIONS = 32
RESOLVE_TIMEOUT = 3.0


def _endpoint(url: str) -> tuple[str, int] | None:
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port or {"https": 443, "http": 80}.get(parts.scheme)
    except (ValueError, AttributeError):
        return None
    return (host, port) if host and port else None


def allowlist_from_config(config: dict, extra: Iterable[tuple[str, int]] = ()) -> frozenset:
    """Exact (host, port) pairs from approved configuration keys only.

    Never derived from model output. Credentials embedded in URLs are dropped
    because only hostname and port are kept.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")
    pairs = set()
    for key in ALLOWLIST_CONFIG_KEYS:
        value = config.get(key)
        if isinstance(value, str) and value:
            endpoint = _endpoint(value)
            if endpoint:
                pairs.add(endpoint)
    for host, port in extra:
        pairs.add((str(host).lower(), int(port)))
    return frozenset(pairs)


def _default_resolver(host: str, port: int) -> list[str]:
    """getaddrinfo bounded by a worker-thread timeout. Raises OSError on failure."""
    import socket
    import threading

    box: dict = {}

    def work():
        try:
            box["infos"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:  # pragma: no cover - depends on resolver
            box["error"] = exc

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(RESOLVE_TIMEOUT)
    if "infos" not in box:
        raise OSError("resolution failed or timed out")
    return list(dict.fromkeys(info[4][0] for info in box["infos"]))


def _default_connector(ip: str, port: int, timeout: float):
    import socket

    return socket.create_connection((ip, port), timeout=timeout)


def decide(host: str, port: int, *, allowlist: frozenset, ranges: RangeSet,
           resolver: Callable[[str, int], list[str]] | None = None, now: datetime | None = None) -> dict:
    """Return a sanitized proxy event plus the address to connect to (if allowed).

    Order: resolve (unresolved => deny), range check on every address
    (cloud/unknown => deny), then exact allowlist (absent => deny).
    """
    host = str(host or "").strip().lower().strip("[]")
    event = {"host": host, "ip": None, "port": port, "decision": "deny", "reason": "", "via": "proxy"}
    if not host or not isinstance(port, int) or not 0 < port < 65536:
        return {**event, "reason": "malformed destination; fail closed", "connect_ip": None}
    try:
        addresses = list((resolver or _default_resolver)(host, port))
    except Exception:  # noqa: BLE001 - any resolver failure fails closed
        addresses = []
    if not addresses:
        return {**event, "reason": "unresolved destination; fail closed", "connect_ip": None}
    verdict = classify_addresses(addresses, ranges, now=now)
    first = next((m for m in verdict["matches"] if m["deny"]), verdict["matches"][0])
    event["ip"] = first["ip"]
    if verdict["deny"]:
        reason = "published cloud range" if verdict["verdict"] == "cloud_range" else verdict["reason"]
        if verdict["verdict"] == "cloud_range" and first.get("provider"):
            reason = f"published cloud range ({first['provider']}{', synthetic fixture' if first['synthetic'] else ''})"
        return {**event, "reason": reason, "connect_ip": None}
    if (host, port) not in allowlist:
        return {**event, "reason": "not on allowlist", "connect_ip": None}
    return {**event, "decision": "allow", "reason": "approved host and port", "connect_ip": first["ip"]}


class EgressProxy:
    """Bounded loopback proxy. Use as a context manager; ``events`` holds sanitized decisions."""

    def __init__(self, *, allowlist: frozenset, ranges: RangeSet,
                 resolver: Callable[[str, int], list[str]] | None = None,
                 connector: Callable | None = None, clock: Callable[[], datetime] | None = None,
                 io_timeout: float = PROXY_IO_TIMEOUT, tunnel_max_seconds: float = PROXY_TUNNEL_MAX_SECONDS,
                 tunnel_max_bytes: int = PROXY_TUNNEL_MAX_BYTES, max_connections: int = PROXY_MAX_CONNECTIONS):
        import threading

        self.allowlist = frozenset(allowlist)
        self.ranges = ranges
        self.resolver = resolver
        self.connector = connector or _default_connector
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.io_timeout = io_timeout
        self.tunnel_max_seconds = tunnel_max_seconds
        self.tunnel_max_bytes = tunnel_max_bytes
        self._slots = threading.BoundedSemaphore(max_connections)
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._threads: list = []
        self._sockets: set = set()
        self._listener = None
        self._stopping = threading.Event()
        self.address: tuple[str, int] | None = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> "EgressProxy":
        import socket
        import threading

        if self._listener is not None:
            raise RuntimeError("proxy already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))  # loopback only
        listener.listen(16)
        listener.settimeout(0.2)
        self._listener = listener
        self.address = listener.getsockname()
        thread = threading.Thread(target=self._accept_loop, name="skyshift-proxy", daemon=True)
        thread.start()
        self._threads.append(thread)
        return self

    def stop(self) -> None:
        self._stopping.set()
        if self._listener is not None:
            self._listener.close()
        with self._lock:
            sockets = list(self._sockets)
        for sock in sockets:
            self._close(sock)
        for thread in list(self._threads):
            thread.join(timeout=2.0)

    def __enter__(self) -> "EgressProxy":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    @property
    def url(self) -> str:
        if self.address is None:
            raise RuntimeError("proxy not started")
        return f"http://{self.address[0]}:{self.address[1]}"

    @property
    def events(self) -> list[dict]:
        with self._lock:
            return [dict(e) for e in self._events]

    # -- internals -----------------------------------------------------------
    def _track(self, sock) -> None:
        with self._lock:
            self._sockets.add(sock)

    def _close(self, sock) -> None:
        if sock is None:
            return
        with self._lock:
            self._sockets.discard(sock)
        try:
            sock.close()
        except OSError:
            pass

    def _record(self, event: dict, outcome: str) -> None:
        clean = {k: event[k] for k in ("host", "ip", "port", "decision", "reason", "via")}
        clean["outcome"] = outcome
        with self._lock:
            self._events.append(clean)

    def _accept_loop(self) -> None:
        import socket
        import threading

        while not self._stopping.is_set():
            try:
                client, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            if not self._slots.acquire(blocking=False):
                self._close(client)
                continue
            self._track(client)
            thread = threading.Thread(target=self._serve, args=(client,), daemon=True)
            self._threads = [t for t in self._threads if t.is_alive()] + [thread]
            thread.start()

    def _read_head(self, client) -> tuple[bytes, bytes] | None:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                return None
            data += chunk
            if len(data) > PROXY_MAX_HEADER_BYTES:
                return None
        head, rest = data.split(b"\r\n\r\n", 1)
        return head, rest

    @staticmethod
    def _reply(client, code: int, text: str) -> None:
        body = text.encode("ascii", "replace")
        try:
            client.sendall(b"HTTP/1.1 %d %s\r\nContent-Type: text/plain\r\nContent-Length: %d\r\n"
                           b"Connection: close\r\n\r\n%s" % (code, text.encode("ascii", "replace"), len(body), body))
        except OSError:
            pass

    def _serve(self, client) -> None:
        upstream = None
        try:
            client.settimeout(self.io_timeout)
            parsed = self._read_head(client)
            if parsed is None:
                self._reply(client, 400, "Bad Request")
                return
            head, rest = parsed
            lines = head.decode("latin-1").split("\r\n")
            parts = lines[0].split(" ")
            if len(parts) != 3:
                self._reply(client, 400, "Bad Request")
                return
            method, target, _version = parts
            if method.upper() == "CONNECT":
                host, _, port_text = target.rpartition(":")
                path = None
            else:
                endpoint = _endpoint(target) if target.lower().startswith("http://") else None
                if endpoint is None:
                    self._reply(client, 400, "Bad Request")
                    return
                host, port_text = endpoint[0], str(endpoint[1])
                from urllib.parse import urlsplit

                split = urlsplit(target)
                path = (split.path or "/") + (f"?{split.query}" if split.query else "")
            try:
                port = int(port_text)
            except ValueError:
                port = -1
            event = decide(host, port, allowlist=self.allowlist, ranges=self.ranges,
                           resolver=self.resolver, now=self.clock())
            if event["decision"] != "allow":
                self._record(event, "blocked")
                self._reply(client, 403, "Forbidden by SkyShift egress policy")
                return
            try:
                upstream = self.connector(event["connect_ip"], port, self.io_timeout)
            except OSError:
                self._record(event, "upstream_error")
                self._reply(client, 502, "Bad Gateway")
                return
            self._track(upstream)
            if path is None:
                self._record(event, "tunnel")
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            else:
                self._record(event, "forwarded")
                headers = [h for h in lines[1:] if h and not h.lower().startswith(("proxy-", "connection:"))]
                request = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{h}\r\n" for h in headers)
                request += "Connection: close\r\n\r\n"
                upstream.sendall(request.encode("latin-1") + rest)
                rest = b""
            if rest:
                upstream.sendall(rest)
            self._relay(client, upstream)
        except Exception:  # noqa: BLE001 - never fall back to direct access
            pass
        finally:
            self._close(upstream)
            self._close(client)
            self._slots.release()

    def _relay(self, client, upstream) -> None:
        import select
        import time

        deadline = time.monotonic() + self.tunnel_max_seconds
        moved = 0
        peers = {client: upstream, upstream: client}
        while not self._stopping.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            readable, _, _ = select.select(list(peers), [], [], min(remaining, 0.5))
            for sock in readable:
                data = sock.recv(65536)
                if not data:
                    return
                moved += len(data)
                if moved > self.tunnel_max_bytes:
                    return
                peers[sock].sendall(data)


# ---------------------------------------------------------------------------
# Socket radar (WS3-04) - DETECTION ONLY
#
# Snapshots TCP sockets from /proc/net/tcp{,6} (or a bounded ``ss -ntH``) and
# reports outbound connections to non-loopback peers that the proxy did not
# open. It never blocks, kills or changes anything. No process attribution is
# collected (no ``ss -p``), so no command lines or environment leak.
# ---------------------------------------------------------------------------

RADAR_LIMITATIONS = (
    "radar detects only and does not enforce network isolation",
    "point-in-time snapshots: connections opened and closed between samples are missed",
    "TCP only: UDP, DNS and ICMP are not observed",
    "only the current network namespace is visible (other containers/VMs are not)",
    "no process attribution: candidates may belong to unrelated host processes",
    "loopback peers and inbound connections to listening ports are not reported",
)
RADAR_MAX_SAMPLES = 50
RADAR_COMMAND_TIMEOUT = 3.0
_TCP_STATES = {"01": "ESTABLISHED", "02": "SYN_SENT", "03": "SYN_RECV", "0A": "LISTEN"}
_SS_STATES = {"ESTAB": "ESTABLISHED", "SYN-SENT": "SYN_SENT", "SYN-RECV": "SYN_RECV", "LISTEN": "LISTEN"}


def _proc_address(text: str) -> tuple[str, int]:
    """Decode a /proc/net/tcp{,6} ``HEXADDR:HEXPORT`` (little-endian 32-bit words)."""
    addr_hex, port_hex = text.split(":")
    port = int(port_hex, 16)
    raw = bytes.fromhex(addr_hex)
    if len(raw) not in (4, 16):
        raise ValueError("bad address length")
    swapped = b"".join(raw[i:i + 4][::-1] for i in range(0, len(raw), 4))
    ip = ipaddress.ip_address(swapped)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return str(ip), port


def parse_proc_net_tcp(text: str, *, family: str = "tcp") -> tuple[list[dict], list[str]]:
    """Parse /proc/net/tcp or tcp6 content into sockets plus sanitized parse errors."""
    sockets, errors = [], []
    for number, line in enumerate((text or "").splitlines()):
        fields = line.split()
        if not fields or fields[0] == "sl":
            continue
        try:
            local_ip, local_port = _proc_address(fields[1])
            remote_ip, remote_port = _proc_address(fields[2])
            state = _TCP_STATES.get(fields[3].upper(), "OTHER")
        except (IndexError, ValueError):
            errors.append(f"{family}: unparsable line {number}")
            continue
        sockets.append({"local_ip": local_ip, "local_port": local_port, "remote_ip": remote_ip,
                        "remote_port": remote_port, "state": state, "family": family})
    return sockets, errors


def _split_hostport(text: str) -> tuple[str, int]:
    host, _, port = text.rpartition(":")
    host = host.strip("[]").split("%", 1)[0]
    ip = _normalise_address("0.0.0.0" if host == "*" else host)
    return str(ip), 0 if port == "*" else int(port)


def parse_ss(text: str) -> tuple[list[dict], list[str]]:
    """Parse ``ss -ntH`` (State Recv-Q Send-Q Local Peer) output; process columns ignored."""
    sockets, errors = [], []
    for number, line in enumerate((text or "").splitlines()):
        fields = line.split()
        if not fields:
            continue
        try:
            local_ip, local_port = _split_hostport(fields[3])
            remote_ip, remote_port = _split_hostport(fields[4])
        except (IndexError, ValueError):
            errors.append(f"ss: unparsable line {number}")
            continue
        sockets.append({"local_ip": local_ip, "local_port": local_port, "remote_ip": remote_ip,
                        "remote_port": remote_port, "state": _SS_STATES.get(fields[0].upper(), "OTHER"),
                        "family": "ss"})
    return sockets, errors


def _default_radar_reader() -> tuple[list[dict], list[str]]:
    """Read /proc/net/tcp{,6}; fall back to bounded ``ss -ntH``. Never raises."""
    sockets, errors, read_any = [], [], False
    for family in ("tcp", "tcp6"):
        path = Path("/proc/net") / family
        try:
            text = path.read_text(encoding="ascii", errors="replace")
        except OSError:
            errors.append(f"{family}: /proc/net/{family} unreadable")
            continue
        read_any = True
        found, bad = parse_proc_net_tcp(text, family=family)
        sockets += found
        errors += bad
    if read_any:
        return sockets, errors
    import shutil
    import subprocess

    if shutil.which("ss") is None:
        return [], errors + ["ss: command not available"]
    try:
        proc = subprocess.run(["ss", "-ntH"], capture_output=True, text=True, timeout=RADAR_COMMAND_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], errors + [f"ss: {type(exc).__name__}"]
    if proc.returncode != 0:
        return [], errors + [f"ss: exit {proc.returncode}"]
    found, bad = parse_ss(proc.stdout)
    return found, errors + bad


def _is_local(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_unspecified


def radar_scan(*, proxy_events: Iterable[dict] = (), reader: Callable[[], tuple] | None = None,
               samples: int = 1, interval: float = 0.0) -> dict:
    """Detect outbound TCP connections the proxy did not make. Detection only.

    ``proxy_events`` are EgressProxy events; their allowed (ip, port) pairs are
    the proxy's own upstream sockets. ``reader`` returns (sockets, errors) and
    is injected in tests. Never raises for collection problems.
    """
    import time

    if not isinstance(samples, int) or isinstance(samples, bool) or not 1 <= samples <= RADAR_MAX_SAMPLES:
        raise ValueError(f"samples must be an integer from 1 to {RADAR_MAX_SAMPLES}")
    read = reader or _default_radar_reader
    proxied = {(e.get("ip"), e.get("port")) for e in proxy_events or []
               if isinstance(e, dict) and e.get("decision") == "allow"}
    errors: list[str] = []
    seen: dict[tuple, dict] = {}
    observed = 0
    successful = 0
    for index in range(samples):
        try:
            sockets, sample_errors = read()
        except Exception as exc:  # noqa: BLE001 - collection failures are evidence, not crashes
            sockets, sample_errors = [], [f"reader failed: {type(exc).__name__}"]
        errors += [e for e in sample_errors if e not in errors]
        if sockets or not sample_errors:
            successful += 1
        listening = {s["local_port"] for s in sockets if s.get("state") == "LISTEN"}
        for sock in sockets:
            if sock.get("state") not in ("ESTABLISHED", "SYN_SENT"):
                continue
            observed += 1
            remote = (sock["remote_ip"], sock["remote_port"])
            if _is_local(sock["remote_ip"]) or sock["local_port"] in listening or remote in proxied:
                continue
            seen.setdefault(remote, {"ip": remote[0], "port": remote[1], "state": sock["state"],
                                     "family": sock.get("family"), "via": "radar",
                                     "reason": "outbound TCP not opened by the proxy (detected, not blocked)"})
        if interval and index + 1 < samples:
            time.sleep(min(interval, 1.0))
    coverage = "unavailable" if successful == 0 else "partial"
    return {
        "enforces": False,
        "coverage": coverage,
        "samples": samples,
        "observed_connections": observed,
        "bypasses": sorted(seen.values(), key=lambda b: (b["ip"], b["port"])),
        "collection_errors": errors,
        "limitations": list(RADAR_LIMITATIONS),
    }


def _envelope(mode: str, status: str, checks: list, data: dict, errors: list) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "step": "sever",
        "mode": mode,
        "status": status,
        "checks": checks,
        "data": data,
        "errors": errors,
    }


def _validate_inputs(data_map, target, config, max_attempts) -> None:
    if not isinstance(data_map, dict):
        raise ValueError("data_map must be the discover envelope's data dict")
    if not isinstance(target, dict):
        raise ValueError("target must be the choose envelope's data dict")
    if not isinstance(config, dict):
        raise ValueError("config must be a dict")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")


def _load_replacement(replacement_id: str) -> dict | None:
    """Read one replacement catalogue entry (JSON-subset YAML). Called only at run time."""
    try:
        with REPLACEMENTS_PATH.open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    for entry in doc.get("replacements", []):
        if isinstance(entry, dict) and entry.get("id") == replacement_id:
            return entry
    return None


def _telemetry_hosts(data_map: dict) -> list[str]:
    """Hosts of non-S3 calls in the data map (e.g. telemetry), for a realistic stub."""
    hosts = []
    for call in data_map.get("calls", []) or []:
        if isinstance(call, dict) and call.get("service") not in (None, "s3") and call.get("endpoint_host"):
            hosts.append(str(call["endpoint_host"]))
    return hosts


def _stub_record(data_map: dict, max_attempts: int) -> dict:
    host = (_telemetry_hosts(data_map) or ["monitoring.amazonaws.com"])[0]
    replacement = _load_replacement("local-otel")
    applied_keys = list(replacement.get("applied_config_keys", [])) if replacement else []

    attempts = [
        {
            "number": 1,
            "events": [
                {
                    "host": host,
                    "ip": "192.0.2.10",
                    "port": 443,
                    "decision": "deny",
                    "reason": "published cloud range (synthetic fixture)",
                    "via": "proxy",
                }
            ],
            "blocked": 1,
            "bypasses": [],
            "replacement": None,
            "status": "incomplete",
        }
    ]
    if max_attempts >= 2:
        attempts.append(
            {
                "number": 2,
                "events": [
                    {
                        "host": "127.0.0.1",
                        "ip": "127.0.0.1",
                        "port": 4318,
                        "decision": "allow",
                        "reason": "approved local replacement (synthetic)",
                        "via": "proxy",
                    }
                ],
                "blocked": 0,
                "bypasses": [],
                "replacement": {
                    "id": "local-otel",
                    "mode": "replay",
                    "applied_config_keys": applied_keys,
                },
                "status": "incomplete",
            }
        )

    checks = [
        {
            "id": "proxy_denies_cloud_egress",
            "status": "incomplete",
            "detail": "synthetic stub; no proxy started, no VM validation. Scope when run: " + PROXY_SCOPE,
        },
        {
            "id": "radar_bypass_detection",
            "status": "incomplete",
            "detail": "synthetic stub; no socket inspection performed",
        },
        {
            "id": "config_only_replacement_retry",
            "status": "incomplete",
            "detail": "synthetic stub; app not run, replacement not applied",
        },
    ]
    data = {
        "attempts": attempts,
        "max_attempts": max_attempts,
        "final": "incomplete",
        "radar_scope": RADAR_SCOPE,
    }
    errors = [] if replacement else ["replacement catalogue entry 'local-otel' unavailable"]
    return _envelope("stub", "incomplete", checks, data, errors)


# ---------------------------------------------------------------------------
# Replacement catalogue, demo telemetry receiver and bounded retry loop (WS3-05)
# ---------------------------------------------------------------------------

MAX_ATTEMPTS_LIMIT = 5
RECEIVER_MAX_BODY = 1024 * 1024
RADAR_SAMPLE_INTERVAL = 0.2


def load_catalogue(path: Path = REPLACEMENTS_PATH) -> list[dict]:
    """Return validated replacement entries; malformed entries are skipped."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    entries = []
    for entry in doc.get("replacements", []) if isinstance(doc, dict) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            continue
        config = entry.get("config")
        allowed = entry.get("allowed_config_keys")
        if not isinstance(config, dict) or not isinstance(allowed, list) or not set(config) <= set(allowed):
            continue
        if entry.get("code_change") is not False:
            continue
        entries.append(entry)
    return entries


def select_replacement(host: str, catalogue: list[dict]) -> dict | None:
    """Deterministically pick the first catalogue entry whose host pattern matches."""
    from fnmatch import fnmatchcase

    host = (host or "").lower()
    for entry in catalogue:
        for pattern in entry.get("matches", {}).get("hosts", []):
            if isinstance(pattern, str) and fnmatchcase(host, pattern.lower()):
                return entry
    return None


class TelemetryReceiver:
    """Bounded loopback HTTP POST receiver used as the local demo telemetry replacement.

    Counts receipts (path and byte count only; bodies are discarded). Not an
    OpenTelemetry collector and not exposed beyond 127.0.0.1.
    """

    def __init__(self, port: int = 0):
        self.port = port
        self._server = None
        self._thread = None
        self._receipts: list[dict] = []

    def start(self) -> "TelemetryReceiver":
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        receipts = self._receipts

        class Handler(BaseHTTPRequestHandler):
            timeout = PROXY_IO_TIMEOUT

            def do_POST(self):  # noqa: N802 - http.server API
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    length = -1
                if not 0 <= length <= RECEIVER_MAX_BODY:
                    self.send_error(413)
                    return
                self.rfile.read(length)
                receipts.append({"path": self.path.split("?", 1)[0], "bytes": length})
                body = b"{}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):  # keep stdout clean
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.1},
                                        name="skyshift-telemetry-receiver", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def __enter__(self) -> "TelemetryReceiver":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def receipts(self) -> list[dict]:
        return list(self._receipts)


def _proposal_schema(entry: dict, catalogue: list[dict]) -> dict:
    return {
        "type": "object",
        "required": ["replacement_id", "rationale", "config_keys"],
        "properties": {
            "replacement_id": {"type": "string", "enum": [e["id"] for e in catalogue]},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 2000},
            "config_keys": {"type": "array", "minItems": 1, "maxItems": 10,
                            "items": {"type": "string", "enum": list(entry["allowed_config_keys"])}},
        },
    }


def _propose(entry: dict, blocked_hosts: list[str], catalogue: list[dict], proposer, config: dict) -> dict:
    """Ask the single LLM client for an explanation; deterministic choice stays authoritative."""
    record = {"id": entry["id"], "mode": "deterministic", "applied_config_keys": list(entry["config"]),
              "proposal_status": "not_requested", "explanation": None}
    if proposer is None:
        return record
    payload = {"blocked_hosts": sorted(set(blocked_hosts))[:10], "candidates": [e["id"] for e in catalogue]}
    try:
        result = proposer("replacement_proposal", payload, _proposal_schema(entry, catalogue), config=config)
    except Exception as exc:  # noqa: BLE001 - proposals are advisory
        record["proposal_status"] = f"incomplete ({type(exc).__name__})"
        return record
    data = result.get("data") if isinstance(result, dict) else None
    record["mode"] = result.get("mode", "replay") if isinstance(result, dict) else "replay"
    if not isinstance(data, dict) or not data:
        record["proposal_status"] = "incomplete"
        return record
    agrees = data.get("replacement_id") == entry["id"] and set(data.get("config_keys", [])) <= set(entry["allowed_config_keys"])
    record["proposal_status"] = "agrees" if agrees else "disagrees (deterministic selection kept)"
    record["explanation"] = str(data.get("rationale", ""))[:500] if agrees else None
    return record


class _RadarSampler:
    """Collect radar snapshots in the background while the app runs (bounded)."""

    def __init__(self, reader):
        import threading

        # Live (default reader) only: sockets already established before the attempt
        # (operator SSH, model tunnel) are excluded and counted, not reported as bypasses.
        self.use_baseline = reader is None
        self.reader = reader or _default_radar_reader
        self.samples: list[tuple] = []
        self.baseline: set = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="skyshift-radar")

    def _take(self):
        if len(self.samples) >= RADAR_MAX_SAMPLES:
            return
        try:
            self.samples.append(self.reader())
        except Exception as exc:  # noqa: BLE001
            self.samples.append(([], [f"reader failed: {type(exc).__name__}"]))

    def _run(self):
        while not self._stop.is_set():
            self._take()
            self._stop.wait(RADAR_SAMPLE_INTERVAL)

    def __enter__(self):
        if self.use_baseline:
            try:
                sockets, _errors = self.reader()
                self.baseline = {(x.get("local_port"), x.get("remote_ip"), x.get("remote_port"))
                                 for x in sockets if x.get("state") in ("ESTABLISHED", "SYN_SENT")}
            except Exception:  # noqa: BLE001 - no baseline means nothing is excluded
                self.baseline = set()
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._take()

    def result(self, proxy_events: list[dict]) -> dict:
        samples = self.samples[:RADAR_MAX_SAMPLES] or [([], ["no radar sample collected"])]
        excluded = set()
        if self.baseline:
            filtered = []
            for sockets, errors in samples:
                keep = []
                for x in sockets:
                    key = (x.get("local_port"), x.get("remote_ip"), x.get("remote_port"))
                    if key in self.baseline:
                        excluded.add(key)
                    else:
                        keep.append(x)
                filtered.append((keep, errors))
            samples = filtered
        replay = iter(samples)
        result = radar_scan(proxy_events=proxy_events, reader=lambda: next(replay), samples=len(samples))
        result["preexisting_excluded"] = len(excluded)
        return result


def _run_attempt(number: int, attempt_config: dict, replacement: dict | None, *, app_runner, ranges,
                 resolver, connector, clock, radar_reader, receiver_port: int | None) -> tuple[dict, dict]:
    """One bounded attempt: proxy + optional receiver + radar around a single app run."""
    receiver = TelemetryReceiver(receiver_port).start() if receiver_port is not None else None
    try:
        config = dict(attempt_config)
        if receiver is not None:
            config["SKYSHIFT_TELEMETRY_ENDPOINT"] = receiver.endpoint
        allowlist = allowlist_from_config(config)
        with EgressProxy(allowlist=allowlist, ranges=ranges, resolver=resolver,
                         connector=connector, clock=clock) as proxy:
            env = {**config, "HTTPS_PROXY": proxy.url, "HTTP_PROXY": proxy.url, "NO_PROXY": ""}
            with _RadarSampler(radar_reader) as sampler:
                try:
                    app = app_runner(env)
                    app_ok = app.get("ok") if isinstance(app, dict) else None
                    app_detail = str(app.get("detail", ""))[:300] if isinstance(app, dict) else "invalid runner result"
                except Exception as exc:  # noqa: BLE001 - runner failure is evidence, not a crash
                    app_ok, app_detail = None, f"app runner failed: {type(exc).__name__}"
            events = proxy.events
        radar = sampler.result(events)
        receipts = receiver.receipts if receiver is not None else []
    finally:
        if receiver is not None:
            receiver.stop()

    denied = [e for e in events if e["decision"] == "deny"]
    reasons = []
    if denied:
        reasons.append(f"{len(denied)} destination(s) denied by proxy")
    if radar["bypasses"]:
        reasons.append(f"{len(radar['bypasses'])} radar bypass candidate(s)")
    if app_ok is False:
        reasons.append("app functional check failed")
    if receiver is not None and not receipts:
        reasons.append("replacement receiver got no telemetry")
    if reasons:
        status = "FAIL"
    elif app_ok is None or radar["coverage"] == "unavailable":
        status = "incomplete"
    else:
        status = "PASS"
    attempt = {
        "number": number,
        "events": events,
        "blocked": len(denied),
        "bypasses": radar["bypasses"],
        "replacement": replacement,
        "status": status,
        "app": {"ok": app_ok, "detail": app_detail},
        "receiver_receipts": len(receipts),
        "radar_coverage": radar["coverage"],
        "notes": reasons,
    }
    return attempt, radar


def run_severance(data_map: dict, target: dict, *, config: dict, app_runner: Callable[[dict], dict],
                  max_attempts: int = 2, ranges: RangeSet | None = None, resolver=None, connector=None,
                  clock=None, radar_reader=None, proposer=None, catalogue: list[dict] | None = None,
                  receiver_port: int = 0) -> dict:
    """Bounded red -> config-only fix -> retry loop. Deterministic code owns every check.

    ``app_runner(env) -> {"ok": bool|None, "detail": str}`` runs the unchanged
    app once with the given environment (WS2 ``run_app`` at WS3-07; injected in
    tests). Every attempt is preserved; the first denial is never erased.
    """
    _validate_inputs(data_map, target, config, max_attempts)
    if max_attempts > MAX_ATTEMPTS_LIMIT:
        raise ValueError(f"max_attempts must be at most {MAX_ATTEMPTS_LIMIT}")
    if not callable(app_runner):
        raise ValueError("app_runner must be callable")
    ranges = ranges if ranges is not None else load_ranges()
    catalogue = load_catalogue() if catalogue is None else catalogue
    allowed_keys = {k for e in catalogue for k in e["allowed_config_keys"]}

    attempt_config = {k: v for k, v in config.items() if isinstance(v, str)}
    replacement, use_receiver = None, False
    attempts, manual, radars = [], [], []
    for number in range(1, max_attempts + 1):
        attempt, radar = _run_attempt(number, attempt_config, replacement, app_runner=app_runner, ranges=ranges,
                                      resolver=resolver, connector=connector, clock=clock,
                                      radar_reader=radar_reader,
                                      receiver_port=receiver_port if use_receiver else None)
        attempts.append(attempt)
        radars.append(radar)
        if attempt["status"] != "FAIL":
            break
        denied_hosts = [e["host"] for e in attempt["events"] if e["decision"] == "deny"]
        if not denied_hosts or attempt["bypasses"]:
            break  # nothing a proxy-side config-only replacement can fix
        matches = {h: select_replacement(h, catalogue) for h in denied_hosts}
        entry = next((m for m in matches.values() if m is not None), None)
        for host in sorted(h for h, m in matches.items() if m is None):
            note = f"no catalogued replacement for {host}; manual remediation required"
            if note not in manual:
                manual.append(note)
        unknown = [h for h, m in matches.items() if m is None]
        if entry is None or unknown or (replacement is not None and replacement["id"] == entry["id"]):
            break  # unknown dependency or the same fix already failed
        if number == max_attempts:
            manual.append(f"replacement {entry['id']} available but attempts exhausted")
            break
        if not set(entry["config"]) <= allowed_keys:
            manual.append(f"replacement {entry['id']} uses keys outside the catalogue allowlist")
            break
        replacement = _propose(entry, denied_hosts, catalogue, proposer, config)
        use_receiver = entry.get("protocol") == "http-post" and "SKYSHIFT_TELEMETRY_ENDPOINT" in entry["config"]
        if not use_receiver:
            manual.append(f"replacement {entry['id']} protocol {entry.get('protocol')!r} has no local demo receiver")
            break

    last = attempts[-1]
    final = {"PASS": "green", "FAIL": "blocked"}.get(last["status"], "incomplete")
    cloud_denials = [e for a in attempts for e in a["events"]
                     if e["decision"] == "deny" and e["reason"].startswith("published cloud range")]
    last_radar = radars[-1]
    checks = [
        {"id": "proxy_denies_cloud_egress",
         "status": "PASS" if cloud_denials else "incomplete",
         "detail": (f"{len(cloud_denials)} cloud-range request(s) denied and logged" if cloud_denials
                    else "no cloud-range destination was attempted; denial not demonstrated") + ". " + PROXY_SCOPE},
        {"id": "radar_bypass_detection",
         "status": {"unavailable": "incomplete"}.get(last_radar["coverage"], "FAIL" if last_radar["bypasses"] else "PASS"),
         "detail": f"final attempt: {len(last_radar['bypasses'])} bypass candidate(s), coverage "
                   f"{last_radar['coverage']}; detection only, never enforcement"},
        {"id": "config_only_replacement_retry",
         "status": {"green": "PASS", "blocked": "FAIL"}.get(final, "incomplete"),
         "detail": f"final {final} after {len(attempts)} of {max_attempts} attempt(s); app code unchanged, "
                   "config-only remediation; earlier attempts preserved"},
    ]
    statuses = {c["status"] for c in checks}
    status = "FAIL" if "FAIL" in statuses else ("PASS" if statuses == {"PASS"} else "incomplete")
    data = {"attempts": attempts, "max_attempts": max_attempts, "final": final, "radar_scope": RADAR_SCOPE,
            "manual": manual, "radar_limitations": list(RADAR_LIMITATIONS),
            "runner": getattr(app_runner, "label", getattr(app_runner, "__name__", "app_runner"))}
    errors = sorted({e for r in radars for e in r["collection_errors"]})
    return _envelope("live", status, checks, data, errors)


def sever(data_map: dict, target: dict, *, config: dict, max_attempts: int = 2, stub: bool = False) -> dict:
    """Return the severance envelope.

    ``data_map`` and ``target`` are the ``data`` objects of the discover and
    choose envelopes. Secrets in ``config`` are never read into the record.
    """
    _validate_inputs(data_map, target, config, max_attempts)
    if stub:
        return _stub_record(data_map, max_attempts)

    needed = ("SKYSHIFT_TARGET_ENDPOINT_URL", "SKYSHIFT_TARGET_ACCESS_KEY_ID",
              "SKYSHIFT_TARGET_SECRET_ACCESS_KEY", "SKYSHIFT_TARGET_BUCKET")
    missing = [k for k in needed if not (isinstance(config.get(k), str) and config.get(k))]
    if missing or not FIXTURE_APP.is_file():
        reason = ("missing configuration: " + ", ".join(missing)) if missing else "fixture app not found"
        checks = [
            {"id": "proxy_denies_cloud_egress", "status": "incomplete",
             "detail": f"live severance not run ({reason}); nothing measured. Scope when run: " + PROXY_SCOPE},
            {"id": "radar_bypass_detection", "status": "incomplete",
             "detail": f"live severance not run ({reason}); nothing measured. Detection only, never enforcement"},
            {"id": "config_only_replacement_retry", "status": "incomplete",
             "detail": f"live severance not run ({reason}); no retry attempted"},
        ]
        data = {"attempts": [], "max_attempts": max_attempts, "final": "incomplete", "radar_scope": RADAR_SCOPE}
        return _envelope("live", "incomplete", checks, data, [f"live severance not run: {reason}; nothing was measured"])
    ranges = live_ranges()
    runner = fixture_app_runner(config)
    record = run_severance(data_map, target, config=_severance_config(config), app_runner=runner,
                           max_attempts=max_attempts, ranges=ranges)
    record["data"]["range_sources"] = {
        p: {"source": "synthetic fixture" if src.get("synthetic") else src.get("source_url"),
            "retrieved_at": src.get("retrieved_at")}
        for p, src in sorted(ranges.sources.items())
    }
    _redact_target_events(record, config)
    record["data"]["app_sha256_before"] = runner.hash_before
    record["data"]["app_sha256_after"] = _sha256_file(runner.app_path)
    if record["data"]["app_sha256_after"] != runner.hash_before:
        record["status"] = "FAIL"
        record["errors"].append("fixture app bytes changed during severance")
    record["errors"].extend(ranges.errors)
    return record


# ---------------------------------------------------------------------------
# Live wiring (WS3-07): published ranges + unchanged fixture app runner.
# ---------------------------------------------------------------------------

FIXTURE_APP = Path(__file__).resolve().parents[1] / "fixtures" / "aws_workload" / "app.py"
APP_TIMEOUT_SECONDS = 90


def live_ranges() -> RangeSet:
    """AWS/Google/Cloudflare from their published feeds; Azure (no stable feed URL) from the fixture, labelled synthetic."""
    ranges = RangeSet()
    for provider in ("aws", "google", "cloudflare"):
        ranges = ranges.merge(load_published_feed(provider, approved_urls=PUBLISHED_FEEDS[provider]))
    fixture = load_ranges()
    azure = RangeSet(entries=[e for e in fixture.entries if e.provider == "azure"],
                     sources={k: v for k, v in fixture.sources.items() if k == "azure"})
    return ranges.merge(azure)


def _redact_target_events(record: dict, config: dict) -> None:
    """Replace approved target/telemetry hosts and their addresses with labels (stage-safe output)."""
    labels = {}
    for key, label in (("SKYSHIFT_TARGET_ENDPOINT_URL", "approved-target-s3"), ("AWS_ENDPOINT_URL", "approved-target-s3")):
        endpoint = _endpoint(config.get(key) or "") if isinstance(config.get(key), str) else None
        if endpoint:
            labels[endpoint[0]] = label
    for attempt in record.get("data", {}).get("attempts", []):
        for event in attempt.get("events", []):
            if event.get("host") in labels:
                event["host"] = labels[event["host"]]
                event["ip"] = None
            elif event.get("decision") == "allow" and event.get("ip"):
                try:
                    if not ipaddress.ip_address(event["ip"]).is_loopback:
                        event["ip"] = None
                except ValueError:
                    event["ip"] = None
        for bypass in attempt.get("bypasses", []):
            bypass["ip"] = "redacted"


def _sha256_file(path: Path) -> str | None:
    import hashlib

    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _severance_config(config: dict) -> dict:
    """Map contract target settings onto the unchanged app's AWS_* names (config only)."""
    out = {k: v for k, v in config.items() if isinstance(v, str)}
    mapping = {"AWS_ENDPOINT_URL": "SKYSHIFT_TARGET_ENDPOINT_URL", "AWS_ACCESS_KEY_ID": "SKYSHIFT_TARGET_ACCESS_KEY_ID",
               "AWS_SECRET_ACCESS_KEY": "SKYSHIFT_TARGET_SECRET_ACCESS_KEY"}
    for app_key, target_key in mapping.items():
        if config.get(target_key):
            out[app_key] = config[target_key]
    out.pop("SKYSHIFT_TELEMETRY_ENDPOINT", None)  # first attempt uses the app's default (AWS) telemetry
    return out


def fixture_app_runner(config: dict, app_path: Path = FIXTURE_APP):
    """Runner that executes the unchanged fixture app once per attempt in a bounded subprocess.

    Direct runner used until WS2-04 ``run_app`` exposes a per-attempt env hook; the label says so.
    """
    import subprocess
    import sys

    hash_before = _sha256_file(app_path)
    passthrough = ("PATH", "HOME", "SYSTEMROOT", "TMPDIR", "LANG")

    def runner(env: dict) -> dict:
        import os

        child = {k: os.environ[k] for k in passthrough if k in os.environ}
        child.update({k: v for k, v in env.items() if k.startswith(("AWS_", "SKYSHIFT_TARGET_BUCKET",
                                                                     "SKYSHIFT_TELEMETRY_", "HTTP", "NO_PROXY"))})
        child["NO_PROXY"] = ""
        try:
            proc = subprocess.run([sys.executable, str(app_path), "--require-telemetry"], env=child,
                                  capture_output=True, timeout=APP_TIMEOUT_SECONDS, shell=False)
        except subprocess.TimeoutExpired:
            return {"ok": False, "detail": f"app timed out after {APP_TIMEOUT_SECONDS}s"}
        detail = f"unchanged app exit {proc.returncode}"
        try:
            result = json.loads(proc.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
            tel = result.get("telemetry", {}) if isinstance(result, dict) else {}
            detail += f"; s3 checks {'PASS' if result.get('status') == 'PASS' or proc.returncode == 0 else 'see telemetry'}"                       f"; telemetry {tel.get('status')}"
        except Exception:  # noqa: BLE001 - output shape is informational only
            pass
        return {"ok": proc.returncode == 0, "detail": detail[:300]}

    runner.label = "direct unchanged-app subprocess (fixtures/aws_workload/app.py --require-telemetry)"
    runner.hash_before = hash_before
    runner.app_path = app_path
    return runner
