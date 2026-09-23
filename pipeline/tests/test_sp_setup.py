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
    assert a["Create_list_ALMConnections"]["runAfter"] == {"Create_field_ALMConfig_AppShareGroupId": ["Succeeded", "Failed"]}
    assert a["Results"]["runAfter"] == {"Read_variables": ["Succeeded", "Failed", "Skipped"]}
