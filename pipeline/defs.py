"""Logic Apps workflow-definition building blocks for the ALM pipeline flows."""
import re

from pipeline.settings import DV_API, URL_AS_OBJECT

# ---------- actions ----------

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


def seq(*groups):
    """Merge action groups in order. Each group's first action runs after the previous group's last."""
    out, prev = {}, None
    for group in groups:
        first = next(iter(group))
        if prev:
            after(group[first], prev)
        out.update(group)
        prev = list(group)[-1]
    return out


def unbound(conn_key, org, action_name, item):
    params = {"organization": org, "actionName": action_name}
    params["item"] = dict(item)
    return op(conn_key, DV_API, "PerformUnboundActionWithOrganization", params)


def list_rows(conn_key, org, entity, select=None, filter_=None, expand=None, fetch=None):
    params = {"organization": org, "entityName": entity}
    for key, value in (("$select", select), ("$filter", filter_), ("$expand", expand), ("fetchXml", fetch)):
        if value:
            params[key] = value
    return op(conn_key, DV_API, "ListRecordsWithOrganization", params)


def sp_items(conn_key, table, filter_=None, top=None):
    from pipeline.settings import ADMIN_SITE, SP_API
    params = {"dataset": ADMIN_SITE, "table": table}
    if filter_:
        params["$filter"] = filter_
    if top:
        params["$top"] = top
    return op(conn_key, SP_API, "GetItems", params)


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


def job_message(prefix):
    return f"coalesce(body('{prefix}_Get_job')?['friendlymessage'], body('{prefix}_Get_job')?['message'], 'no message')"


def if_job_succeeded(prefix, on_success, on_fail):
    """statuscode 30 = Succeeded."""
    return {
        "type": "If",
        "expression": {"equals": [f"@body('{prefix}_Get_job')?['statuscode']", 30]},
        "actions": on_success,
        "else": {"actions": on_fail},
    }


def terminate(message_expr):
    """Child flows only: stops the run as Failed. The parent sees the child action fail."""
    return {"type": "Terminate", "inputs": {"runStatus": "Failed",
                                            "runError": {"code": "DeployStepFailed", "message": message_expr}}}


def fail_steps(name, message_expr):
    """Parent only: record the message, then fail one action so the Main scope fails but Log still runs.

    Terminate would end the whole run and skip the Log scope. int() of a text message throws.
    """
    return {
        f"Set_{name}": {"type": "SetVariable", "inputs": {"name": "FailMessage", "value": message_expr}},
        name: after({"type": "Compose", "inputs": "@int(variables('FailMessage'))"}, f"Set_{name}"),
    }


def respond(outputs):
    """'Respond to a PowerApp or flow' with string outputs. Required at the end of a child flow."""
    return {"type": "Response", "kind": "PowerApp", "inputs": {
        "statusCode": 200,
        "body": dict(outputs),
        "schema": {"type": "object", "properties": {
            k: {"title": k, "type": "string", "x-ms-dynamically-added": True} for k in outputs}},
    }}


def run_child(workflow_id, body):
    """Built-in 'Run a Child Flow'. workflow_id is the child's Dataverse workflowid.

    retryPolicy 'none': a child failure must not be retried by the built-in action; the parent
    inspects the child's own reply (see Check_C2/Check_C3 in c1()) to decide success/failure.
    """
    return {"type": "Workflow", "inputs": {"host": {"workflowReferenceName": workflow_id}, "body": body,
                                           "retryPolicy": {"type": "none"}}}


def manual_trigger(inputs):
    """Button trigger with optional text inputs: (key, title, description) tuples."""
    props = {key: {"title": title, "type": "string", "x-ms-dynamically-added": True,
                   "description": desc, "x-ms-content-hint": "TEXT"}
             for key, title, desc in inputs}
    return {"manual": {"type": "Request", "kind": "Button", "inputs": {
        "schema": {"type": "object", "properties": props, "required": []}}}}


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


# ---------- expressions ----------

def fetch_in_solution(entity, pk, attrs, solution_expr, conditions=()):
    """FetchXML for rows of `entity` that are components of the solution named by solution_expr.

    `pk` is always emitted first (the connector needs the entity's key property populated even
    when only other attributes are selected), and is never duplicated if already in `attrs`.
    """
    ordered_attrs = [pk] + [a for a in attrs if a != pk]
    attr_xml = "".join(f'<attribute name="{a}"/>' for a in ordered_attrs)
    cond_xml = "".join(f'<condition attribute="{a}" operator="eq" value="{v}"/>' for a, v in conditions)
    filter_xml = f"<filter>{cond_xml}</filter>" if conditions else ""
    return (f'<fetch distinct="true"><entity name="{entity}">{attr_xml}{filter_xml}'
            f'<link-entity name="solutioncomponent" from="objectid" to="{pk}" link-type="inner">'
            f'<link-entity name="solution" from="solutionid" to="solutionid" link-type="inner">'
            f'<filter><condition attribute="uniquename" operator="eq" value="@{{{solution_expr}}}"/></filter>'
            f"</link-entity></link-entity></entity></fetch>")


def url_expr(obj_expr, field):
    """Expression (no leading @) for a SharePoint Hyperlink column's URL."""
    suffix = "?['Url']" if URL_AS_OBJECT else ""
    return f"{obj_expr}?['{field}']{suffix}"


# ---------- validation ----------

_REF = re.compile(r"\b(?:body|outputs|actions|items|result)\('([^']+)'\)")


def _action_maps(actions, path="actions"):
    """Yield (path, actions-dict) for every level of nesting."""
    yield path, actions
    for name, action in actions.items():
        if isinstance(action.get("actions"), dict):
            yield from _action_maps(action["actions"], f"{path}.{name}")
        els = action.get("else")
        if isinstance(els, dict) and isinstance(els.get("actions"), dict):
            yield from _action_maps(els["actions"], f"{path}.{name}.else")


def _walk(value, path, keys, strings):
    if isinstance(value, dict):
        for k, v in value.items():
            keys.append((f"{path}.{k}", k))
            _walk(v, f"{path}.{k}", keys, strings)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk(v, f"{path}[{i}]", keys, strings)
    elif isinstance(value, str):
        strings.append((path, value))


def validate(cd):
    """Static checks the flow engine would otherwise fail on at save or run time."""
    definition = cd["properties"]["definition"]
    errors, names = [], set()
    maps = list(_action_maps(definition["actions"]))
    for _, level in maps:
        names.update(level)
    for path, level in maps:
        for name, action in level.items():
            for prev in action.get("runAfter", {}):
                if prev not in level:
                    errors.append(f"{path}.{name}: runAfter '{prev}' is not a sibling")
    keys, strings = [], []
    _walk(definition, "definition", keys, strings)
    for path, key in keys:
        if key.startswith("@"):
            errors.append(f"{path}: object key '{key}' starts with '@'")
    for path, text in strings:
        for ref in _REF.findall(text):
            if ref not in names:
                errors.append(f"{path}: references unknown action '{ref}'")
    return errors
