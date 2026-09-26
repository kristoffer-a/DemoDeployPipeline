# Deploy Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One click on flow C1 deploys a solution from DEV to a target environment. Export and archive always run. Import (C2) and post-import (C3) run as child flows, each switched on or off per solution and target in SharePoint config.

**Architecture:** A Python builder (`pipeline/`) generates Logic Apps workflow definitions and deploys them as solution-aware cloud flows into ADMIN through the Dataverse Web API. This is the same method the spike proved in `spike/build_spike.py`. The flows read config from three ALM-Admin SharePoint lists and act on DEV and TEST through the Dataverse connector's selected-environment actions. Pure definition builders are unit-tested with pytest. Live behaviour is tested by running C1 and reading TEST back.

**Tech Stack:** Python 3.12 (stdlib only), pytest, az CLI tokens, Dataverse Web API v9.2, Power Automate (Logic Apps schema 2016-06-01), SharePoint REST (browser pane, signed in as kriall076), FlowAgent MCP `run_flow`.

**Spec:** `docs/superpowers/specs/2026-09-23-deploy-orchestrator-design.md`

## Global Constraints

- Tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac` only. Stop immediately if az or the browser shows another tenant.
- Account `kriall076@7xpydh.onmicrosoft.com` for this session. This is the user's explicit exception to the bosso-only rule.
- ADMIN env `f2280ea5-6793-e664-8f21-ea3ba6a4cb5c`, `https://adminorg774eae27.crm17.dynamics.com`.
- DEV `https://devorgf20ef6ea.crm17.dynamics.com`. TEST `https://testorg5fd244de.crm17.dynamics.com`.
- ALM-Admin site `https://7xpydh.sharepoint.com/sites/ALM-Admin`. `ALMConfig` list ID `049eba5a-700e-44db-9d2b-4e95c3af51b6`.
- TEST SharePoint connection `shared-sharepointonl-0f567e53`. ADMIN connections: Dataverse `shared-commondataser-88f9738e`, SharePoint `shared-sharepointonl-a0f00819`.
- Archive name: `Solutions/<Solution>/<Solution>_managed_<yyyyMMdd-HHmmss>.zip`. Log name: `DeploymentLogs/<Solution>_<Target>_<yyyyMMdd-HHmmss>.json`.
- No object key in a flow definition may start with `@`. The engine parses it as an expression.
- **Commit only when the user says so.** Each task ends with a checkpoint, not an automatic commit.
- Never delete flows, lists, columns or rows without the user's yes. Reversible edits that the tests need are allowed if the task restores them.
- Do not change the spike (`spike/`) or its flows. Cleanup is Task 8, with user approval.

---

## File Structure

| File | Responsibility |
|---|---|
| `pipeline/__init__.py` | package marker |
| `pipeline/settings.py` | every tenant, environment, list and connection constant, in one place |
| `pipeline/defs.py` | generic definition building blocks plus `validate()` |
| `pipeline/flows.py` | C1, C2 and C3 definitions, from `defs` |
| `pipeline/deploy.py` | Dataverse Web API: solution, connection references, flows. Prints Power Automate flow IDs. |
| `pipeline/flowapi.py` | reads run action outputs (the log entry) through the Flow API |
| `pipeline/verify_target.py` | prints Demo's state in TEST (solution, variables, bindings, flows) |
| `pipeline/tests/test_defs.py` | unit tests for `defs` |
| `pipeline/tests/test_flows.py` | unit tests for the three flow definitions |
| `pipeline/definitions/*.json` | generated definitions, for review (written by `deploy.py`) |
| `docs/alm/deploy-orchestrator-runbook.md` | how to run, configure and test the pipeline |
| `docs/alm/c4-share-spike.md` | C4 spike result |

---

### Task 1: Pipeline package, settings and definition helpers

**Files:**
- Create: `pipeline/__init__.py`, `pipeline/settings.py`, `pipeline/defs.py`, `pipeline/tests/__init__.py`, `pipeline/tests/test_defs.py`

**Interfaces:**
- Produces:
  - `settings.*` constants (names below).
  - In `defs`:
    - `op(conn_key, api, operation, params) -> dict`
    - `after(action, *prev, status=("Succeeded",)) -> dict`
    - `seq(*groups: dict) -> dict`
    - `unbound(conn_key, org, action_name, item) -> dict`
    - `list_rows(conn_key, org, entity, select=None, filter_=None, expand=None, fetch=None) -> dict`
    - `sp_items(conn_key, table, filter_=None, top=None) -> dict`
    - `poll_block(conn_key, org, job_expr, prefix) -> dict`
    - `if_job_succeeded(prefix, on_success, on_fail) -> dict`
    - `terminate(message_expr) -> dict`
    - `fail_steps(name, message_expr) -> dict`
    - `respond(outputs: dict) -> dict`
    - `run_child(workflow_id, body) -> dict`
    - `manual_trigger(inputs) -> dict`
    - `clientdata(trigger, actions, refs) -> dict`
    - `fetch_in_solution(entity, pk, attrs, solution_expr, conditions=()) -> str`
    - `url_expr(obj_expr, field) -> str`
    - `validate(cd) -> list[str]`

