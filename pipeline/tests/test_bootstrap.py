import json

import pytest

from pipeline import bootstrap, defs, settings as s


@pytest.fixture(autouse=True)
def configure_test_target(monkeypatch):
    monkeypatch.setattr(s, "ADMIN_ENV_ID", bootstrap.TEST_ENV_ID)
    monkeypatch.setattr(s, "ADMIN", bootstrap.TEST_ORG)
    monkeypatch.setattr(s, "ADMIN_SITE", bootstrap.TEST_SITE)
    monkeypatch.setattr(s, "DV_CONN", bootstrap.TEST_DV_CONN)
    monkeypatch.setattr(s, "SP_CONN", bootstrap.TEST_SP_CONN)
    refs = {
        "alm_PipelineDataverse_ALMQualification": ("ALM Qualification Dataverse", s.DV_API, bootstrap.TEST_DV_CONN),
        "alm_PipelineSharePoint_ALMQualification": ("ALM Qualification SharePoint", s.SP_API, bootstrap.TEST_SP_CONN),
    }
    monkeypatch.setattr(s, "CONN_REFS", refs)
    monkeypatch.setattr(s, "FLOW_REFS", {
        s.DV_KEY: ("alm_PipelineDataverse_ALMQualification", s.DV_API),
        s.SP_KEY: ("alm_PipelineSharePoint_ALMQualification", s.SP_API),
    })


def actions(cd):
    return cd["properties"]["definition"]["actions"]


def walk(level):
    for name, action in level.items():
        yield name, action
        if isinstance(action.get("actions"), dict):
            yield from walk(action["actions"])
        branch = action.get("else")
        if isinstance(branch, dict) and isinstance(branch.get("actions"), dict):
            yield from walk(branch["actions"])


def test_build_returns_valid_flow_with_failmessage_and_readback():
    cd = bootstrap.build()
    assert defs.validate(cd) == []
    a = actions(cd)
    assert list(a)[0] == "Init_FailMessage"
    assert a["Init_FailMessage"]["type"] == "InitializeVariable"
    assert list(a)[-2:] == ["Results", "Stop_on_failure"]
    results = a["Results"]["inputs"]
    assert set(results["lists"]) == {"ALMQConfig", "ALMQConnections", "ALMQVariables"}
    assert "ALMQConfig.TargetEnvironment" in results["fields"]
    assert "ALMQConnections.ConnectionId" in results["fields"]
    assert "ALMQVariables.SchemaName" in results["fields"]
    json.dumps(cd)


def test_lists_require_404_and_fields_require_successful_empty_collection():
    a = actions(bootstrap.build())
    for title in bootstrap.LIST_FIELDS:
        get = a[f"Get_list_{title}"]
        ensure = a[f"Ensure_list_{title}"]
        assert get["inputs"]["parameters"]["parameters/method"] == "GET"
        assert ensure["expression"] == {"equals": [f"@actions('Get_list_{title}')?['outputs']?['statusCode']", 404]}
        assert f"Create_list_{title}" in ensure["actions"]
        assert ensure["runAfter"][f"Get_list_{title}"] == ["Succeeded", "Failed", "TimedOut"]
        for name in bootstrap.LIST_FIELDS[title]:
            field_get = a[f"Get_field_{title}_{name}"]
            field_ensure = a[f"Ensure_field_{title}_{name}"]
            assert field_get["inputs"]["parameters"]["parameters/uri"].endswith(
                f"$select=InternalName,TypeAsString&$filter=InternalName%20eq%20'{name}'&$top=2")
            assert field_ensure["expression"] == {
                "equals": [f"@actions('Get_field_{title}_{name}')?['outputs']?['statusCode']", 200]}
            empty = field_ensure["actions"][f"Field_results_{title}_{name}"]
            assert empty["expression"]["and"][0] == {"equals": [
                f"@length(body('Get_field_{title}_{name}')?['value'])", 0]}
            create = empty["actions"][f"Create_field_{title}_{name}"]
            assert create["inputs"]["parameters"]["parameters/method"] == "POST"
            assert "CreateFieldAsXml" in create["inputs"]["parameters"]["parameters/uri"]
            assert field_get["inputs"]["parameters"]["parameters/headers"]["Accept"] == bootstrap.JSON_NOMETA


