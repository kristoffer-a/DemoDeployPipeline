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
    assert a["Import_to_target"]["inputs"]["parameters"]["item"]["ComponentParameters"] == \
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
    assert upd["item"] == {"value": "@items('For_each_variable')?['Value']"}


def test_children_stop_when_config_row_missing():
    for cd in (flows.c2(), flows.c3()):
        check = acts(cd)["Check_config"]
        assert check["expression"] == {"equals": ["@empty(body('Get_config')?['value'])", True]}
        assert check["actions"]["Stop_no_config"]["type"] == "Terminate"


IDS = {flows.s.C2_NAME: "c2-id", flows.s.C3_NAME: "c3-id"}


def test_c1_validates_clean():
    cd = flows.c1(IDS)
    assert defs.validate(cd) == []
    json.dumps(cd)


def test_c1_structure_main_log_report():
    a = acts(flows.c1(IDS))
    assert a["Init_FailMessage"]["type"] == "InitializeVariable"
    assert a["Main"]["type"] == "Scope"
    assert a["Log"]["runAfter"] == {"Main": ["Succeeded", "Failed", "Skipped", "TimedOut"]}
    assert a["Report_failure"]["runAfter"] == {"Log": ["Succeeded", "Failed"]}
    assert a["Report_failure"]["else"]["actions"]["Stop_failed"]["type"] == "Terminate"


def test_c1_children_are_switched_and_get_the_archived_path():
    main = acts(flows.c1(IDS))["Main"]["actions"]
    imp = main["If_RunImport"]
    assert imp["expression"] == {"equals": ["@outputs('Config')?['RunImport']", True]}
    call = imp["actions"]["Run_C2_import"]["inputs"]
    assert call["host"]["workflowReferenceName"] == "c2-id"
    assert call["body"]["text"] == "@body('Archive_ZIP')?['Path']"
    post = main["If_RunPostImport"]
    assert post["runAfter"] == {"If_RunImport": ["Succeeded"]}
    assert post["actions"]["Run_C3_post_import"]["inputs"]["host"]["workflowReferenceName"] == "c3-id"


def test_c1_prechecks_before_export():
    main = acts(flows.c1(IDS))["Main"]["actions"]
    assert main["Missing_refs"]["inputs"]["where"] == "@not(contains(body('Mapped_refs'), item()))"
    assert main["Export_from_DEV"]["runAfter"] == {"Check_mappings": ["Succeeded"]}
    assert main["Check_config"]["actions"]["Fail_no_config"]["inputs"] == "@int(variables('FailMessage'))"


def test_c1_archives_per_solution_and_logs_per_run():
    a = acts(flows.c1(IDS))
    archive = a["Main"]["actions"]["Export_succeeded"]["actions"]["Archive_ZIP"]["inputs"]["parameters"]
    assert archive["folderPath"] == "/Solutions/@{outputs('Solution')}"
    assert archive["name"] == "@{concat(outputs('Solution'), '_managed_', utcNow('yyyyMMdd-HHmmss'), '.zip')}"
    log = a["Log"]["actions"]["Write_log"]["inputs"]["parameters"]
    assert log["folderPath"] == "/DeploymentLogs"
    assert log["name"] == "@{concat(outputs('Solution'), '_', outputs('Target'), '_', utcNow('yyyyMMdd-HHmmss'), '.json')}"
    steps = a["Log"]["actions"]["Log_entry"]["inputs"]["steps"]
    assert [x["step"] for x in steps] == ["Prechecks", "Export", "Import", "PostImport"]


def test_flows_deploy_children_first():
    assert [name for name, _ in flows.FLOWS] == [flows.s.C2_NAME, flows.s.C3_NAME, flows.s.C1_NAME]


def test_update_row_actions_pass_item_as_one_object():
    """UpdateOnlyRecordWithOrganization with a dynamic organization needs 'item' as a single object."""
    def walk(actions):
        for name, a in actions.items():
            yield name, a
            for key in ("actions",):
                if isinstance(a.get(key), dict):
                    yield from walk(a[key])
            if isinstance(a.get("else"), dict):
                yield from walk(a["else"]["actions"])
    for cd in (flows.c2(), flows.c3(), flows.c1(IDS)):
        for name, a in walk(acts(cd)):
            host = a.get("inputs", {}).get("host", {}) if isinstance(a.get("inputs"), dict) else {}
            if host.get("operationId") in ("UpdateOnlyRecordWithOrganization", "PerformUnboundActionWithOrganization"):
                params = a["inputs"]["parameters"]
                assert isinstance(params.get("item"), dict), name
                assert not any(k.startswith("item/") for k in params), name


def test_c1_failure_message_ignores_skipped_children_and_reads_export_errors():
    msg = acts(flows.c1(IDS))["Log"]["actions"]["Log_entry"]["inputs"]["message"]
    assert "actions('Export_from_DEV')?['outputs']?['body']?['error']?['message']" in msg
    assert "if(equals(actions('Run_C2_import')?['status'], 'Failed')" in msg


def test_log_step_message_only_reports_errors_for_failed_steps():
    step = flows.log_step("Import", "Run_C2_import")
    assert step["message"].startswith("@{if(equals(actions('Run_C2_import')?['status'], 'Failed')")
