"""Change ALM-Admin SharePoint config through a flow (the browser pane cannot reach SharePoint).

This is a Demo -> TEST test/admin helper, not a general config tool: `provision` and `config` are
hard-pinned to solution 'Demo' and target 'TEST' (see DEMO_CONFIG below), matching the fixed
TEST_ORG/TEST_SITE constants in pipeline.settings. `connection-env` and `variable` take an explicit
environment/solution argument, but are only ever exercised against Demo/TEST in this project.

Each command regenerates and deploys the flow "ALM Setup - SharePoint config" with a fixed list of
SharePoint REST requests, sent through the kriall076 SharePoint connection. Run the flow afterwards
(FlowAgent run_flow) and read its 'Results' action with pipeline.flowapi.

Usage:
  python3 -m pipeline.sp_setup provision
  python3 -m pipeline.sp_setup config RunImport=false RunPostImport=false
  python3 -m pipeline.sp_setup connection-env TEST|PROD
  python3 -m pipeline.sp_setup variable dev_ProductsList=<value>
  python3 -m pipeline.sp_setup readback
"""
import json
import sys

from pipeline import settings as s
from pipeline.defs import after, clientdata, manual_trigger, op, validate

SETUP_NAME = "ALM Setup - SharePoint config"
JSON_NOMETA = "application/json;odata=nometadata"
TEST_SITE = s.TEST_SITE
TEST_ORG = s.TEST_ORG
PLACEHOLDER_LIST_ID = "00000000-0000-0000-0000-000000000000"


def request(method, uri, body=None, extra_headers=None):
    params = {"dataset": s.ADMIN_SITE, "parameters/method": method, "parameters/uri": uri,
              "parameters/headers": {"Accept": JSON_NOMETA, "Content-Type": "application/json;odata=verbose",
                                     **(extra_headers or {})}}
    if body is not None:
        params["parameters/body"] = json.dumps(body)
    return op(s.SP_KEY, s.SP_API, "HttpRequest", params)


def lst(title):
    return f"_api/web/lists/getbytitle('{title}')"


def item_type(title):
    return f"SP.Data.{title}ListItem"


# ---------- operations: each returns an ordered dict of actions ----------

def ensure_list(title):
    return {f"Create_list_{title}": request("POST", "_api/web/lists", {
        "__metadata": {"type": "SP.List"}, "BaseTemplate": 100, "Title": title})}