- [ ] **Step 1: Write `pipeline/settings.py`**

```python
"""Constants for the ALM deploy pipeline. Everything tenant-specific lives here."""

TENANT = "1c5afb69-a82c-4c81-b2cc-743ce7f91dac"
ADMIN_ENV_ID = "f2280ea5-6793-e664-8f21-ea3ba6a4cb5c"
ADMIN = "https://adminorg774eae27.crm17.dynamics.com"
ADMIN_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Admin"

SOLUTION = "ALMPipeline"
PUBLISHER = "almspike"  # exists in ADMIN, prefix alm

DV_API = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
SP_API = "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"
DV_KEY = "shared_commondataserviceforapps"
SP_KEY = "shared_sharepointonline"

# ADMIN connections owned by kriall076.
DV_CONN = "shared-commondataser-88f9738e"
SP_CONN = "shared-sharepointonl-a0f00819"

CONN_REFS = {
    "alm_PipelineDataverse": ("ALM Pipeline Dataverse", DV_API, DV_CONN),
    "alm_PipelineSharePoint": ("ALM Pipeline SharePoint", SP_API, SP_CONN),
}
FLOW_REFS = {
    DV_KEY: ("alm_PipelineDataverse", DV_API),
    SP_KEY: ("alm_PipelineSharePoint", SP_API),
}

# ALM-Admin lists. ALMConnections and ALMVariables IDs are filled in by Task 2.
LIST_CONFIG = "049eba5a-700e-44db-9d2b-4e95c3af51b6"
LIST_CONNECTIONS = ""
LIST_VARIABLES = ""
LOG_FOLDER = "/DeploymentLogs"

# How the SharePoint connector returns Hyperlink columns from Get items.
# False: plain URL string. True: object with 'Url'. Confirmed by the first live run (Task 5).
URL_AS_OBJECT = False

C1_NAME = "ALM C1 - Deploy (parent)"
C2_NAME = "ALM C2 - Import (child)"
C3_NAME = "ALM C3 - Post-import (child)"
```

- [ ] **Step 2: Write the failing tests `pipeline/tests/test_defs.py`**

```python
from pipeline import defs


def test_seq_links_first_action_of_each_group_to_last_of_previous():
    out = defs.seq({"A": {"type": "Compose"}}, {"B": {"type": "Compose"}, "C": {"type": "Compose", "runAfter": {"B": ["Succeeded"]}}}, {"D": {"type": "Compose"}})
    assert "runAfter" not in out["A"]
    assert out["B"]["runAfter"] == {"A": ["Succeeded"]}
    assert out["C"]["runAfter"] == {"B": ["Succeeded"]}
    assert out["D"]["runAfter"] == {"C": ["Succeeded"]}


def test_fetch_in_solution_filters_on_solution_and_extra_conditions():
    xml = defs.fetch_in_solution("workflow", "workflowid", ["workflowid", "name"], "outputs('Solution')",
                                 [("category", "5"), ("statecode", "0")])
    assert '<entity name="workflow">' in xml
    assert 'to="workflowid"' in xml
    assert "value=\"@{outputs('Solution')}\"" in xml
    assert '<condition attribute="category" operator="eq" value="5"/>' in xml


def test_url_expr_plain_and_object(monkeypatch):
    monkeypatch.setattr(defs, "URL_AS_OBJECT", False)
    assert defs.url_expr("outputs('Config')", "DevPowerPlatformUrl") == "outputs('Config')?['DevPowerPlatformUrl']"
    monkeypatch.setattr(defs, "URL_AS_OBJECT", True)
    assert defs.url_expr("outputs('Config')", "DevPowerPlatformUrl") == "outputs('Config')?['DevPowerPlatformUrl']?['Url']"


def test_respond_schema_matches_body():
    r = defs.respond({"status": "Succeeded", "message": "@{'x'}"})
    assert r["kind"] == "PowerApp"
    assert set(r["inputs"]["body"]) == set(r["inputs"]["schema"]["properties"]) == {"status", "message"}


def test_fail_steps_sets_message_then_fails():
    steps = defs.fail_steps("Fail_x", "@concat('a', 'b')")
    assert list(steps) == ["Set_Fail_x", "Fail_x"]
    assert steps["Set_Fail_x"]["inputs"] == {"name": "FailMessage", "value": "@concat('a', 'b')"}
    assert steps["Fail_x"]["runAfter"] == {"Set_Fail_x": ["Succeeded"]}


def _cd(actions):
    return defs.clientdata(defs.manual_trigger([]), actions, {})


def test_validate_rejects_at_keys():
    errors = defs.validate(_cd({"A": {"type": "Compose", "inputs": {"@odata.type": "x"}}}))
    assert any("@odata.type" in e for e in errors)


def test_validate_rejects_unknown_run_after_and_references():
    errors = defs.validate(_cd({
        "A": {"type": "Compose", "inputs": "@body('Nope')", "runAfter": {"Missing": ["Succeeded"]}},
    }))
    assert any("Missing" in e for e in errors)
    assert any("Nope" in e for e in errors)


def test_validate_accepts_nested_scopes():
    cd = _cd({
        "S": {"type": "Scope", "actions": {"A": {"type": "Compose", "inputs": 1}}},
        "B": after_ok({"type": "Compose", "inputs": "@outputs('A')"}, "S"),
    })
    assert defs.validate(cd) == []


def after_ok(action, prev):
    return defs.after(action, prev)
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `cd /Users/kristoffer/AI-Developer/Work/ALM-af/DemoDeployPipeline && python3 -m pytest pipeline/tests/test_defs.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline'` or `cannot import name 'defs'`.

