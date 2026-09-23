import json

from pipeline import defs, flows


def acts(cd):
    return cd["properties"]["definition"]["actions"]


def test_children_validate_clean():
    for cd in (flows.c2(), flows.c3()):
        assert defs.validate(cd) == []
        json.dumps(cd)


def test_c2_builds_component_parameters_from_config_rows():
    a = acts(flows.c2())
    assert a["Import_to_target"]["inputs"]["parameters"]["item/ComponentParameters"] == \
        "@union(body('Connection_params'), body('Variable_params'))"
    assert "'@odata.type', 'Microsoft.Dynamics.CRM.connectionreference'" in a["Connection_params"]["inputs"]["select"]
    assert "'@odata.type', 'Microsoft.Dynamics.CRM.environmentvariablevalue'" in a["Variable_params"]["inputs"]["select"]
    assert a["Import_to_target"]["inputs"]["parameters"]["organization"] == "@outputs('Target_url')"


def test_c2_only_maps_connection_refs_that_are_in_the_solution():
    a = acts(flows.c2())
    assert a["Solution_connections"]["inputs"]["where"] == \
        "@contains(body('Dev_ref_names'), item()?['ConnectionReference'])"


def test_children_reply_on_success():
    c2 = acts(flows.c2())["Import_succeeded"]["actions"]
    assert c2["Reply"]["type"] == "Response"
    assert set(c2["Reply"]["inputs"]["body"]) == {"status", "message", "importjobkey"}
    c3 = acts(flows.c3())
    assert c3["Reply"]["type"] == "Response"
    assert set(c3["Reply"]["inputs"]["body"]) == {"status", "message"}


def test_c3_runs_check_then_variables_then_flows():
    a = acts(flows.c3())
    assert a["Check_bindings"]["runAfter"] == {"Wrong_bindings": ["Succeeded"]}
    assert a["Target_defs"]["runAfter"] == {"Check_bindings": ["Succeeded"]}
    assert a["For_each_variable"]["runAfter"] == {"Check_value_rows": ["Succeeded"]}
    assert a["Off_flows"]["runAfter"] == {"For_each_variable": ["Succeeded"]}
    assert a["For_each_variable"]["runtimeConfiguration"] == {"concurrency": {"repetitions": 1}}
    assert a["Check_value_rows"]["actions"]["Stop_no_value_row"]["type"] == "Terminate"
    upd = a["For_each_variable"]["actions"]["Update_value"]["inputs"]["parameters"]
    assert upd["entityName"] == "environmentvariablevalues"
    assert upd["item/value"] == "@items('For_each_variable')?['Value']"


def test_children_stop_when_config_row_missing():
    for cd in (flows.c2(), flows.c3()):
        check = acts(cd)["Check_config"]
        assert check["expression"] == {"equals": ["@empty(body('Get_config')?['value'])", True]}
        assert check["actions"]["Stop_no_config"]["type"] == "Terminate"