def test_auth_or_non_404_lookup_failure_sets_failmessage():
    a = actions(bootstrap.build())
    list_ensure = a["Ensure_list_ALMQConfig"]
    non_404 = list_ensure["else"]["actions"]["Check_existing_list_ALMQConfig"]
    assert non_404["expression"] == {
        "equals": ["@actions('Get_list_ALMQConfig')?['outputs']?['statusCode']", 200]}
    assert "Fail_ALMQConfig" in non_404["else"]["actions"]
    field_ensure = a["Ensure_field_ALMQConfig_SolutionName"]
    assert "Fail_field ALMQConfig.SolutionName" in field_ensure["else"]["actions"]
    empty_else = field_ensure["actions"]["Field_results_ALMQConfig_SolutionName"]["else"]["actions"]
    assert "Field_results_ambiguous_ALMQConfig_SolutionName" in \
        empty_else["Check_one_field_ALMQConfig_SolutionName"]["else"]["actions"]
    assert a["Stop_on_failure"]["else"]["actions"]["Terminate_failed"]["inputs"]["runStatus"] == "Failed"


def test_existing_field_type_mismatch_fails_without_modifying_field():
    a = actions(bootstrap.build())
    ensure = a["Ensure_field_ALMQConfig_SolutionName"]
    type_check = ensure["actions"]["Field_results_ALMQConfig_SolutionName"]["else"]["actions"][
        "Check_one_field_ALMQConfig_SolutionName"]["actions"]["Check_existing_type_ALMQConfig_SolutionName"]
    assert type_check["expression"] == {
        "equals": ["@first(body('Get_field_ALMQConfig_SolutionName')?['value'])?['TypeAsString']", "Text"]}
    all_actions = list(walk(a))
    methods = [item["inputs"]["parameters"].get("parameters/method")
               for _, item in all_actions if item.get("type") == "OpenApiConnection"]
    assert "PATCH" not in methods and "DELETE" not in methods
    readback = a["Check_field_ALMQConfig_SolutionName"]["actions"]["Check_one_readback_ALMQConfig_SolutionName"][
        "actions"]["Check_readback_type_ALMQConfig_SolutionName"]
    assert readback["expression"] == {
        "equals": ["@first(body('Readback_field_ALMQConfig_SolutionName')?['value'])?['TypeAsString']", "Text"]}


def test_field_collection_http_400_never_enters_create_branch():
    a = actions(bootstrap.build())
    ensure = a["Ensure_field_ALMQConfig_SolutionName"]
    assert ensure["expression"]["equals"][1] == 200
    assert "Create_field_ALMQConfig_SolutionName" in \
        ensure["actions"]["Field_results_ALMQConfig_SolutionName"]["actions"]
    assert "Fail_field ALMQConfig.SolutionName" in ensure["else"]["actions"]
    assert "getbyinternalnameortitle" not in a["Get_field_ALMQConfig_SolutionName"]["inputs"][
        "parameters"]["parameters/uri"]


def test_optional_fixture_is_inert_and_uses_no_guessed_entity_type():
    a = actions(bootstrap.build(include_fixture=True))
    body = json.loads(a["Ensure_qualification_fixture"]["actions"]["If_no_fixture"][
        "actions"]["Create_qualification_fixture"]["inputs"]["parameters"]["parameters/body"])
    assert body == {
        "__metadata": {"type": "SP.Data.ALMQConfigListItem"},
        "Title": "ALMQualificationFixtures TEST inert fixture",
        "SolutionName": "ALMQualificationFixtures", "TargetEnvironment": "TEST",
        "DevPowerPlatformUrl": {"__metadata": {"type": "SP.FieldUrlValue"},
                                "Url": bootstrap.TEST_ORG, "Description": bootstrap.TEST_ORG},
        "TargetPowerPlatformUrl": {"__metadata": {"type": "SP.FieldUrlValue"},
                                   "Url": bootstrap.TEST_ORG, "Description": bootstrap.TEST_ORG},
        "TargetSharePointUrl": {"__metadata": {"type": "SP.FieldUrlValue"},
                                "Url": bootstrap.TEST_SITE, "Description": bootstrap.TEST_SITE},
        "RunImport": False, "RunPostImport": True,
        "RunShare": False,
    }
    assert a["Readback_qualification_fixture"]["inputs"]["parameters"]["parameters/method"] == "GET"
    assert a["Results"]["inputs"]["fixtureId"] == \
        "@first(body('Readback_qualification_fixture')?['value'])?['Id']"
    assert not any("items" in params.get("parameters/uri", "") and
                   "ALMQConnections" in params.get("parameters/uri", "")
                   for _, action in walk(a) if action.get("type") == "OpenApiConnection"
                   for params in [action["inputs"]["parameters"]])


