import json

from pipeline import defs, flows


def acts(cd):
    return cd["properties"]["definition"]["actions"]


def _walk(actions):
    """Yield (name, action) for every action nested under actions/else, recursively."""
    for name, a in actions.items():
        yield name, a
        if isinstance(a.get("actions"), dict):
            yield from _walk(a["actions"])
        if isinstance(a.get("else"), dict) and isinstance(a["else"].get("actions"), dict):
            yield from _walk(a["else"]["actions"])


def _find(actions, name):
    for n, a in _walk(actions):
        if n == name:
            return a
    return None


def test_children_validate_clean():
    for cd in (flows.c2(), flows.c3()):
        assert defs.validate(cd) == []
        json.dumps(cd)


def test_c2_builds_component_parameters_from_config_rows():
    a = acts(flows.c2())["Try"]["actions"]
    assert a["Import_to_target"]["inputs"]["parameters"]["item"]["ComponentParameters"] == \
        "@json(replace(string(union(body('Connection_params'), body('Variable_params'))), '\"odata_type\"', '\"@odata.type\"'))"
    assert "'odata_type', 'Microsoft.Dynamics.CRM.connectionreference'" in a["Connection_params"]["inputs"]["select"]
    assert "'odata_type', 'Microsoft.Dynamics.CRM.environmentvariablevalue'" in a["Variable_params"]["inputs"]["select"]
    assert "'@odata.type'" not in a["Connection_params"]["inputs"]["select"]
    assert "'@odata.type'" not in a["Variable_params"]["inputs"]["select"]
    assert a["Import_to_target"]["inputs"]["parameters"]["organization"] == "@outputs('Target_url')"


def test_c2_only_maps_connection_refs_that_are_in_the_solution():
    a = acts(flows.c2())["Try"]["actions"]
    assert a["Solution_connections"]["inputs"]["where"] == \
        "@contains(body('Dev_ref_names'), item()?['ConnectionReference'])"


def test_children_reply_on_success():
    c2 = acts(flows.c2())["Try"]["actions"]["Import_succeeded"]["actions"]
    assert c2["Reply"]["type"] == "Response"
    assert set(c2["Reply"]["inputs"]["body"]) == {"status", "message", "importjobkey"}
    c3 = acts(flows.c3())["Try"]["actions"]
    assert c3["Reply"]["type"] == "Response"
    assert set(c3["Reply"]["inputs"]["body"]) == {"status", "message"}


def test_c3_runs_check_then_variables_then_flows():
    a = acts(flows.c3())["Try"]["actions"]
    assert a["Check_bindings"]["runAfter"] == {"Wrong_bindings": ["Succeeded"]}
    assert a["Target_defs"]["runAfter"] == {"Check_bindings": ["Succeeded"]}
    assert a["For_each_variable"]["runAfter"] == {"Check_value_rows": ["Succeeded"]}
    assert a["Off_flows"]["runAfter"] == {"For_each_variable": ["Succeeded"]}
    assert a["For_each_variable"]["runtimeConfiguration"] == {"concurrency": {"repetitions": 1}}
    assert a["Check_value_rows"]["actions"]["Stop_no_value_row"]["inputs"] == "@int(variables('FailMessage'))"
    upd = a["For_each_variable"]["actions"]["Update_value"]["inputs"]["parameters"]
    assert upd["entityName"] == "environmentvariablevalues"
    assert upd["item"] == {"value": "@items('For_each_variable')?['Value']"}


def test_children_stop_when_config_row_missing():
    for cd in (flows.c2(), flows.c3()):
        check = acts(cd)["Try"]["actions"]["Check_config"]
        assert check["expression"] == {"equals": ["@empty(body('Get_config')?['value'])", True]}
        assert check["actions"]["Stop_no_config"]["inputs"] == "@int(variables('FailMessage'))"


def test_children_top_level_structure_is_try_wrapped():
    for cd in (flows.c2(), flows.c3()):
        assert list(acts(cd)) == ["Init_FailMessage", "Try", "Failed_actions", "Reply_failed", "Stop_failed"]
        a = acts(cd)
        assert a["Init_FailMessage"]["type"] == "InitializeVariable"
        assert a["Try"]["type"] == "Scope"
        assert a["Failed_actions"]["inputs"]["from"] == "@result('Try')"
        assert a["Failed_actions"]["inputs"]["where"] == "@equals(item()?['status'], 'Failed')"
        assert a["Failed_actions"]["runAfter"] == {"Try": ["Failed", "Skipped", "TimedOut"]}
        assert a["Reply_failed"]["type"] == "Response"
        assert a["Reply_failed"]["runAfter"] == {"Failed_actions": ["Succeeded"]}
        assert a["Stop_failed"]["type"] == "Terminate"
        assert a["Stop_failed"]["runAfter"] == {"Reply_failed": ["Succeeded"]}


