"""Build and deploy the ALM spike flows into the ADMIN environment.

Creates (idempotently) publisher `almspike`, solution `ALMSpike`, four connection
references and five solution-aware cloud flows:

  Variant A (two flows, one Dataverse reference):
    ALMSpike A1 - Export Demo (DEV)
    ALMSpike A2 - Import Demo (TEST)
  Variant B (one flow, two Dataverse references: DEV + TEST):
    ALMSpike B - Export and Import Demo (DEV to TEST)
  Variant C (parent calls child, passes the archived ZIP path):
    ALMSpike C2 - Import Demo (TEST, child)
    ALMSpike C1 - Export Demo and run C2 (parent)

Usage:  python3 spike/build_spike.py [--dry-run]
Auth:   az CLI token for the ADMIN org. Refuses to run outside the approved tenant.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TENANT = "1c5afb69-a82c-4c81-b2cc-743ce7f91dac"
ADMIN = "https://adminorg774eae27.crm17.dynamics.com"
DEV = "https://devorgf20ef6ea.crm17.dynamics.com"
TEST = "https://testorg5fd244de.crm17.dynamics.com"
ADMIN_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Admin"
TEST_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Test"
SOLUTION = "ALMSpike"

DV_API = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
SP_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"

# ADMIN connections owned by kriall076 (read back 2026-09-23).
DV_CONN = "shared-commondataser-88f9738e"
SP_CONN = "shared-sharepointonl-a0f00819"
# TEST SharePoint connection created 2026-09-23 for the dev_SharePoint import binding.
TEST_SP_CONN = "shared-sharepointonl-0f567e53"

CONN_REFS = {
    "alm_Dataverse": ("ALMSpike Dataverse", DV_API, DV_CONN),
    "alm_DataverseDEV": ("ALMSpike Dataverse DEV", DV_API, DV_CONN),
    "alm_DataverseTEST": ("ALMSpike Dataverse TEST", DV_API, DV_CONN),
    "alm_SharePoint": ("ALMSpike SharePoint", SP_API, SP_CONN),
}

OUT = Path(__file__).parent / "flows"


# ---------- definition building blocks ----------

def op(conn_key, api, operation, params):
    return {
        "type": "OpenApiConnection",
        "inputs": {
            "host": {"connectionName": conn_key, "operationId": operation, "apiId": api},
            "parameters": params,
            "authentication": "@parameters('$authentication')",
        },
    }


def after(action, *prev, status=("Succeeded",)):
    action["runAfter"] = {p: list(status) for p in prev}
    return action


def unbound(conn_key, org, action_name, item):
    params = {"organization": org, "actionName": action_name}
    params.update({f"item/{k}": v for k, v in item.items()})
    return op(conn_key, DV_API, "PerformUnboundActionWithOrganization", params)


def poll_block(conn_key, org, job_expr, prefix):
    """Do-until loop that waits for an asyncoperation to reach statecode 3 (Completed)."""
    get = op(conn_key, DV_API, "GetItemWithOrganization", {
        "organization": org,
        "entityName": "asyncoperations",
        "recordId": job_expr,
        "$select": "statecode,statuscode,message,friendlymessage",
    })
    return {
        f"{prefix}_Wait_for_job": {
            "type": "Until",
            "expression": f"@equals(body('{prefix}_Get_job')?['statecode'], 3)",
            "limit": {"count": 90, "timeout": "PT30M"},
            "actions": {
                f"{prefix}_Delay": {"type": "Wait", "inputs": {"interval": {"count": 20, "unit": "Second"}}},
                f"{prefix}_Get_job": after(get, f"{prefix}_Delay"),
            },
        }
    }


def fail_if_not_succeeded(prefix, on_success):
    """statuscode 30 = Succeeded. Anything else terminates the run as Failed with the job message."""
    return {
        "type": "If",
        "expression": {"equals": [f"@body('{prefix}_Get_job')?['statuscode']", 30]},
        "actions": on_success,
        "else": {"actions": {
            f"{prefix}_Job_failed": {
                "type": "Terminate",
                "inputs": {
                    "runStatus": "Failed",
                    "runError": {
                        "code": f"@{{string(body('{prefix}_Get_job')?['statuscode'])}}",
                        "message": f"@{{coalesce(body('{prefix}_Get_job')?['friendlymessage'], body('{prefix}_Get_job')?['message'], 'no message')}}",
                    },
                },
            }
        }},
    }


def component_parameters_text(list_id_expr, test_conn):
    """ImportSolutionAsync ComponentParameters as JSON text.

    Built as a string because the flow engine parses an object key starting with '@'
    ('@odata.type') as an expression, and '@@' does not escape object keys.
    """
    params = [
        {"@odata.type": "Microsoft.Dynamics.CRM.environmentvariablevalue",
         "schemaname": "dev_SharePointSite", "value": TEST_SITE},
        {"@odata.type": "Microsoft.Dynamics.CRM.environmentvariablevalue",
         "schemaname": "dev_ProductsList", "value": "__LIST_ID__"},
        {"@odata.type": "Microsoft.Dynamics.CRM.connectionreference",
         "connectionreferencelogicalname": "dev_SharePoint",
         "connectionid": test_conn, "connectorid": SP_API},
    ]
    # The @{...} interpolation makes the whole string a template, where a bare '@' fails
    # validation. Write '@@' here; the import action swaps it back with replace().
    text = json.dumps(params).replace("@odata.type", "@@odata.type")
    return text.replace("__LIST_ID__", "@{" + list_id_expr + "}")


def manual_trigger(inputs):
    """Button trigger with optional text inputs (optional so API runs can start it without inputs)."""
    props = {key: {"title": title, "type": "string", "x-ms-dynamically-added": True,
                   "description": desc, "x-ms-content-hint": "TEXT"}
             for key, title, desc in inputs}
    return {"manual": {"type": "Request", "kind": "Button", "inputs": {
        "schema": {"type": "object", "properties": props, "required": []}}}}


def export_steps(dv_key):
    """Export Demo (managed) from DEV, wait, download, archive to ALM-Admin/Solutions/Demo."""
    acts = {
        "Export_Demo_from_DEV": unbound(dv_key, DEV, "ExportSolutionAsync",
                                        {"SolutionName": "Demo", "Managed": True}),
    }
    poll = poll_block(dv_key, DEV, "@body('Export_Demo_from_DEV')?['AsyncOperationId']", "Export")
    acts.update({k: after(v, "Export_Demo_from_DEV") for k, v in poll.items()})
    acts["Export_succeeded"] = after(fail_if_not_succeeded("Export", {
        "Download_export": unbound(dv_key, DEV, "DownloadSolutionExportData",
                                   {"ExportJobId": "@body('Export_Demo_from_DEV')?['ExportJobId']"}),
        "Archive_ZIP_in_ALM_Admin": after(op("shared_sharepointonline", SP_API, "CreateFile", {
            "dataset": ADMIN_SITE,
            "folderPath": "/Solutions/Demo",
            "name": "@{concat('Demo_managed_', utcNow('yyyyMMdd-HHmmss'), '.zip')}",
            "body": "@base64ToBinary(body('Download_export')?['ExportSolutionFile'])",
        }), "Download_export"),
    }), "Export_Wait_for_job")
    return acts


def import_steps(dv_key, customization_expr, list_id_expr, run_after):
    acts = {
        "Component_parameters": after({"type": "Compose",
                                       "inputs": component_parameters_text(list_id_expr, TEST_SP_CONN)},
                                      *run_after),
        "Import_Demo_to_TEST": after(unbound(dv_key, TEST, "ImportSolutionAsync", {
            "CustomizationFile": customization_expr,
            "OverwriteUnmanagedCustomizations": False,
            "PublishWorkflows": True,
            # '@@' survives the Compose unchanged; restore '@odata.type' at run time.
            "ComponentParameters": "@json(replace(outputs('Component_parameters'), '@@odata', '@odata'))",
        }), "Component_parameters"),
    }
    poll = poll_block(dv_key, TEST, "@body('Import_Demo_to_TEST')?['AsyncOperationId']", "Import")
    acts.update({k: after(v, "Import_Demo_to_TEST") for k, v in poll.items()})
    acts["Import_succeeded"] = after(fail_if_not_succeeded("Import", {
        "Import_result": {"type": "Compose", "inputs": {
            "ImportJobKey": "@body('Import_Demo_to_TEST')?['ImportJobKey']",
            "AsyncOperationId": "@body('Import_Demo_to_TEST')?['AsyncOperationId']",
            "statuscode": "@body('Import_Get_job')?['statuscode']",
        }},
    }), "Import_Wait_for_job")
    return acts


def respond(outputs):
    """'Respond to a PowerApp or flow' with string outputs. Required for a child flow."""
    return {"type": "Response", "kind": "PowerApp", "inputs": {
        "statusCode": 200,
        "body": {k: v for k, v in outputs.items()},
        "schema": {"type": "object", "properties": {
            k: {"title": k, "type": "string", "x-ms-dynamically-added": True} for k in outputs}},
    }}


def run_child(workflow_id, body):
    """Built-in 'Run a Child Flow'. workflow_id is the child's Dataverse workflowid."""
    return {"type": "Workflow", "inputs": {"host": {"workflowReferenceName": workflow_id}, "body": body}}


