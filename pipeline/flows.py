"""Definitions of the deploy pipeline flows: C1 parent, C2 import child, C3 post-import child."""
from pipeline import settings as s
from pipeline.defs import (after, clientdata, fail_steps, fetch_in_solution, if_job_succeeded, job_message, list_rows,
                           manual_trigger, op, poll_block, respond, run_child, seq, sp_items, terminate, unbound, url_expr)

DV, SP = s.DV_KEY, s.SP_KEY


def config_actions(sol, target, on_missing):
    """Read the ALMConfig row, the mapping rows and DEV's solution components.

    sol / target are expressions without a leading @, e.g. "outputs('Solution')".
    on_missing: actions run when no ALMConfig row matches (they must stop the run).
    """
    return seq(
        {"Get_config": sp_items(SP, s.LIST_CONFIG,
                                f"SolutionName eq '@{{{sol}}}' and TargetEnvironment eq '@{{{target}}}'", top=1)},
        {"Config": {"type": "Compose", "inputs": "@first(body('Get_config')?['value'])"}},
        {"Check_config": {"type": "If",
                          "expression": {"equals": ["@empty(body('Get_config')?['value'])", True]},
                          "actions": on_missing}},
        {"Dev_url": {"type": "Compose", "inputs": "@" + url_expr("outputs('Config')", "DevPowerPlatformUrl")}},
        {"Target_url": {"type": "Compose", "inputs": "@" + url_expr("outputs('Config')", "TargetPowerPlatformUrl")}},
        {"Get_connection_map": sp_items(SP, s.LIST_CONNECTIONS, f"Environment eq '@{{{target}}}'")},
        {"Get_variable_map": sp_items(SP, s.LIST_VARIABLES,
                                      f"SolutionName eq '@{{{sol}}}' and Environment eq '@{{{target}}}'")},
        {"Dev_refs": list_rows(DV, "@outputs('Dev_url')", "connectionreferences",
                               fetch=fetch_in_solution("connectionreference", "connectionreferenceid",
                                                       ["connectionreferencelogicalname"], sol))},
        {"Dev_ref_names": {"type": "Select", "inputs": {
            "from": "@body('Dev_refs')?['value']", "select": "@item()?['connectionreferencelogicalname']"}}},
        {"Dev_vars": list_rows(DV, "@outputs('Dev_url')", "environmentvariabledefinitions",
                               fetch=fetch_in_solution("environmentvariabledefinition", "environmentvariabledefinitionid",
                                                       ["schemaname"], sol))},
        {"Dev_var_names": {"type": "Select", "inputs": {
            "from": "@body('Dev_vars')?['value']", "select": "@item()?['schemaname']"}}},
    )


def no_config_message(sol, target):
    return f"@concat('No ALMConfig row for ', {sol}, ' -> ', {target})"


def solution_connections():
    """ALMConnections rows whose connection reference is part of the DEV solution."""
    return {"Solution_connections": {"type": "Query", "inputs": {
        "from": "@body('Get_connection_map')?['value']",
        "where": "@contains(body('Dev_ref_names'), item()?['ConnectionReference'])"}}}


def child_wrapper(try_actions, reply_body):
    """Wrap a child flow's real work so a failure always produces a reply and a Failed run.

    Top-level shape (same for C2 and C3): InitializeVariable FailMessage, a Try scope holding
    every existing action (with all internal Terminate actions replaced by fail_steps so the
    scope itself fails instead of ending the run early), a Query over the failed actions inside
    Try, a Reply with the same body keys as the success Reply, then a Terminate so the run is
    marked Failed in history after the reply has already gone out.
    """
    fail_message_expr = (
        "@{if(empty(variables('FailMessage')), coalesce("
        "first(body('Failed_actions'))?['outputs']?['body']?['error']?['message'], "
        "first(body('Failed_actions'))?['error']?['message'], 'unknown error'), "
        "variables('FailMessage'))}")
    reply = dict(reply_body)
    reply["message"] = fail_message_expr

    actions = seq(
        {"Init_FailMessage": {"type": "InitializeVariable", "inputs": {
            "variables": [{"name": "FailMessage", "type": "string", "value": ""}]}}},
        {"Try": {"type": "Scope", "actions": try_actions}},
    )
    actions["Failed_actions"] = after({"type": "Query", "inputs": {
        "from": "@result('Try')", "where": "@equals(item()?['status'], 'Failed')"}},
        "Try", status=("Failed", "Skipped", "TimedOut"))
    actions["Reply_failed"] = after(respond(reply), "Failed_actions")
    actions["Stop_failed"] = after(terminate("@{variables('FailMessage')}"), "Reply_failed")
    return actions


