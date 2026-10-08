"""Local, single-user access boundary for Ontology Studio.

The trusted identity is the owner of this machine. There are no API keys or
remote user roles. Do not put this application behind a public reverse proxy.
"""

import ipaddress
import hashlib
import json
import os
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import current_app, has_app_context, has_request_context, jsonify, request

from graph_io import graph_file_lock, write_bytes_atomic

_AUDIT_LOGS = deque(maxlen=200)
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUDIT_RECORD_FIELDS = ("timestamp", "action", "identity", "role", "method")


def _audit_path():
    configured = _setting("ONTOLOGY_AUDIT_LOG_PATH", "")
    return Path(configured).expanduser() if configured else None


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_audit_record(record):
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _read_audit_records(path):
    records = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                records.append({"_invalid_line": line_number})
                continue
            records.append(record if isinstance(record, dict) else {"_invalid_line": line_number})
    return records


def verify_audit_integrity(path=None):
    """Verify the tamper-evident SHA-256 chain of the configured audit file."""
    target = Path(path).expanduser() if path else _audit_path()
    if target is None:
        return {"configured": False, "valid": True, "records": 0, "errors": []}
    previous = ""
    errors = []
    valid_records = 0
    for line_number, record in enumerate(_read_audit_records(target), 1):
        if "_invalid_line" in record:
            errors.append({"line": record["_invalid_line"], "reason": "invalid_json"})
            continue
        record_errors = []
        if record.get("previous_hash") != previous:
            record_errors.append({"line": line_number, "reason": "previous_hash_mismatch"})
        expected = _hash_audit_record(record)
        if record.get("record_hash") != expected:
            record_errors.append({"line": line_number, "reason": "record_hash_mismatch"})
        errors.extend(record_errors)
        if not record_errors:
            valid_records += 1
        previous = record.get("record_hash", "")
    return {
        "configured": True, "valid": not errors, "records": valid_records,
        "errors": errors, "last_hash": previous,
    }


def _retention_days():
    raw = _setting("ONTOLOGY_AUDIT_RETENTION_DAYS", "0")
    try:
        days = int(raw)
    except (TypeError, ValueError):
        raise ValueError("ONTOLOGY_AUDIT_RETENTION_DAYS must be a nonnegative integer.") from None
    if days < 0:
        raise ValueError("ONTOLOGY_AUDIT_RETENTION_DAYS must be a nonnegative integer.")
    return days


def _append_persistent_record(record, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("Audit log path must not be a symbolic link.")
    with graph_file_lock(path):
        integrity = verify_audit_integrity(path)
        if not integrity["valid"]:
            raise OSError("Audit log integrity check failed; refusing to append.")
        records = _read_audit_records(path)
        retention = _retention_days()
        if retention:
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention)
            retained = []
            for existing in records:
                try:
                    timestamp = datetime.fromisoformat(existing["timestamp"].replace("Z", "+00:00"))
                except (KeyError, ValueError, TypeError):
                    retained.append(existing)
                    continue
                if timestamp >= cutoff:
                    retained.append(existing)
            records = retained

        previous = ""
        encoded_records = []
        for existing in records:
            clean = {key: existing[key] for key in _AUDIT_RECORD_FIELDS if key in existing}
            chained = {**clean, "previous_hash": previous}
            chained["record_hash"] = _hash_audit_record(chained)
            previous = chained["record_hash"]
            encoded_records.append(_canonical_json(chained))
        chained = {**record, "previous_hash": previous}
        chained["record_hash"] = _hash_audit_record(chained)
        encoded_records.append(_canonical_json(chained))
        payload = ("\n".join(encoded_records) + "\n").encode("utf-8")
        write_bytes_atomic(payload, path)
    return chained


def _setting(name, default=""):
    if has_app_context() and name in current_app.config:
        return current_app.config[name]
    return os.environ.get(name, default)


def _docker_mode():
    return str(_setting("ONTOLOGY_LOCAL_DOCKER", "0")) == "1"


def _address(value):
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            return address.ipv4_mapped
        return address
    except (ValueError, TypeError):
        return None


