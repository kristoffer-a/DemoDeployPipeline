"""Fail-closed activation contract for C1/C2/C3 (no live side effects here)."""
import json
from pathlib import Path

from pipeline import settings as s
from pipeline.defs import fail_steps, fetch_in_solution, list_rows, op, runtime_json_schema, seq

SCHEMA = json.loads((Path(__file__).parents[1] / "contracts/flow-activation.schema.json").read_text())
RUNTIME_SCHEMA = runtime_json_schema(SCHEMA)
IMPORT_BLOCK = (
    "Cloud-flow imports are not qualified yet. Import can activate flows before C3; "
    "PublishWorkflows does not control cloud flows. Complete the isolated TEST import qualification first."
)


def solution_flows(org, solution):
    fetch = fetch_in_solution(
        "workflow", "workflowid", ["name", "statecode"], solution, [("category", "5"), ("type", "1")])
    # One more than the manifest limit detects truncation even without paging annotations.
    fetch = fetch.replace('<fetch distinct="true">', '<fetch distinct="true" count="101" page="1">')
    return list_rows(s.DV_KEY, org, "workflows", fetch=fetch)


def incomplete_inventory(action):
    return {"or": [
        {"not": {"equals": [f"@empty(body('{action}')?['@odata.nextLink'])", True]}},
        {"equals": [f"@body('{action}')?['@Microsoft.Dynamics.CRM.morerecords']", True]},
        {"not": {"equals": [f"@empty(body('{action}')?['@Microsoft.Dynamics.CRM.fetchxmlpagingcookie'])", True]}},
        {"greater": [f"@length(body('{action}')?['value'])", 100]},
    ]}


def reject(name, expression, message):
    return {name: {"type": "If", "expression": expression, "actions": fail_steps("Fail_" + name, message)}}


def validate_policy(content, solution, org):
    """Require a complete, unique policy for this solution before any mutation.

    Fail on pagination instead of silently treating a partial page as full coverage.
    The GUID is workflowid (stable across imports), never display name/workflowidunique.
    """
    return seq(
        {"Activation_policy": {"type": "ParseJson", "inputs": {"content": content, "schema": RUNTIME_SCHEMA}}},
        reject("Check_policy_solution", {"not": {"equals": ["@body('Activation_policy')?['solution']", "@" + solution]}},
               "Activation manifest is for a different solution."),
        {"Solution_flows": solution_flows(org, solution)},
        reject("Check_flow_page", incomplete_inventory("Solution_flows"),
               "Solution flow inventory is paginated; complete inventory support is required."),
        {"Policy_ids": {"type": "Select", "inputs": {
            "from": "@body('Activation_policy')?['flows']", "select": "@item()?['workflowId']"}}},
        {"Solution_flow_ids": {"type": "Select", "inputs": {
            "from": "@body('Solution_flows')?['value']", "select": "@toLower(item()?['workflowid'])"}}},
        {"Unknown_flow_ids": {"type": "Query", "inputs": {
            "from": "@body('Policy_ids')", "where": "@not(contains(body('Solution_flow_ids'), item()))"}}},
        {"Missing_flow_ids": {"type": "Query", "inputs": {
            "from": "@body('Solution_flow_ids')", "where": "@not(contains(body('Policy_ids'), item()))"}}},
        reject("Check_policy_coverage", {"or": [
            {"greater": ["@length(body('Unknown_flow_ids'))", 0]},
            {"greater": ["@length(body('Missing_flow_ids'))", 0]},
            {"not": {"equals": ["@length(body('Policy_ids'))", "@length(union(body('Policy_ids'), body('Policy_ids')))"]}},
        ]}, "Activation manifest must list every solution flow exactly once, with no foreign IDs."),
    )


def block_cloud_imports(solution, target_org, conditional=False):
    """Temporary gate: no cloud-flow imports until import-time activation is qualified.

    Check source AND target: removing a flow from DEV must not evade the gate on upgrades.
    C2 also invokes this independently, so bypassing C1 cannot bypass the gate.
    """
    present = {"greater": ["@add(length(body('Solution_flows')?['value']), length(body('Import_target_flows')?['value']))", 0]}
    unsafe = {"or": [present, incomplete_inventory("Import_target_flows")]}
    guard = seq(
        {"Import_target_flows": solution_flows(target_org, solution)},
        reject("Check_cloud_import", unsafe, IMPORT_BLOCK),
    )
    if conditional:
        return {"If_check_import": {"type": "If", "expression": {"equals": ["@outputs('Config')?['RunImport']", True]},
                                    "actions": guard}}
    return guard


def apply_policy(org, solution):
    """Disable first, then enable in manifest order; verify all desired states afterwards."""
    # A failed connector call leaves FailMessage set even when Foreach continues.
    # Clear it only after success; every later iteration checks it before writing.
    phases = []
    for phase, enabled, state, status in (("Disable", False, 0, 1), ("Enable", True, 1, 2)):
        loop = f"For_each_{phase}"
        current = f"Current_{phase}"
        phases.extend([
            {f"{phase}_flows": {"type": "Query", "inputs": {
                "from": "@body('Activation_policy')?['flows']",
                "where": f"@equals(item()?['enabled'], {str(enabled).lower()})"}}},
            {loop: {"type": "Foreach", "foreach": f"@body('{phase}_flows')",
                    "runtimeConfiguration": {"concurrency": {"repetitions": 1}}, "actions": seq(
                        reject(f"Check_previous_{phase}", {"not": {"equals": ["@empty(variables('FailMessage'))", True]}},
                               "A previous flow state update failed; later updates were blocked."),
                        {current: {"type": "Query", "inputs": {
                            "from": "@body('Solution_flows')?['value']",
                            "where": f"@equals(toLower(item()?['workflowid']), items('{loop}')?['workflowId'])"}}},
                        {f"If_change_{phase}": {"type": "If", "expression": {
                            "not": {"equals": [f"@first(body('{current}'))?['statecode']", state]}},
                            "actions": seq(
                                {f"Mark_pending_{phase}": {"type": "SetVariable", "inputs": {
                                    "name": "FailMessage", "value": "Flow state update failed; inspect target states before retrying."}}},
                                {f"Set_{phase}": op(s.DV_KEY, s.DV_API, "UpdateOnlyRecordWithOrganization", {
                                    "organization": org, "entityName": "workflows",
                                    "recordId": f"@items('{loop}')?['workflowId']",
                                    "item": {"statecode": state, "statuscode": status},
                                })},
                                {f"Clear_pending_{phase}": {"type": "SetVariable", "inputs": {
                                    "name": "FailMessage", "value": ""}}},
                            )}},
                    )}},
        ])
    return seq(
        *phases,
        {"Verify_flows": solution_flows(org, solution)},
        {"Expected_states": {"type": "Select", "inputs": {
            "from": "@body('Activation_policy')?['flows']",
            "select": "@concat(item()?['workflowId'], '|', if(item()?['enabled'], '1', '0'))"}}},
        {"Observed_states": {"type": "Select", "inputs": {
            "from": "@body('Verify_flows')?['value']",
            "select": "@concat(toLower(item()?['workflowid']), '|', string(item()?['statecode']))"}}},
        reject("Check_final_states", {"or": [
            incomplete_inventory("Verify_flows"),
            {"not": {"equals": ["@length(body('Expected_states'))", "@length(body('Observed_states'))"]}},
            {"not": {"equals": ["@length(intersection(body('Expected_states'), body('Observed_states')))", "@length(body('Expected_states'))"]}},
        ]}, "Flow activation readback did not match the manifest; inspect target states before retrying."),
    )
