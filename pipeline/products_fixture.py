"""Generate a guarded flow that provisions and verifies the TEST Products list.

This is deliberately a basic SharePoint-list fixture, not a general field migrator.
It only writes a flow definition locally; it never deploys or runs that definition.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from pipeline import bootstrap
from pipeline import settings as s
from pipeline.defs import after, clientdata, fail_steps, manual_trigger, validate

PROVISIONED_PRODUCTS_LIST_ID = "9ca71bdc-8192-4321-85ce-f29ac9d3a7d8"


def load_source_fields(path: str | Path) -> list[dict]:
    """Read the captured DEV fields and reject schemas this fixture cannot represent."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read captured Products fields: {exc}") from exc
    if not isinstance(doc, dict) or set(doc) != {"value"} or not isinstance(doc["value"], list):
        raise ValueError("captured Products fields must be an object containing only a value array")
    fields = doc["value"]
    if not fields or any(not isinstance(field, dict) for field in fields):
        raise ValueError("captured Products fields must contain field objects")
    names = [field.get("InternalName") for field in fields]
    if any(not isinstance(name, str) or not name for name in names) or len(names) != len(set(names)):
        raise ValueError("captured Products fields have missing or duplicate InternalName values")
    for field in fields:
        for key in ("FromBaseType", "Hidden", "ReadOnlyField", "Required"):
            if type(field.get(key)) is not bool:
                raise ValueError(f"captured field {field['InternalName']} has invalid {key}")
        if not isinstance(field.get("TypeAsString"), str):
            raise ValueError(f"captured field {field['InternalName']} has no TypeAsString")

    unsupported = [field["InternalName"] for field in fields
                   if field["FromBaseType"] is False and field["Hidden"] is False]
    if unsupported:
        raise ValueError("Products fixture does not migrate custom visible columns: " + ", ".join(unsupported))
    title = [field for field in fields if field["InternalName"] == "Title"]
    if (len(title) != 1 or title[0]["TypeAsString"] != "Text" or title[0]["Required"] is not False
            or title[0]["Hidden"] is not False or title[0]["ReadOnlyField"] is not False
            or title[0]["FromBaseType"] is not True):
        raise ValueError("Products source must have the standard writable optional Text Title field")
    return fields


def _field_collection_uri() -> str:
    return ("_api/web/lists/getbytitle('Products')/fields?"
            "$select=InternalName,TypeAsString,Required,Hidden,ReadOnlyField,FromBaseType&$top=5000")


def _status(action: str) -> str:
    return f"actions('{action}')?['outputs']?['statusCode']"


def _no_next_page(action: str) -> str:
    return (f"and(empty(body('{action}')?['odata.nextLink']), "
            f"empty(body('{action}')?['@odata.nextLink']))")


def _title_field_uri() -> str:
    return ("_api/web/lists/getbytitle('Products')/fields/getbyinternalnameortitle('Title')?"
            "$select=InternalName,TypeAsString,Required,Hidden,ReadOnlyField,FromBaseType")


def _title_query(action: str) -> dict:
    return {"type": "Query", "inputs": {
        "from": f"@body('{action}')?['value']",
        "where": "@equals(item()?['InternalName'], 'Title')"}}


def _custom_visible_query(action: str) -> dict:
    return {"type": "Query", "inputs": {
        "from": f"@body('{action}')?['value']",
        "where": "@and(equals(item()?['FromBaseType'], false), equals(item()?['Hidden'], false))"}}


def _merge_title_required_false(site_url: str) -> dict:
    action = bootstrap._request(site_url, "POST",
        "_api/web/lists/getbytitle('Products')/fields/getbyinternalnameortitle('Title')", {
            "__metadata": {"type": "SP.Field"}, "Required": False})
    params = action["inputs"]["parameters"]
    params["parameters/headers"].update({
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose",
        "X-HTTP-Method": "MERGE",
        "IF-MATCH": "*",
    })
    action["inputs"]["retryPolicy"] = {"type": "none"}
    return action


