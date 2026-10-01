import json
import re
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from pipeline.artifacts import (ArtifactError, build_descriptor, load_json, verify_bytes,
                                verify_descriptor, verify_descriptor_bytes)


A = "11111111-1111-1111-1111-111111111111"
B = "22222222-2222-2222-2222-222222222222"


def package(*workflow_ids, unique_name="Demo", version="2.3.4.5", managed="1", root_ids=None,
            customizations="<ImportExportXml />", workflow_json=None, sidecar_ids=None, sidecars=True):
    root_ids = workflow_ids if root_ids is None else root_ids
    solution = (
        f"<ImportExportXml><SolutionManifest><UniqueName>{unique_name}</UniqueName>"
        f"<Version>{version}</Version><Managed>{managed}</Managed><RootComponents>"
        + "".join(f'<RootComponent type="29" id="{{{wid}}}" />' for wid in root_ids)
        + "</RootComponents></SolutionManifest></ImportExportXml>"
    )
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Other/Solution.xml", solution)
        archive.writestr("Other/Customizations.xml", customizations)
        for workflow_id in workflow_ids:
            filename = f"Workflows/Flow-{workflow_id.upper()}.json"
            content = (workflow_json or {}).get(workflow_id, {"properties": {"displayName": "fixture"}})
            archive.writestr(filename, json.dumps(content))
            metadata_id = (sidecar_ids or {}).get(workflow_id, workflow_id)
            if sidecars:
                archive.writestr(filename + ".data.xml",
                                 f'<Workflow WorkflowId="{{{metadata_id}}}"><JsonFileName>/{filename}</JsonFileName>'
                                 "<Type>1</Type><Category>5</Category></Workflow>")
    return stream.getvalue()


def manifest(*workflow_ids):
    return {"version": 1, "solution": "Demo",
            "flows": [{"workflowId": wid, "enabled": True} for wid in workflow_ids]}


def test_verifies_managed_identity_inventory_and_hashes_exact_inputs():
    data = package(A, B)
    result = verify_bytes(data, manifest(B, A), "Demo", "2.3.4.5")
    assert result["solution"] == "Demo"
    assert result["solutionVersion"] == "2.3.4.5"
    assert result["managed"] is True
    assert result["cloudFlowIds"] == [A, B]
    assert result["zipSha256"]
    assert result["manifestSha256"]


def test_accepts_explicit_empty_manifest_for_flowless_package():
    assert verify_bytes(package(), manifest(), "Demo")["cloudFlowIds"] == []


@pytest.mark.parametrize("kwargs", [
    {"unique_name": "Other"},
    {"version": "2.3.4"},
    {"managed": "0"},
    {"root_ids": []},
])
def test_rejects_unrelated_unmanaged_invalid_or_unrooted_package(kwargs):
    data = package(A, **kwargs)
    with pytest.raises(ArtifactError):
        verify_bytes(data, manifest(A), "Demo")


@pytest.mark.parametrize("bad", [
    {"version": 1, "solution": "Demo", "flows": [{"workflowId": A, "enabled": 1}]},
    {"version": 1, "solution": "Demo", "flows": [{"workflowId": A.upper(), "enabled": True}]},
    {"version": 1, "solution": "Demo", "flows": [{"workflowId": A, "enabled": True},
                                                        {"workflowId": A, "enabled": False}]},
    {"version": 1, "solution": "Demo", "flows": [], "extra": True},
    {"version": True, "solution": "Demo", "flows": []},
])
def test_rejects_malformed_or_duplicate_manifest_entries(bad):
    with pytest.raises(ArtifactError):
        verify_bytes(package(), bad, "Demo")


@pytest.mark.parametrize("listed,actual", [((A,), (B,)), ((A, B), (A,)), ((A, A), (A,))])
def test_rejects_missing_foreign_or_duplicate_zip_workflow_ids(listed, actual):
    data = package(*actual)
    with pytest.raises(ArtifactError, match="exactly cover|duplicate cloud-flow|duplicate activation manifest"):
        verify_bytes(data, manifest(*listed), "Demo")