- [ ] **Step 4: Write `pipeline/__init__.py` and `pipeline/tests/__init__.py`** (both empty files)

- [ ] **Step 5: Write `pipeline/defs.py`**

```python
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
    params.update({f"item/{k}": v for k, v in item.items()})
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
    """Built-in 'Run a Child Flow'. workflow_id is the child's Dataverse workflowid."""
    return {"type": "Workflow", "inputs": {"host": {"workflowReferenceName": workflow_id}, "body": body}}


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
    """FetchXML for rows of `entity` that are components of the solution named by solution_expr."""
    attr_xml = "".join(f'<attribute name="{a}"/>' for a in attrs)
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

_REF = re.compile(r"\b(?:body|outputs|actions|items)\('([^']+)'\)")
_NESTED = ("actions",)


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
```

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `python3 -m pytest pipeline/tests/test_defs.py -q`
Expected: `8 passed`

- [ ] **Step 7: Checkpoint.** Show the user `git status --short pipeline/`. Commit only if they say so: `git add pipeline && git commit -m "feat(pipeline): definition helpers and validator"`.

---

### Task 2: Provision the SharePoint config (ALM-Admin)

Creates the new `ALMConfig` columns, the `ALMConnections` and `ALMVariables` lists, and the Demo → TEST rows. Uses SharePoint REST from the browser pane, signed in as kriall076. az tokens can't reach SharePoint here (seen 2026-09-23).

**Files:**
- Modify: `pipeline/settings.py` (`LIST_CONNECTIONS`, `LIST_VARIABLES`)
- Test: `pipeline/tests/test_defs.py` (add a settings test)

**Interfaces:**
- Produces: list IDs in `settings`. The column internal names below are used by Tasks 3–4 exactly as spelled:
  - `ALMConfig`: `SolutionName`, `DevPowerPlatformUrl`, `TargetEnvironment`, `TargetPowerPlatformUrl`, `TargetSharePointUrl`, `RunImport`, `RunPostImport`, `RunShare`, `AppShareGroupId`
  - `ALMConnections`: `Environment`, `ConnectionReference`, `ConnectionId`, `ConnectorId`
  - `ALMVariables`: `SolutionName`, `Environment`, `SchemaName`, `Value`
- Also produces `window.alm` in the browser page, reused by Task 6.

- [ ] **Step 1: Write the failing settings test** (append to `pipeline/tests/test_defs.py`)

```python
import re as _re

from pipeline import settings

GUID = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_config_list_ids_are_set():
    for value in (settings.LIST_CONFIG, settings.LIST_CONNECTIONS, settings.LIST_VARIABLES):
        assert GUID.match(value), value
```

Run: `python3 -m pytest pipeline/tests/test_defs.py::test_config_list_ids_are_set -q`
Expected: FAIL. `LIST_CONNECTIONS` is `''`.

- [ ] **Step 2: Open ALM-Admin in the browser pane and check the identity**

Navigate the browser pane to `https://7xpydh.sharepoint.com/sites/ALM-Admin`. Then run with `javascript_tool`:

```js
const me = await (await fetch('/sites/ALM-Admin/_api/web/currentuser?$select=LoginName', {headers:{Accept:'application/json;odata=nometadata'}})).json();
me.LoginName
```

Expected: a string that ends with `kriall076@7xpydh.onmicrosoft.com`. **Any other account: stop and tell the user.**

- [ ] **Step 3: Define the helper `window.alm`** (`javascript_tool`, same page)

