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


def test_fetch_in_solution_always_includes_pk_first_no_duplicate():
    xml = defs.fetch_in_solution("connectionreference", "connectionreferenceid",
                                 ["connectionreferencelogicalname"], "outputs('Solution')")
    assert xml.count('<attribute name="connectionreferenceid"/>') == 1
    assert xml.index('<attribute name="connectionreferenceid"/>') < xml.index(
        '<attribute name="connectionreferencelogicalname"/>')

    xml2 = defs.fetch_in_solution("workflow", "workflowid", ["workflowid", "name"], "outputs('Solution')")
    assert xml2.count('<attribute name="workflowid"/>') == 1
    assert xml2.index('<attribute name="workflowid"/>') < xml2.index('<attribute name="name"/>')


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


def test_unbound_passes_item_as_one_object():
    a = defs.unbound("k", "@outputs('Dev_url')", "ExportSolutionAsync", {"SolutionName": "@outputs('Solution')", "Managed": True})
    params = a["inputs"]["parameters"]
    assert params["item"] == {"SolutionName": "@outputs('Solution')", "Managed": True}
    assert not any(k.startswith("item/") for k in params)


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


def test_validate_accepts_result_reference():
    cd = _cd({
        "S": {"type": "Scope", "actions": {"A": {"type": "Compose", "inputs": 1}}},
        "B": after_ok({"type": "Query", "inputs": {"from": "@result('S')", "where": "@true"}}, "S"),
    })
    assert defs.validate(cd) == []


def test_run_child_sets_no_retry_policy():
    a = defs.run_child("wf-id", {"text": "@x"})
    assert a["inputs"]["retryPolicy"] == {"type": "none"}
    assert a["inputs"]["host"]["workflowReferenceName"] == "wf-id"


def after_ok(action, prev):
    return defs.after(action, prev)


import re as _re

from pipeline import settings

GUID = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_config_list_ids_are_set():
    for value in (settings.LIST_CONFIG, settings.LIST_CONNECTIONS, settings.LIST_VARIABLES):
        assert GUID.match(value), value
