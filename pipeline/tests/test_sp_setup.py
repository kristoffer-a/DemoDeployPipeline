import json

import pytest

from pipeline import defs, sp_setup


def acts(cd):
    return cd["properties"]["definition"]["actions"]


@pytest.mark.parametrize("argv", [["provision"], ["config", "RunImport=false"], ["connection-env", "PROD"],
                                  ["variable", "dev_ProductsList=abc"], ["readback"]])
def test_every_command_builds_a_valid_flow_ending_in_results(argv):
    cd = sp_setup.build(sp_setup.command_ops(argv))
    assert defs.validate(cd) == []
    a = acts(cd)
    assert list(a)[-1] == "Results"
    assert "Read_config" in a
    json.dumps(cd)


def test_connection_env_filter_ignores_current_environment():
    for env in ("TEST", "PROD"):
        find = acts(sp_setup.build(sp_setup.command_ops(["connection-env", env])))["Find_connection"]
        uri = find["inputs"]["parameters"]["parameters/uri"]
        assert "ConnectionReference%20eq%20'dev_SharePoint'" in uri
        assert "Environment" not in uri


def test_connection_env_rejects_unknown_environment():
    with pytest.raises(SystemExit):
        sp_setup.command_ops(["connection-env", "DEV"])


def test_config_parses_booleans():
    upd = acts(sp_setup.build(sp_setup.command_ops(["config", "RunImport=false", "RunShare=true"])))
    body = json.loads(upd["Upsert_config"]["actions"]["Update_config"]["inputs"]["parameters"]["parameters/body"])
    assert body["RunImport"] is False and body["RunShare"] is True
    assert body["__metadata"] == {"type": "SP.Data.ALMConfigListItem"}


def test_later_groups_run_after_failures():
    a = acts(sp_setup.build(sp_setup.command_ops(["provision"])))
    assert a["Get_list_ALMConnections"]["runAfter"] == \
        {"Create_field_ALMConfig_AppShareGroupId": ["Succeeded", "Failed", "Skipped"]}
    assert a["Results"]["runAfter"] == {"Read_variables": ["Succeeded", "Failed", "Skipped"]}


def test_ensure_field_checks_before_creating():
    group = sp_setup.ensure_field("ALMConfig", sp_setup.text("Foo"))
    assert list(group) == ["Get_field_ALMConfig_Foo", "Create_field_ALMConfig_Foo"]
    assert group["Create_field_ALMConfig_Foo"]["runAfter"] == {"Get_field_ALMConfig_Foo": ["Failed"]}


def test_ensure_list_checks_before_creating():
    group = sp_setup.ensure_list("ALMConnections")
    assert list(group) == ["Get_list_ALMConnections", "Create_list_ALMConnections"]
    assert group["Create_list_ALMConnections"]["runAfter"] == {"Get_list_ALMConnections": ["Failed"]}


def test_setup_requests_have_no_retry_policy():
    for argv in (["provision"], ["config", "RunImport=false"], ["connection-env", "PROD"],
                 ["variable", "dev_ProductsList=abc"], ["readback"]):
        a = acts(sp_setup.build(sp_setup.command_ops(argv)))
        for name, action in a.items():
            if action.get("type") == "OpenApiConnection" and \
                    action["inputs"]["host"].get("operationId") == "HttpRequest":
                assert action["inputs"]["retryPolicy"] == {"type": "none"}, name


def test_results_includes_get_actions():
    a = acts(sp_setup.build(sp_setup.command_ops(["provision"])))
    assert "Get_field_ALMConfig_AppShareGroupId" in a["Results"]["inputs"]
    assert "Get_list_ALMConnections" in a["Results"]["inputs"]


def test_config_filter_is_pinned_to_demo_test():
    find = acts(sp_setup.build(sp_setup.command_ops(["config", "RunImport=false"])))["Find_config"]
    uri = find["inputs"]["parameters"]["parameters/uri"]
    assert "SolutionName%20eq%20'Demo'" in uri
    assert "TargetEnvironment%20eq%20'TEST'" in uri


def test_provision_config_row_uses_demo_test_filter():
    find = acts(sp_setup.build(sp_setup.command_ops(["provision"])))["Find_config"]
    uri = find["inputs"]["parameters"]["parameters/uri"]
    assert "TargetEnvironment%20eq%20'TEST'" in uri


def test_delete_duplicates_targets_only_the_eleven_suffixed_columns():
    a = acts(sp_setup.build(sp_setup.command_ops(["delete-duplicates"])))
    deletes = {n: x for n, x in a.items() if n.startswith("Delete_field_")}
    assert len(deletes) == 11
    for name, x in deletes.items():
        p = x["inputs"]["parameters"]
        assert p["parameters/method"] == "POST"
        assert p["parameters/headers"]["X-HTTP-Method"] == "DELETE"
        column = p["parameters/uri"].split("getbyinternalnameortitle('", 1)[1].split("'", 1)[0]
        assert column.endswith("0") and column[:-1] in {
            "AppShareGroupId", "RunImport", "RunPostImport", "RunShare", "TargetEnvironment",
            "TargetPowerPlatformUrl", "TargetSharePointUrl",
            "ConnectionId", "ConnectionReference", "ConnectorId", "Environment"}
