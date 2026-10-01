"""Generate the ALM Qualification SharePoint bootstrap helper flow source.

This module only builds and writes flow JSON. It never deploys or runs the flow.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pipeline import settings as s
from pipeline import target as target_config
from pipeline.defs import after, clientdata, fail_steps, manual_trigger, op, validate

TEST_ENV_ID = "8fcc484b-d74e-e479-84da-ad5a78d6d55b"
TEST_ORG = "https://testorg5fd244de.crm17.dynamics.com"
TEST_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Test"
TEST_DV_CONN = "shared-commondataser-3dbb75d1"
TEST_SP_CONN = "shared-sharepointonl-0f567e53"
LIST_FIELDS = {
    "ALMQConfig": {
        "SolutionName": ("Text", True), "TargetEnvironment": ("Choice", True),
        "DevPowerPlatformUrl": ("URL", True), "TargetPowerPlatformUrl": ("URL", True),
        "TargetSharePointUrl": ("URL", False), "RunImport": ("Boolean", False),
        "RunPostImport": ("Boolean", False), "RunShare": ("Boolean", False),
        "AppShareGroupId": ("Text", False),
    },
    "ALMQConnections": {
        "Environment": ("Choice", True), "ConnectionReference": ("Text", True),
        "ConnectionId": ("Text", True), "ConnectorId": ("Text", True),
    },
    "ALMQVariables": {
        "SolutionName": ("Text", True), "Environment": ("Choice", True),
        "SchemaName": ("Text", True), "Value": ("Text", True),
    },
}
JSON_NOMETA = "application/json;odata=nometadata"


def _request(site_url, method, uri, body=None):
    params = {
        "dataset": site_url,
        "parameters/method": method,
        "parameters/uri": uri,
        "parameters/headers": {"Accept": JSON_NOMETA, "Content-Type": "application/json;odata=verbose"},
    }
    if body is not None:
        params["parameters/body"] = json.dumps(body)
    action = op(s.SP_KEY, s.SP_API, "HttpRequest", params)
    action["inputs"]["retryPolicy"] = {"type": "none"}
    return action


def _status(action):
    return f"actions('{action}')?['outputs']?['statusCode']"


def _field_uri(title, name):
    return (f"_api/web/lists/getbytitle('{title}')/fields?"
            f"$select=InternalName,TypeAsString&$filter=InternalName%20eq%20'{name}'&$top=2")


def _field_count(action):
    return f"length(body('{action}')?['value'])"


def _no_next_page(action):
    return (f"and(empty(body('{action}')?['odata.nextLink']), "
            f"empty(body('{action}')?['@odata.nextLink']))")


def _list_failure(label, get_action):
    return fail_steps(f"Fail_{label}",
                      f"@concat('SharePoint {label} request failed; HTTP ', string({_status(get_action)}))")


def list_schema(title, template=100):
    """SharePoint REST creation body for a basic list; list creation is never destructive."""
    if template not in (100, 101):
        raise ValueError('unsupported qualification list template')
    return {"__metadata": {"type": "SP.List"}, "BaseTemplate": template, "Title": title}


def field_xml(name, kind, required):
    req = "TRUE" if required else "FALSE"
    if kind == "Text":
        return f"<Field Type='Text' Name='{name}' StaticName='{name}' DisplayName='{name}' Required='{req}'/>"
    if kind == "URL":
        return (f"<Field Type='URL' Name='{name}' StaticName='{name}' DisplayName='{name}' "
                f"Format='Hyperlink' Required='{req}'/>")
    if kind == "Boolean":
        return (f"<Field Type='Boolean' Name='{name}' StaticName='{name}' DisplayName='{name}' "
                f"Required='{req}'><Default>0</Default></Field>")
    if kind == "Choice":
        return (f"<Field Type='Choice' Name='{name}' StaticName='{name}' DisplayName='{name}' Required='{req}'>"
                "<CHOICES><CHOICE>TEST</CHOICE><CHOICE>PROD</CHOICE></CHOICES></Field>")
    raise ValueError(f"unsupported SharePoint field kind: {kind}")


def ensure_list(title, site_url=TEST_SITE, template=100):
    """Read, create only after exact 404, then capture and verify the resulting list ID."""
    get_name, ensure_name = f"Get_list_{title}", f"Ensure_list_{title}"
    verify_name, check_name = f"Readback_list_{title}", f"Check_list_{title}"
    actions = {
        get_name: _request(site_url, "GET", f"_api/web/lists/getbytitle('{title}')?$select=Id,Title,EntityTypeName,BaseTemplate"),
        ensure_name: {
            "type": "If",
            "expression": {"equals": [f"@{_status(get_name)}", 404]},
            "actions": {f"Create_list_{title}": _request(site_url, "POST", "_api/web/lists", list_schema(title, template))},
            "else": {"actions": {
                f"Check_existing_list_{title}": {
                    "type": "If", "expression": {"equals": [f"@{_status(get_name)}", 200]},
                    "actions": {f"List_exists_{title}": {"type": "Compose", "inputs": True}},
                    "else": {"actions": _list_failure(title, get_name)},
                },
            }},
        },
        verify_name: _request(site_url, "GET", f"_api/web/lists/getbytitle('{title}')?$select=Id,Title,EntityTypeName,BaseTemplate"),
        check_name: {
            "type": "If", "expression": {"and": [
                {"equals": [f"@{_status(verify_name)}", 200]},
                {"equals": [f"@body('{verify_name}')?['BaseTemplate']", template]},
            ]},
            "actions": {f"List_verified_{title}": {"type": "Compose", "inputs": True}},
            "else": {"actions": _list_failure(f"{title} readback", verify_name)},
        },
    }
    actions[ensure_name] = after(actions[ensure_name], get_name,
                                 status=("Succeeded", "Failed", "TimedOut"))
    actions[verify_name] = after(actions[verify_name], ensure_name,
                                 status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions[check_name] = after(actions[check_name], verify_name,
                                status=("Succeeded", "Failed", "TimedOut"))
    return actions


def ensure_field(title, name, kind, required, site_url=TEST_SITE):
    """Query fields collection; create only after HTTP 200 with an empty, complete result."""
    get_name = f"Get_field_{title}_{name}"
    ensure_name = f"Ensure_field_{title}_{name}"
    verify_name = f"Readback_field_{title}_{name}"
    check_name = f"Check_field_{title}_{name}"
    uri = _field_uri(title, name)
    fail = _list_failure(f"field {title}.{name}", get_name)
    create = _request(site_url, "POST", f"_api/web/lists/getbytitle('{title}')/fields/CreateFieldAsXml", {
        "parameters": {"__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                      "SchemaXml": field_xml(name, kind, required), "Options": 25}})
    type_check = {
        "type": "If", "expression": {"equals": [
            f"@first(body('{get_name}')?['value'])?['TypeAsString']", kind]},
        "actions": {f"Field_type_ok_{title}_{name}": {"type": "Compose", "inputs": True}},
        "else": {"actions": fail_steps(
            f"Field_type_mismatch_{title}_{name}",
            f"@concat('Refusing field type mismatch for {title}.{name}; expected {kind}, got ', "
            f"string(first(body('{get_name}')?['value'])?['TypeAsString']))")},
    }
    actions = {
        get_name: _request(site_url, "GET", uri),
        ensure_name: {
            "type": "If", "expression": {"equals": [f"@{_status(get_name)}", 200]},
            "actions": {f"Field_results_{title}_{name}": {
                "type": "If", "expression": {"and": [
                    {"equals": [f"@{_field_count(get_name)}", 0]},
                    {"equals": [f"@{_no_next_page(get_name)}", True]},
                ]},
                "actions": {f"Create_field_{title}_{name}": create},
                "else": {"actions": {f"Check_one_field_{title}_{name}": {
                    "type": "If", "expression": {"and": [
                        {"equals": [f"@{_field_count(get_name)}", 1]},
                        {"equals": [f"@{_no_next_page(get_name)}", True]},
                    ]},
                    "actions": {f"Check_existing_type_{title}_{name}": type_check},
                    "else": {"actions": fail_steps(
                        f"Field_results_ambiguous_{title}_{name}",
                        f"@concat('Field lookup for {title}.{name} was duplicated or paged; refusing to create')")},
                }}}},
            },
            "else": {"actions": fail},
        },
        verify_name: _request(site_url, "GET", uri),
        check_name: {
            "type": "If", "expression": {"equals": [f"@{_status(verify_name)}", 200]},
            "actions": {f"Check_one_readback_{title}_{name}": {
                "type": "If", "expression": {"and": [
                    {"equals": [f"@{_field_count(verify_name)}", 1]},
                    {"equals": [f"@{_no_next_page(verify_name)}", True]},
                ]},
                "actions": {f"Check_readback_type_{title}_{name}": {
                    "type": "If", "expression": {"equals": [
                        f"@first(body('{verify_name}')?['value'])?['TypeAsString']", kind]},
                    "actions": {f"Field_verified_{title}_{name}": {"type": "Compose", "inputs": True}},
                    "else": {"actions": fail_steps(
                        f"Readback_type_mismatch_{title}_{name}",
                        f"@concat('SharePoint field readback type mismatch for {title}.{name}; expected {kind}, got ', "
                        f"string(first(body('{verify_name}')?['value'])?['TypeAsString']))")},
                }},
                "else": {"actions": fail_steps(
                    f"Readback_results_ambiguous_{title}_{name}",
                    f"@concat('Field readback for {title}.{name} is missing, duplicated, or paged')")},
            }},
            "else": {"actions": _list_failure(f"field {title}.{name} readback", verify_name)},
        },
    }
    actions[ensure_name] = after(actions[ensure_name], get_name,
                                 status=("Succeeded", "Failed", "TimedOut"))
    actions[verify_name] = after(actions[verify_name], ensure_name,
                                 status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions[check_name] = after(actions[check_name], verify_name,
                                status=("Succeeded", "Failed", "TimedOut"))
    return actions


def ensure_fixture(site_url=TEST_SITE):
    """Optionally add the inert TEST config fixture once; it creates no mapping rows."""
    find = "Find_qualification_fixture"
    ensure = "Ensure_qualification_fixture"
    readback = "Readback_qualification_fixture"
    check = "Check_qualification_fixture_readback"
    filt = "SolutionName eq 'ALMQualificationFixtures' and TargetEnvironment eq 'TEST'"
    def url_field(value):
        return {"__metadata": {"type": "SP.FieldUrlValue"}, "Url": value, "Description": value}

    fields = {
        "__metadata": {"type": "SP.Data.ALMQConfigListItem"},
        "Title": "ALMQualificationFixtures TEST inert fixture",
        "SolutionName": "ALMQualificationFixtures",
        "TargetEnvironment": "TEST",
        "DevPowerPlatformUrl": url_field(TEST_ORG),
        "TargetPowerPlatformUrl": url_field(TEST_ORG),
        "TargetSharePointUrl": url_field(TEST_SITE),
        "RunImport": False,
        "RunPostImport": True,
        "RunShare": False,
    }
    actions = {
        find: _request(site_url, "GET", "_api/web/lists/getbytitle('ALMQConfig')/items?"
                       f"$select=Id,RunImport,RunPostImport,RunShare&$filter={filt.replace(' ', '%20')}"),
        ensure: after({
            "type": "If", "expression": {"equals": [f"@{_status(find)}", 200]},
            "actions": {"If_no_fixture": {
                "type": "If", "expression": {"equals": ["@length(body('Find_qualification_fixture')?['value'])", 0]},
                "actions": {"Create_qualification_fixture": _request(
                    site_url, "POST", "_api/web/lists/getbytitle('ALMQConfig')/items", fields)},
                "else": {"actions": {"If_one_fixture": {
                    "type": "If",
                    "expression": {"equals": ["@length(body('Find_qualification_fixture')?['value'])", 1]},
                    "actions": {"Check_existing_fixture_switches": {
                        "type": "If",
                        "expression": {"and": [
                            {"equals": ["@first(body('Find_qualification_fixture')?['value'])?['RunImport']", False]},
                            {"equals": ["@first(body('Find_qualification_fixture')?['value'])?['RunPostImport']", True]},
                            {"equals": ["@first(body('Find_qualification_fixture')?['value'])?['RunShare']", False]},
                        ]},
                        "actions": {"Fixture_already_safe": {"type": "Compose", "inputs": True}},
                        "else": {"actions": fail_steps("Fixture_switches_unsafe",
                            "@concat('Existing fixture row has unsafe switches; refusing to change it')")},
                    }},
                    "else": {"actions": fail_steps("Fixture_duplicates",
                        "@concat('Multiple ALMQualificationFixtures TEST rows exist; refusing to choose one')")},
                }}}},
            },
            "else": {"actions": _list_failure("qualification fixture lookup", find)},
        }, find, status=("Succeeded", "Failed", "TimedOut")),
        readback: _request(site_url, "GET", "_api/web/lists/getbytitle('ALMQConfig')/items?"
                           f"$select=Id,RunImport,RunPostImport,RunShare&$filter={filt.replace(' ', '%20')}"),
        check: {
            "type": "If", "expression": {"equals": [f"@{_status(readback)}", 200]},
            "actions": {"Check_fixture_result": {
                "type": "If", "expression": {"and": [
                    {"equals": ["@length(body('Readback_qualification_fixture')?['value'])", 1]},
                    {"equals": ["@first(body('Readback_qualification_fixture')?['value'])?['RunImport']", False]},
                    {"equals": ["@first(body('Readback_qualification_fixture')?['value'])?['RunPostImport']", True]},
                    {"equals": ["@first(body('Readback_qualification_fixture')?['value'])?['RunShare']", False]},
                ]},
                "actions": {"Fixture_readback_safe": {"type": "Compose", "inputs": True}},
                "else": {"actions": fail_steps("Fixture_readback_unsafe",
                    "@concat('Fixture readback is missing, duplicated, or has unsafe switches')")},
            }},
            "else": {"actions": _list_failure("qualification fixture readback", readback)},
        },
    }
    actions[readback] = after(actions[readback], ensure,
                              status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions[check] = after(actions[check], readback, status=("Succeeded", "Failed", "TimedOut"))
    return actions


def _result_expression(name, output_path):
    expr = f"actions('{name}')?['outputs']"
    for key in output_path:
        expr += f"?['{key}']"
    return "@" + expr


def _results_payload():
    lists = {title: {
        "id": _result_expression(f"Readback_list_{title}", ("body", "Id")),
        "exists": f"@equals({_status(f'Readback_list_{title}')}, 200)",
    } for title in LIST_FIELDS}
    fields = {f"{title}.{name}": {
        "exists": f"@and(equals({_status(f'Readback_field_{title}_{name}')}, 200), "
                  f"equals({_field_count(f'Readback_field_{title}_{name}')}, 1), "
                  f"{_no_next_page(f'Readback_field_{title}_{name}')})",
        "type": f"@first(body('Readback_field_{title}_{name}')?['value'])?['TypeAsString']",
    } for title, schema in LIST_FIELDS.items() for name in schema}
    return {"lists": lists, "fields": fields, "failMessage": "@variables('FailMessage')"}


def configure_from_target_config(path):
    """Apply TEST connection refs for source generation when list IDs are not bootstrapped yet.

    Only target identity and connector bindings are read. List IDs are deliberately not required
    by this SharePoint-only helper and are not fabricated or written into settings.
    """
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read bootstrap target config {path}: {exc}") from exc
    required = {"mode", "tenant_id", "allowed_accounts", "environment_id", "organization_url", "site_url",
                "solution", "publisher", "connections"}
    if not isinstance(data, dict) or required - data.keys():
        raise ValueError(f"bootstrap target config is missing {sorted(required - (data.keys() if isinstance(data, dict) else set()))}")
    if not isinstance(data["allowed_accounts"], list) or not data["allowed_accounts"]:
        raise ValueError("bootstrap target config requires an approved account allowlist")
    if (data["mode"] != "isolated" or data["tenant_id"].lower() != target_config.APPROVED_TENANT
            or not set(data["allowed_accounts"]).issubset(target_config.APPROVED_ACCOUNTS)
            or data["environment_id"].lower() != TEST_ENV_ID
            or data["organization_url"].rstrip("/") != TEST_ORG
            or data["site_url"].rstrip("/") != TEST_SITE):
        raise ValueError("bootstrap generation accepts only the isolated test-eu environment and ALM-Test site")
    if data["connections"] != {"dataverse": TEST_DV_CONN, "sharepoint": TEST_SP_CONN}:
        raise ValueError("bootstrap generation requires the configured test-eu connections")
    for key in ("solution", "publisher"):
        value = data[key]
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value) or any(
                marker in value.lower() for marker in ("admin", "prod", "production", "flowadmin", "development")):
            raise ValueError(f"unsafe bootstrap {key}")

    s.TENANT = data["tenant_id"]
    s.ALLOWED_ACCOUNTS = frozenset(data["allowed_accounts"])
    s.ADMIN_ENV_ID = TEST_ENV_ID
    s.ADMIN = TEST_ORG
    s.ADMIN_SITE = TEST_SITE
    s.SOLUTION = data["solution"]
    s.PUBLISHER = data["publisher"]
    s.DV_CONN, s.SP_CONN = TEST_DV_CONN, TEST_SP_CONN
    dv_logical, sp_logical = f"alm_PipelineDataverse_{s.SOLUTION}", f"alm_PipelineSharePoint_{s.SOLUTION}"
    s.CONN_REFS = {
        dv_logical: ("ALM Qualification Dataverse", s.DV_API, TEST_DV_CONN),
        sp_logical: ("ALM Qualification SharePoint", s.SP_API, TEST_SP_CONN),
    }
    s.FLOW_REFS = {s.DV_KEY: (dv_logical, s.DV_API), s.SP_KEY: (sp_logical, s.SP_API)}


def build(site_url=TEST_SITE, include_fixture=False, include_logs=False):
    """Build the generated helper definition against the already-applied isolated TEST settings."""
    if site_url.rstrip("/") != TEST_SITE:
        raise ValueError("bootstrap is pinned to the ALM-Test SharePoint site")
    if (s.ADMIN_ENV_ID != TEST_ENV_ID or s.ADMIN.rstrip("/") != TEST_ORG
            or s.ADMIN_SITE.rstrip("/") != TEST_SITE):
        raise ValueError("apply the isolated test-eu target settings before building bootstrap flow")
    if (s.TENANT != target_config.APPROVED_TENANT
            or not s.ALLOWED_ACCOUNTS.issubset(target_config.APPROVED_ACCOUNTS)):
        raise ValueError("bootstrap requires the approved tenant and interactive account allowlist")
    if s.DV_CONN != TEST_DV_CONN or s.SP_CONN != TEST_SP_CONN:
        raise ValueError("bootstrap requires the configured test-eu Dataverse and SharePoint connections")
    for key, connection_id in ((s.DV_KEY, TEST_DV_CONN), (s.SP_KEY, TEST_SP_CONN)):
        ref = s.FLOW_REFS.get(key)
        if not ref or ref[0] not in s.CONN_REFS or s.CONN_REFS[ref[0]][2] != connection_id:
            raise ValueError("bootstrap refuses connection references outside the configured test-eu target")

    actions = {"Init_FailMessage": {"type": "InitializeVariable", "inputs": {
        "variables": [{"name": "FailMessage", "type": "string", "value": ""}]}}}
    previous = "Init_FailMessage"

    def append(group):
        nonlocal previous
        names = list(group)
        if not names:
            return
        group[names[0]] = after(group[names[0]], previous,
                                status=("Succeeded", "Failed", "Skipped", "TimedOut"))
        actions.update(group)
        previous = names[-1]

    for title in LIST_FIELDS:
        append(ensure_list(title, site_url))
        for name, (kind, required) in LIST_FIELDS[title].items():
            append(ensure_field(title, name, kind, required, site_url))
    if include_fixture:
        append(ensure_fixture(site_url))
    if include_logs:
        append(ensure_list('DeploymentLogs', site_url, template=101))
    results = _results_payload()
    if include_logs:
        results['logLibraryId'] = "@body('Readback_list_DeploymentLogs')?['Id']"
    if include_fixture:
        results["fixtureMatchCountBefore"] = "@length(body('Find_qualification_fixture')?['value'])"
        results["fixtureId"] = "@first(body('Readback_qualification_fixture')?['value'])?['Id']"
        results["fixtureSafe"] = "@equals(variables('FailMessage'), '')"
    actions["Results"] = after({"type": "Compose", "inputs": results}, previous,
                               status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions["Stop_on_failure"] = after({
        "type": "If", "expression": {"equals": ["@empty(variables('FailMessage'))", True]},
        "actions": {},
        "else": {"actions": {"Terminate_failed": {
            "type": "Terminate", "inputs": {"runStatus": "Failed", "runError": {
                "code": "BootstrapFailed", "message": "@variables('FailMessage')"}}}}},
    }, "Results")
    return clientdata(manual_trigger([]), actions, s.FLOW_REFS)


def write_definition(path, site_url=TEST_SITE, include_fixture=False, include_logs=False):
    cd = build(site_url, include_fixture, include_logs)
    errors = validate(cd)
    if errors:
        raise ValueError("bootstrap flow failed validation:\n  " + "\n  ".join(errors))
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cd, indent=2))
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="write generated flow JSON to this path")
    parser.add_argument("--target-config", required=True, help="isolated target config with test-eu connections")
    parser.add_argument("--site-url", default=TEST_SITE)
    parser.add_argument("--fixture", action="store_true", help="include an inert ALMQualificationFixtures TEST row")
    parser.add_argument('--logs', action='store_true', help='provision the isolated DeploymentLogs document library')
    args = parser.parse_args(argv)
    configure_from_target_config(args.target_config)
    path = write_definition(args.output, args.site_url, args.fixture, args.logs)
    print(f"wrote validated bootstrap flow definition to {path}")


if __name__ == "__main__":
    main()