```js
window.alm = (() => {
  const site = '/sites/ALM-Admin';
  const J = 'application/json;odata=nometadata';
  async function digest() {
    const r = await fetch(site + '/_api/contextinfo', {method: 'POST', headers: {Accept: J}});
    return (await r.json()).FormDigestValue;
  }
  async function call(method, path, body, extra = {}) {
    const headers = {Accept: J, 'Content-Type': 'application/json;odata=verbose', 'X-RequestDigest': await digest(), ...extra};
    const r = await fetch(site + '/_api/' + path, {method, headers, body: body ? JSON.stringify(body) : undefined});
    const text = await r.text();
    if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}: ${text.slice(0, 400)}`);
    return text ? JSON.parse(text) : {};
  }
  async function ensureList(title) {
    try { return (await call('GET', `web/lists/getbytitle('${title}')?$select=Id`)).Id; }
    catch { return (await call('POST', 'web/lists', {__metadata: {type: 'SP.List'}, BaseTemplate: 100, Title: title})).Id; }
  }
  async function ensureField(title, schemaXml) {
    const name = /Name='([^']+)'/.exec(schemaXml)[1];
    try { await call('GET', `web/lists/getbytitle('${title}')/fields/getbyinternalnameortitle('${name}')?$select=Id`); return `${name}: exists`; }
    catch { await call('POST', `web/lists/getbytitle('${title}')/fields/CreateFieldAsXml`,
      {parameters: {__metadata: {type: 'SP.XmlSchemaFieldCreationInformation'}, SchemaXml: schemaXml, Options: 25}});
      return `${name}: created`; }
  }
  async function itemType(title) {
    return (await call('GET', `web/lists/getbytitle('${title}')?$select=ListItemEntityTypeFullName`)).ListItemEntityTypeFullName;
  }
  async function items(title, filter) {
    return (await call('GET', `web/lists/getbytitle('${title}')/items?$filter=${encodeURIComponent(filter)}`)).value;
  }
  // Upsert by OData filter: update the first match, else create.
  async function upsert(title, filter, fields) {
    const type = await itemType(title);
    const found = await items(title, filter);
    const body = {__metadata: {type}, ...fields};
    if (found.length) {
      await call('POST', `web/lists/getbytitle('${title}')/items(${found[0].Id})`, body, {'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*'});
      return `updated ${title} #${found[0].Id}`;
    }
    const created = await call('POST', `web/lists/getbytitle('${title}')/items`, body);
    return `created ${title} #${created.Id}`;
  }
  const url = (u) => ({__metadata: {type: 'SP.FieldUrlValue'}, Url: u, Description: u});
  return {call, ensureList, ensureField, items, upsert, url};
})();
'ok'
```

Expected: `"ok"`

- [ ] **Step 4: Add the `ALMConfig` columns and create the two lists** (`javascript_tool`)

```js
const out = [];
const choiceEnv = (n) => `<Field Type='Choice' Name='${n}' StaticName='${n}' DisplayName='${n}' Required='TRUE'><CHOICES><CHOICE>TEST</CHOICE><CHOICE>PROD</CHOICE></CHOICES></Field>`;
const text = (n, req = 'TRUE') => `<Field Type='Text' Name='${n}' StaticName='${n}' DisplayName='${n}' Required='${req}'/>`;
const yesno = (n) => `<Field Type='Boolean' Name='${n}' StaticName='${n}' DisplayName='${n}'><Default>0</Default></Field>`;
const link = (n) => `<Field Type='URL' Name='${n}' StaticName='${n}' DisplayName='${n}' Format='Hyperlink' Required='TRUE'/>`;

for (const x of [choiceEnv('TargetEnvironment'), link('TargetPowerPlatformUrl'), link('TargetSharePointUrl'),
                 yesno('RunImport'), yesno('RunPostImport'), yesno('RunShare'), text('AppShareGroupId', 'FALSE')])
  out.push(await alm.ensureField('ALMConfig', x));

const connections = await alm.ensureList('ALMConnections');
for (const x of [choiceEnv('Environment'), text('ConnectionReference'), text('ConnectionId'), text('ConnectorId')])
  out.push(await alm.ensureField('ALMConnections', x));

const variables = await alm.ensureList('ALMVariables');
for (const x of [text('SolutionName'), choiceEnv('Environment'), text('SchemaName'), text('Value')])
  out.push(await alm.ensureField('ALMVariables', x));

({connections, variables, out})
```

Expected: two GUIDs, and 15 lines ending in `created` or `exists`. Running it again gives only `exists`.

- [ ] **Step 5: Write the Demo → TEST rows** (`javascript_tool`)

```js
const r = [];
r.push(await alm.upsert('ALMConfig', "SolutionName eq 'Demo'", {
  TargetEnvironment: 'TEST',
  TargetPowerPlatformUrl: alm.url('https://testorg5fd244de.crm17.dynamics.com'),
  TargetSharePointUrl: alm.url('https://7xpydh.sharepoint.com/sites/ALM-Test'),
  RunImport: true, RunPostImport: true, RunShare: false,
}));
r.push(await alm.upsert('ALMConnections', "Environment eq 'TEST' and ConnectionReference eq 'dev_SharePoint'", {
  Title: 'TEST dev_SharePoint', Environment: 'TEST', ConnectionReference: 'dev_SharePoint',
  ConnectionId: 'shared-sharepointonl-0f567e53',
  ConnectorId: '/providers/Microsoft.PowerApps/apis/shared_sharepointonline',
}));
r.push(await alm.upsert('ALMVariables', "SolutionName eq 'Demo' and Environment eq 'TEST' and SchemaName eq 'dev_SharePointSite'", {
  Title: 'Demo TEST dev_SharePointSite', SolutionName: 'Demo', Environment: 'TEST',
  SchemaName: 'dev_SharePointSite', Value: 'https://7xpydh.sharepoint.com/sites/ALM-Test',
}));
r.push(await alm.upsert('ALMVariables', "SolutionName eq 'Demo' and Environment eq 'TEST' and SchemaName eq 'dev_ProductsList'", {
  Title: 'Demo TEST dev_ProductsList', SolutionName: 'Demo', Environment: 'TEST',
  SchemaName: 'dev_ProductsList', Value: '00000000-0000-0000-0000-000000000000',
}));
r
```

Expected: 4 lines, `updated ALMConfig #1` and three `created …` (or `updated …` on a re-run).
If the user has created the TEST `Products` list by now, use its ID as the `dev_ProductsList` value instead of the placeholder.

