"""Fail-closed inspection and content binding for managed Dataverse solution ZIPs.

This verifies package identity and cloud-flow inventory. It does not test execution,
connectivity, import-time activation, or any other Power Automate runtime behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


class ArtifactError(ValueError):
    """Raised when a release artifact is malformed or does not match its contract."""


DESCRIPTOR_VERSION = 1
MAX_ZIP_BYTES = 256 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ZIP_ENTRIES = 10_000
MAX_FLOW_JSON_BYTES = 10 * 1024 * 1024
MAX_XML_BYTES = 64 * 1024 * 1024
_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")
_SOLUTION = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def _json_load(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=_pairs_no_duplicates,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              ArtifactError(f"invalid JSON constant {value} in {label}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"malformed UTF-8 JSON in {label}: {exc}") from exc


def _validate_manifest(manifest: Any, expected_solution: str) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(manifest, dict) or set(manifest) != {"version", "solution", "flows"}:
        raise ArtifactError("activation manifest must contain exactly version, solution and flows")
    if type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ArtifactError("activation manifest version must be integer 1")
    solution = manifest["solution"]
    if not isinstance(solution, str) or not _SOLUTION.fullmatch(solution):
        raise ArtifactError("activation manifest solution must be a valid solution unique name")
    if solution != expected_solution:
        raise ArtifactError(f"manifest solution {solution!r} does not match expected {expected_solution!r}")
    flows = manifest["flows"]
    if not isinstance(flows, list) or len(flows) > 100:
        raise ArtifactError("activation manifest flows must be an array of at most 100 entries")
    ids: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(flows):
        if not isinstance(item, dict) or set(item) != {"workflowId", "enabled"}:
            raise ArtifactError(f"manifest flow {index} must contain exactly workflowId and enabled")
        workflow_id = item["workflowId"]
        if not isinstance(workflow_id, str) or not _GUID.fullmatch(workflow_id):
            raise ArtifactError(f"manifest flow {index} workflowId must be a lowercase GUID")
        if workflow_id in seen:
            raise ArtifactError(f"duplicate activation manifest workflowId: {workflow_id}")
        if type(item["enabled"]) is not bool:
            raise ArtifactError(f"manifest flow {index} enabled must be a JSON boolean")
        seen.add(workflow_id)
        ids.append(workflow_id)
    return manifest, ids


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(root: ElementTree.Element, name: str, label: str) -> str:
    matches = [node.text.strip() for node in list(root)
               if _local_name(node.tag) == name.casefold() and node.text and node.text.strip()]
    if len(matches) != 1:
        raise ArtifactError(f"{label} must contain exactly one non-empty {name} element")
    return matches[0]


def _safe_member_path(name: str) -> str:
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        raise ArtifactError(f"unsafe ZIP member path: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts[:-1]) or (parts[-1] in ("", ".", "..")):
        # A trailing slash is allowed only for a directory entry.
        if not (name.endswith("/") and all(part not in ("", ".", "..") for part in parts[:-1])):
            raise ArtifactError(f"unsafe ZIP member path: {name!r}")
    if re.match(r"^[A-Za-z]:", parts[0]):
        raise ArtifactError(f"drive-qualified ZIP member path: {name!r}")
    return "/".join(parts).casefold()


def _archive_members(zip_bytes: bytes) -> tuple[zipfile.ZipFile, list[zipfile.ZipInfo]]:
    if not zip_bytes or len(zip_bytes) > MAX_ZIP_BYTES:
        raise ArtifactError("solution ZIP is empty or exceeds the size limit")
    try:
        archive = zipfile.ZipFile(__import__("io").BytesIO(zip_bytes), "r")
        infos = archive.infolist()
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        raise ArtifactError(f"invalid solution ZIP: {exc}") from exc
    if not infos or len(infos) > MAX_ZIP_ENTRIES:
        archive.close()
        raise ArtifactError("solution ZIP has no members or exceeds the entry limit")
    seen: set[str] = set()
    file_paths: set[str] = set()
    total_size = 0
    for info in infos:
        key = _safe_member_path(info.filename)
        if key in seen:
            archive.close()
            raise ArtifactError(f"duplicate or case-colliding ZIP member: {info.filename}")
        seen.add(key)
        if not info.is_dir():
            file_paths.add(key)
        if info.flag_bits & 0x1:
            archive.close()
            raise ArtifactError(f"encrypted ZIP member is unsupported: {info.filename}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            archive.close()
            raise ArtifactError(f"symbolic-link ZIP member is unsupported: {info.filename}")
        if info.file_size < 0 or info.file_size > MAX_UNCOMPRESSED_BYTES:
            archive.close()
            raise ArtifactError(f"ZIP member exceeds the expanded size limit: {info.filename}")
        total_size += info.file_size
        if total_size > MAX_UNCOMPRESSED_BYTES:
            archive.close()
            raise ArtifactError("solution ZIP exceeds the total expanded size limit")
    for path in file_paths:
        parent = path.rpartition("/")[0]
        while parent:
            if parent in file_paths:
                archive.close()
                raise ArtifactError(f"ZIP member is nested beneath a file: {parent}")
            parent = parent.rpartition("/")[0]
    return archive, infos


def _member_data(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    if info.file_size > limit:
        raise ArtifactError(f"ZIP member exceeds its type-specific size limit: {info.filename}")
    try:
        chunks: list[bytes] = []
        size = 0
        ceiling = min(info.file_size, limit)
        with archive.open(info, "r") as stream:
            while True:
                # Request at most one byte beyond the declared/allowed size so a forged
                # ZIP directory entry cannot turn a size check into an expansion bomb.
                chunk = stream.read(min(64 * 1024, ceiling - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > ceiling:
                    raise ArtifactError(f"ZIP member expands past its declared or allowed size: {info.filename}")
                chunks.append(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise ArtifactError(f"cannot read ZIP member {info.filename}: {exc}") from exc
    if size != info.file_size:
        raise ArtifactError(f"ZIP member size mismatch: {info.filename}")
    return b"".join(chunks)


def _locate_xml(infos: list[zipfile.ZipInfo], name: str) -> zipfile.ZipInfo:
    options = [i for i in infos if not i.is_dir() and
               i.filename.casefold() in {name.casefold(), f"other/{name}".casefold()}]
    if len(options) != 1:
        raise ArtifactError(f"solution ZIP must contain exactly one {name} at its root or under Other/")
    return options[0]


def _parse_xml(data: bytes, label: str) -> ElementTree.Element:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactError(f"unsupported non-UTF-8 XML encoding in {label}") from exc
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise ArtifactError(f"DTD/entity declarations are unsupported in {label}")
    try:
        return ElementTree.fromstring(data)
    except (ElementTree.ParseError, UnicodeError) as exc:
        raise ArtifactError(f"malformed XML in {label}: {exc}") from exc


def _parse_guid(value: str, label: str) -> str:
    normalized = value.strip().strip("{}").lower()
    if not _GUID.fullmatch(normalized):
        raise ArtifactError(f"invalid workflow GUID in {label}: {value!r}")
    return normalized


def _cloud_workflow_metadata(root: ElementTree.Element, label: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    for node in root.iter():
        if _local_name(node.tag) != "workflow":
            continue
        attrs = {_local_name(key): value for key, value in node.attrib.items()}
        if "workflowid" not in attrs:
            continue
        children: dict[str, list[str]] = {}
        for child in list(node):
            children.setdefault(_local_name(child.tag), []).append((child.text or "").strip())
        category_values = children.get("category", [])
        if "5" not in category_values:
            continue
        for field in ("category", "type", "jsonfilename"):
            if len(children.get(field, [])) != 1:
                raise ArtifactError(f"cloud-flow metadata must contain exactly one {field} element in {label}")
        workflow_type = children["type"][0]
        if workflow_type != "1":
            continue
        json_name = children["jsonfilename"][0]
        if not json_name:
            raise ArtifactError(f"cloud-flow metadata has no JsonFileName in {label}")
        normalized_name = json_name.lstrip("/").casefold()
        if not normalized_name.startswith("workflows/") or not normalized_name.endswith(".json"):
            raise ArtifactError(f"cloud-flow metadata has unsafe or unsupported JsonFileName in {label}")
        records.append((normalized_name, _parse_guid(attrs["workflowid"], label)))
    return records


def _workflow_json_ids(archive: zipfile.ZipFile, infos: list[zipfile.ZipInfo]) -> list[str]:
    for info in infos:
        path = info.filename.casefold()
        if info.is_dir():
            continue
        if "modernflows" in path.split("/"):
            raise ArtifactError("modernflows/ YAML source packages are unsupported by the XML ZIP verifier")
        if path.startswith("workflows/") and not path.endswith((".json", ".json.data.xml")):
            raise ArtifactError(f"unsupported file type in Workflows package directory: {info.filename}")
    entries = [i for i in infos if not i.is_dir() and i.filename.casefold().startswith("workflows/")
               and i.filename.casefold().endswith(".json")]
    ids: list[str] = []
    info_by_path = {i.filename.casefold(): i for i in infos if not i.is_dir()}
    metadata_records: list[tuple[str, str]] = []
    customization_info = next((i for i in infos if not i.is_dir() and
                               i.filename.casefold() in {"customizations.xml", "other/customizations.xml"}), None)
    if customization_info is None:
        raise ArtifactError("solution ZIP is missing Customizations.xml")
    customization_root = _parse_xml(_member_data(archive, customization_info, MAX_XML_BYTES),
                                    customization_info.filename)
    metadata_records.extend(_cloud_workflow_metadata(customization_root, customization_info.filename))
    sidecars: set[str] = set()
    for info in infos:
        if info.is_dir() or not info.filename.casefold().startswith("workflows/") or \
                not info.filename.casefold().endswith(".json.data.xml"):
            continue
        sidecars.add(info.filename.casefold())
        metadata = _parse_xml(_member_data(archive, info, MAX_XML_BYTES), info.filename)
        metadata_records.extend(_cloud_workflow_metadata(metadata, info.filename))
    paths = [path for path, _ in metadata_records]
    if len(paths) != len(set(paths)):
        raise ArtifactError("duplicate cloud-flow metadata JsonFileName entries")
    metadata_by_path = dict(metadata_records)
    for info in entries:
        document = _json_load(_member_data(archive, info, MAX_FLOW_JSON_BYTES), info.filename)
        if not isinstance(document, dict):
            raise ArtifactError(f"workflow JSON must be an object: {info.filename}")
        workflow_id = metadata_by_path.get(info.filename.casefold())
        if workflow_id is None:
            raise ArtifactError(f"workflow JSON has no cloud-flow metadata mapping: {info.filename}")
        filename_id = re.search(r"-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.json$",
                                info.filename, re.IGNORECASE)
        if filename_id is None or filename_id.group(1).lower() != workflow_id:
            raise ArtifactError(f"workflow metadata ID does not match stable ID in filename: {info.filename}")
        ids.append(workflow_id)
    if set(metadata_by_path) != {info.filename.casefold() for info in entries}:
        raise ArtifactError("cloud-flow metadata references a missing workflow JSON file")
    for sidecar in sidecars:
        if sidecar[:-len(".data.xml")] not in info_by_path:
            raise ArtifactError(f"workflow metadata sidecar has no matching JSON file: {sidecar}")
    if len(ids) != len(set(ids)):
        raise ArtifactError("solution ZIP contains duplicate cloud-flow workflow IDs")
    return ids


def _root_workflow_ids(root: ElementTree.Element) -> set[str]:
    found: set[str] = set()
    for node in root.iter():
        if _local_name(node.tag) != "rootcomponent":
            continue
        component_type = next((value for key, value in node.attrib.items()
                               if _local_name(key) == "type"), None)
        component_id = next((value for key, value in node.attrib.items()
                            if _local_name(key) == "id"), None)
        if component_type == "29" and component_id:
            found.add(_parse_guid(component_id, "Solution.xml RootComponent"))
    return found


def _inspect_zip(zip_bytes: bytes, manifest: Any, expected_solution: str,
                 expected_version: str | None = None) -> dict[str, Any]:
    if not isinstance(expected_solution, str) or not _SOLUTION.fullmatch(expected_solution):
        raise ArtifactError("expected solution must be a valid solution unique name")
    manifest, manifest_ids = _validate_manifest(manifest, expected_solution)
    archive, infos = _archive_members(zip_bytes)
    try:
        solution_info = _locate_xml(infos, "solution.xml")
        customizations_info = _locate_xml(infos, "customizations.xml")
        solution_root = _parse_xml(_member_data(archive, solution_info, MAX_XML_BYTES), solution_info.filename)
        # Customizations.xml is parsed even though workflow identities are bound from the
        # documented Workflows/*.json package inventory and solution root components.
        _parse_xml(_member_data(archive, customizations_info, MAX_XML_BYTES), customizations_info.filename)
        solution_manifests = [node for node in solution_root.iter()
                              if _local_name(node.tag) == "solutionmanifest"]
        if len(solution_manifests) != 1:
            raise ArtifactError("solution.xml must contain exactly one SolutionManifest")
        solution_manifest = solution_manifests[0]
        unique_name = _child_text(solution_manifest, "UniqueName", "SolutionManifest")
        version = _child_text(solution_manifest, "Version", "SolutionManifest")
        managed = _child_text(solution_manifest, "Managed", "SolutionManifest").casefold()
        if unique_name != expected_solution:
            raise ArtifactError(f"ZIP solution {unique_name!r} does not match expected {expected_solution!r}")
        if not _VERSION.fullmatch(version):
            raise ArtifactError(f"invalid four-part solution version: {version!r}")
        if expected_version is not None and version != expected_version:
            raise ArtifactError(f"ZIP solution version {version!r} does not match expected {expected_version!r}")
        if managed not in {"1", "true"}:
            raise ArtifactError("solution ZIP is not marked managed")
        flow_ids = _workflow_json_ids(archive, infos)
        if set(flow_ids) != set(manifest_ids) or len(flow_ids) != len(manifest_ids):
            missing = sorted(set(flow_ids) - set(manifest_ids))
            foreign = sorted(set(manifest_ids) - set(flow_ids))
            raise ArtifactError(f"activation manifest does not exactly cover ZIP cloud flows; "
                                f"missing={missing}, foreign={foreign}")
        root_ids = _root_workflow_ids(solution_root)
        if flow_ids and not root_ids:
            raise ArtifactError("cloud-flow files exist but solution root components contain no workflow type 29 IDs")
        unrooted = sorted(set(flow_ids) - root_ids)
        if unrooted:
            raise ArtifactError(f"cloud-flow files are not referenced by solution root components: {unrooted}")
        # Read all remaining entries to force CRC/decompression validation before binding bytes.
        for info in infos:
            if not info.is_dir() and info not in (solution_info, customizations_info):
                _member_data(archive, info, MAX_UNCOMPRESSED_BYTES)
        return {
            "version": DESCRIPTOR_VERSION,
            "solution": unique_name,
            "solutionVersion": version,
            "managed": True,
            "cloudFlowIds": sorted(flow_ids),
            "zipSha256": hashlib.sha256(zip_bytes).hexdigest(),
            "manifestSha256": hashlib.sha256(_canonical_json(manifest)).hexdigest(),
        }
    finally:
        archive.close()


def verify_bytes(zip_bytes: bytes, manifest: dict[str, Any], expected_solution: str,
                 expected_version: str | None = None) -> dict[str, Any]:
    """Inspect exact ZIP bytes and manifest object; useful immediately before a local import."""
    if not isinstance(zip_bytes, bytes):
        raise TypeError("zip_bytes must be bytes")
    return _inspect_zip(zip_bytes, manifest, expected_solution, expected_version)


def load_json(path: str | Path) -> Any:
    """Load strict UTF-8 JSON, rejecting duplicate object keys and non-JSON constants."""
    return _json_load(Path(path).read_bytes(), str(path))


def build_descriptor(zip_path: str | Path, manifest_path: str | Path, expected_solution: str,
                     descriptor_path: str | Path | None = None,
                     expected_version: str | None = None) -> dict[str, Any]:
    """Inspect local release inputs and optionally write a deterministic descriptor."""
    zip_bytes = Path(zip_path).read_bytes()
    manifest_bytes = Path(manifest_path).read_bytes()
    manifest = _json_load(manifest_bytes, str(manifest_path))
    descriptor = verify_bytes(zip_bytes, manifest, expected_solution, expected_version)
    if descriptor_path is not None:
        _write_json_atomic(Path(descriptor_path), descriptor)
    return descriptor


def verify_descriptor_bytes(zip_bytes: bytes, manifest: dict[str, Any], descriptor: dict[str, Any],
                           expected_solution: str, expected_version: str) -> dict[str, Any]:
    """Verify a saved descriptor against the exact in-memory bytes intended for import."""
    if not isinstance(descriptor, dict) or set(descriptor) != {
        "version", "solution", "solutionVersion", "managed", "cloudFlowIds", "zipSha256", "manifestSha256"
    }:
        raise ArtifactError("release descriptor has an unsupported shape")
    current = verify_bytes(zip_bytes, manifest, expected_solution, expected_version)
    if _canonical_json(descriptor) != _canonical_json(current):
        raise ArtifactError("release descriptor does not match the supplied ZIP and activation manifest")
    return current


def verify_descriptor(zip_path: str | Path, manifest_path: str | Path,
                      descriptor_path: str | Path, expected_solution: str,
                      expected_version: str) -> dict[str, Any]:
    """Recompute package evidence and require exact agreement with a saved descriptor."""
    zip_bytes = Path(zip_path).read_bytes()
    manifest = _json_load(Path(manifest_path).read_bytes(), str(manifest_path))
    stored = _json_load(Path(descriptor_path).read_bytes(), str(descriptor_path))
    return verify_descriptor_bytes(zip_bytes, manifest, stored, expected_solution, expected_version)


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Inspect and bind managed solution release artifacts")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="inspect inputs and write a release descriptor")
    build.add_argument("--zip", required=True)
    build.add_argument("--manifest", required=True)
    build.add_argument("--solution", required=True)
    build.add_argument("--version")
    build.add_argument("--descriptor", required=True)
    verify = commands.add_parser("verify", help="recheck an existing release descriptor against local files")
    verify.add_argument("--zip", required=True)
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--solution", required=True)
    verify.add_argument("--version", required=True)
    verify.add_argument("--descriptor", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            descriptor = build_descriptor(args.zip, args.manifest, args.solution, args.descriptor, args.version)
        else:
            descriptor = verify_descriptor(args.zip, args.manifest, args.descriptor, args.solution, args.version)
        print(json.dumps(descriptor, sort_keys=True, indent=2))
        return 0
    except (ArtifactError, OSError, TypeError) as exc:
        print(f"artifact verification failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