def test_optional_fixture_refuses_duplicate_rows_and_unsafe_import_switch():
    ensure = actions(bootstrap.build(include_fixture=True))["Ensure_qualification_fixture"]
    one = ensure["actions"]["If_no_fixture"]["else"]["actions"]["If_one_fixture"]
    assert "Fixture_duplicates" in one["else"]["actions"]
    safe = one["actions"]["Check_existing_fixture_switches"]
    assert safe["expression"]["and"][0] == {
        "equals": ["@first(body('Find_qualification_fixture')?['value'])?['RunImport']", False]}
    assert "Fixture_switches_unsafe" in safe["else"]["actions"]


def test_bootstrap_rejects_other_site_or_unconfigured_connections(monkeypatch):
    with pytest.raises(ValueError, match="pinned"):
        bootstrap.build("https://7xpydh.sharepoint.com/sites/ALM-Admin")
    monkeypatch.setattr(s, "SP_CONN", "shared-sharepointonl-a0f00819")
    with pytest.raises(ValueError, match="test-eu"):
        bootstrap.build()


def test_bootstrap_rejects_admin_connection_reference(monkeypatch):
    monkeypatch.setitem(s.FLOW_REFS, s.SP_KEY, ("alm_PipelineSharePoint", s.SP_API))
    with pytest.raises(ValueError, match="outside the configured test-eu target"):
        bootstrap.build()


def test_write_definition_only_writes_validated_source(tmp_path, monkeypatch):
    output = tmp_path / "bootstrap.json"
    cd = bootstrap.build()
    monkeypatch.setattr(bootstrap, "build", lambda site_url, include_fixture, include_logs: cd)
    path = bootstrap.write_definition(output)
    assert path == output
    assert json.loads(output.read_text()) == cd


def test_cli_target_config_applies_connections_without_fabricating_list_ids(tmp_path):
    config = tmp_path / "target.json"
    config.write_text(json.dumps({
        "mode": "isolated", "tenant_id": "1c5afb69-a82c-4c81-b2cc-743ce7f91dac",
        "allowed_accounts": ["kriall076@7xpydh.onmicrosoft.com"],
        "environment_id": bootstrap.TEST_ENV_ID, "organization_url": bootstrap.TEST_ORG,
        "site_url": bootstrap.TEST_SITE, "solution": "ALMQualification", "publisher": "almqualification",
        "connections": {"dataverse": bootstrap.TEST_DV_CONN, "sharepoint": bootstrap.TEST_SP_CONN},
    }))
    bootstrap.configure_from_target_config(config)
    assert s.SP_CONN == bootstrap.TEST_SP_CONN
    assert s.FLOW_REFS[s.SP_KEY][0] in s.CONN_REFS
    assert not hasattr(s, "LIST_CONFIG") or s.LIST_CONFIG != "00000000-0000-0000-0000-000000000000"


def test_optional_log_library_is_typed_and_does_not_create_release_archives():
    a = actions(bootstrap.build(include_logs=True))
    create = a['Ensure_list_DeploymentLogs']['actions']['Create_list_DeploymentLogs']
    assert json.loads(create['inputs']['parameters']['parameters/body'])['BaseTemplate'] == 101
    assert {'equals': ["@body('Readback_list_DeploymentLogs')?['BaseTemplate']", 101]} in a[
        'Check_list_DeploymentLogs']['expression']['and']
    assert 'Ensure_list_Solutions' not in a
    assert a['Results']['inputs']['logLibraryId'] == "@body('Readback_list_DeploymentLogs')?['Id']"