def _validate_provisioned_list_id(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", value):
        raise ValueError("provisioned Products list ID must be a canonical GUID")
    if value.lower() != PROVISIONED_PRODUCTS_LIST_ID:
        raise ValueError("Title adjustment is allowed only for the explicitly provisioned TEST Products list")
    return value.lower()


def build(source_fields: list[dict], site_url: str = bootstrap.TEST_SITE,
          provisioned_list_id: str | None = None) -> dict:
    """Build the flow against the pinned TEST site after target-config validation."""
    # Re-check even when called directly by another Python caller.
    if site_url.rstrip("/") != bootstrap.TEST_SITE:
        raise ValueError("Products fixture is pinned to the isolated ALM-Test SharePoint site")
    if (s.ADMIN_ENV_ID != bootstrap.TEST_ENV_ID or s.ADMIN.rstrip("/") != bootstrap.TEST_ORG
            or s.ADMIN_SITE.rstrip("/") != bootstrap.TEST_SITE
            or s.TENANT != bootstrap.target_config.APPROVED_TENANT
            or not s.ALLOWED_ACCOUNTS
            or not s.ALLOWED_ACCOUNTS.issubset(bootstrap.target_config.APPROVED_ACCOUNTS)
            or s.SP_CONN != bootstrap.TEST_SP_CONN):
        raise ValueError("apply the isolated test-eu target config before building Products fixture")
    sp_ref = s.FLOW_REFS.get(s.SP_KEY)
    if (not sp_ref or sp_ref[0] not in s.CONN_REFS
            or s.CONN_REFS[sp_ref[0]][2] != bootstrap.TEST_SP_CONN):
        raise ValueError("Products fixture refuses SharePoint connections outside the test-eu target")
    # Validate structure and supported scope from the passed parsed capture as well.
    _validate_source_fields(source_fields)
    provisioned_list_id = _validate_provisioned_list_id(provisioned_list_id)

    actions = {"Init_FailMessage": {"type": "InitializeVariable", "inputs": {
        "variables": [{"name": "FailMessage", "type": "string", "value": ""}]}}}
    previous = "Init_FailMessage"

    def append(group: dict) -> None:
        nonlocal previous
        names = list(group)
        if not names:
            return
        group[names[0]] = after(group[names[0]], previous,
                                status=("Succeeded", "Failed", "Skipped", "TimedOut"))
        actions.update(group)
        previous = names[-1]

    append(bootstrap.ensure_list("Products", site_url))

    if provisioned_list_id is not None:
        # This exact ID is the only list for which this helper may relax Title.Required.
        # Verify target identity, emptiness, and complete supported schema before PATCH.
        guard = "Readback_Products_provisioned_identity"
        append({guard: bootstrap._request(site_url, "GET",
            "_api/web/lists/getbytitle('Products')?$select=Id,Title,ItemCount")})
        append({"Check_Products_provisioned_identity": {
            "type": "If", "expression": {"and": [
                {"equals": [f"@{_status(guard)}", 200]},
                {"equals": [f"@body('{guard}')?['Id']", provisioned_list_id]},
                {"equals": [f"@body('{guard}')?['ItemCount']", 0]},
            ]},
            "actions": {"Products_provisioned_identity_verified": {"type": "Compose", "inputs": True}},
            "else": {"actions": fail_steps("Products_provisioned_identity_mismatch",
                "@concat('Provisioned Products list ID mismatch or list is not empty; expected ', "
                f"'{provisioned_list_id}', '; actual ', string(body('{guard}')?['Id']), "
                "'; item count ', string(body('Readback_Products_provisioned_identity')?['ItemCount']))")},
        }})
        pre = "Readback_Products_fields_before_adjustment"
        append({pre: bootstrap._request(site_url, "GET", _field_collection_uri())})
        append({"Find_Products_Title_before_adjustment": _title_query(pre)})
        append({"Find_Products_custom_visible_fields_before_adjustment": _custom_visible_query(pre)})
        pre_ok = {"and": [
            {"equals": ["@empty(variables('FailMessage'))", True]},
            {"equals": [f"@{_status(pre)}", 200]},
            {"equals": [f"@{_no_next_page(pre)}", True]},
            {"equals": ["@length(body('Find_Products_Title_before_adjustment'))", 1]},
            {"equals": ["@first(body('Find_Products_Title_before_adjustment'))?['TypeAsString']", "Text"]},
            {"equals": ["@first(body('Find_Products_Title_before_adjustment'))?['FromBaseType']", True]},
            {"equals": ["@first(body('Find_Products_Title_before_adjustment'))?['Hidden']", False]},
            {"equals": ["@first(body('Find_Products_Title_before_adjustment'))?['ReadOnlyField']", False]},
            {"equals": ["@length(body('Find_Products_custom_visible_fields_before_adjustment'))", 0]},
        ]}
        adjust_required = {
            "type": "If", "expression": pre_ok,
            "actions": {"If_Products_Title_is_required": {
                "type": "If", "expression": {"equals": [
                    "@first(body('Find_Products_Title_before_adjustment'))?['Required']", True]},
                "actions": {"Update_Products_Title_required": _merge_title_required_false(site_url)},
                "else": {"actions": {"If_Products_Title_already_optional": {
                    "type": "If", "expression": {"equals": [
                        "@first(body('Find_Products_Title_before_adjustment'))?['Required']", False]},
                    "actions": {"Products_Title_already_optional": {"type": "Compose", "inputs": True}},
                    "else": {"actions": fail_steps("Products_Title_required_invalid",
                        "@concat('Products Title Required value is not boolean')")},
                }}}},
            },
            "else": {"actions": fail_steps("Products_Title_adjustment_refused",
                "@concat('Refusing Title adjustment: complete list schema is unsupported or Title is not a standard writable Text field')")},
        }
        append({"Check_Products_Title_adjustment_preconditions": adjust_required})
        append({"Check_Products_Title_adjustment_result": {
            "type": "If", "expression": {"or": [
                {"equals": [f"@{_status('Update_Products_Title_required')}", 204]},
                {"equals": [f"@{_status('Update_Products_Title_required')}", 200]},
                {"equals": ["@equals(first(body('Find_Products_Title_before_adjustment'))?['Required'], false)", True]},
            ]},
            "actions": {"Products_Title_adjustment_verified": {"type": "Compose", "inputs": True}},
            "else": {"actions": fail_steps("Products_Title_adjustment_failed",
                "@concat('Title Required adjustment did not return HTTP 200/204; HTTP ', "
                f"string({_status('Update_Products_Title_required')}))")},
        }})

    readback = "Readback_Products_fields"
    append({readback: bootstrap._request(site_url, "GET", _field_collection_uri())})
    append({"Find_Products_Title": _title_query(readback)})
    append({"Find_Products_custom_visible_fields": _custom_visible_query(readback)})

    schema_check = {
        "type": "If",
        "expression": {"and": [
            {"equals": [f"@{_status(readback)}", 200]},
            {"equals": [f"@{_no_next_page(readback)}", True]},
            {"equals": ["@length(body('Find_Products_Title'))", 1]},
            {"equals": ["@first(body('Find_Products_Title'))?['TypeAsString']", "Text"]},
            {"equals": ["@first(body('Find_Products_Title'))?['Required']", False]},
            {"equals": ["@first(body('Find_Products_Title'))?['Hidden']", False]},
            {"equals": ["@first(body('Find_Products_Title'))?['ReadOnlyField']", False]},
            {"equals": ["@length(body('Find_Products_custom_visible_fields'))", 0]},
        ]},
        "actions": {"Products_schema_verified": {"type": "Compose", "inputs": True}},
        "else": {"actions": fail_steps(
            "Products_schema_mismatch",
            "@concat('Products list field schema did not match optional writable Text Title; HTTP ', "
            f"string({_status(readback)}), '; title matches ', string(length(body('Find_Products_Title'))), "
            "'; visible custom fields ', string(length(body('Find_Products_custom_visible_fields'))))")},
    }
    append({"Check_Products_schema": schema_check})
    actions["Results"] = after({"type": "Compose", "inputs": {
        "listId": "@body('Readback_list_Products')?['Id']",
        "listTitle": "@body('Readback_list_Products')?['Title']",
        "fieldCount": "@length(body('Readback_Products_fields')?['value'])",
        "titleType": "@first(body('Find_Products_Title'))?['TypeAsString']",
        "titleRequired": "@first(body('Find_Products_Title'))?['Required']",
        "visibleCustomFieldCount": "@length(body('Find_Products_custom_visible_fields'))",
        "failMessage": "@variables('FailMessage')",
    }}, previous, status=("Succeeded", "Failed", "Skipped", "TimedOut"))
    actions["Stop_on_failure"] = after({
        "type": "If", "expression": {"equals": ["@empty(variables('FailMessage'))", True]},
        "actions": {}, "else": {"actions": {"Terminate_failed": {
            "type": "Terminate", "inputs": {"runStatus": "Failed", "runError": {
                "code": "ProductsFixtureFailed", "message": "@variables('FailMessage')"}}}}},
    }, "Results")
    # Dataverse is unused by this helper; keep its connection reference out of
    # the generated definition entirely.
    cd = clientdata(manual_trigger([]), actions, {s.SP_KEY: sp_ref})
    errors = validate(cd)
    if errors:
        raise ValueError("Products fixture flow failed validation:\n  " + "\n  ".join(errors))
    return cd


def _validate_source_fields(fields: list[dict]) -> None:
    if not isinstance(fields, list) or not fields or any(not isinstance(f, dict) for f in fields):
        raise ValueError("captured Products fields must be a non-empty list of objects")
    names = [f.get("InternalName") for f in fields]
    if any(not isinstance(n, str) or not n for n in names) or len(names) != len(set(names)):
        raise ValueError("captured Products fields have missing or duplicate InternalName values")
    for f in fields:
        for key in ("FromBaseType", "Hidden", "ReadOnlyField", "Required"):
            if type(f.get(key)) is not bool:
                raise ValueError(f"captured field {f['InternalName']} has invalid {key}")
        if not isinstance(f.get("TypeAsString"), str):
            raise ValueError(f"captured field {f['InternalName']} has no TypeAsString")
    custom = [f["InternalName"] for f in fields
              if f["FromBaseType"] is False and f["Hidden"] is False]
    if custom:
        raise ValueError("Products fixture does not migrate custom visible columns: " + ", ".join(custom))
    title = [f for f in fields if f["InternalName"] == "Title"]
    if (len(title) != 1 or title[0]["TypeAsString"] != "Text" or title[0]["Required"] is not False
            or title[0]["Hidden"] is not False or title[0]["ReadOnlyField"] is not False
            or title[0]["FromBaseType"] is not True):
        raise ValueError("Products source must have the standard writable optional Text Title field")


def write_definition(output: str | Path, source_fields: list[dict], provisioned_list_id=None) -> Path:
    cd = build(source_fields, provisioned_list_id=provisioned_list_id)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cd, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-config", required=True, help="explicit isolated test-eu target configuration")
    parser.add_argument("--source-fields", required=True, help="captured DEV Products fields JSON")
    parser.add_argument("--output", required=True, help="write generated flow JSON to this local path")
    parser.add_argument("--provisioned-list-id", help="explicit ID of the empty list created by qualification")
    args = parser.parse_args(argv)
    bootstrap.configure_from_target_config(args.target_config)
    fields = load_source_fields(args.source_fields)
    path = write_definition(args.output, fields, args.provisioned_list_id)
    print(f"wrote validated Products fixture flow definition to {path}")


if __name__ == "__main__":
    main()