def test_rejects_workflow_id_disagreement_between_json_and_filename():
    data = package(A, sidecar_ids={A: B})
    with pytest.raises(ArtifactError, match="ID does not match"):
        verify_bytes(data, manifest(A), "Demo")


def test_rejects_flow_json_without_metadata_sidecar():
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("Other/Solution.xml", "<ImportExportXml><SolutionManifest><UniqueName>Demo</UniqueName>"
                         "<Version>1.0.0.0</Version><Managed>1</Managed><RootComponents /></SolutionManifest></ImportExportXml>")
        archive.writestr("Other/Customizations.xml", "<ImportExportXml />")
        archive.writestr(f"Workflows/Flow-{A.upper()}.json", "{}")
    with pytest.raises(ArtifactError, match="no cloud-flow metadata mapping"):
        verify_bytes(stream.getvalue(), manifest(A), "Demo")


def test_accepts_workflow_metadata_declared_inline_in_customizations_xml():
    filename = f"Workflows/Flow-{A.upper()}.json"
    customizations = (f'<ImportExportXml><Workflows><Workflow WorkflowId="{{{A}}}">'
                      f'<JsonFileName>/{filename}</JsonFileName><Type>1</Type><Category>5</Category>'
                      "</Workflow></Workflows></ImportExportXml>")
    data = package(A, customizations=customizations, sidecars=False)
    assert verify_bytes(data, manifest(A), "Demo")["cloudFlowIds"] == [A]


@pytest.mark.parametrize("member", ["../solution.xml", "/absolute.json", "C:/escape.txt", "folder\\escape.txt"])
def test_rejects_unsafe_zip_member_paths(member):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member, "bad")
    with pytest.raises(ArtifactError, match="unsafe|drive-qualified"):
        verify_bytes(stream.getvalue(), manifest(), "Demo")


def test_rejects_duplicate_and_case_colliding_zip_members():
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("solution.xml", "x")
        archive.writestr("SOLUTION.XML", "x")
    with pytest.raises(ArtifactError, match="duplicate or case-colliding"):
        verify_bytes(stream.getvalue(), manifest(), "Demo")


def test_rejects_malformed_customizations_xml():
    with pytest.raises(ArtifactError, match="malformed XML"):
        verify_bytes(package(customizations="<broken>"), manifest(), "Demo")


@pytest.mark.parametrize("payload", [
    "<!DOCTYPE x [<!ENTITY e 'expanded'>]><ImportExportXml>&e;</ImportExportXml>".encode("utf-16"),
    b"<!DOCTYPE x><ImportExportXml />",
])
def test_rejects_doctype_even_when_xml_is_not_plain_utf8(payload):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("solution.xml", payload if payload.startswith(b"\xff\xfe") else
                         "<ImportExportXml><SolutionManifest><UniqueName>Demo</UniqueName>"
                         "<Version>1.0.0.0</Version><Managed>1</Managed><RootComponents /></SolutionManifest></ImportExportXml>")
        archive.writestr("customizations.xml", payload)
    with pytest.raises(ArtifactError, match="DTD/entity|non-UTF-8"):
        verify_bytes(stream.getvalue(), manifest(), "Demo")


@pytest.mark.parametrize("member", ["modernflows/flow.yaml", "Workflows/flow.yaml"])
def test_rejects_unsupported_flow_package_formats(member):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("solution.xml", "<ImportExportXml><SolutionManifest><UniqueName>Demo</UniqueName>"
                         "<Version>1.0.0.0</Version><Managed>1</Managed><RootComponents /></SolutionManifest></ImportExportXml>")
        archive.writestr("customizations.xml", "<ImportExportXml />")
        archive.writestr(member, "flow source")
    with pytest.raises(ArtifactError, match="unsupported"):
        verify_bytes(stream.getvalue(), manifest(), "Demo")


