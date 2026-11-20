"""Discover AWS dependencies and choose a Leaseweb target (WS1).

Contract: tasks/contracts.md (Python API, shared envelope, data map, target choice).
Importing this module performs no I/O, network or service start, and imports only the
standard library. Optional dependencies (python-hcl2, PyYAML, boto3) are imported lazily
on the live path only; the ``stub=True`` path never touches them.

discover (live, WS1-02): parses workload ``*.tf`` with python-hcl2 (no evaluation),
scans ``*.py`` with ``ast`` (never executed), lists source buckets read-only with
paginated ``list_objects_v2`` and computes the v1 readiness score deterministically.
choose (live, WS1-03): deterministic Leaseweb selection from targets.yaml, the human VM
gate record (tasks/WS0-setup/validation.md) and SKYSHIFT_TARGET_PROVIDER; prices stay null.
No stub ever reports PASS.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1

READINESS_FORMULA = "max(0, 100 - 20*proprietary - 10*unsupported - 5*us_calls)"

CATALOGUE_PATH = Path(__file__).resolve().parent / "catalogue" / "resources.yaml"

# Used by the offline stub only; the live path reads catalogue/resources.yaml.
SUPPORTED_RESOURCE_TYPES = frozenset({"aws_instance", "aws_security_group", "aws_s3_bucket"})
SUPPORTED_S3_OPERATIONS = frozenset(
    {
        "put_object",
        "get_object",
        "list_objects_v2",
        "head_object",
        "delete_object",
        "create_multipart_upload",
        "upload_part",
        "complete_multipart_upload",
        "generate_presigned_url",
    }
)

# Hosts operated by US-controlled hyperscalers/CDNs (suffix match). A European region
# of these operators is still US-controlled.
US_CONTROLLED_SUFFIXES = (
    "amazonaws.com",
    "amazon.com",
    "aws.amazon.com",
    "cloudfront.net",
    "googleapis.com",
    "google.com",
    "azure.com",
    "windows.net",
    "microsoft.com",
    "cloudflare.com",
)

# Attribute names never copied from HCL into records.
SENSITIVE_ATTRIBUTE = re.compile(
    r"(user_data|password|secret|token|access_key|private_key|credentials?)", re.IGNORECASE
)
RESOURCE_REF = re.compile(r"\b((?:aws|google|azurerm)_[a-z0-9_]+)\.([A-Za-z0-9_-]+)")
URL_LITERAL = re.compile(r"https?://[^\s\"'<>]+")
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "request"})

DATA_MAP_KEYS = ("resources", "calls", "buckets", "readiness")
CHOICE_KEYS = (
    "target_id",
    "operator",
    "jurisdiction",
    "storage_mode",
    "criteria",
    "prices",
    "explanation",
)


def _envelope(step: str, mode: str, status: str, checks: list, data: dict, errors: list) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "step": step,
        "mode": mode,
        "status": status,
        "checks": checks,
        "data": data,
        "errors": errors,
    }


def _check_config(config: object) -> None:
    if not isinstance(config, dict):
        raise ValueError("config must be a dict of environment names to values")


def _overall(checks: list[dict]) -> str:
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        return "FAIL"
    if statuses and all(s == "PASS" for s in statuses):
        return "PASS"
    return "incomplete"


def is_us_controlled(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower().rstrip(".")
    return any(host == s or host.endswith("." + s) for s in US_CONTROLLED_SUFFIXES)


def _dedupe_calls(calls: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique = []
    for call in calls:
        key = (call["file"], call["line"], call["service"], call["operation"])
        if key not in seen:
            seen.add(key)
            unique.append(call)
    return unique


def compute_readiness(resources: list[dict], calls: list[dict],
                      supported_s3_ops: frozenset | set = SUPPORTED_S3_OPERATIONS) -> dict:
    """Deterministic readiness score v1 (no AI).

    proprietary: resource instances that are unsupported or proprietary.
    unsupported: distinct S3 operation names outside the supported set.
    us_calls: deduplicated non-S3 calls whose literal/resolved host is US-controlled
    (S3 calls are the migrated surface, rewired by endpoint configuration).
    """
    unique_calls = _dedupe_calls(calls)
    proprietary = sum(1 for r in resources if not r["supported"] or r.get("proprietary"))
    unsupported = len({
        c["operation"] for c in unique_calls
        if c["service"] == "s3" and c.get("interface", "client") == "client"
        and c["operation"] not in supported_s3_ops
    })
    us_calls = sum(1 for c in unique_calls if c["service"] != "s3" and c.get("us_controlled",
                   is_us_controlled(c.get("endpoint_host"))))
    score = max(0, 100 - 20 * proprietary - 10 * unsupported - 5 * us_calls)
    return {
        "score": score,
        "formula": READINESS_FORMULA,
        "proprietary": proprietary,
        "unsupported": unsupported,
        "us_calls": us_calls,
    }


# --------------------------------------------------------------------------- stub


def _stub_data_map(workload: Path) -> dict:
    app_file = (workload / "app.py").as_posix()
    resources = [
        {"id": "aws_instance.app", "type": "aws_instance", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_security_group.app", "type": "aws_security_group", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_s3_bucket.demo", "type": "aws_s3_bucket", "provider": "aws",
         "region": "eu-central-1", "synthetic": True},
        {"id": "aws_cloudwatch_metric_alarm.app_errors", "type": "aws_cloudwatch_metric_alarm",
         "provider": "aws", "region": "eu-central-1", "synthetic": True},
    ]
    for resource in resources:
        resource["supported"] = resource["type"] in SUPPORTED_RESOURCE_TYPES

    calls = [
        {"file": app_file, "line": 18, "service": "s3", "operation": "put_object",
         "bucket": "demo", "endpoint_host": None},
        {"file": app_file, "line": 24, "service": "s3", "operation": "get_object",
         "bucket": "demo", "endpoint_host": None},
        {"file": app_file, "line": 31, "service": "s3", "operation": "list_objects_v2",
         "bucket": "demo", "endpoint_host": None},
        # Visible telemetry dependency on an AWS-operated endpoint (severance target in WS3).
        {"file": app_file, "line": 40, "service": "cloudwatch", "operation": "put_metric_data",
         "bucket": None, "endpoint_host": "monitoring.eu-central-1.amazonaws.com",
         "dependency": "telemetry"},
    ]
    buckets = [
        {"name": "demo", "provider": "aws", "jurisdiction": "US-controlled",
         "object_count": 12, "total_bytes": 48213, "synthetic": True},
    ]
    return {
        "resources": resources,
        "calls": calls,
        "buckets": buckets,
        "readiness": compute_readiness(resources, calls),
    }


# --------------------------------------------------------------------------- catalogue


def load_catalogue(path: Path = CATALOGUE_PATH) -> dict:
    """Load and validate resources.yaml (requires PyYAML)."""
    import yaml  # optional dependency, live path only

    with open(path, encoding="utf-8") as handle:
        catalogue = yaml.safe_load(handle)
    if not isinstance(catalogue, dict) or catalogue.get("schema_version") != 1:
        raise ValueError("resources.yaml must have schema_version: 1")
    resources = catalogue.get("resources")
    s3_ops = catalogue.get("s3_operations")
    if not isinstance(resources, dict) or not isinstance(s3_ops, dict):
        raise ValueError("resources.yaml needs resources and s3_operations mappings")
    for rtype, entry in resources.items():
        if not isinstance(entry, dict) or not {"supported", "proprietary", "target_kind",
                                               "template"} <= set(entry):
            raise ValueError(f"resources.yaml entry {rtype} is incomplete")
    return catalogue


def _catalogue_entry(catalogue: dict, rtype: str) -> dict:
    entry = catalogue["resources"].get(rtype)
    if entry is None:
        return {"supported": False, "proprietary": True, "target_kind": None, "template": None,
                "catalogued": False}
    return {**entry, "catalogued": True}


# --------------------------------------------------------------------------- HCL


def _hcl_label(label: str) -> str:
    return label[1:-1] if len(label) >= 2 and label[0] == label[-1] == '"' else label


def _hcl_value(value):
    """Normalise python-hcl2 output (v4 unquoted and v7+/v8 quoted literals).

    Returns (value, unresolved_expressions).
    """
    if isinstance(value, str):
        if "${" in value:
            return {"unresolved": True, "expression": value}, [value]
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1].replace('\\"', '"').replace("\\\\", "\\"), []
        return value, []
    if isinstance(value, list):
        out, unresolved = [], []
        for item in value:
            v, u = _hcl_value(item)
            out.append(v)
            unresolved += u
        return out, unresolved
    if isinstance(value, dict):
        out, unresolved = {}, []
        for key, item in value.items():
            if key.startswith("__"):
                continue
            v, u = _hcl_value(item)
            out[_hcl_label(key)] = v
            unresolved += u
        return out, unresolved
    return value, []


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)


def _iter_tf_files(workload: Path) -> list[Path]:
    return sorted(
        (p for p in workload.rglob("*.tf")
         if not any(part.startswith(".") for part in p.relative_to(workload).parts)),
        key=lambda p: p.relative_to(workload).as_posix(),
    )


def _iter_py_files(workload: Path) -> list[Path]:
    skip = {"__pycache__", "venv", ".venv", "node_modules"}
    return sorted(
        (p for p in workload.rglob("*.py")
         if not any(part.startswith(".") or part in skip
                    for part in p.relative_to(workload).parts)),
        key=lambda p: p.relative_to(workload).as_posix(),
    )


def _display_path(path: Path, workload: Path, workload_display: str) -> str:
    rel = path.relative_to(workload).as_posix()
    return f"{workload_display}/{rel}" if workload_display not in ("", ".") else rel


VAR_ONLY = re.compile(r"\$\{var\.([A-Za-z_][A-Za-z0-9_]*)\}")


def _variable_defaults(docs: list) -> dict:
    """Literal (non-expression) variable defaults declared in the workload."""
    defaults: dict = {}
    for _display, doc in docs:
        for block in doc.get("variable", []):
            for name, body in block.items():
                if isinstance(body, dict) and "default" in body:
                    value, unresolved = _hcl_value(body["default"])
                    if not unresolved and isinstance(value, (str, int, float, bool)):
                        defaults[_hcl_label(name)] = value
    return defaults


def _resolvable(expr: str, var_defaults: dict) -> bool:
    """True when the expression only interpolates variables with literal defaults."""
    names = VAR_ONLY.findall(expr)
    rest = VAR_ONLY.sub("", expr)
    return bool(names) and "${" not in rest and "%{" not in rest and all(
        n in var_defaults for n in names)


def parse_hcl(workload: Path, catalogue: dict, workload_display: str) -> tuple[list, list]:
    """Return (resources, findings). Malformed HCL raises ValueError."""
    import hcl2  # optional dependency, live path only

    resources: list[dict] = []
    findings: list[dict] = []
    docs = []
    for tf in _iter_tf_files(workload):
        display = _display_path(tf, workload, workload_display)
        try:
            with open(tf, encoding="utf-8") as handle:
                docs.append((display, hcl2.load(handle)))
        except Exception as exc:  # lark/hcl2 raise several exception types
            raise ValueError(f"invalid HCL in {display}: {type(exc).__name__}") from None
    var_defaults = _variable_defaults(docs)
    for display, doc in docs:

        provider_regions: dict[str, object] = {}
        for block in doc.get("provider", []):
            for name, body in block.items():
                pname = _hcl_label(name)
                region, unresolved = _hcl_value(body.get("region")) if isinstance(body, dict) \
                    else (None, [])
                if pname not in provider_regions:
                    provider_regions[pname] = None if unresolved else region
                if unresolved:
                    findings.append({"file": display, "kind": "unresolved_expression",
                                     "detail": f"provider {pname} region is an expression"})

        for block in doc.get("resource", []):
            for rtype_raw, named in block.items():
                rtype = _hcl_label(rtype_raw)
                for name_raw, body in named.items():
                    name = _hcl_label(name_raw)
                    rid = f"{rtype}.{name}"
                    attrs, unresolved = {}, []
                    for key, value in (body or {}).items():
                        if key.startswith("__"):
                            continue
                        if SENSITIVE_ATTRIBUTE.search(key):
                            attrs[key] = {"redacted": True}
                            continue
                        v, u = _hcl_value(value)
                        attrs[key] = v
                        unresolved += u
                    refs = sorted({f"{m.group(1)}.{m.group(2)}"
                                   for expr in unresolved
                                   for m in RESOURCE_REF.finditer(expr)} - {rid})
                    provider = rtype.split("_", 1)[0]
                    region = provider_regions.get(provider)
                    entry = _catalogue_entry(catalogue, rtype)
                    record = {
                        "id": rid,
                        "type": rtype,
                        "provider": provider,
                        "region": region,
                        "supported": bool(entry["supported"]),
                        "proprietary": bool(entry["proprietary"]),
                        "catalogued": entry["catalogued"],
                        "target_kind": entry["target_kind"],
                        "template": entry["template"],
                        "file": display,
                        "references": refs,
                        "attributes": attrs,
                        "unresolved": len(unresolved),
                    }
                    resources.append(record)
                    if region is None:
                        findings.append({"file": display, "kind": "unresolved_region",
                                         "detail": f"{rid}: no literal provider region"})
                    for expr in unresolved:
                        if not RESOURCE_REF.search(expr) and not _resolvable(expr, var_defaults):
                            findings.append({"file": display, "kind": "unresolved_expression",
                                             "detail": f"{rid}: expression not evaluated"})
                            break
    return resources, findings


# --------------------------------------------------------------------------- Python


def _literal_str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _kwarg(call: ast.Call, name: str):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return None
    return host.lower() if host else None


class _CallScanner(ast.NodeVisitor):
    """Static boto3/requests scanner; never executes the scanned code."""

    def __init__(self, display: str):
        self.display = display
        self.boto3_names: set[str] = set()         # aliases of the boto3 module
        self.factory_names: dict[str, str] = {}     # from boto3 import client as c -> "client"
        self.requests_names: set[str] = set()
        self.http_funcs: dict[str, str] = {}        # from requests import post as p
        self.clients: dict[str, dict] = {}          # expr -> {service, endpoint_host, interface}
        self.calls: list[dict] = []
        self.findings: list[dict] = []
        self.seen_hosts: set[str] = set()

    # imports -----------------------------------------------------------------
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "boto3":
                self.boto3_names.add(alias.asname or "boto3")
            elif alias.name == "requests":
                self.requests_names.add(alias.asname or "requests")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "boto3":
            for alias in node.names:
                if alias.name in ("client", "resource"):
                    self.factory_names[alias.asname or alias.name] = alias.name
        elif node.module == "requests":
            for alias in node.names:
                if alias.name in HTTP_METHODS:
                    self.http_funcs[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    # client construction ----------------------------------------------------
    def _factory(self, call: ast.Call) -> str | None:
        func = call.func
        if isinstance(func, ast.Attribute) and func.attr in ("client", "resource"):
            base = func.value
            if isinstance(base, ast.Name) and base.id in self.boto3_names:
                return func.attr
            # boto3.session.Session(...).client / boto3.Session(...).client
            if isinstance(base, ast.Call):
                inner = ast.unparse(base.func)
                if any(inner in (f"{b}.Session", f"{b}.session.Session")
                       for b in self.boto3_names):
                    return func.attr
        if isinstance(func, ast.Name) and func.id in self.factory_names:
            return self.factory_names[func.id]
        return None

    def _client_info(self, call: ast.Call) -> dict | None:
        kind = self._factory(call)
        if kind is None:
            return None
        service_node = call.args[0] if call.args else _kwarg(call, "service_name")
        service = _literal_str(service_node)
        endpoint_node = _kwarg(call, "endpoint_url")
        endpoint_host, endpoint_state = None, "sdk_default"
        if endpoint_node is not None:
            literal = _literal_str(endpoint_node)
            endpoint_host = _host(literal) if literal else None
            endpoint_state = "literal" if literal else "unresolved"
            if endpoint_host:
                self.seen_hosts.add(endpoint_host)
        if service is None:
            self.findings.append({"file": self.display, "line": call.lineno,
                                  "kind": "dynamic_service",
                                  "detail": "boto3 service name is not a literal"})
        return {"service": service, "endpoint_host": endpoint_host,
                "endpoint_state": endpoint_state, "interface": kind}

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call):
            info = self._client_info(node.value)
            if info and info["service"]:
                for target in node.targets:
                    self.clients[ast.unparse(target)] = info
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.value, ast.Call):
            info = self._client_info(node.value)
            if info and info["service"]:
                self.clients[ast.unparse(node.target)] = info
        self.generic_visit(node)

    # calls ------------------------------------------------------------------
    def _record(self, line: int, info: dict, operation: str, bucket, host, **extra):
        call = {
            "file": self.display,
            "line": line,
            "service": info["service"],
            "operation": operation,
            "bucket": bucket,
            "endpoint_host": host,
            "interface": info.get("interface", "client"),
            "endpoint_state": info.get("endpoint_state"),
        }
        call.update(extra)
        self.calls.append(call)

    def _http_call(self, node: ast.Call, method: str):
        url_node = node.args[0] if node.args else _kwarg(node, "url")
        if method == "request":
            url_node = node.args[1] if len(node.args) > 1 else _kwarg(node, "url")
        url = _literal_str(url_node) if url_node is not None else None
        host = _host(url)
        if host is None:
            self.findings.append({"file": self.display, "line": node.lineno,
                                  "kind": "unresolved_endpoint",
                                  "detail": f"requests.{method} URL is not a literal"})
        else:
            self.seen_hosts.add(host)
        self._record(node.lineno, {"service": "http", "interface": "requests",
                                   "endpoint_state": "literal" if host else "unresolved"},
                     method, None, host, us_controlled=is_us_controlled(host))

    def visit_Call(self, node):
        func = node.func
        # getattr(client, name)(...) dynamic dispatch
        if (isinstance(func, ast.Call) and isinstance(func.func, ast.Name)
                and func.func.id == "getattr" and func.args
                and ast.unparse(func.args[0]) in self.clients):
            self.findings.append({"file": self.display, "line": node.lineno,
                                  "kind": "dynamic_dispatch",
                                  "detail": "getattr on an AWS client; operation unknown"})
        elif isinstance(func, ast.Attribute):
            owner = ast.unparse(func.value)
            info = self.clients.get(owner)
            if info is None and isinstance(func.value, ast.Call):
                info = self._client_info(func.value)   # chained boto3.client("s3").op()
                if info is not None and not info["service"]:
                    info = None
            if info is not None:
                bucket = _literal_str(_kwarg(node, "Bucket"))
                if info["interface"] == "resource" and node.args:
                    bucket = bucket or _literal_str(node.args[0])
                if func.attr != "meta":
                    self._record(node.lineno, info, func.attr, bucket, info["endpoint_host"],
                                 us_controlled=self._aws_us(info))
            elif isinstance(func.value, ast.Name) and func.value.id in self.requests_names \
                    and func.attr in HTTP_METHODS:
                self._http_call(node, func.attr)
        elif isinstance(func, ast.Name) and func.id in self.http_funcs:
            self._http_call(node, self.http_funcs[func.id])
        self.generic_visit(node)

    @staticmethod
    def _aws_us(info: dict) -> bool:
        if info["endpoint_state"] == "literal":
            return is_us_controlled(info["endpoint_host"])
        # No endpoint override: boto3 resolves the AWS-operated default endpoint.
        return info["endpoint_state"] == "sdk_default"

    # hidden telemetry: literal URLs anywhere in the module ------------------
    def scan_literals(self, tree: ast.AST):
        docstrings = {id(n.value) for n in ast.walk(tree)
                      if isinstance(n, ast.Expr) and _literal_str(n.value) is not None}
        for node in ast.walk(tree):
            value = _literal_str(node)
            if not value or id(node) in docstrings:
                continue
            for match in URL_LITERAL.finditer(value):
                host = _host(match.group(0))
                if host and host not in self.seen_hosts:
                    self.seen_hosts.add(host)
                    extra = {"us_controlled": is_us_controlled(host)}
                    if extra["us_controlled"]:
                        extra["dependency"] = "telemetry"
                    self._record(node.lineno, {"service": "http", "interface": "literal_url",
                                               "endpoint_state": "literal"},
                                 "literal_url", None, host, **extra)


def scan_python(workload: Path, workload_display: str) -> tuple[list, list]:
    """Return (calls, findings). Invalid Python raises ValueError."""
    calls: list[dict] = []
    findings: list[dict] = []
    for py in _iter_py_files(workload):
        display = _display_path(py, workload, workload_display)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=display)
        except (SyntaxError, UnicodeDecodeError, ValueError):
            raise ValueError(f"invalid Python in {display}") from None
        scanner = _CallScanner(display)
        scanner.visit(tree)
        scanner.scan_literals(tree)
        calls += scanner.calls
        findings += scanner.findings
    calls.sort(key=lambda c: (c["file"], c["line"], c["service"], c["operation"]))
    return _dedupe_calls(calls), findings


# --------------------------------------------------------------------------- inventory


def _source_client(config: dict):
    """Explicit read-only source S3 client from SKYSHIFT_SOURCE_* keys (never global)."""
    import boto3  # optional dependency, live path only

    kwargs = {
        "aws_access_key_id": config["SKYSHIFT_SOURCE_ACCESS_KEY_ID"],
        "aws_secret_access_key": config["SKYSHIFT_SOURCE_SECRET_ACCESS_KEY"],
    }
    if config.get("SKYSHIFT_SOURCE_ENDPOINT_URL"):
        kwargs["endpoint_url"] = config["SKYSHIFT_SOURCE_ENDPOINT_URL"]
    if config.get("AWS_DEFAULT_REGION"):
        kwargs["region_name"] = config["AWS_DEFAULT_REGION"]
    return boto3.session.Session().client("s3", **kwargs)


def _error_code(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", code):
            return code
    return type(exc).__name__


def inventory_buckets(names: list[str], config: dict) -> tuple[list, dict]:
    """Count objects/bytes per bucket without downloading bodies.

    Returns (buckets, check). Missing credentials => incomplete with null counts.
    A measured service failure (e.g. AccessDenied) => FAIL.
    """
    buckets = [{"name": n, "provider": "aws", "jurisdiction": "US-controlled",
                "object_count": None, "total_bytes": None, "inventory": "not_run"}
               for n in names]
    if not names:
        return buckets, {"id": "bucket_inventory", "status": "incomplete",
                         "detail": "no source bucket identified in IaC, code or config"}
    if not (config.get("SKYSHIFT_SOURCE_ACCESS_KEY_ID")
            and config.get("SKYSHIFT_SOURCE_SECRET_ACCESS_KEY")):
        return buckets, {"id": "bucket_inventory", "status": "incomplete",
                         "detail": "source credentials not supplied; counts unknown, not zero"}
    try:
        client = _source_client(config)
    except ImportError:
        return buckets, {"id": "bucket_inventory", "status": "incomplete",
                         "detail": "boto3 not installed; inventory not run"}

    failures = []
    for bucket in buckets:
        count = size = 0
        try:
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket["name"]):
                for obj in page.get("Contents", []) or []:
                    count += 1
                    size += int(obj.get("Size", 0))
        except Exception as exc:  # botocore errors; recorded by code only
            bucket["inventory"] = f"failed:{_error_code(exc)}"
            failures.append(f"{bucket['name']}: {_error_code(exc)}")
            continue
        bucket.update(object_count=count, total_bytes=size, inventory="measured")
    if failures:
        return buckets, {"id": "bucket_inventory", "status": "FAIL",
                         "detail": "source listing failed: " + "; ".join(failures)}
    return buckets, {"id": "bucket_inventory", "status": "PASS",
                     "detail": f"{len(buckets)} bucket(s) listed read-only with pagination"}


# --------------------------------------------------------------------------- discover


def _bucket_names(resources: list[dict], calls: list[dict], config: dict) -> list[str]:
    names: list[str] = []
    for r in resources:
        if r["type"] == "aws_s3_bucket":
            name = r["attributes"].get("bucket")
            if isinstance(name, str) and name not in names:
                names.append(name)
    for c in calls:
        if c["service"] == "s3" and isinstance(c.get("bucket"), str) and c["bucket"] not in names:
            names.append(c["bucket"])
    configured = config.get("SKYSHIFT_SOURCE_BUCKET")
    if isinstance(configured, str) and configured and configured not in names:
        names.append(configured)
    return names


def _live_discover(workload: Path, config: dict) -> dict:
    if not workload.is_dir():
        raise ValueError("workload must be an existing directory")
    display = workload.as_posix()
    errors: list[str] = []
    try:
        catalogue = load_catalogue()
        resources, hcl_findings = parse_hcl(workload, catalogue, display)
    except ImportError as exc:
        missing = getattr(exc, "name", None) or "dependency"
        data = {"resources": [], "calls": [], "buckets": [],
                "readiness": {"score": None, "formula": READINESS_FORMULA,
                              "proprietary": None, "unsupported": None, "us_calls": None}}
        checks = [{"id": "inventory_parsed", "status": "incomplete",
                   "detail": f"{missing} not installed; inventory unknown, not empty"}]
        return _envelope("discover", "live", "incomplete", checks, data,
                         [f"missing optional dependency: {missing}"])

    s3_ops = frozenset(op for op, ok in catalogue["s3_operations"].items() if ok)
    calls, py_findings = scan_python(workload, display)
    findings = hcl_findings + py_findings

    tf_count = len(_iter_tf_files(workload))
    checks = [
        {"id": "inventory_parsed",
         "status": "incomplete" if tf_count == 0 or hcl_findings else "PASS",
         "detail": (f"{tf_count} .tf file(s), {len(resources)} resource(s); "
                    f"{len(hcl_findings)} unresolved finding(s); modules not evaluated")},
        {"id": "calls_scanned",
         "status": "incomplete" if py_findings else "PASS",
         "detail": (f"{len(_iter_py_files(workload))} .py file(s) parsed with ast, not executed; "
                    f"{len(calls)} call(s), {len(py_findings)} dynamic/unresolved finding(s)")},
    ]
    buckets, inventory_check = inventory_buckets(_bucket_names(resources, calls, config), config)
    checks.append(inventory_check)
    errors += [f"{c['id']}: {c['status']}: {c['detail']}" for c in checks
               if c["status"] != "PASS"]

    readiness = compute_readiness(resources, calls, s3_ops)
    readiness["us_calls_scope"] = ("non-S3 calls to US-controlled hosts, including boto3 "
                                   "clients on the SDK default AWS endpoint")
    readiness["findings"] = len(findings)
    data = {
        "resources": resources,
        "calls": calls,
        "buckets": buckets,
        "readiness": readiness,
        "findings": findings,
        "catalogue": "skyshift/catalogue/resources.yaml (mapping eligibility, not measured "
                     "target compatibility)",
    }
    return _envelope("discover", "live", _overall(checks), checks, data, errors)


def discover(workload: Path, *, config: dict, stub: bool = False) -> dict:
    """Return a discover envelope whose data is the data map."""
    if not isinstance(workload, (Path, str)):
        raise ValueError("workload must be a path")
    _check_config(config)
    workload = Path(workload)

    if stub:
        data = _stub_data_map(workload)
        checks = [
            {"id": "inventory_parsed", "status": "incomplete",
             "detail": "synthetic stub; workload IaC not parsed, no VM validation"},
            {"id": "calls_scanned", "status": "incomplete",
             "detail": "synthetic stub; application source not scanned"},
            {"id": "bucket_inventory", "status": "incomplete",
             "detail": "synthetic stub; counts are synthetic, no source bucket listed"},
            {"id": "telemetry_dependency_visible", "status": "incomplete",
             "detail": "synthetic telemetry call to monitoring.eu-central-1.amazonaws.com listed"},
        ]
        return _envelope("discover", "stub", "incomplete", checks, data, [])

    return _live_discover(workload, config)


# --------------------------------------------------------------------------- choose


def _require_keys(obj: object, keys: tuple, name: str) -> None:
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be the preceding envelope's data dict")
    if "schema_version" in obj and "data" in obj:
        raise ValueError(f"{name} must be the envelope's data object, not the envelope")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"{name} missing required keys: {', '.join(missing)}")


def choose(data_map: dict, *, config: dict, stub: bool = False) -> dict:
    """Return a choose envelope selecting a Leaseweb deployment option."""
    _require_keys(data_map, DATA_MAP_KEYS, "data_map")
    _check_config(config)

    if stub:
        data = {
            "target_id": "leaseweb-selfhosted",
            "operator": "Leaseweb",
            "jurisdiction": "EU",
            # No native storage verified accessible (human gate NOT RUN) -> self-hosted S3.
            "storage_mode": "self_hosted_s3",
            "criteria": [
                {"name": "operator_jurisdiction", "value": "EU",
                 "source_url": "https://www.leaseweb.com/", "synthetic": True},
                {"name": "provider_availability", "value": None, "source_url": None,
                 "assumptions": "human VM gate not run; provider mode unapproved"},
                {"name": "native_storage_verified", "value": False, "source_url": None,
                 "assumptions": "not verified accessible; falls back to self-hosted S3"},
            ],
            "prices": [
                {"item": "compute", "amount": None, "currency": "EUR", "unit": "hour",
                 "source_url": None, "assumptions": "not verified"},
                {"item": "storage", "amount": None, "currency": "EUR", "unit": "GB-month",
                 "source_url": None, "assumptions": "not verified"},
            ],
            "explanation": {
                "mode": "replay",
                "text": "SYNTHETIC STUB, no model call: only Leaseweb options are considered; "
                        "native storage is unverified, so self-hosted S3 on Leaseweb compute is "
                        "selected. Prices are unknown and left null.",
            },
            "open_items": ["prices unverified", "provider mode awaits human VM gate"],
        }
        checks = [
            {"id": "provider_availability", "status": "incomplete",
             "detail": "synthetic stub; human-approved provider availability not recorded"},
            {"id": "prices_cited", "status": "incomplete",
             "detail": "prices null; no cited public source"},
        ]
        return _envelope("choose", "stub", "incomplete", checks, data, [])

    return _live_choose(config)


# ------------------------------------------------------------------ live choice (WS1-03)

TARGETS_PATH = Path(__file__).resolve().parent / "catalogue" / "targets.yaml"
GATE_RECORD_PATH = Path(__file__).resolve().parents[1] / "tasks" / "WS0-setup" / "validation.md"
GATE_DECISIONS_GO = ("go-with-fallback", "go")
TARGET_REQUIRED = ("target_id", "operator", "jurisdiction", "storage_mode", "provider_modes",
                   "criteria", "prices")


def load_targets(path: Path = TARGETS_PATH) -> list[dict]:
    """Load the Leaseweb-only target catalogue (JSON-subset YAML, stdlib json)."""
    import json

    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise ValueError("targets.yaml must have schema_version: 1")
    targets = doc.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("targets.yaml needs a non-empty targets list")
    for t in targets:
        if not isinstance(t, dict) or any(k not in t for k in TARGET_REQUIRED):
            raise ValueError("targets.yaml entry is incomplete")
        if t["operator"] != "Leaseweb":
            raise ValueError("targets.yaml may only contain Leaseweb targets")
        for price in t["prices"]:
            if price.get("amount") is not None and not price.get("source_url"):
                raise ValueError(f"{t['target_id']}: numeric price without a source_url")
    return targets


def _section(text: str, heading_prefix: str) -> str | None:
    match = re.search(rf"^## {re.escape(heading_prefix)}.*?$(.*?)(?=^## |\Z)", text,
                      re.MULTILINE | re.DOTALL)
    return match.group(1) if match else None


def parse_gate_record(text: str) -> dict:
    """Extract the sanitized human gate decision; unknown fields stay None/False."""
    decision_body = _section(text, "Human decision") or ""
    decision = None
    if re.search(r"Signed:\s*\S", decision_body):
        m = re.search(r"\b(go-with-fallback|go|switch)\b", decision_body)
        decision = m.group(1) if m else None
    pm = re.search(r"Provider choice:\s*([A-Za-z][A-Za-z0-9_-]*)", text)
    check1 = _section(text, "1.") or ""
    native = bool(re.search(r"Leaseweb (bucket|Object Storage)", check1)
                  and re.search(r"Result:\s*\*\*PASS\*\*", check1))
    return {"decision": decision, "provider": pm.group(1).lower() if pm else None,
            "native_storage_verified": native, "selfhosted_verified": False,
            "source": "tasks/WS0-setup/validation.md"}


def read_gate_record(path: Path = GATE_RECORD_PATH) -> dict | None:
    try:
        return parse_gate_record(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def select_target(targets: list[dict], gate: dict | None, provider_config: str | None) -> dict:
    """Pure deterministic selection. Returns {target, provider, checks, open_items, reasons}."""
    checks: list[dict] = []
    open_items: list[str] = []
    reasons: list[str] = []
    gate_provider = gate.get("provider") if gate else None
    decision = gate.get("decision") if gate else None
    provider = (provider_config or "").strip().lower() or None

    if decision not in GATE_DECISIONS_GO:
        checks.append({"id": "provider_approved", "status": "incomplete",
                       "detail": f"no signed human go decision in the VM gate record "
                                 f"(decision={decision})"})
        open_items.append("human VM gate go/provider decision missing")
        provider = None
    elif provider is None and gate_provider:
        provider = gate_provider
        checks.append({"id": "provider_approved", "status": "PASS",
                       "detail": f"provider {provider} from signed gate record ({decision}); "
                                 "SKYSHIFT_TARGET_PROVIDER not set"})
    elif provider and provider == gate_provider:
        checks.append({"id": "provider_approved", "status": "PASS",
                       "detail": f"SKYSHIFT_TARGET_PROVIDER={provider} matches signed gate "
                                 f"record ({decision})"})
    else:
        checks.append({"id": "provider_approved", "status": "incomplete",
                       "detail": f"configured provider {provider!r} not approved by gate "
                                 f"(gate provider {gate_provider!r})"})
        open_items.append("configured provider is not the human-approved provider")
        provider = None

    chosen = None
    if provider:
        eligible = [t for t in targets if provider in t["provider_modes"]]
        by_mode = {t["storage_mode"]: t for t in eligible}
        if gate.get("native_storage_verified") and "native_s3" in by_mode:
            chosen = by_mode["native_s3"]
            reasons.append("native Leaseweb Object Storage measured accessible in VM gate check 1")
            checks.append({"id": "storage_verified", "status": "PASS",
                           "detail": "native Leaseweb Object Storage put/get/list PASS in gate "
                                     "check 1 (single small object; path-style)"})
        elif gate.get("selfhosted_verified") and "self_hosted_s3" in by_mode:
            chosen = by_mode["self_hosted_s3"]
            reasons.append("native storage not verified; self-hosted S3 human-verified accessible")
            checks.append({"id": "storage_verified", "status": "PASS",
                           "detail": "self-hosted S3 human-verified accessible"})
        else:
            checks.append({"id": "storage_verified", "status": "incomplete",
                           "detail": "neither native nor self-hosted storage verified accessible"})
            open_items.append("no verified accessible Leaseweb storage option")
    else:
        checks.append({"id": "storage_verified", "status": "incomplete",
                       "detail": "not evaluated: no approved provider"})
    if chosen:
        reasons.insert(0, f"human-approved provider {provider} ({decision})")
        unknown = [p["item"] for p in chosen["prices"] if p.get("amount") is None]
        if unknown:
            open_items.append("prices unverified (null): " + ", ".join(unknown))
    return {"target": chosen, "provider": provider, "checks": checks,
            "open_items": open_items, "reasons": reasons}


EXPLANATION_SCHEMA = {
    "type": "object",
    "required": ["text"],
    "properties": {"text": {"type": "string", "maxLength": 800}},
    "additionalProperties": False,
}


def _explain(payload: dict, deterministic_text: str, config: dict) -> dict:
    """Optional narrative via skyshift.llm.complete; never affects the selection or checks."""
    try:
        from skyshift import llm

        result = llm.complete("choose_explanation", payload, EXPLANATION_SCHEMA, config=config)
    except Exception as exc:  # explanation is optional; selection stays deterministic
        return {"mode": "replay", "text": deterministic_text, "deterministic": deterministic_text,
                "model_status": "incomplete", "model_errors": [type(exc).__name__]}
    text = (result.get("data") or {}).get("text") if isinstance(result, dict) else None
    mode = result.get("mode") if isinstance(result, dict) else None
    return {"mode": mode if mode in ("live", "replay") else "replay",
            "text": text if isinstance(text, str) and text else deterministic_text,
            "deterministic": deterministic_text,
            "model_status": result.get("status") if isinstance(result, dict) else "incomplete",
            "model_errors": list(result.get("errors", [])) if isinstance(result, dict) else []}


def _live_choose(config: dict, *, gate: dict | None = None, targets: list[dict] | None = None,
                 explain=None) -> dict:
    targets = load_targets() if targets is None else targets
    gate = read_gate_record() if gate is None else gate
    sel = select_target(targets, gate, config.get("SKYSHIFT_TARGET_PROVIDER"))
    chosen = sel["target"]
    checks = sel["checks"]
    if chosen is None:
        data = {"target_id": None, "operator": "Leaseweb", "jurisdiction": None,
                "storage_mode": None, "criteria": [], "prices": [],
                "explanation": {"mode": "replay", "text": "no target selected: " +
                                "; ".join(sel["open_items"]), "deterministic": True},
                "provider": sel["provider"], "open_items": sel["open_items"]}
        return _envelope("choose", "live", "incomplete", checks, data,
                         [f"{c['id']}: {c['detail']}" for c in checks if c["status"] != "PASS"])
    det_text = (f"Selected {chosen['target_id']} ({chosen['storage_mode']}) deterministically: "
                + "; ".join(sel["reasons"]) + ". Prices remain null (unverified); API "
                "coverage is measured by parity, not claimed here.")
    payload = {"target_id": chosen["target_id"], "storage_mode": chosen["storage_mode"],
               "provider": sel["provider"], "reasons": sel["reasons"],
               "unknown_prices": [p["item"] for p in chosen["prices"] if p["amount"] is None]}
    explanation = (explain or _explain)(payload, det_text, config)
    criteria = [dict(c) for c in chosen["criteria"]] + [
        {"name": "provider_availability", "value": sel["provider"],
         "source_url": None, "evidence": "tasks/WS0-setup/validation.md (signed human gate)"},
        {"name": "native_storage_verified", "value": chosen["storage_mode"] == "native_s3",
         "source_url": None, "evidence": "tasks/WS0-setup/validation.md check 1"},
    ]
    data = {"target_id": chosen["target_id"], "operator": chosen["operator"],
            "jurisdiction": chosen["jurisdiction"], "storage_mode": chosen["storage_mode"],
            "criteria": criteria, "prices": [dict(p) for p in chosen["prices"]],
            "explanation": explanation, "provider": sel["provider"],
            "open_items": sel["open_items"]}
    return _envelope("choose", "live", _overall(checks), checks, data,
                     [f"{c['id']}: {c['detail']}" for c in checks if c["status"] != "PASS"])