def clientdata(trigger, actions, refs):
    conn_refs = {key: {"runtimeSource": "embedded",
                       "connection": {"connectionReferenceLogicalName": logical},
                       "api": {"name": api.rsplit("/", 1)[1]}}
                 for key, (logical, api) in refs.items()}
    return {"properties": {
        "connectionReferences": conn_refs,
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {"$connections": {"defaultValue": {}, "type": "Object"},
                           "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
            "triggers": trigger,
            "actions": actions,
        },
        "templateName": "",
    }, "schemaVersion": "1.0.0.0"}


# Placeholder when the list-ID input is empty (API runs cannot pass button inputs).
# The import still proves transport; set the real TEST list ID on dev_ProductsList afterwards.
PLACEHOLDER_LIST_ID = "00000000-0000-0000-0000-000000000000"
# Spike default: the ZIP archived by A1 run 08584114276248311268643739549CU22.
# The API cannot pass button inputs as kriall076, so A2 falls back to it.
DEFAULT_ZIP_PATH = "/Solutions/Demo/Demo_managed_20260923-160145.zip"


def list_id(field):
    return f"coalesce(triggerBody()?['{field}'], '{PLACEHOLDER_LIST_ID}')"


C2_NAME = "ALMSpike C2 - Import Demo (TEST, child)"
C1_NAME = "ALMSpike C1 - Export Demo and run C2 (parent)"