def test_descriptor_detects_zip_manifest_and_expected_version_changes(tmp_path):
    zip_path = tmp_path / "Demo.zip"
    manifest_path = tmp_path / "Demo.activation.json"
    descriptor_path = tmp_path / "Demo.release.json"
    zip_path.write_bytes(package(A))
    manifest_path.write_text(json.dumps(manifest(A)), encoding="utf-8")
    build_descriptor(zip_path, manifest_path, "Demo", descriptor_path, "2.3.4.5")
    assert verify_descriptor(zip_path, manifest_path, descriptor_path, "Demo", "2.3.4.5")

    zip_path.write_bytes(package(A, version="2.3.4.6"))
    with pytest.raises(ArtifactError, match="descriptor does not match"):
        verify_descriptor(zip_path, manifest_path, descriptor_path, "Demo", "2.3.4.6")
    zip_path.write_bytes(package(A))
    manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
    with pytest.raises(ArtifactError, match="exactly cover"):
        verify_descriptor(zip_path, manifest_path, descriptor_path, "Demo", "2.3.4.5")


def test_descriptor_uses_strict_json_types(tmp_path):
    zip_path = tmp_path / "Demo.zip"
    manifest_path = tmp_path / "Demo.activation.json"
    descriptor_path = tmp_path / "Demo.release.json"
    zip_path.write_bytes(package())
    manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
    descriptor = build_descriptor(zip_path, manifest_path, "Demo", descriptor_path)
    descriptor["version"] = True
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    with pytest.raises(ArtifactError, match="descriptor does not match"):
        verify_descriptor(zip_path, manifest_path, descriptor_path, "Demo", "2.3.4.5")


def test_descriptor_verification_can_bind_the_exact_in_memory_import_bytes(tmp_path):
    data = package(A)
    descriptor = verify_bytes(data, manifest(A), "Demo", "2.3.4.5")
    assert verify_descriptor_bytes(data, manifest(A), descriptor, "Demo", "2.3.4.5") == descriptor
    with pytest.raises(ArtifactError, match="does not match expected"):
        verify_descriptor_bytes(package(A, version="2.3.4.6"), manifest(A), descriptor,
                                "Demo", "2.3.4.5")


def test_rejects_zip_with_truncated_or_invalid_archive_bytes():
    with pytest.raises(ArtifactError):
        verify_bytes(b"not a zip", manifest(), "Demo")


def test_release_descriptor_matches_contract_shape_and_strict_json_rejects_duplicates(tmp_path):
    schema = json.loads((Path(__file__).parents[2] / "contracts/release-artifact.schema.json").read_text())
    descriptor = verify_bytes(package(A), manifest(A), "Demo")
    assert set(descriptor) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert descriptor["version"] == 1 and descriptor["managed"] is True
    assert re.fullmatch(schema["properties"]["solutionVersion"]["pattern"], "1.0.0.0")
    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text('{"version":1,"version":1}', encoding="utf-8")
    with pytest.raises(ArtifactError, match="duplicate JSON property"):
        load_json(duplicate_path)


def test_release_descriptor_schema_is_valid_draft4_when_jsonschema_is_installed():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((Path(__file__).parents[2] / "contracts/release-artifact.schema.json").read_text())
    jsonschema.Draft4Validator.check_schema(schema)
    jsonschema.Draft4Validator(schema).validate(verify_bytes(package(A), manifest(A), "Demo"))


def test_build_and_verify_cli_operate_on_local_files(tmp_path):
    zip_path = tmp_path / "Demo.zip"
    manifest_path = tmp_path / "Demo.activation.json"
    descriptor_path = tmp_path / "Demo.release.json"
    zip_path.write_bytes(package(A))
    manifest_path.write_text(json.dumps(manifest(A)), encoding="utf-8")
    build = subprocess.run([
        sys.executable, "-m", "pipeline.artifacts", "build", "--zip", str(zip_path),
        "--manifest", str(manifest_path), "--solution", "Demo", "--version", "2.3.4.5",
        "--descriptor", str(descriptor_path),
    ], capture_output=True, text=True, check=False)
    assert build.returncode == 0, build.stderr
    verify = subprocess.run([
        sys.executable, "-m", "pipeline.artifacts", "verify", "--zip", str(zip_path),
        "--manifest", str(manifest_path), "--solution", "Demo", "--version", "2.3.4.5",
        "--descriptor", str(descriptor_path),
    ], capture_output=True, text=True, check=False)
    assert verify.returncode == 0, verify.stderr
    assert json.loads(verify.stdout)["cloudFlowIds"] == [A]
