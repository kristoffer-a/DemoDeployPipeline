"""Generate inert fixtures and activation cases for an isolated C3 qualification.

Fixtures have no external connectors or business-data actions. This command
generates files only; deployment and runtime results are recorded separately.
"""
import argparse
import copy
import json
from pathlib import Path
import uuid

from pipeline.defs import clientdata, manual_trigger, respond, run_child, validate

CASES = ("valid", "unchanged", "missing", "malformed", "duplicate", "foreign", "incomplete")


def fault_variant(c3_definition, kind):
    """Generate a fault-only C3 clone for dedicated isolated manual harnesses.

    Never replace the real C3 with this definition. Generation makes no live calls.
    """
    result = copy.deepcopy(c3_definition)
    actions = result['properties']['definition']['actions']['Try']['actions']
    if kind == 'enable-write':
        actions['For_each_Enable']['actions']['If_change_Enable']['actions']['Set_Enable'][
            'inputs']['parameters']['recordId'] = 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
    elif kind == 'readback':
        actions['Observed_states']['inputs']['select'] = "@concat(toLower(item()?['workflowid']), '|9')"
    else:
        raise ValueError('unknown qualification fault')
    return result


def fixtures(ids):
    """Supply actual workflow IDs after deployment; generated IDs are offline placeholders."""
    child = clientdata(manual_trigger([]), {"Reply": respond({"status": "Succeeded"})}, {})
    parent = clientdata(manual_trigger([]), {"Call_child": run_child(ids["child"], {}),
                                            "Reply": {**respond({"status": "Succeeded"}),
                                                      "runAfter": {"Call_child": ["Succeeded"]}}}, {})
    return {"helper": child, "legacy": child, "child": child, "parent": parent}


def policies(solution, ids):
    # Disable helper and legacy before enabling the child and its caller.
    valid = {"version": 1, "solution": solution, "flows": [
        {"workflowId": ids["legacy"], "enabled": False},
        {"workflowId": ids["helper"], "enabled": False},
        {"workflowId": ids["child"], "enabled": True},
        {"workflowId": ids["parent"], "enabled": True}]}
    duplicate = json.loads(json.dumps(valid))
    duplicate["flows"].append(dict(valid["flows"][0]))
    foreign = json.loads(json.dumps(valid))
    foreign["flows"][0]["workflowId"] = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    incomplete = json.loads(json.dumps(valid))
    incomplete["flows"].pop()
    return {"valid": valid, "unchanged": valid, "missing": None, "malformed": "not-an-object", "duplicate": duplicate,
            "foreign": foreign, "incomplete": incomplete}


def harness(child_id, solution, stage, policy):
    """The harness binds inputs explicitly; a button trigger otherwise cannot supply them via CLI."""
    body = {"text": solution, "text_1": stage}
    if policy is not None:
        body["text_2"] = json.dumps(policy, separators=(",", ":"))
    return clientdata(manual_trigger([]), {"Run_C3": run_child(child_id, body)}, {})


def generate(out, solution, ids, c3_id=None):
    if set(ids) != {"helper", "legacy", "child", "parent"}:
        raise ValueError("fixture IDs must include helper, legacy, child and parent")
    normalized = [str(uuid.UUID(value)) for value in ids.values()]
    if normalized != list(ids.values()) or len(set(normalized)) != len(normalized):
        raise ValueError("fixture workflow IDs must be unique lowercase GUIDs")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, definition in fixtures(ids).items():
        errors = validate(definition)
        if errors:
            raise ValueError("; ".join(errors))
        (out / f"fixture-{name}.json").write_text(json.dumps(definition, indent=2) + "\n")
    for name, policy in policies(solution, ids).items():
        (out / f"policy-{name}.json").write_text(json.dumps(policy, indent=2) + "\n")
        if c3_id:
            definition = harness(str(uuid.UUID(c3_id)), solution, "TEST", policy)
            errors = validate(definition)
            if errors:
                raise ValueError("; ".join(errors))
            (out / f"harness-{name}.json").write_text(json.dumps(definition, indent=2) + "\n")
    return {"status": "Generated", "runtimeAcceptance": "Not executed", "fixtureSolution": solution,
            "workflowIds": ids, "cases": list(CASES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--solution", default="ALMQualificationFixtures")
    parser.add_argument("--fixture-ids", required=True, help="JSON object containing four real workflow IDs")
    parser.add_argument("--c3-id", help="real isolated candidate C3 workflow ID")
    args = parser.parse_args()
    result = generate(args.out, args.solution, json.loads(Path(args.fixture_ids).read_text()), args.c3_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