def flows(ids=None):
    """Flow definitions in deploy order. ids maps flow name -> workflowid (C1 needs C2's)."""
    ids = ids or {}
    list_input = ("text", "TEST Products list ID", "GUID of the Products list on the ALM-Test site")

    # A1: export + archive. One Dataverse reference.
    a1 = clientdata(manual_trigger([]), export_steps("shared_commondataserviceforapps"), {
        "shared_commondataserviceforapps": ("alm_Dataverse", DV_API),
        "shared_sharepointonline": ("alm_SharePoint", SP_API),
    })

    # A2: read archived ZIP, import. Same Dataverse reference.
    a2_actions = {"Get_archived_ZIP": op("shared_sharepointonline", SP_API, "GetFileContentByPath", {
        "dataset": ADMIN_SITE, "path": f"@coalesce(triggerBody()?['text'], '{DEFAULT_ZIP_PATH}')", "inferContentType": False})}
    a2_actions.update(import_steps("shared_commondataserviceforapps",
                                   "@body('Get_archived_ZIP')?['$content']",
                                   list_id("text_1"), ["Get_archived_ZIP"]))
    a2 = clientdata(manual_trigger([
        ("text", "Archived ZIP path", "e.g. /Solutions/Demo/Demo_managed_20260923-120000.zip"),
        ("text_1",) + list_input[1:],
    ]), a2_actions, {
        "shared_commondataserviceforapps": ("alm_Dataverse", DV_API),
        "shared_sharepointonline": ("alm_SharePoint", SP_API),
    })

    # B: one flow. DEV reference for export, TEST reference for import. Imports the archived bytes.
    b_actions = export_steps("shared_commondataserviceforapps_dev")
    b_actions.update(import_steps("shared_commondataserviceforapps_test",
                                  "@body('Download_export')?['ExportSolutionFile']",
                                  list_id("text"), ["Export_succeeded"]))
    b = clientdata(manual_trigger([list_input]), b_actions, {
        "shared_commondataserviceforapps_dev": ("alm_DataverseDEV", DV_API),
        "shared_commondataserviceforapps_test": ("alm_DataverseTEST", DV_API),
        "shared_sharepointonline": ("alm_SharePoint", SP_API),
    })

    # C2: child. Same as A2, no default path, ends with a response to the parent.
    c2_actions = {"Get_archived_ZIP": op("shared_sharepointonline", SP_API, "GetFileContentByPath", {
        "dataset": ADMIN_SITE, "path": "@triggerBody()?['text']", "inferContentType": False})}
    c2_actions.update(import_steps("shared_commondataserviceforapps",
                                   "@body('Get_archived_ZIP')?['$content']",
                                   list_id("text_1"), ["Get_archived_ZIP"]))
    c2_actions["Import_succeeded"]["actions"]["Respond_to_parent"] = after(respond({
        "status": "Succeeded",
        "zippath": "@{triggerBody()?['text']}",
        "importjobkey": "@{body('Import_Demo_to_TEST')?['ImportJobKey']}",
    }), "Import_result")
    c2 = clientdata(manual_trigger([
        ("text", "Archived ZIP path", "Set by the parent flow"),
        ("text_1",) + list_input[1:],
    ]), c2_actions, {
        "shared_commondataserviceforapps": ("alm_Dataverse", DV_API),
        "shared_sharepointonline": ("alm_SharePoint", SP_API),
    })

    # C1: parent. A1 + run C2 with the path of the ZIP it just archived.
    c1_actions = export_steps("shared_commondataserviceforapps")
    c1_actions["Run_C2_import"] = after(run_child(ids.get(C2_NAME, PLACEHOLDER_LIST_ID), {
        "text": "@body('Archive_ZIP_in_ALM_Admin')?['Path']",
        "text_1": f"@{list_id('text')}",
    }), "Export_succeeded")
    c1 = clientdata(manual_trigger([list_input]), c1_actions, {
        "shared_commondataserviceforapps": ("alm_Dataverse", DV_API),
        "shared_sharepointonline": ("alm_SharePoint", SP_API),
    })

    return {
        "ALMSpike A1 - Export Demo (DEV)": a1,
        "ALMSpike A2 - Import Demo (TEST)": a2,
        "ALMSpike B - Export and Import Demo (DEV to TEST)": b,
        C2_NAME: c2,
        C1_NAME: c1,
    }


