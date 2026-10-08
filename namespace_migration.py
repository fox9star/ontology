"""Plan or apply a reversible migration from reserved example.org namespaces."""

import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
RESERVED = (
    "https://example.org/ontology/core",
    "https://example.org/mv",
    "https://example.org/agent",
    "http://example.org/ontology/devops",
    "http://example.org/ontology/ecommerce",
    "http://example.org/ontology/healthcare",
    "https://example.org/ontology/academic",
    "https://example.org/ontology/vocab",
)
TEXT_SUFFIXES = {".ttl", ".owl", ".py", ".md", ".html", ".yml", ".yaml", ".json", ".js", ".txt"}
EXCLUDED_DIRS = {".git", ".venv", ".runtime", "node_modules", "__pycache__", "exports"}
BOUNDARY = re.compile(r"(?=[#>\"'\s]|$)")


def validate_host(host):
    """Require a host name only; callers must provide a domain they control."""
    value = str(host or "").strip().lower().rstrip(".")
    if not value or any(char in value for char in "/:@?#"):
        raise ValueError("Pass a hostname only, such as ontology.example.net.")
    parsed = urlsplit("https://" + value)
    if parsed.hostname != value or parsed.port is not None:
        raise ValueError("The namespace host must be a valid hostname without a port.")
    if value in {"example.org", "www.example.org", "example.com", "www.example.com"}:
        raise ValueError("A reserved example.org/example.com host cannot be used for release.")
    return value


def namespace_map(host):
    host = validate_host(host)
    result = {}
    for old in RESERVED:
        path = urlsplit(old).path
        result[old] = f"https://{host}{path}"
    return result


def replace_namespaces(content, mapping):
    """Replace ontology bases only; leave unrelated example.org asset URLs alone."""
    changed = content
    for old, new in sorted(mapping.items(), key=lambda item: -len(item[0])):
        changed = re.sub(re.escape(old) + r"(?=[#>\"'\s]|$)", new, changed)
    return changed


def _text_files(root, include_project_data=False):
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if not include_project_data and relative.parts and relative.parts[0] in {"projects", "snapshots"}:
            continue
        yield path


def plan_migration(root, host, include_project_data=False):
    """Return changed paths and replacement text without modifying the workspace."""
    root = Path(root).resolve()
    mapping = namespace_map(host)
    replacements = {}
    for path in _text_files(root, include_project_data=include_project_data):
        original = path.read_text(encoding="utf-8")
        updated = replace_namespaces(original, mapping)
        if updated != original:
            replacements[path] = updated
    return mapping, replacements


def apply_migration(root, host, include_project_data=False):
    """Back up changed files, then atomically write the prepared namespace map."""
    root = Path(root).resolve()
    mapping, replacements = plan_migration(root, host, include_project_data)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = root / ".runtime" / "namespace-migrations" / stamp
    # Finish every backup before changing the first source file. If backup
    # creation fails, the workspace remains untouched; if a later write fails,
    # the complete source set is available for recovery.
    for source, content in replacements.items():
        relative = source.relative_to(root)
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)
    for source, content in replacements.items():
        temporary = source.with_name(source.name + ".namespace-migration.tmp")
        temporary.write_text(content, encoding="utf-8", newline="")
        temporary.replace(source)
    return mapping, replacements, backup_root if replacements else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Owned namespace hostname, without scheme or path")
    parser.add_argument("--apply", action="store_true", help="Write changes; default mode is dry-run")
    parser.add_argument("--include-project-data", action="store_true",
                        help="Also rewrite project graphs and snapshots after reviewing backups")
    options = parser.parse_args(argv)
    try:
        if options.apply:
            mapping, replacements, backup = apply_migration(
                ROOT, options.host, include_project_data=options.include_project_data
            )
        else:
            mapping, replacements = plan_migration(
                ROOT, options.host, include_project_data=options.include_project_data
            )
            backup = None
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL: {error}")
        return 2
    print(f"Namespace map: {len(mapping)} reserved ontology bases -> https://{validate_host(options.host)}")
    for path in replacements:
        print(f"{'UPDATED' if options.apply else 'WOULD UPDATE'} {path.relative_to(ROOT)}")
    if backup:
        print(f"Backups: {backup.relative_to(ROOT)}")
    print("Review the diff, regenerate RDF/XML exports, and run namespace_policy.py --release before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