def _docker_network():
    try:
        network = ipaddress.ip_network(_setting("ONTOLOGY_DOCKER_CLIENT_CIDR"), strict=True)
    except (ValueError, TypeError):
        raise ValueError("Local Docker mode requires an explicit ONTOLOGY_DOCKER_CLIENT_CIDR.") from None
    private_bridges = (ipaddress.ip_network("10.0.0.0/8"),
                       ipaddress.ip_network("172.16.0.0/12"),
                       ipaddress.ip_network("192.168.0.0/16"))
    if network.version != 4 or network.prefixlen < 24 or not any(network.subnet_of(bridge) for bridge in private_bridges):
        raise ValueError("ONTOLOGY_DOCKER_CLIENT_CIDR must be a private IPv4 bridge subnet of /24 or narrower.")
    return network


def validate_bind_host(host):
    """Fail startup if a native instance would listen beyond loopback."""
    address = _address(host)
    if host.lower() == "localhost" or (address and address.is_loopback):
        return host
    if host == "0.0.0.0" and _docker_mode():
        _docker_network()
        return host
    raise ValueError("Ontology Studio must bind to loopback. Only explicit local Docker mode permits 0.0.0.0.")


def _local_hostname(hostname):
    address = _address(hostname)
    return hostname == "localhost" or bool(address and address.is_loopback)


def _origin(value):
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or parts.username or parts.password:
            return None
        if parts.path not in {"", "/"} or parts.query or parts.fragment:
            return None
        if not parts.hostname or not _local_hostname(parts.hostname):
            return None
        return parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)
    except (ValueError, TypeError):
        return None


def _denial_reason():
    address = _address(request.remote_addr)
    trusted_client = bool(address and address.is_loopback)
    if not trusted_client and address and _docker_mode():
        try:
            trusted_client = address in _docker_network()
        except ValueError:
            return "invalid_local_docker_configuration"
    if not trusted_client:
        return "remote_client"
    local_origin = _origin(request.host_url)
    if local_origin is None:
        return "untrusted_host"
    supplied_origin = request.headers.get("Origin")
    if supplied_origin is not None and _origin(supplied_origin) != local_origin:
        return "foreign_origin"
    if request.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        return "cross_site_request"
    return None


def get_client_identity():
    """Return the trusted local owner's identity, independent of credentials."""
    if _denial_reason():
        return False, "none", "untrusted_client"
    return True, "admin", "local_owner"


def authorize_request():
    """Register as Flask.before_request; covers pages, reads and mutations."""
    reason = _denial_reason()
    if reason:
        return jsonify({
            "error": "Ontology Studio accepts trusted local requests only.",
            "code": "LOCAL_ACCESS_REQUIRED",
            "reason": reason,
        }), 403
    if request.method in _MUTATING_METHODS:
        try:
            log_audit_action(request.path, "local_owner", "admin", request.method)
        except (OSError, ValueError):
            return jsonify({
                "error": "The audit log is unavailable; the operation was not started.",
                "code": "AUDIT_LOG_UNAVAILABLE",
            }), 503
    return None


def require_role(min_role="viewer"):
    """Compatibility decorator: the local owner can perform all operations."""
    if min_role not in {"viewer", "editor", "admin"}:
        raise ValueError("Unknown role")

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            denied = authorize_request()
            return denied if denied is not None else fn(*args, **kwargs)
        return wrapper
    return decorator


def log_audit_action(action, identity, role, details=""):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "identity": identity,
        "role": role,
        "method": details,
        "ip": request.remote_addr if has_request_context() else None,
    }
    path = _audit_path()
    if path is not None:
        persistent = {key: record[key] for key in _AUDIT_RECORD_FIELDS}
        _append_persistent_record(persistent, path)
    _AUDIT_LOGS.append(record)


def get_audit_logs(limit=50):
    count = max(0, min(int(limit), 1000))
    path = _audit_path()
    if path is not None and path.exists():
        return _read_audit_records(path)[-count:] if count else []
    return list(_AUDIT_LOGS)[-count:] if count else []