- [ ] **Step 6: Read back** (`javascript_tool`)

```js
({
  config: await alm.items('ALMConfig', "SolutionName eq 'Demo'"),
  connections: await alm.items('ALMConnections', "Environment eq 'TEST'"),
  variables: await alm.items('ALMVariables', "SolutionName eq 'Demo'"),
})
```

Expected:
- One config row with `TargetEnvironment: "TEST"`, `RunImport: true`, `RunPostImport: true`, `RunShare: false`, and both Target URLs set.
- One connection row.
- Two variable rows.

- [ ] **Step 7: Put the two list IDs from Step 4 into `pipeline/settings.py`**

```python
LIST_CONNECTIONS = "<Id returned for ALMConnections in Step 4>"
LIST_VARIABLES = "<Id returned for ALMVariables in Step 4>"
```

Use the literal GUIDs from the Step 4 output. Don't commit the angle-bracket text.

- [ ] **Step 8: Run the tests**

Run: `python3 -m pytest pipeline/tests -q`
Expected: `9 passed`

- [ ] **Step 9: Checkpoint.** Tell the user what was created in SharePoint, with the readback. Commit only if they say so.

---

### Task 3: Child flow definitions C2 (import) and C3 (post-import)

**Files:**
- Create: `pipeline/flows.py`, `pipeline/tests/test_flows.py`

**Interfaces:**
- Consumes: everything from `defs`, and `settings.LIST_*`, `FLOW_REFS`, `DV_KEY`, `SP_KEY`, `ADMIN_SITE`, `SP_API`, `C*_NAME`.
- Produces:
  - `config_actions(sol_expr, target_expr, on_missing) -> dict`: actions `Get_config`, `Config`, `Check_config`, `Dev_url`, `Target_url`, `Get_connection_map`, `Get_variable_map`, `Dev_refs`, `Dev_ref_names`, `Dev_vars`, `Dev_var_names`.
  - `c2() -> dict`
  - `c3() -> dict`
- Child contract:
  - C2 inputs: `text` = ZIP path, `text_1` = solution, `text_2` = target.
  - C3 inputs: `text` = solution, `text_1` = target.
  - Both reply with `status` and `message`. C2 also returns `importjobkey`.

- [ ] **Step 1: Write the failing tests `pipeline/tests/test_flows.py`**

```python
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
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python3 -m pytest pipeline/tests/test_flows.py -q`
Expected: FAIL with `ImportError: cannot import name 'flows'`.

- [ ] **Step 3: Write `pipeline/flows.py` (config block + C2 + C3)**

```python
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m pytest pipeline/tests -q`
Expected: `15 passed`. If `test_children_validate_clean` fails, read each error line (unknown reference, non-sibling runAfter, `@` key) and fix the named action.

- [ ] **Step 5: Checkpoint.** Show the user the diff summary. Commit only if they say so.

---

### Task 4: Parent flow definition C1 (switches, pre-checks, export, log)

**Files:**
- Modify: `pipeline/flows.py` (add `export_steps`, `log_step`, `c1`, `FLOWS`)
- Modify: `pipeline/tests/test_flows.py`

**Interfaces:**
- Consumes: `config_actions`, `c2`, `c3` from Task 3, and `fail_steps`, `run_child` from Task 1.
- Produces:
  - `c1(ids: dict[str, str]) -> dict`, where `ids` maps a flow name to its Dataverse workflowid.
  - `FLOWS: list[tuple[str, callable]]` in deploy order: C2, C3, C1. Each callable takes `ids`.
  - C1 inputs: `text` = solution (default `Demo`), `text_1` = target (default `TEST`).

- [ ] **Step 1: Add the failing tests** (append to `pipeline/tests/test_flows.py`)

```python
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
```

- [ ] **Step 2: Run them and confirm they fail**

Run: `python3 -m pytest pipeline/tests/test_flows.py -q`
Expected: FAIL with `AttributeError: module 'pipeline.flows' has no attribute 'c1'`.

- [ ] **Step 3: Add C1 to `pipeline/flows.py`**

Add `fail_steps, run_child` to the `from pipeline.defs import (...)` line. Then append:

