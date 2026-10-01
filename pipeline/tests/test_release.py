import base64
import io
import json
from unittest.mock import Mock
import zipfile

import pytest

from pipeline import artifacts, release, settings


def package():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("solution.xml", "<ImportExportXml><SolutionManifest><UniqueName>Demo</UniqueName>"
                         "<Version>1.0.0.0</Version><Managed>1</Managed><Publisher><UniqueName>dev</UniqueName>"
                         "</Publisher><RootComponents/></SolutionManifest></ImportExportXml>")
        archive.writestr("customizations.xml", "<ImportExportXml/>")
    return stream.getvalue()


def config():
    return {"mode": "isolated", "tenant_id": "1c5afb69-a82c-4c81-b2cc-743ce7f91dac",
            "allowed_accounts": ["kriall076@7xpydh.onmicrosoft.com"],
            "environment_id": "8fcc484b-d74e-e479-84da-ad5a78d6d55b",
            "organization_url": "https://testorg5fd244de.crm17.dynamics.com",
            "site_url": "https://7xpydh.sharepoint.com/sites/ALM-Test",
            "solution": "ALMQualification", "publisher": "almspike",
            "connections": {"dataverse": "shared-commondataser-test", "sharepoint": "shared-sharepointonl-test"},
            "lists": {"config": "11111111-1111-4111-8111-111111111111",
                      "connections": "22222222-2222-4222-8222-222222222222",
                      "variables": "33333333-3333-4333-8333-333333333333"}}


@pytest.fixture(autouse=True)
def restore_settings():
    before = {key: value for key, value in vars(settings).items() if key.isupper()}
    yield
    for key, value in before.items():
        setattr(settings, key, value)


def test_descriptor_tamper_fails_before_authentication_or_write():
    data = package()
    manifest = {"version": 1, "solution": "Demo", "flows": []}
    descriptor = artifacts.verify_bytes(data, manifest, "Demo", "1.0.0.0")
    descriptor["zipSha256"] = "0" * 64
    api, token = Mock(), Mock()
    with pytest.raises(ValueError, match="descriptor"):
        release.import_verified(data, manifest, descriptor, config(), {"connections": [], "variables": []},
                                api=api, token_provider=token)
    api.assert_not_called()
    token.assert_not_called()


def test_exact_verified_bytes_are_submitted_and_target_version_is_checked():
    data = package()
    manifest = {"version": 1, "solution": "Demo", "flows": []}
    descriptor = artifacts.verify_bytes(data, manifest, "Demo", "1.0.0.0")
    api = Mock(side_effect=[{"value": []}, {"AsyncOperationId": "job", "ImportJobKey": "key"},
                            {"statecode": 3, "statuscode": 30},
                            {"value": [{"uniquename": "Demo", "version": "1.0.0.0", "ismanaged": True}]}])
    result = release.import_verified(data, manifest, descriptor, config(), {"connections": [], "variables": []},
                                     api=api, token_provider=Mock(return_value="token"))
    assert result["status"] == "Succeeded"
    post = api.call_args_list[1]
    assert post.args[1:3] == ("POST", "ImportSolutionAsync")
    assert base64.b64decode(post.args[3]["CustomizationFile"]) == data
    assert post.args[3]["PublishWorkflows"] is False


@pytest.mark.parametrize("inventory", [
    {"value": [{"workflowid": "existing"}]},
    {"value": [], "@odata.nextLink": "next"},
    {"value": [], "@Microsoft.Dynamics.CRM.morerecords": True},
])
def test_target_cloud_flows_or_incomplete_inventory_block_all_writes(inventory):
    data = package()
    manifest = {"version": 1, "solution": "Demo", "flows": []}
    descriptor = artifacts.verify_bytes(data, manifest, "Demo", "1.0.0.0")
    api = Mock(return_value=inventory)
    with pytest.raises(ValueError):
        release.import_verified(data, manifest, descriptor, config(), {"connections": [], "variables": []},
                                api=api, token_provider=Mock(return_value="token"))
    assert all(call.args[1] == "GET" for call in api.call_args_list)


def test_failed_import_stops_before_success_readback():
    data = package()
    manifest = {"version": 1, "solution": "Demo", "flows": []}
    descriptor = artifacts.verify_bytes(data, manifest, "Demo", "1.0.0.0")
    api = Mock(side_effect=[{"value": []}, {"AsyncOperationId": "job"},
                            {"statecode": 3, "statuscode": 31, "message": "missing dependency"}])
    with pytest.raises(RuntimeError, match="missing dependency"):
        release.import_verified(data, manifest, descriptor, config(), {"connections": [], "variables": []},
                                api=api, token_provider=Mock(return_value="token"))
    assert api.call_count == 3


def test_duplicate_component_bindings_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        release.component_parameters({"connections": [], "variables": [
            {"schemaName": "dev_List", "value": "a"}, {"schemaName": "dev_List", "value": "b"}]})


def test_dynamic_flow_api_uses_applied_target(monkeypatch):
    from pipeline import flowapi
    monkeypatch.setattr(settings, "ADMIN_ENV_ID", "isolated-env")
    assert flowapi.flow_api().endswith("/isolated-env")