def test_reply_failed_matches_success_reply_body_keys():
    for cd in (flows.c2(), flows.c3()):
        a = acts(cd)
        success = _find(a["Try"]["actions"], "Reply")
        assert set(success["inputs"]["body"]) == set(a["Reply_failed"]["inputs"]["body"])


def test_reply_failed_status_and_importjobkey():
    c2 = acts(flows.c2())
    assert c2["Reply_failed"]["inputs"]["body"]["status"] == "Failed"
    assert c2["Reply_failed"]["inputs"]["body"]["importjobkey"] == ""
    msg = c2["Reply_failed"]["inputs"]["body"]["message"]
    assert "variables('FailMessage')" in msg
    assert "first(body('Failed_actions'))?['outputs']?['body']?['error']?['message']" in msg
    assert "first(body('Failed_actions'))?['error']?['message']" in msg
    assert "'unknown error'" in msg

    c3 = acts(flows.c3())
    assert c3["Reply_failed"]["inputs"]["body"]["status"] == "Failed"
    assert "importjobkey" not in c3["Reply_failed"]["inputs"]["body"]


def test_no_terminate_action_exists_inside_try():
    for cd in (flows.c2(), flows.c3()):
        a = acts(cd)
        for name, action in _walk(a["Try"]["actions"]):
            assert action["type"] != "Terminate", name


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


def test_c1_checks_child_status_and_fails_on_non_succeeded():
    main = acts(flows.c1(IDS))["Main"]["actions"]
    imp_actions = main["If_RunImport"]["actions"]
    check_c2 = imp_actions["Check_C2"]
    assert check_c2["expression"] == {"equals": ["@body('Run_C2_import')?['status']", "Succeeded"]}
    assert check_c2["runAfter"] == {"Run_C2_import": ["Succeeded"]}
    assert check_c2["actions"] == {}
    fail_import = check_c2["else"]["actions"]
    assert "Fail_import" in fail_import
    assert fail_import["Set_Fail_import"]["inputs"]["value"] == "@concat('Import: ', body('Run_C2_import')?['message'])"

    post_actions = main["If_RunPostImport"]["actions"]
    check_c3 = post_actions["Check_C3"]
    assert check_c3["expression"] == {"equals": ["@body('Run_C3_post_import')?['status']", "Succeeded"]}
    fail_post = check_c3["else"]["actions"]
    assert "Fail_post_import" in fail_post
    assert fail_post["Set_Fail_post_import"]["inputs"]["value"] == \
        "@concat('Post-import: ', body('Run_C3_post_import')?['message'])"


def test_run_child_calls_carry_no_retry_policy():
    main = acts(flows.c1(IDS))["Main"]["actions"]
    assert main["If_RunImport"]["actions"]["Run_C2_import"]["inputs"]["retryPolicy"] == {"type": "none"}
    assert main["If_RunPostImport"]["actions"]["Run_C3_post_import"]["inputs"]["retryPolicy"] == {"type": "none"}


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


def test_c1_failure_message_prefers_fail_message_then_export_errors():
    msg = acts(flows.c1(IDS))["Log"]["actions"]["Log_entry"]["inputs"]["message"]
    assert "variables('FailMessage')" in msg
    assert "actions('Export_from_DEV')?['outputs']?['body']?['error']?['message']" in msg
    assert "actions('Download_export')?['outputs']?['body']?['error']?['message']" in msg
    assert "actions('Archive_ZIP')?['outputs']?['body']?['message']" in msg
    # child status is now checked by Check_C2/Check_C3 + Fail_import/Fail_post_import (which set
    # FailMessage), so the message no longer needs to inspect Run_C2_import/Run_C3_post_import itself.
    assert "Run_C2_import" not in msg
    assert "Run_C3_post_import" not in msg


def test_log_step_message_only_reports_errors_for_failed_steps():
    step = flows.log_step("Import", "Check_C2", "Run_C2_import")
    assert step["status"] == "@{actions('Check_C2')?['status']}"
    assert step["message"].startswith("@{if(equals(actions('Check_C2')?['status'], 'Failed')")
    assert "actions('Check_C2')?['outputs']?['body']?['error']?['message']" in step["message"]
    assert "actions('Run_C2_import')?['outputs']?['body']?['message']" in step["message"]


def test_log_step_defaults_message_action_to_status_action():
    step = flows.log_step("Export", "Export_succeeded")
    assert "actions('Export_succeeded')?['outputs']?['body']?['message']" in step["message"]


def test_c1_uses_check_actions_for_import_and_postimport_log_steps():
    steps = acts(flows.c1(IDS))["Log"]["actions"]["Log_entry"]["inputs"]["steps"]
    by_step = {s["step"]: s for s in steps}
    assert by_step["Import"]["status"] == "@{actions('Check_C2')?['status']}"
    assert "actions('Run_C2_import')?['outputs']?['body']?['message']" in by_step["Import"]["message"]
    assert by_step["PostImport"]["status"] == "@{actions('Check_C3')?['status']}"
    assert "actions('Run_C3_post_import')?['outputs']?['body']?['message']" in by_step["PostImport"]["message"]