```python
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


def log_step(step, action):
    """One log line. actions('X') works for skipped actions; body('X') would throw."""
    a = f"actions('{action}')"
    return {
        "step": step,
        "status": f"@{{{a}?['status']}}",
        "seconds": f"@{{div(sub(ticks(coalesce({a}?['endTime'], utcNow())), "
                   f"ticks(coalesce({a}?['startTime'], utcNow()))), 10000000)}}",
        "message": f"@{{coalesce({a}?['outputs']?['body']?['message'], {a}?['error']?['message'], '')}}",
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
                          "actions": {"Run_C2_import": run_child(ids.get(s.C2_NAME, PLACEHOLDER_ID), {
                              "text": "@body('Archive_ZIP')?['Path']", "text_1": f"@{SOL}", "text_2": f"@{TARGET}"})}}},
        {"If_RunPostImport": {"type": "If",
                              "expression": {"equals": ["@outputs('Config')?['RunPostImport']", True]},
                              "actions": {"Run_C3_post_import": run_child(ids.get(s.C3_NAME, PLACEHOLDER_ID), {
                                  "text": f"@{SOL}", "text_1": f"@{TARGET}"})}}},
    )
    message = ("@{if(empty(variables('FailMessage')), coalesce(actions('Run_C2_import')?['error']?['message'], "
               "actions('Run_C3_post_import')?['error']?['message'], ''), variables('FailMessage'))}")
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
                      log_step("Import", "Run_C2_import"), log_step("PostImport", "Run_C3_post_import")],
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
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python3 -m pytest pipeline/tests -q`
Expected: `21 passed`

- [ ] **Step 5: Checkpoint.** Show the user the diff summary. Commit only if they say so.

---

### Task 5: Deploy, run and verify (test case 1: all switches on)

**Files:**
- Create: `pipeline/deploy.py`, `pipeline/flowapi.py`, `pipeline/verify_target.py`

**Interfaces:**
- Consumes: `flows.FLOWS`, `defs.validate`, `settings.*`.
- Produces:
  - CLI `python3 -m pipeline.deploy [--dry-run]`. Prints `<name>: workflowid=<guid> flow=<power automate id>`.
  - CLI `python3 -m pipeline.flowapi <flow> <run> <action>`. Prints that action's outputs as JSON.
  - CLI `python3 -m pipeline.verify_target`. Prints Demo's TEST state as JSON.
  - Shared helper `flowapi.az_token(resource) -> str`, with the tenant guard.

- [ ] **Step 1: Write `pipeline/flowapi.py`**

```python
"""Tokens (tenant-guarded) and Flow API run-output reads."""
import json
import subprocess
import sys
import urllib.request

from pipeline.settings import ADMIN_ENV_ID, TENANT

FLOW_API = f"https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/{ADMIN_ENV_ID}"


def az_token(resource):
    acct = json.loads(subprocess.check_output(["az", "account", "show", "-o", "json"]))
    if acct["tenantId"] != TENANT:
        sys.exit(f"STOP: az tenant is {acct['tenantId']}, expected {TENANT}")
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", resource,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()


def get_json(url, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
        return json.loads(r.read())


def flow_ids():
    """Power Automate flow id by display name, for flows in ADMIN."""
    tok = az_token("https://service.flow.microsoft.com")
    rows = get_json(f"{FLOW_API}/flows?api-version=2016-11-01", tok)["value"]
    return {f["properties"]["displayName"]: f["name"] for f in rows}


def action_outputs(flow, run, action):
    tok = az_token("https://service.flow.microsoft.com")
    meta = get_json(f"{FLOW_API}/flows/{flow}/runs/{run}/actions/{action}?api-version=2016-11-01", tok)
    link = meta["properties"].get("outputsLink")
    return get_json(link["uri"]) if link else {"status": meta["properties"].get("status")}


if __name__ == "__main__":
    print(json.dumps(action_outputs(*sys.argv[1:4]), indent=1))
```

- [ ] **Step 2: Write `pipeline/deploy.py`**

