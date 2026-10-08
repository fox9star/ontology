"""Local FHIR export checks and opt-in official validation of a synthetic fixture.

Exit codes: 0 passed, 1 validation failed, 2 setup/input blocked, 3 requested
official validation skipped (never a passing check).
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import urllib.request

from rdflib import Graph

from fhir_export import export_healthcare_bundle
from fhir_validation import validate_collection_bundle

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests" / "fixtures" / "fhir" / "synthetic-clinical.ttl"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_validator(config, path, *, fetch=False):
    path = Path(path)
    if not path.exists():
        if not fetch:
            return {"status": "skipped", "reason": "Pinned validator JAR is absent; use --fetch-validator or --validator-jar."}
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".download")
        try:
            with urllib.request.urlopen(config["validator_url"], timeout=60) as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target)
            if sha256(temporary) != config["validator_sha256"]:
                return {"status": "blocked", "reason": "Downloaded validator checksum does not match the pinned official release."}
            temporary.replace(path)
        except (OSError, ValueError) as exc:
            return {"status": "blocked", "reason": f"Validator download failed: {type(exc).__name__}."}
        finally:
            temporary.unlink(missing_ok=True)
    if sha256(path) != config["validator_sha256"]:
        return {"status": "blocked", "reason": "Validator checksum does not match the pinned official release."}
    return {"status": "ready", "jar_sha256": config["validator_sha256"]}


def outcome_issues(outcome):
    if not isinstance(outcome, dict):
        return []
    if outcome.get("resourceType") == "OperationOutcome":
        return [item for item in outcome.get("issue", []) if isinstance(item, dict)]
    if outcome.get("resourceType") == "Bundle":
        return [issue for entry in outcome.get("entry", []) if isinstance(entry, dict)
                for issue in outcome_issues(entry.get("resource"))]
    return []


def prepare_core_package(config, jar, *, fetch=False):
    """Seed a verified R5 core package in the isolated Java cache.

    All engine packages are pinned. Dynamic package fetching is disabled when
    the official validator executes.
    """
    pinned = [{"id": config["core_package"], "url": config["core_package_url"], "sha256": config["core_package_sha256"]}, *config.get("support_packages", [])]
    for package in pinned:
        result = _prepare_package(package, jar, fetch=fetch)
        if result["status"] != "ready":
            return result
    return {"status": "ready", "archive_and_definition_files_verified": True, "packages": [{"id": package["id"], "sha256": package["sha256"]} for package in pinned]}


def _archive_members(archive, destination):
    """Accept only ordinary files/directories below package/, on Python 3.10+."""
    root = destination.resolve()
    for member in archive.getmembers():
        relative = PurePosixPath(member.name)
        if relative.is_absolute() or not relative.parts or relative.parts[0] != "package" or ".." in relative.parts or "\\" in member.name or ":" in member.name:
            raise ValueError("Unsafe package archive path.")
        if not member.isfile() and not member.isdir():
            raise ValueError("Package links and special archive members are prohibited.")
        target = root.joinpath(*relative.parts).resolve()
        if root not in target.parents:
            raise ValueError("Package archive path escaped its cache directory.")
        yield member, target


def _extract_package(archive_path, cache):
    cache.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member, target in _archive_members(archive, cache):
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def _verify_package_files(archive_path, cache):
    with tarfile.open(archive_path, "r:gz") as archive:
        files = set()
        for member, target in _archive_members(archive, cache):
            if not member.isfile():
                continue
            files.add(target)
            # The engine can regenerate its search index. It does not define
            # conformance rules and is excluded from definition-file checks.
            if target.name == ".index.json":
                continue
            if not target.is_file():
                return False
            with archive.extractfile(member) as source:
                digest = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if sha256(target) != digest.hexdigest():
                return False
        # Extra JSON definitions could change the engine's loaded content.
        if any(path.resolve() not in files and path.name != ".index.json" for path in (cache / "package").rglob("*.json")):
            return False
    return True


def _prepare_package(config, jar, *, fetch):
    root = Path(jar).resolve().parent
    cache = root / "validator-home" / ".fhir" / "packages" / config["id"]
    manifest = cache / "package" / "package.json"
    archive_path = root / (config["id"].replace("#", "-") + ".tgz")
    try:
        if not archive_path.exists() or sha256(archive_path) != config["sha256"]:
            if not fetch:
                return {"status": "skipped", "reason": f"Verified package archive is absent: {config['id']}; use --fetch-validator."}
            with urllib.request.urlopen(config["url"], timeout=60) as source, archive_path.open("wb") as target:
                shutil.copyfileobj(source, target)
        if sha256(archive_path) != config["sha256"]:
            return {"status": "blocked", "reason": "FHIR core package checksum disagrees with the pinned package."}
        if not manifest.exists():
            _extract_package(archive_path, cache)
        package = json.loads(manifest.read_text(encoding="utf-8"))
        if f"{package.get('name')}#{package.get('version')}" != config["id"]:
            return {"status": "blocked", "reason": f"FHIR package identity disagrees with configuration: {config['id']}."}
        if not _verify_package_files(archive_path, cache):
            return {"status": "blocked", "reason": f"Cached FHIR definition files disagree with the pinned archive: {config['id']}."}
    except (OSError, ValueError, tarfile.TarError) as exc:
        return {"status": "blocked", "reason": f"FHIR core package setup failed: {type(exc).__name__}."}
    return {"status": "ready", "package_sha256": config["sha256"]}


def run_official(config, bundle_path, output_dir, *, java, jar, mode, profiles=None, implementation_guides=None, timeout=None):
    """Run the local JAR; input must have been generated from FIXTURE by main."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outcome_path = output_dir / f"{mode}-outcome.json"
    log_path = output_dir / f"{mode}-validator.log"
    tx_log = output_dir / f"{mode}-terminology.log"
    # Eliminate stale results from earlier executions of the same directory.
    outcome_path.unlink(missing_ok=True)
    tx_log.unlink(missing_ok=True)
    settings = output_dir / "validator-settings.json"
    settings.write_text('{"ignoreDefaultPackageServers":true,"servers":[]}\n', encoding="utf-8")
    cache_home = Path(jar).resolve().parent / "validator-home"
    cache_home.mkdir(parents=True, exist_ok=True)
    profiles = list(profiles or config["profiles"])
    implementation_guides = list(implementation_guides or config["implementation_guides"])
    server = "n/a" if mode == "structural" else config["terminology_server"]
    command = [str(java), "-Xmx2g", f"-Duser.home={cache_home}", "-jar", str(jar), str(bundle_path), "-version", config["fhir_version"],
               "-profile", profiles[0], "-tx", server, "-output", str(outcome_path),
               "-fhir-settings", str(settings), "-disable-default-resource-fetcher", "-jurisdiction", "uv",
               "-txCache", str(output_dir / "terminology-cache"), "-clear-tx-cache"]
    for profile in profiles[1:]:
        command.extend(["-profile", profile])
    for ig in implementation_guides:
        if "#" not in ig or ig.endswith(("#current", "#latest")):
            return {"status": "blocked", "reason": "Implementation-guide packages require a pinned version."}
        if ig not in {config["core_package"], *(package["id"] for package in config.get("support_packages", []))}:
            return {"status": "blocked", "reason": "Implementation-guide packages must also be pinned with SHA-256 in support_packages."}
        command.extend(["-ig", ig])
    if mode == "terminology":
        command.extend(["-txLog", str(tx_log), "-unknown-codesystems-cause-errors"])
    else:
        command.append("-no-http-access")
    evidence = {"status": "blocked", "validator_version": config["validator_version"], "jar_sha256": sha256(jar),
                "fhir_version": config["fhir_version"], "core_package": config["core_package"], "profiles": profiles,
                "support_packages": [{"id": package["id"], "sha256": package["sha256"]} for package in config.get("support_packages", [])],
                "implementation_guides": implementation_guides, "mode": mode, "terminology_server": server,
                "terminology_service_validated": False, "input_sha256": sha256(bundle_path),
                "command": command, "log": str(log_path), "outcome": str(outcome_path)}
    try:
        java_info = subprocess.run([str(java), "-version"], capture_output=True, text=True, timeout=15)
        evidence["java_version"] = (java_info.stderr or java_info.stdout).strip()
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout or config["timeout_seconds"])
    except subprocess.TimeoutExpired:
        evidence["status"] = "failed"
        evidence["reason"] = "Official validator timed out; validation is incomplete."
        return evidence
    except OSError as exc:
        evidence["reason"] = f"Official validator could not start: {type(exc).__name__}."
        return evidence
    evidence["returncode"] = result.returncode
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    version_match = re.search(r"FHIR Validation tool Version (\S+)", log_text)
    if not version_match or version_match.group(1) != config["validator_version"]:
        evidence["reason"] = "Validator version could not be verified from its output."
        return evidence
    package_match = re.search(r"Package Summary: \[([^\]]+)\]", log_text)
    loaded_packages = [item.strip() for item in package_match.group(1).split(",")] if package_match else []
    pinned_packages = {config["core_package"], *(package["id"] for package in config.get("support_packages", []))}
    evidence["loaded_packages"] = loaded_packages
    if set(loaded_packages) != pinned_packages:
        evidence["reason"] = "Official engine package set disagrees with the pinned configuration."
        return evidence
    try:
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        evidence["reason"] = "Official validator produced no readable OperationOutcome; validation is incomplete."
        return evidence
    if outcome.get("resourceType") not in {"OperationOutcome", "Bundle"}:
        evidence["reason"] = "Official validator produced an unexpected outcome format."
        return evidence
    issues = outcome_issues(outcome)
    if not issues:
        evidence["reason"] = "Official validator returned no issue evidence; validation is incomplete."
        return evidence
    evidence["issues"] = issues
    counts = {severity: sum(issue.get("severity") == severity for issue in issues)
              for severity in ("fatal", "error", "warning", "information", "success")}
    evidence["issue_counts"] = counts
    evidence["status"] = "failed" if result.returncode != 0 or counts["error"] or counts["fatal"] else "passed"
    if mode == "terminology":
        # Never claim terminology coverage if the service was not consulted, or
        # the engine explicitly could not validate a code/system/ValueSet.
        incomplete_patterns = ("cannot be validated", "could not be validated", "unable to validate", "cannot validate", "could not validate", "no terminology service", "unable to connect", "not found", "unknown code system")
        diagnostic_text = " ".join(str(issue.get("diagnostics", "")) + " " + str(issue.get("details", {})) for issue in issues).lower()
        service_evidence = tx_log.exists() and bool(re.search(r"\$(?:validate-code|expand)", tx_log.read_text(encoding="utf-8", errors="replace")))
        incomplete = any(pattern in diagnostic_text for pattern in incomplete_patterns)
        if not service_evidence or incomplete:
            if evidence["status"] == "passed":
                evidence["status"] = "blocked"
            evidence["reason"] = "Terminology validation coverage is incomplete; inspect the recorded issues and service log."
        else:
            evidence["terminology_service_validated"] = evidence["status"] == "passed"
        evidence["terminology_log"] = str(tx_log)
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic-fixture", action="store_true", help="Generate only the committed constructed fixture.")
    source.add_argument("--bundle", type=Path, help="Validate a Bundle locally; this input is never sent to the official validator.")
    parser.add_argument("--official", choices=("structural", "terminology"))
    parser.add_argument("--config", type=Path, default=ROOT / "fhir-validator-config.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".runtime" / "fhir-validation")
    parser.add_argument("--validator-jar", type=Path)
    parser.add_argument("--java", help="Java executable; otherwise PATH or this project's portable runtime.")
    parser.add_argument("--fetch-validator", action="store_true")
    parser.add_argument("--profile", action="append")
    parser.add_argument("--ig", action="append")
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args(argv)
    if args.official and not args.synthetic_fixture:
        parser.error("Official validation requires --synthetic-fixture; arbitrary input remains local-only.")
    if args.timeout is not None and args.timeout <= 0:
        parser.error("--timeout must be positive.")
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "constructed-synthetic-fixture" if args.synthetic_fixture else "local-input", "official": {"status": "not-requested"}}
    report_path = args.output_dir / "validation-report.json"
    try:
        if args.synthetic_fixture:
            bundle = export_healthcare_bundle(Graph().parse(FIXTURE, format="turtle"))
            bundle_path = args.output_dir / "synthetic-bundle.json"
            bundle_path.write_text(json.dumps(bundle, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            report["fixture_sha256"] = sha256(FIXTURE)
        else:
            bundle_path = args.bundle.resolve()
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON number")))
        report["local"] = validate_collection_bundle(bundle)
        report["input_sha256"] = sha256(bundle_path)
        report["status"] = "passed" if report["local"]["valid"] else "failed"
        if args.official and report["status"] == "passed":
            config = json.loads(args.config.read_text(encoding="utf-8"))
            jar = (args.validator_jar or ROOT / ".runtime" / "fhir-tools" / f"validator_cli-{config['validator_version']}.jar").resolve()
            prepared = prepare_validator(config, jar, fetch=args.fetch_validator)
            if prepared["status"] == "ready":
                prepared = prepare_core_package(config, jar, fetch=args.fetch_validator)
            java = args.java or shutil.which("java")
            if not java:
                portable = sorted((ROOT / ".runtime" / "fhir-tools" / "java").glob("*/bin/java.exe"))
                java = str(portable[0]) if portable else None
            if prepared["status"] != "ready":
                report["official"] = prepared
            elif not java:
                report["official"] = {"status": "skipped", "reason": "Java is absent; provide --java or install a Java runtime."}
            else:
                report["official"] = run_official(config, bundle_path, args.output_dir, java=java, jar=jar, mode=args.official, profiles=args.profile, implementation_guides=args.ig, timeout=args.timeout)
                report["official"]["package_verification"] = prepared
            report["status"] = report["official"]["status"]
        elif args.official:
            report["official"] = {"status": "skipped", "reason": "Local export checks failed; official validation was not run."}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.update(status="blocked", reason=f"Input or validator setup failed: {type(exc).__name__}.")
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path)}, ensure_ascii=False))
    return {"passed": 0, "failed": 1, "blocked": 2, "skipped": 3}.get(report["status"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
