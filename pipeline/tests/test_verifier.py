import base64
import json
from http.server import HTTPServer
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from pipeline import artifact_bridge, artifacts, flows, verifier
from pipeline.tests.test_release import package


def request():
    return {"zipBase64": base64.b64encode(package()).decode(),
            "manifest": {"version": 1, "solution": "Demo", "flows": []},
            "solution": "Demo", "solutionVersion": "1.0.0.0"}


def test_verifier_returns_the_exact_verified_bytes_and_rejects_descriptor_tamper():
    body = request()
    result = verifier.verify_request(body)
    assert result["zipBase64"] == body["zipBase64"]
    body["descriptor"] = {**result["descriptor"], "manifestSha256": "0" * 64}
    with pytest.raises(ValueError, match="descriptor"):
        verifier.verify_request(body)


@pytest.mark.parametrize("change", [{"solution": "Other"}, {"solutionVersion": "2.0.0.0"},
                                     {"zipBase64": "not-base64"}])
def test_verifier_rejects_wrong_package_identity_version_or_content(change):
    with pytest.raises(ValueError):
        verifier.verify_request({**request(), **change})


def test_http_endpoint_requires_authentication_before_inspection():
    server = HTTPServer(("127.0.0.1", 0), verifier.handler("test-secret" * 4))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/verify"
        with pytest.raises(HTTPError) as error:
            urlopen(Request(url, data=b"{}", method="POST"), timeout=3)
        assert error.value.code == 401
        payload = json.dumps(request()).encode()
        with urlopen(Request(url, data=payload, headers={"Authorization": "Bearer " + "test-secret" * 4},
                             method="POST"), timeout=3) as response:
            assert json.load(response)["descriptor"]["solution"] == "Demo"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_unconfigured_verifier_blocks_c1_and_direct_c2_before_archive_or_import(monkeypatch):
    monkeypatch.delenv("ALM_ARTIFACT_VERIFIER_URL", raising=False)
    c1 = flows.c1({})["properties"]["definition"]["actions"]["Main"]["actions"]["Export"]["actions"]["If_export_release"]["actions"]
    success = c1["Export_succeeded"]["actions"]
    assert success["Inspect_export"]["type"] == "Scope"
    assert success["Archive_ZIP"]["runAfter"] == {"Inspect_export": ["Succeeded"]}
    c2 = flows.c2()["properties"]["definition"]["actions"]["Try"]["actions"]
    assert c2["Verify_archived_ZIP"]["type"] == "Scope"
    assert c2["Import_to_target"]["runAfter"] == {"Verify_archived_ZIP": ["Succeeded"]}
    assert c2["Import_to_target"]["inputs"]["parameters"]["item"]["CustomizationFile"] == \
        "@body('Verify_archived_ZIP')?['zipBase64']"


def test_configured_bridge_protects_payload_and_auth_in_run_history(monkeypatch):
    monkeypatch.setenv("ALM_ARTIFACT_VERIFIER_URL", "https://approved.example/verify")
    monkeypatch.setenv("ALM_ARTIFACT_VERIFIER_AUTHORIZATION", "Bearer " + "a" * 32)
    action = artifact_bridge.verification_action("zip", "manifest", "Demo", "1.0.0.0", "descriptor")
    assert action["inputs"]["body"]["descriptor"] == "descriptor"
    assert action["inputs"]["headers"]["Authorization"] == "@parameters('$artifactVerifierAuthorization')"
    assert action["runtimeConfiguration"]["secureData"]["properties"] == ["inputs", "outputs"]
    cd = artifact_bridge.add_authorization_parameter(flows.c1({}))
    assert cd["properties"]["definition"]["parameters"]["$artifactVerifierAuthorization"]["type"] == "SecureString"
    assert cd["properties"]["definition"]["parameters"]["$artifactVerifierAuthorization"]["defaultValue"] == ""
    assert "a" * 32 not in json.dumps(cd)


@pytest.mark.parametrize("run_import,run_post,export_needed", [
    (False, True, False), (True, True, True), (True, False, True), (False, False, True),
])
def test_configuration_only_skips_zip_and_target_policy_is_not_bound_to_dev_export(run_import, run_post, export_needed):
    from pipeline.tests.activation_runtime import Runtime
    action = flows.c1({})["properties"]["definition"]["actions"]["Main"]["actions"]["Export"]["actions"]["If_export_release"]
    runtime = Runtime({}, [])
    runtime.results["Config"] = {"RunImport": run_import, "RunPostImport": run_post}
    assert runtime.condition(action["expression"]) == export_needed
    # This exercises the emitted condition; the false branch has no archive/import actions.
    if not export_needed:
        runtime.run({"If_export_release": action})
        assert set(runtime.results) == {"Config", "If_export_release"}