```python
"""Deploy the pipeline flows into ADMIN as solution-aware cloud flows.

Usage: python3 -m pipeline.deploy [--dry-run]
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from pipeline import settings as s
from pipeline.defs import validate
from pipeline.flowapi import az_token, flow_ids
from pipeline.flows import FLOWS

OUT = Path(__file__).parent / "definitions"


def api(tok, method, path, body=None, solution=None):
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json", "OData-Version": "4.0",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    if solution:
        headers["MSCRM.SolutionUniqueName"] = solution
    path = urllib.parse.quote(path, safe="/?&=$(),'@")
    req = urllib.request.Request(f"{s.ADMIN}/api/data/v9.2/{path}", method=method, headers=headers,
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


def ensure_solution(tok):
    pub = first(tok, f"publishers?$filter=uniquename eq '{s.PUBLISHER}'&$select=publisherid")
    if not pub:
        sys.exit(f"STOP: publisher {s.PUBLISHER} not found in ADMIN")
    if not first(tok, f"solutions?$filter=uniquename eq '{s.SOLUTION}'&$select=solutionid"):
        api(tok, "POST", "solutions", {"uniquename": s.SOLUTION, "friendlyname": "ALM Pipeline", "version": "1.0.0.0",
                                       "publisherid@odata.bind": f"/publishers({pub['publisherid']})"})
        print(f"created solution {s.SOLUTION}")
    for logical, (display, connector, conn) in s.CONN_REFS.items():
        if not first(tok, f"connectionreferences?$filter=connectionreferencelogicalname eq '{logical}'"
                          "&$select=connectionreferenceid"):
            api(tok, "POST", "connectionreferences", {
                "connectionreferencelogicalname": logical, "connectionreferencedisplayname": display,
                "connectorid": connector, "connectionid": conn}, solution=s.SOLUTION)
            print(f"created connection reference {logical} -> {conn}")


def ensure_flow(tok, name, cd):
    existing = first(tok, f"workflows?$filter=name eq '{name}' and category eq 5&$select=workflowid,statecode")
    payload = {"clientdata": json.dumps(cd)}
    if existing:
        wid = existing["workflowid"]
        if existing["statecode"] == 1:  # turning off re-validates the stored definition
            api(tok, "PATCH", f"workflows({wid})", {"statecode": 0, "statuscode": 1})
        api(tok, "PATCH", f"workflows({wid})", payload)
    else:
        payload.update({"name": name, "category": 5, "type": 1, "primaryentity": "none"})
        wid = api(tok, "POST", "workflows", payload, solution=s.SOLUTION)["workflowid"]
    api(tok, "PATCH", f"workflows({wid})", {"statecode": 1, "statuscode": 2})
    return wid


def build(ids):
    OUT.mkdir(exist_ok=True)
    out = {}
    for name, make in FLOWS:
        cd = make(ids)
        errors = validate(cd)
        if errors:
            sys.exit(f"STOP: {name} failed validation:\n  " + "\n  ".join(errors))
        (OUT / (name.split(" - ")[0].replace(" ", "_") + ".json")).write_text(json.dumps(cd, indent=2))
        out[name] = cd
    return out


def main():
    build({})
    print(f"wrote {len(FLOWS)} definitions to {OUT}")
    if "--dry-run" in sys.argv:
        return
    tok = az_token(s.ADMIN)
    ensure_solution(tok)
    ids = {}
    for name, make in FLOWS:  # children first: C1 needs their workflowids
        ids[name] = ensure_flow(tok, name, make(ids))
    build(ids)
    pa = flow_ids()
    for name, wid in ids.items():
        print(f"{name}: workflowid={wid} flow={pa.get(name, '?')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `pipeline/verify_target.py`**

```python
"""Print the Demo solution's state in TEST: solution, variable values, bindings, flow states."""
import json
import urllib.parse

from pipeline.flowapi import az_token, get_json

TEST = "https://testorg5fd244de.crm17.dynamics.com"


def q(tok, path):
    return get_json(f"{TEST}/api/data/v9.2/{urllib.parse.quote(path, safe='/?&=$(),')}", tok)["value"]


def main():
    tok = az_token(TEST)
    print(json.dumps({
        "solution": q(tok, "solutions?$filter=uniquename eq 'Demo'&$select=version,ismanaged,modifiedon"),
        "lastImport": q(tok, "importjobs?$select=solutionname,completedon,progress&$orderby=createdon desc&$top=1"),
        "variables": [{"schemaname": v["EnvironmentVariableDefinitionId"]["schemaname"], "value": v["value"]}
                      for v in q(tok, "environmentvariablevalues?$select=value"
                                      "&$expand=EnvironmentVariableDefinitionId($select=schemaname)")
                      if v["EnvironmentVariableDefinitionId"]["schemaname"].startswith("dev_")],
        "bindings": q(tok, "connectionreferences?$filter=startswith(connectionreferencelogicalname,'dev_')"
                           "&$select=connectionreferencelogicalname,connectionid"),
        "flows": q(tok, "workflows?$filter=category eq 5&$select=name,statecode"),
    }, indent=1))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Dry run**

Run: `python3 -m pipeline.deploy --dry-run`
Expected: `wrote 3 definitions to …/pipeline/definitions`. No `STOP: … failed validation`.

- [ ] **Step 5: Deploy**

Run: `python3 -m pipeline.deploy`
Expected:
- `created solution ALMPipeline`
- two `created connection reference …` lines
- three `ALM C… : workflowid=<guid> flow=<guid>` lines, with no `flow=?`

Note C1's `flow=` id for the next steps.
A `-> 400` on turn-on means the engine rejected the definition. Fix it with the error text, add a unit test for that case, and redeploy.

- [ ] **Step 6: Run test case 1 (all switches on)**

Call MCP `run_flow` with `env=f2280ea5-6793-e664-8f21-ea3ba6a4cb5c`, `flow=<C1 flow id>`, `wait=true`, `timeout=600`.
Expected: `status: Succeeded`, and `Run_C2_import` and `Run_C3_post_import` both `Succeeded`.

**If it fails at `Dev_refs`** with an invalid `organization`: the Hyperlink column is an object, not a string.
1. Set `URL_AS_OBJECT = True` in `settings.py`.
2. Run `python3 -m pytest pipeline/tests -q`, which must pass.
3. Redeploy and re-run.

If it fails anywhere else, use `diagnose_run` on the run, fix the definition, add a unit test for the fix, and redeploy.

- [ ] **Step 7: Read the log entry**

Run: `python3 -m pipeline.flowapi <C1 flow id> <run id> Log_entry`
Expected:
- `status: "Succeeded"`
- `zipPath` like `/Solutions/Demo/Demo_managed_2026….zip`
- four steps: Prechecks, Export, Import and PostImport all `Succeeded`

PostImport's message should read `Bindings OK; variables set: 2; flows turned on: <n>`.

- [ ] **Step 8: Verify TEST**