# ---------- C2: import child ----------

C2_SOL, C2_TARGET = "triggerBody()?['text_1']", "triggerBody()?['text_2']"


def c2():
    # setProperty() rejects '.' in names, so build 'odata_type' and rename it to '@odata.type' in text form below.
    conn_param = ("@setProperty(setProperty(setProperty(setProperty(json('{}'), "
                  "'odata_type', 'Microsoft.Dynamics.CRM.connectionreference'), "
                  "'connectionreferencelogicalname', item()?['ConnectionReference']), "
                  "'connectionid', item()?['ConnectionId']), 'connectorid', item()?['ConnectorId'])")
    var_param = ("@setProperty(setProperty(setProperty(json('{}'), "
                 "'odata_type', 'Microsoft.Dynamics.CRM.environmentvariablevalue'), "
                 "'schemaname', item()?['SchemaName']), 'value', item()?['Value'])")

    importing = {
        "Import_to_target": unbound(DV, "@outputs('Target_url')", "ImportSolutionAsync", {
            "CustomizationFile": "@body('Get_archived_ZIP')?['$content']",
            "OverwriteUnmanagedCustomizations": False,
            "PublishWorkflows": True,
            "ComponentParameters": "@json(replace(string(union(body('Connection_params'), body('Variable_params'))), '\"odata_type\"', '\"@odata.type\"'))",
        }),
    }
    importing.update({k: after(v, "Import_to_target") for k, v in poll_block(
        DV, "@outputs('Target_url')", "@body('Import_to_target')?['AsyncOperationId']", "Import").items()})
    importing["Import_succeeded"] = after(if_job_succeeded("Import", {
        "Reply": respond({
            "status": "Succeeded",
            "message": "@{concat('Imported ', triggerBody()?['text'])}",
            "importjobkey": "@{body('Import_to_target')?['ImportJobKey']}",
        }),
    }, fail_steps("Import_failed", "@" + job_message("Import"))), "Import_Wait_for_job")

    try_actions = seq(
        config_actions(C2_SOL, C2_TARGET, fail_steps("Stop_no_config", no_config_message(C2_SOL, C2_TARGET))),
        solution_connections(),
        {"Connection_params": {"type": "Select", "inputs": {
            "from": "@body('Solution_connections')", "select": conn_param}}},
        {"Variable_params": {"type": "Select", "inputs": {
            "from": "@body('Get_variable_map')?['value']", "select": var_param}}},
        {"Get_archived_ZIP": op(SP, s.SP_API, "GetFileContentByPath", {
            "dataset": s.ADMIN_SITE, "path": "@triggerBody()?['text']", "inferContentType": False})},
        importing,
    )
    actions = child_wrapper(try_actions, {"status": "Failed", "importjobkey": ""})
    return clientdata(manual_trigger([
        ("text", "Archived ZIP path", "Set by C1, e.g. /Solutions/Demo/Demo_managed_20260923-164536.zip"),
        ("text_1", "Solution", "Solution unique name, e.g. Demo"),
        ("text_2", "Target", "TEST or PROD"),
    ]), actions, s.FLOW_REFS)


# ---------- C3: post-import child ----------

C3_SOL, C3_TARGET = "triggerBody()?['text']", "triggerBody()?['text_1']"


