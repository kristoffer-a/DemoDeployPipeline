"""Definitions of the deploy pipeline flows: C1 parent, C2 import child, C3 post-import child."""
from pipeline import settings as s
from pipeline.defs import (after, clientdata, fetch_in_solution, if_job_succeeded, job_message, list_rows,
                           manual_trigger, op, poll_block, respond, seq, sp_items, terminate, unbound, url_expr)

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


# ---------- C2: import child ----------

C2_SOL, C2_TARGET = "triggerBody()?['text_1']", "triggerBody()?['text_2']"


def c2():
    # setProperty() builds the '@odata.type' key at run time; a literal '@' key is rejected by the engine.
    conn_param = ("@setProperty(setProperty(setProperty(setProperty(json('{}'), "
                  "'@odata.type', 'Microsoft.Dynamics.CRM.connectionreference'), "
                  "'connectionreferencelogicalname', item()?['ConnectionReference']), "
                  "'connectionid', item()?['ConnectionId']), 'connectorid', item()?['ConnectorId'])")
    var_param = ("@setProperty(setProperty(setProperty(json('{}'), "
                 "'@odata.type', 'Microsoft.Dynamics.CRM.environmentvariablevalue'), "
                 "'schemaname', item()?['SchemaName']), 'value', item()?['Value'])")

    importing = {
        "Import_to_target": unbound(DV, "@outputs('Target_url')", "ImportSolutionAsync", {
            "CustomizationFile": "@body('Get_archived_ZIP')?['$content']",
            "OverwriteUnmanagedCustomizations": False,
            "PublishWorkflows": True,
            "ComponentParameters": "@union(body('Connection_params'), body('Variable_params'))",
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
    }, {"Import_failed": terminate("@{" + job_message("Import") + "}")}), "Import_Wait_for_job")

    actions = seq(
        config_actions(C2_SOL, C2_TARGET, {"Stop_no_config": terminate(no_config_message(C2_SOL, C2_TARGET))}),
        {"Solution_connections": {"type": "Query", "inputs": {
            "from": "@body('Get_connection_map')?['value']",
            "where": "@contains(body('Dev_ref_names'), item()?['ConnectionReference'])"}}},
        {"Connection_params": {"type": "Select", "inputs": {
            "from": "@body('Solution_connections')", "select": conn_param}}},
        {"Variable_params": {"type": "Select", "inputs": {
            "from": "@body('Get_variable_map')?['value']", "select": var_param}}},
        {"Get_archived_ZIP": op(SP, s.SP_API, "GetFileContentByPath", {
            "dataset": s.ADMIN_SITE, "path": "@triggerBody()?['text']", "inferContentType": False})},
        importing,
    )
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
        {"Solution_connections": {"type": "Query", "inputs": {
            "from": "@body('Get_connection_map')?['value']",
            "where": "@contains(body('Dev_ref_names'), item()?['ConnectionReference'])"}}},
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
                            "actions": {"Stop_wrong_bindings": terminate(
                                "@concat('Connection references not bound as mapped (reference|connection): ', "
                                "join(body('Wrong_bindings'), ', '))")}}},
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
                              "actions": {"Stop_no_value_row": terminate(
                                  "@concat('No value row in the target for: ', join(body('Missing_value_rows'), ', '), "
                                  "'. Run the import first.')")}}},
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
                    "item/value": "@items('For_each_variable')?['Value']",
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
                "item/statecode": 1,
                "item/statuscode": 2,
            })},
        }},
        {"Reply": respond({
            "status": "Succeeded",
            "message": "@{concat('Bindings OK; variables set: ', length(body('Get_variable_map')?['value']), "
                       "'; flows turned on: ', length(body('Off_flows')?['value']))}",
        })},
    )
    actions = seq(
        config_actions(C3_SOL, C3_TARGET, {"Stop_no_config": terminate(no_config_message(C3_SOL, C3_TARGET))}),
        check, variables, turn_on,
    )
    return clientdata(manual_trigger([
        ("text", "Solution", "Solution unique name, e.g. Demo"),
        ("text_1", "Target", "TEST or PROD"),
    ]), actions, s.FLOW_REFS)
