import json

import pytest

from pipeline import qualification
from pipeline import flows

IDS = {name: f"{i:08d}-0000-4000-8000-000000000000"
       for i, name in enumerate(("helper", "legacy", "child", "parent"), 1)}


def test_inert_fixture_parent_invokes_the_bound_child_without_external_connectors():
    flows = qualification.fixtures(IDS)
    parent = flows["parent"]["properties"]["definition"]["actions"]
    assert parent["Call_child"]["inputs"]["host"]["workflowReferenceName"] == IDS["child"]
    assert all(flow["properties"]["connectionReferences"] == {} for flow in flows.values())


def test_policies_preserve_disable_first_child_before_parent_and_invalid_coverage():
    cases = qualification.policies("Fixtures", IDS)
    assert [flow["workflowId"] for flow in cases["valid"]["flows"]] == [
        IDS["legacy"], IDS["helper"], IDS["child"], IDS["parent"]]
    assert [flow["enabled"] for flow in cases["valid"]["flows"]] == [False, False, True, True]
    assert cases["missing"] is None
    assert len(cases["duplicate"]["flows"]) == 5
    assert len(cases["incomplete"]["flows"]) == 3


def test_harness_explicitly_binds_manifest_and_missing_input_case(tmp_path):
    result = qualification.generate(tmp_path, "Fixtures", IDS, IDS["child"])
    assert result["runtimeAcceptance"] == "Not executed"
    valid = json.loads((tmp_path / "harness-valid.json").read_text())
    body = valid["properties"]["definition"]["actions"]["Run_C3"]["inputs"]["body"]
    assert json.loads(body["text_2"])["solution"] == "Fixtures"
    missing = json.loads((tmp_path / "harness-missing.json").read_text())
    assert "text_2" not in missing["properties"]["definition"]["actions"]["Run_C3"]["inputs"]["body"]


def test_rejects_duplicate_fixture_ids(tmp_path):
    with pytest.raises(ValueError, match="unique"):
        qualification.generate(tmp_path, "Fixtures", {**IDS, "parent": IDS["child"]})


def test_fault_variants_are_explicit_clones_and_preserve_real_c3():
    original = flows.c3()
    snapshot = json.dumps(original, sort_keys=True)
    write = qualification.fault_variant(original, 'enable-write')
    action = write['properties']['definition']['actions']['Try']['actions']['For_each_Enable'][
        'actions']['If_change_Enable']['actions']['Set_Enable']
    assert action['inputs']['parameters']['recordId'] == 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
    readback = qualification.fault_variant(original, 'readback')
    assert readback['properties']['definition']['actions']['Try']['actions']['Observed_states'][
        'inputs']['select'].endswith("'|9')")
    assert json.dumps(original, sort_keys=True) == snapshot
    with pytest.raises(ValueError, match='unknown qualification fault'):
        qualification.fault_variant(original, 'other')