def c3():
    target = "@outputs('Target_url')"
    check = seq(
        solution_connections(),
        {"Expected_pairs": {"type": "Select", "inputs": {
            "from": "@body('Solution_connections')",
            "select": "@concat(item()?['ConnectionReference'], '|', item()?['ConnectionId'])"}}},
        {"Target_refs": list_rows(DV, target, "connectionreferences",
                                  select="connectionreferencelogicalname,connectionid")},
        {"Target_pairs": {"type": "Select", "inputs": {
            "from": "@body('Target_refs')?['value']",
            "select": "@concat(item()?['connectionreferencelogicalname'], '|', item()?['connectionid'])"}}},
        {"Wrong_bindings": {"type": "Query", "inputs": {
            "from": "@body('Expected_pairs')", "where": "@not(contains(body('Target_pairs'), item()))"}}},
        {"Check_bindings": {"type": "If",
                            "expression": {"greater": ["@length(body('Wrong_bindings'))", 0]},
                            "actions": fail_steps("Stop_wrong_bindings",
                                "@concat('Connection references not bound as mapped (reference|connection): ', "
                                "join(body('Wrong_bindings'), ', '))")}},
    )
    # Terminate is not allowed inside a Foreach, so missing value rows are checked before the loop.
    variables = seq(
        {"Target_defs": list_rows(
            DV, target, "environmentvariabledefinitions", select="schemaname",
            expand="environmentvariabledefinition_environmentvariablevalue($select=environmentvariablevalueid)")},
        {"Target_value_rows": {"type": "Select", "inputs": {
            "from": "@body('Target_defs')?['value']",
            "select": {"schemaname": "@item()?['schemaname']",
                       "valueid": "@first(item()?['environmentvariabledefinition_environmentvariablevalue'])"
                                  "?['environmentvariablevalueid']"}}}},
        {"Rows_with_value": {"type": "Query", "inputs": {
            "from": "@body('Target_value_rows')", "where": "@not(empty(item()?['valueid']))"}}},
        {"Names_with_value": {"type": "Select", "inputs": {
            "from": "@body('Rows_with_value')", "select": "@item()?['schemaname']"}}},
        {"Wanted_names": {"type": "Select", "inputs": {
            "from": "@body('Get_variable_map')?['value']", "select": "@item()?['SchemaName']"}}},
        {"Missing_value_rows": {"type": "Query", "inputs": {
            "from": "@body('Wanted_names')", "where": "@not(contains(body('Names_with_value'), item()))"}}},
        {"Check_value_rows": {"type": "If",
                              "expression": {"greater": ["@length(body('Missing_value_rows'))", 0]},
                              "actions": fail_steps("Stop_no_value_row",
                                  "@concat('No value row in the target for: ', join(body('Missing_value_rows'), ', '), "
                                  "'. Run the import first.')")}},
        {"For_each_variable": {
            "type": "Foreach",
            "foreach": "@body('Get_variable_map')?['value']",
            "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
            "actions": seq(
                {"Value_row": {"type": "Query", "inputs": {
                    "from": "@body('Rows_with_value')",
                    "where": "@equals(item()?['schemaname'], items('For_each_variable')?['SchemaName'])"}}},
                {"Update_value": op(DV, s.DV_API, "UpdateOnlyRecordWithOrganization", {
                    "organization": target,
                    "entityName": "environmentvariablevalues",
                    "recordId": "@first(body('Value_row'))?['valueid']",
                    "item": {"value": "@items('For_each_variable')?['Value']"},
                })},
            ),
        }},
    )
    turn_on = seq(
        {"Off_flows": list_rows(DV, target, "workflows", fetch=fetch_in_solution(
            "workflow", "workflowid", ["workflowid", "name"], C3_SOL, [("category", "5"), ("statecode", "0")]))},
        {"For_each_flow": {
            "type": "Foreach",
            "foreach": "@body('Off_flows')?['value']",
            "actions": {"Turn_on_flow": op(DV, s.DV_API, "UpdateOnlyRecordWithOrganization", {
                "organization": target,
                "entityName": "workflows",
                "recordId": "@items('For_each_flow')?['workflowid']",
                "item": {"statecode": 1, "statuscode": 2},
            })},
        }},
        {"Reply": respond({
            "status": "Succeeded",
            "message": "@{concat('Bindings OK; variables set: ', length(body('Get_variable_map')?['value']), "
                       "'; flows turned on: ', length(body('Off_flows')?['value']))}",
        })},
    )
    try_actions = seq(
        config_actions(C3_SOL, C3_TARGET, fail_steps("Stop_no_config", no_config_message(C3_SOL, C3_TARGET))),
        check, variables, turn_on,
    )
    actions = child_wrapper(try_actions, {"status": "Failed"})
    return clientdata(manual_trigger([
        ("text", "Solution", "Solution unique name, e.g. Demo"),
        ("text_1", "Target", "TEST or PROD"),
    ]), actions, s.FLOW_REFS)