# ---------- Dataverse Web API ----------

def token():
    acct = json.loads(subprocess.check_output(["az", "account", "show", "-o", "json"]))
    if acct["tenantId"] != TENANT:
        sys.exit(f"STOP: az tenant is {acct['tenantId']}, expected {TENANT}")
    print(f"az identity: {acct['user']['name']} / {acct['tenantId']}")
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", ADMIN,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()


def api(tok, method, path, body=None, solution=None):
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json",
               "OData-Version": "4.0", "Content-Type": "application/json",
               "Prefer": "return=representation"}
    if solution:
        headers["MSCRM.SolutionUniqueName"] = solution
    path = urllib.parse.quote(path, safe="/?&=$(),'@")
    req = urllib.request.Request(f"{ADMIN}/api/data/v9.2/{path}", method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")


def first(tok, path):
    rows = api(tok, "GET", path)["value"]
    return rows[0] if rows else None


def ensure(tok):
    pub = first(tok, "publishers?$filter=uniquename eq 'almspike'&$select=publisherid")
    if not pub:
        pub = api(tok, "POST", "publishers", {
            "uniquename": "almspike", "friendlyname": "ALM Spike",
            "customizationprefix": "alm", "customizationoptionvalueprefix": 25310})
        print("created publisher almspike")
    sol = first(tok, f"solutions?$filter=uniquename eq '{SOLUTION}'&$select=solutionid")
    if not sol:
        api(tok, "POST", "solutions", {
            "uniquename": SOLUTION, "friendlyname": "ALM Spike", "version": "1.0.0.0",
            "publisherid@odata.bind": f"/publishers({pub['publisherid']})"})
        print(f"created solution {SOLUTION}")

    for logical, (display, connector, conn) in CONN_REFS.items():
        if first(tok, f"connectionreferences?$filter=connectionreferencelogicalname eq '{logical}'"
                      "&$select=connectionreferenceid"):
            continue
        api(tok, "POST", "connectionreferences", {
            "connectionreferencelogicalname": logical, "connectionreferencedisplayname": display,
            "connectorid": connector, "connectionid": conn}, solution=SOLUTION)
        print(f"created connection reference {logical} -> {conn}")

    ids = {}
    for name in flows():
        cd = flows(ids)[name]
        existing = first(tok, f"workflows?$filter=name eq '{name}' and category eq 5"
                              "&$select=workflowid,statecode")
        payload = {"clientdata": json.dumps(cd)}
        if existing:
            wid = existing["workflowid"]
            if existing["statecode"] == 1:  # turning off re-validates the stored definition
                api(tok, "PATCH", f"workflows({wid})", {"statecode": 0, "statuscode": 1})
            api(tok, "PATCH", f"workflows({wid})", payload)
            print(f"updated flow {name} ({wid})")
        else:
            payload.update({"name": name, "category": 5, "type": 1, "primaryentity": "none"})
            wid = api(tok, "POST", "workflows", payload, solution=SOLUTION)["workflowid"]
            print(f"created flow {name} ({wid})")
        ids[name] = wid
        api(tok, "PATCH", f"workflows({wid})", {"statecode": 1, "statuscode": 2})
        print(f"  turned on {name}")


def main():
    OUT.mkdir(exist_ok=True)
    for name, cd in flows().items():
        (OUT / (name.split(" - ")[0].replace(" ", "_") + ".json")).write_text(json.dumps(cd, indent=2))
    print(f"wrote {len(flows())} definitions to {OUT}")
    if "--dry-run" in sys.argv:
        return
    ensure(token())


if __name__ == "__main__":
    main()
