#!/usr/bin/env python3
"""Release-readiness gates for FlowError source, unpacked solutions and acceptance evidence.

This tool is deliberately offline. It does not call Power Platform and it never
infers runtime acceptance from static checks or successful flow runs alone.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ACCEPTANCE = {
    "same-flow-failure-recovery",
    "notification-failure-retry",
    "replay-60",
    "backlog-over-900",
    "overlong-run-id",
    "child-duration-under-120s",
    "coverage-and-heartbeat-routing",
    "owner-and-run-links",
}
SOURCE_FLOWS = {
    "MON-FailureScan", "MON-FailureScan-Dataverse", "MON-HandleIncident",
    "MON-Heartbeat", "SETUP-CoreLists", "SETUP-CreateFields",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(root: Path) -> dict[str, str]:
    return {name: sha256(root / "flows" / f"{name}.json")
            for name in sorted(SOURCE_FLOWS)
            if (root / "flows" / f"{name}.json").is_file()}


def load_json(path: Path) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key {key}')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError(f'invalid JSON constant {value}')
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=reject_constant)


def safe_load(path: Path, label: str, errors: list[str]) -> Any:
    try:
        return load_json(path)
    except (OSError, ValueError, UnicodeError) as exc:
        errors.append(f"{label}: cannot read valid JSON at {path}: {exc}")
        return None


def workflow_guid(value: Any) -> str:
    text = str(value).lower().removesuffix(".json")
    matches = re.findall(r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[0-9a-f]{32})$", text)
    if not matches:
        return ""
    return matches[-1].replace("-", "")


def compare_exports(root: Path, errors: list[str]) -> None:
    manifest = safe_load(root / "flows" / "_workflow-ids.json", "workflow manifest", errors)
    if not isinstance(manifest, dict):
        errors.append("workflow manifest must be a JSON object")
        return
    for name in sorted(SOURCE_FLOWS):
        entry = manifest.get(name)
        if not entry:
            errors.append(f"manifest missing required flow {name}")
            continue
        if not isinstance(entry, dict):
            errors.append(f"manifest entry {name} must be an object")
            continue
        solution = entry.get("solution")
        workflowid = entry.get("workflowid")
        if not isinstance(workflowid, str) or not re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', workflowid):
            errors.append(f'{name}: invalid manifest workflowid')
            continue
        files = []
        workflow_dir = root / "solution" / str(solution) / "Workflows"
        if workflow_dir.is_dir() and workflowid:
            wanted = workflow_guid(workflowid)
            files = [p for p in workflow_dir.glob("*.json")
                     if workflow_guid(p.stem).endswith(wanted)]
        if len(files) != 1:
            errors.append(f"{name}: expected one unpacked workflow export ending in workflowid {workflowid} under {solution}, found {len(files)}")
            continue
        src = safe_load(root / "flows" / f"{name}.json", f"{name} editable source", errors)
        exported = safe_load(files[0], f"{name} unpacked export", errors)
        if not isinstance(src, dict) or not isinstance(exported, dict):
            continue
        # Compare executable definition plus connection-reference contracts. Export metadata
        # (workflow IDs, names and timestamps) is intentionally excluded.
        fields = ("definition", "connectionReferences")
        if not isinstance(src.get('properties'), dict) or not isinstance(exported.get('properties'), dict):
            errors.append(f'{name}: source/export properties must be objects')
            continue
        for field in fields:
            left = src.get("properties", {}).get(field)
            right = exported.get("properties", {}).get(field)
            if left != right:
                errors.append(f"{name}: unpacked export differs from editable source ({field}); export may be stale")
                break


def check_cloud_sources(root: Path, errors: list[str]) -> None:
    for name in sorted(SOURCE_FLOWS):
        path = root / "flows" / f"{name}.json"
        if not path.is_file():
            errors.append(f"required editable source missing: {path.relative_to(root)}")
            continue
        try:
            doc = load_json(path)
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(f"{name}: invalid JSON source: {exc}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{name}: source JSON root must be an object")
            continue
        props = doc.get("properties", {})
        if not isinstance(props, dict):
            errors.append(f"{name}: properties must be an object")
            continue
        definition_obj = props.get("definition")
        if not isinstance(definition_obj, dict) or not isinstance(definition_obj.get("actions"), dict):
            errors.append(f"{name}: missing cloud flow properties.definition.actions")
        refs = props.get("connectionReferences", {})
        if not isinstance(refs, dict):
            errors.append(f"{name}: properties.connectionReferences must be an object")
            refs = {}
        declared_keys = set(refs)
        declared_logical = {v['connection'].get('connectionReferenceLogicalName')
                            for v in refs.values() if isinstance(v, dict) and isinstance(v.get('connection'), dict)
                            and isinstance(v['connection'].get('connectionReferenceLogicalName'), str)}
        referenced_keys: set[str] = set()
        referenced_logical: set[str] = set()
        def walk(value: Any) -> None:
            if isinstance(value, dict):
                host = value.get("host")
                if isinstance(host, dict) and isinstance(host.get("connectionName"), str):
                    referenced_keys.add(host["connectionName"])
                connection = value.get("connection")
                if isinstance(connection, dict) and isinstance(connection.get("connectionReferenceLogicalName"), str):
                    referenced_logical.add(connection["connectionReferenceLogicalName"])
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(definition_obj)
        dangling_keys = referenced_keys - declared_keys
        if dangling_keys:
            errors.append(f"{name}: definition host.connectionName uses undeclared connection-reference keys: {sorted(dangling_keys)}")
        dangling_logical = referenced_logical - declared_logical
        if dangling_logical:
            errors.append(f"{name}: definition references undeclared logical connection references: {sorted(dangling_logical)}")


def check_manifest(root: Path, errors: list[str], warnings: list[str]) -> None:
    manifest = safe_load(root / "flows" / "_workflow-ids.json", "workflow manifest", errors)
    if not isinstance(manifest, dict):
        errors.append("workflow manifest must be a JSON object")
        return
    ids: dict[str, str] = {}
    for name, entry in manifest.items():
        if not isinstance(entry, dict):
            errors.append(f"manifest entry {name} must be an object")
            continue
        if not (root / "flows" / f"{name}.json").is_file():
            errors.append(f"manifest entry {name} has no editable flow source")
        wid = entry.get("workflowid")
        if not isinstance(wid, str) or not wid:
            errors.append(f"manifest entry {name} has no workflowid")
        elif wid in ids:
            errors.append(f"workflowid {wid} is reused by {ids[wid]} and {name}")
        else:
            ids[wid] = name
        if entry.get("solution") not in {"FlowAdminCore", "FlowAdminMonitoring", "FlowAdminGovernance", "Default"}:
            errors.append(f"{name}: unknown owning solution {entry.get('solution')!r}")
    for name in SOURCE_FLOWS:
        if name not in manifest:
            errors.append(f"manifest missing required flow {name}")
    for name, entry in manifest.items():
        if not isinstance(entry, dict):
            continue
        if type(entry.get("statecode")) is not int or entry.get("statecode") not in (0, 1):
            errors.append(f"{name}: statecode must be 0 (Stopped) or 1 (Started)")
    # State expectations come from source-hash-bound coverage acceptance, not a permanent
    # assumption that one scanner is always enabled.
    acceptance_path = root / "docs" / "acceptance-evidence.json"
    evidence = safe_load(acceptance_path, "acceptance evidence", errors) if acceptance_path.exists() else None
    if not acceptance_path.exists():
        errors.append("acceptance evidence file missing; desired scanner states are unknown")
    coverage_cases = evidence.get("cases", {}) if isinstance(evidence, dict) else {}
    if not isinstance(coverage_cases, dict):
        errors.append("acceptance evidence cases must be a JSON object")
        coverage_cases = {}
    coverage = coverage_cases.get("coverage-and-heartbeat-routing", {})
    if not isinstance(coverage, dict):
        coverage = {}
    expected_hashes = source_hashes(root)
    if coverage.get("result") != "passed":
        errors.append("coverage acceptance must be passed before scanner state expectations can be used")
    if coverage.get("source_hashes") != expected_hashes:
        errors.append("coverage acceptance source hashes are absent, stale, or do not match editable sources")
    desired = coverage.get("desired_scanner_states")
    required_scanners = {"MON-FailureScan", "MON-FailureScan-Dataverse"}
    if (not isinstance(desired, dict) or set(desired) != required_scanners
            or any(type(v) is not int or v not in (0, 1) for v in desired.values())):
        errors.append("coverage acceptance must declare desired_scanner_states for both scanners using statecode 0 or 1")
    else:
        for name, expected in desired.items():
            state_entry = manifest.get(name, {})
            actual = state_entry.get("statecode") if isinstance(state_entry, dict) else None
            if actual != expected:
                errors.append(f"manifest state mismatch: {name} is {actual!r}, coverage acceptance requires {expected}")
    warnings.append("manifest states are checked against accepted source-bound coverage, not queried live")


def check_acceptance(root: Path, errors: list[str], warnings: list[str], max_age_days: int) -> None:
    acceptance_path = root / "docs" / "acceptance-evidence.json"
    if not acceptance_path.exists():
        errors.append("acceptance evidence file missing; live acceptance is unknown")
        return
    data = safe_load(acceptance_path, "acceptance evidence", errors)
    if not isinstance(data, dict):
        errors.append("acceptance evidence must be a JSON object")
        return
    expected_hashes = source_hashes(root)
    cases = data.get("cases", {})
    if not isinstance(cases, dict):
        errors.append("acceptance evidence cases must be a JSON object")
        return
    for case in sorted(REQUIRED_ACCEPTANCE):
        record = cases.get(case)
        if not isinstance(record, dict):
            errors.append(f"acceptance {case}: no evidence record (unknown)")
            continue
        if record.get("result") != "passed":
            errors.append(f"acceptance {case}: result is {record.get('result', 'missing')!r}, expected passed")
        if record.get("source_hashes") != expected_hashes:
            errors.append(f"acceptance {case}: source hashes are absent, stale, or do not match current editable flows")
        for field in ("run_ids", "environment", "executed_at", "owner", "evidence_links"):
            value = record.get(field)
            if not value:
                errors.append(f"acceptance {case}: required evidence field {field} is empty")
        try:
            timestamp_value = record["executed_at"]
            if not isinstance(timestamp_value, str):
                raise ValueError("timestamp must be a string")
            timestamp = dt.datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("timezone required")
            age = (dt.datetime.now(dt.timezone.utc) - timestamp.astimezone(dt.timezone.utc)).total_seconds() / 86400
            if age < 0 or age > max_age_days:
                errors.append(f"acceptance {case}: evidence is outside freshness window ({max_age_days} days)")
        except (KeyError, TypeError, ValueError):
            errors.append(f"acceptance {case}: executed_at must be ISO-8601 with timezone")
    warnings.append("static checks and flow success statuses do not count as live acceptance evidence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="FlowError checkout root")
    parser.add_argument("--max-evidence-age-days", type=int, default=30)
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    check_manifest(root, errors, warnings)
    check_cloud_sources(root, errors)
    compare_exports(root, errors)
    check_acceptance(root, errors, warnings, args.max_evidence_age_days)
    for warning in warnings:
        print(f"INFO: {warning}")
    for error in errors:
        print(f"BLOCKED: {error}")
    if errors:
        print(f"NOT READY: {len(errors)} gate(s) failed")
        return 1
    print("READY: source, manifest, unpacked exports and required fresh acceptance evidence agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