# ---------- C1: parent ----------

SOL, TARGET = "outputs('Solution')", "outputs('Target')"
PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"


def export_steps():
    """Export managed from DEV, wait, download, archive as Solutions/<sol>/<sol>_managed_<time>.zip."""
    dev = "@outputs('Dev_url')"
    acts = {"Export_from_DEV": unbound(DV, dev, "ExportSolutionAsync", {"SolutionName": f"@{SOL}", "Managed": True})}
    acts.update({k: after(v, "Export_from_DEV") for k, v in poll_block(
        DV, dev, "@body('Export_from_DEV')?['AsyncOperationId']", "Export").items()})
    acts["Export_succeeded"] = after(if_job_succeeded("Export", {
        "Download_export": unbound(DV, dev, "DownloadSolutionExportData",
                                   {"ExportJobId": "@body('Export_from_DEV')?['ExportJobId']"}),
        "Archive_ZIP": after(op(SP, s.SP_API, "CreateFile", {
            "dataset": s.ADMIN_SITE,
            "folderPath": f"/Solutions/@{{{SOL}}}",
            "name": f"@{{concat({SOL}, '_managed_', utcNow('yyyyMMdd-HHmmss'), '.zip')}}",
            "body": "@base64ToBinary(body('Download_export')?['ExportSolutionFile'])",
        }), "Download_export"),
    }, fail_steps("Fail_export", "@" + job_message("Export"))), "Export_Wait_for_job")
    return acts


def log_step(step, status_action, message_action=None):
    """One log line. actions('X') works for skipped actions; body('X') would throw.

    status/seconds come from `status_action`. On failure the message is that action's own error;
    otherwise it's `message_action`'s (default: same as status_action) reply body message - used
    for Import/PostImport where the real status now lives on Check_C2/Check_C3 (which reflects
    the child's reply) but the success message is on the Run_C2_import/Run_C3_post_import reply.
    """
    message_action = message_action or status_action
    sa = f"actions('{status_action}')"
    ma = f"actions('{message_action}')"
    return {
        "step": step,
        "status": f"@{{{sa}?['status']}}",
        "seconds": f"@{{div(sub(ticks(coalesce({sa}?['endTime'], utcNow())), "
                   f"ticks(coalesce({sa}?['startTime'], utcNow()))), 10000000)}}",
        "message": f"@{{if(equals({sa}?['status'], 'Failed'), "
                   f"coalesce({sa}?['outputs']?['body']?['error']?['message'], {sa}?['error']?['message'], ''), "
                   f"coalesce({ma}?['outputs']?['body']?['message'], ''))}}",
    }