Run: `python3 -m pipeline.verify_target`
Expected:
- solution `ismanaged: true`, `version: "1.0.0.0"`, `modifiedon` = this run
- `dev_SharePointSite` = `https://7xpydh.sharepoint.com/sites/ALM-Test`
- `dev_ProductsList` = the `ALMVariables` value
- binding `dev_SharePoint` → `shared-sharepointonl-0f567e53`
- Demo's flow `statecode: 1`

- [ ] **Step 9: Checkpoint.** Show the user the run result, log entry and TEST readback. Commit only if they say so.

---

### Task 6: Acceptance tests 2–4

Uses `window.alm` from Task 2 (re-run Task 2 Step 3 if the page was reloaded). Every change is restored at the end of its test.

- [ ] **Step 1: Test 2 — `RunImport` off.** Run `await alm.upsert('ALMConfig', "SolutionName eq 'Demo'", {RunImport: false, RunPostImport: false})`, then run C1 (`run_flow`, wait).
Expected:
- run `Succeeded`
- `Log_entry`: Export `Succeeded`, Import `Skipped`, PostImport `Skipped`
- `switches.RunImport` false
- a new ZIP in `zipPath`
- `verify_target` → `lastImport.completedon` unchanged from Task 5

- [ ] **Step 2: Test 3 — missing mapping row.** Hide the TEST row without deleting it: `await alm.upsert('ALMConnections', "Environment eq 'TEST' and ConnectionReference eq 'dev_SharePoint'", {Environment: 'PROD'})`. Then run C1.
Expected:
- run `Failed`
- `Log_entry.message` = `Missing mapping rows for TEST: dev_SharePoint`
- Export `Skipped`, and no new ZIP in `Solutions/Demo` (`zipPath` empty)

Restore with `await alm.upsert('ALMConnections', "ConnectionReference eq 'dev_SharePoint' and Environment eq 'PROD'", {Environment: 'TEST'})`.

- [ ] **Step 3: Test 4 — variable change without import.**
1. Set `{RunImport: false, RunPostImport: true}` on the config row.
2. Change the `dev_ProductsList` row in `ALMVariables`:
   - If the user has made the TEST Products list, use its real ID.
   - Otherwise use `11111111-1111-1111-1111-111111111111`.
3. Run C1.

Expected:
- run `Succeeded`, with Import `Skipped` and PostImport `Succeeded`
- `verify_target` shows `dev_ProductsList` = the new value
- `lastImport.completedon` unchanged

- [ ] **Step 4: Restore the config.**
1. Set `{RunImport: true, RunPostImport: true}`.
2. Set `dev_ProductsList` back to the real list ID, or to `00000000-0000-0000-0000-000000000000` if there's no list yet.
3. Run C1 once more.

Expected: test case 1 results again.

- [ ] **Step 5: Checkpoint.** Report the 4 test results as a table to the user.

---

### Task 7: C4 share-app spike (research only, no pipeline change)

**Files:**
- Create: `docs/alm/c4-share-spike.md`

- [ ] **Step 1: Find the action.** MCP `search_operations` with `env=ADMIN`, first with `query="app role assignment"`, then with `query="Edit App Role Assignment"`. Expected: an operation on the Power Apps for Admins connector (`shared_powerappsforadmins`). If there's none, record "not found" and go to Step 4.

- [ ] **Step 2: Read its parameters.** MCP `get_operation_details` with that connector and operation ID. Record the required parameters: environment, app name, principal type/ID, role.

- [ ] **Step 3: Check the connection.** MCP `list_connections` in ADMIN for `shared_powerappsforadmins`. If there's no connection, **don't create one**. Record that the user must create it, and that kriall076 needs the Power Platform admin role.

- [ ] **Step 4: Write `docs/alm/c4-share-spike.md`** with:
  - the operation found (or not)
  - its parameters
  - the connection state
  - a go/no-go recommendation for building C4 in a later plan

- [ ] **Step 5: Checkpoint.** Give the user the go/no-go in one line.

---

### Task 8: Runbook and cleanup requests

**Files:**
- Create: `docs/alm/deploy-orchestrator-runbook.md`

- [ ] **Step 1: Write the runbook.** Sections, each with the literal commands from Tasks 2–6:
  1. Prerequisites: az tenant, kriall076 exception, connections.
  2. Configure a new solution/target: the three lists and their columns.
  3. Deploy flows: `python3 -m pipeline.deploy`.
  4. Run a deployment: C1 in the portal or `run_flow`; read the log with `pipeline.flowapi`.
  5. Verify TEST: `pipeline.verify_target`.
  6. Known limits: the 120 s child reply; the service account still to replace kriall076.

- [ ] **Step 2: Run the full unit suite.**

Run: `python3 -m pytest pipeline/tests -q`
Expected: `21 passed`

- [ ] **Step 3: Ask the user, one item at a time, and act only on a yes:**
  1. Delete spike flows A1, A2, B, C1, C2 from ADMIN, and the `ALMSpike` solution.
  2. Remove the old `Test*` columns from `ALMConfig`.
  3. Commit `pipeline/`, `spike/`, the spec, this plan and the runbook.