def ensure_field(title, schema_xml):
    name = schema_xml.split("Name='", 1)[1].split("'", 1)[0]
    return {f"Create_field_{title}_{name}": request("POST", f"{lst(title)}/fields/CreateFieldAsXml", {
        "parameters": {"__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                       "SchemaXml": schema_xml, "Options": 25}})}


def upsert(key, title, odata_filter, fields):
    """Update the first item matching odata_filter, else create it."""
    find = f"Find_{key}"
    body = {"__metadata": {"type": item_type(title)}, **fields}
    return {
        find: request("GET", f"{lst(title)}/items?$select=Id&$filter={odata_filter.replace(' ', '%20')}"),
        f"Upsert_{key}": after({
            "type": "If",
            "expression": {"greater": [f"@length(body('{find}')?['value'])", 0]},
            "actions": {f"Update_{key}": request(
                "POST", f"{lst(title)}/items(@{{first(body('{find}')?['value'])?['Id']}})", body,
                {"X-HTTP-Method": "MERGE", "IF-MATCH": "*"})},
            "else": {"actions": {f"Create_{key}": request("POST", f"{lst(title)}/items", body)}},
        }, find),
    }


def readback():
    return {
        "Read_lists": request("GET", "_api/web/lists?$select=Title,Id&$filter=startswith(Title,'ALM')"),
        "Read_config": request("GET", f"{lst('ALMConfig')}/items"),
        "Read_connections": request("GET", f"{lst('ALMConnections')}/items"),
        "Read_variables": request("GET", f"{lst('ALMVariables')}/items"),
    }


# ---------- field schemas ----------

def choice_env(name):
    return (f"<Field Type='Choice' Name='{name}' StaticName='{name}' DisplayName='{name}' Required='TRUE'>"
            "<CHOICES><CHOICE>TEST</CHOICE><CHOICE>PROD</CHOICE></CHOICES></Field>")


def text(name, required=True):
    req = "TRUE" if required else "FALSE"
    return f"<Field Type='Text' Name='{name}' StaticName='{name}' DisplayName='{name}' Required='{req}'/>"


def yesno(name):
    return f"<Field Type='Boolean' Name='{name}' StaticName='{name}' DisplayName='{name}'><Default>0</Default></Field>"


def link(name):
    return (f"<Field Type='URL' Name='{name}' StaticName='{name}' DisplayName='{name}' "
            "Format='Hyperlink' Required='TRUE'/>")


def url_value(u):
    return {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": u, "Description": u}


# ---------- commands ----------

DEMO_CONFIG = "SolutionName eq 'Demo' and TargetEnvironment eq 'TEST'"
TEST_SP_REF = "Environment eq 'TEST' and ConnectionReference eq 'dev_SharePoint'"


def variable_filter(schema):
    return f"SolutionName eq 'Demo' and Environment eq 'TEST' and SchemaName eq '{schema}'"


def provision_ops():
    groups = []
    for x in (choice_env("TargetEnvironment"), link("TargetPowerPlatformUrl"), link("TargetSharePointUrl"),
              yesno("RunImport"), yesno("RunPostImport"), yesno("RunShare"), text("AppShareGroupId", False)):
        groups.append(ensure_field("ALMConfig", x))
    groups.append(ensure_list("ALMConnections"))
    for x in (choice_env("Environment"), text("ConnectionReference"), text("ConnectionId"), text("ConnectorId")):
        groups.append(ensure_field("ALMConnections", x))
    groups.append(ensure_list("ALMVariables"))
    for x in (text("SolutionName"), choice_env("Environment"), text("SchemaName"), text("Value")):
        groups.append(ensure_field("ALMVariables", x))
    groups.append(upsert("config", "ALMConfig", DEMO_CONFIG, {
        "TargetEnvironment": "TEST",
        "TargetPowerPlatformUrl": url_value(TEST_ORG),
        "TargetSharePointUrl": url_value(TEST_SITE),
        "RunImport": True, "RunPostImport": True, "RunShare": False,
    }))
    groups.append(upsert("connection", "ALMConnections", TEST_SP_REF, {
        "Title": "TEST dev_SharePoint", "Environment": "TEST", "ConnectionReference": "dev_SharePoint",
        "ConnectionId": "shared-sharepointonl-0f567e53", "ConnectorId": s.SP_API,
    }))
    groups.append(upsert("var_site", "ALMVariables", variable_filter("dev_SharePointSite"), {
        "Title": "Demo TEST dev_SharePointSite", "SolutionName": "Demo", "Environment": "TEST",
        "SchemaName": "dev_SharePointSite", "Value": TEST_SITE,
    }))
    groups.append(upsert("var_list", "ALMVariables", variable_filter("dev_ProductsList"), {
        "Title": "Demo TEST dev_ProductsList", "SolutionName": "Demo", "Environment": "TEST",
        "SchemaName": "dev_ProductsList", "Value": PLACEHOLDER_LIST_ID,
    }))
    return groups


def parse_value(v):
    return {"true": True, "false": False}.get(v.lower(), v)


def command_ops(argv):
    cmd, args = argv[0], argv[1:]
    if cmd == "provision":
        return provision_ops()
    if cmd == "config":
        return [upsert("config", "ALMConfig", DEMO_CONFIG,
                       {k: parse_value(v) for k, v in (a.split("=", 1) for a in args)})]
    if cmd == "connection-env":
        env = args[0]
        if env not in ("TEST", "PROD"):
            sys.exit(__doc__)
        return [upsert("connection", "ALMConnections",
                       "ConnectionReference eq 'dev_SharePoint'",
                       {"Environment": env})]
    if cmd == "variable":
        name, value = args[0].split("=", 1)
        return [upsert("variable", "ALMVariables", variable_filter(name), {"Value": value})]
    if cmd == "readback":
        return []
    sys.exit(__doc__)


def build(groups):
    """Chain every group so each group's first action runs after the previous group's last action,
    on ["Succeeded", "Failed", "Skipped"] (not just Succeeded/Failed): a group whose own first
    action was Skipped (e.g. its Find failed, so its If-branch Upsert never ran) must not skip every
    later group too. One failed request (e.g. 'already exists') therefore never cascades past its
    own group.
    """
    actions, prev = {}, None
    for group in groups + [readback()]:
        names = list(group)
        for i, name in enumerate(names):
            action = group[name]
            if i == 0 and prev:
                after(action, prev, status=("Succeeded", "Failed", "Skipped"))
            elif i > 0 and "runAfter" not in action:
                after(action, names[i - 1], status=("Succeeded", "Failed", "Skipped"))
            actions[name] = action
        prev = names[-1]
    step_names = [n for n in actions if n != "Results"]
    actions["Results"] = after({"type": "Compose", "inputs": {
        n: {"status": f"@{{actions('{n}')?['status']}}",
            "body": f"@actions('{n}')?['outputs']?['body']"} for n in step_names}},
        prev, status=("Succeeded", "Failed", "Skipped"))
    return clientdata(manual_trigger([]), actions, {s.SP_KEY: s.FLOW_REFS[s.SP_KEY]})


def main():
    from pipeline.deploy import ensure_flow, ensure_solution
    from pipeline.flowapi import az_token, flow_ids
    cd = build(command_ops(sys.argv[1:] or ["readback"]))
    errors = validate(cd)
    if errors:
        sys.exit("STOP: setup flow failed validation:\n  " + "\n  ".join(errors))
    tok = az_token(s.ADMIN)
    ensure_solution(tok)
    wid = ensure_flow(tok, SETUP_NAME, cd)
    print(f"{SETUP_NAME}: workflowid={wid} flow={flow_ids().get(SETUP_NAME, '?')}")


if __name__ == "__main__":
    main()