def c1(ids):
    missing = ("@concat('Missing mapping rows for ', outputs('Target'), ': ', "
               "join(union(body('Missing_refs'), body('Missing_vars')), ', '))")
    main = seq(
        config_actions(SOL, TARGET, fail_steps("Fail_no_config", no_config_message(SOL, TARGET))),
        {"Mapped_refs": {"type": "Select", "inputs": {
            "from": "@body('Get_connection_map')?['value']", "select": "@item()?['ConnectionReference']"}}},
        {"Missing_refs": {"type": "Query", "inputs": {
            "from": "@body('Dev_ref_names')", "where": "@not(contains(body('Mapped_refs'), item()))"}}},
        {"Mapped_vars": {"type": "Select", "inputs": {
            "from": "@body('Get_variable_map')?['value']", "select": "@item()?['SchemaName']"}}},
        {"Missing_vars": {"type": "Query", "inputs": {
            "from": "@body('Dev_var_names')", "where": "@not(contains(body('Mapped_vars'), item()))"}}},
        {"Check_mappings": {"type": "If",
                            "expression": {"greater": ["@add(length(body('Missing_refs')), length(body('Missing_vars')))", 0]},
                            "actions": fail_steps("Fail_missing_mapping", missing)}},
        export_steps(),
        {"If_RunImport": {"type": "If",
                          "expression": {"equals": ["@outputs('Config')?['RunImport']", True]},
                          "actions": seq(
                              {"Run_C2_import": run_child(ids.get(s.C2_NAME, PLACEHOLDER_ID), {
                                  "text": "@body('Archive_ZIP')?['Path']", "text_1": f"@{SOL}", "text_2": f"@{TARGET}"})},
                              {"Check_C2": {"type": "If",
                                           "expression": {"equals": ["@body('Run_C2_import')?['status']", "Succeeded"]},
                                           "actions": {},
                                           "else": {"actions": fail_steps(
                                               "Fail_import", "@concat('Import: ', body('Run_C2_import')?['message'])")}}},
                          )}},
        {"If_RunPostImport": {"type": "If",
                              "expression": {"equals": ["@outputs('Config')?['RunPostImport']", True]},
                              "actions": seq(
                                  {"Run_C3_post_import": run_child(ids.get(s.C3_NAME, PLACEHOLDER_ID), {
                                      "text": f"@{SOL}", "text_1": f"@{TARGET}"})},
                                  {"Check_C3": {"type": "If",
                                               "expression": {"equals": ["@body('Run_C3_post_import')?['status']", "Succeeded"]},
                                               "actions": {},
                                               "else": {"actions": fail_steps(
                                                   "Fail_post_import",
                                                   "@concat('Post-import: ', body('Run_C3_post_import')?['message'])")}}},
                              )}},
    )
    # FailMessage covers pre-checks, export-job failure, and now Fail_import/Fail_post_import
    # (set when Check_C2/Check_C3 see a non-Succeeded child reply); the rest are export errors.
    message = ("@{if(not(empty(variables('FailMessage'))), variables('FailMessage'), coalesce("
               "actions('Export_from_DEV')?['outputs']?['body']?['error']?['message'], "
               "actions('Download_export')?['outputs']?['body']?['error']?['message'], "
               "actions('Archive_ZIP')?['outputs']?['body']?['message'], "
               "''))}")
    log = seq(
        {"Log_entry": {"type": "Compose", "inputs": {
            "runId": "@{workflow()?['run']?['name']}",
            "solution": f"@{{{SOL}}}",
            "target": f"@{{{TARGET}}}",
            "status": "@{actions('Main')?['status']}",
            "zipPath": "@{actions('Archive_ZIP')?['outputs']?['body']?['Path']}",
            "switches": {
                "RunImport": "@{actions('Config')?['outputs']?['RunImport']}",
                "RunPostImport": "@{actions('Config')?['outputs']?['RunPostImport']}",
            },
            "message": message,
            "steps": [log_step("Prechecks", "Check_mappings"), log_step("Export", "Export_succeeded"),
                      log_step("Import", "Check_C2", "Run_C2_import"),
                      log_step("PostImport", "Check_C3", "Run_C3_post_import")],
        }}},
        {"Write_log": op(SP, s.SP_API, "CreateFile", {
            "dataset": s.ADMIN_SITE,
            "folderPath": s.LOG_FOLDER,
            "name": f"@{{concat({SOL}, '_', {TARGET}, '_', utcNow('yyyyMMdd-HHmmss'), '.json')}}",
            "body": "@{string(outputs('Log_entry'))}",
        })},
    )
    actions = seq(
        {"Solution": {"type": "Compose", "inputs": "@coalesce(triggerBody()?['text'], 'Demo')"}},
        {"Target": {"type": "Compose", "inputs": "@coalesce(triggerBody()?['text_1'], 'TEST')"}},
        {"Init_FailMessage": {"type": "InitializeVariable", "inputs": {
            "variables": [{"name": "FailMessage", "type": "string", "value": ""}]}}},
        {"Main": {"type": "Scope", "actions": main}},
    )
    actions["Log"] = after({"type": "Scope", "actions": log}, "Main",
                           status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions["Report_failure"] = after({
        "type": "If",
        "expression": {"equals": ["@actions('Main')?['status']", "Succeeded"]},
        "actions": {},
        "else": {"actions": {"Stop_failed": terminate("@{outputs('Log_entry')?['message']}")}},
    }, "Log", status=("Succeeded", "Failed"))
    return clientdata(manual_trigger([
        ("text", "Solution", "Solution unique name (default Demo)"),
        ("text_1", "Target", "TEST or PROD (default TEST)"),
    ]), actions, s.FLOW_REFS)


FLOWS = [
    (s.C2_NAME, lambda ids: c2()),
    (s.C3_NAME, lambda ids: c3()),
    (s.C1_NAME, c1),
]
