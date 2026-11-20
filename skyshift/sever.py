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
RADAR_SCOPE = "socket detection only; proxy enforces requests using it"


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
            "detail": "synthetic stub; no proxy started, no VM validation",
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


def sever(data_map: dict, target: dict, *, config: dict, max_attempts: int = 2, stub: bool = False) -> dict:
    """Return the severance envelope.

    ``data_map`` and ``target`` are the ``data`` objects of the discover and
    choose envelopes. Secrets in ``config`` are never read into the record.
    """
    _validate_inputs(data_map, target, config, max_attempts)
    if stub:
        return _stub_record(data_map, max_attempts)

    checks = [
        {
            "id": "proxy_denies_cloud_egress",
            "status": "incomplete",
            "detail": "not implemented (WS3-03); no proxy started",
        },
        {
            "id": "radar_bypass_detection",
            "status": "incomplete",
            "detail": "not implemented (WS3-04); no socket inspection performed",
        },
        {
            "id": "config_only_replacement_retry",
            "status": "incomplete",
            "detail": "not implemented (WS3-05); no retry attempted",
        },
    ]
    data = {"attempts": [], "max_attempts": max_attempts, "final": "incomplete", "radar_scope": RADAR_SCOPE}
    return _envelope("live", "incomplete", checks, data, ["live severance not implemented yet; nothing was measured"])
