import jsonschema
import pytest

from pipeline import activation, artifacts, defs, flows
from pipeline.tests.activation_runtime import RunFailed, Runtime

A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'
C = '33333333-3333-3333-3333-333333333333'


def policy(rows):
    return {'version': 1, 'solution': 'Example', 'flows': [{'workflowId': wid, 'enabled': enabled} for wid, enabled in rows]}


def inventory(rows):
    return [{'workflowid': wid, 'name': 'same display name', 'statecode': state} for wid, state in rows]


def contract():
    return defs.seq(activation.validate_policy("@triggerBody()?['manifest']", "'Example'", 'https://example.invalid'),
                    activation.apply_policy('https://example.invalid', "'Example'"))


@pytest.mark.parametrize('bad', [None, '', '{}', '{broken', {'version': 2, 'solution': 'Example', 'flows': []},
                               policy([(A, 'false')]),
                               {**policy([]), 'unexpected': True}])
def test_invalid_manifest_never_writes(bad):
    runtime = Runtime(bad, inventory([(A, 0)]))
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        runtime.run(contract())
    assert runtime.writes == []


@pytest.mark.parametrize('bad', [policy([]), policy([(B, True)]), policy([(A, True), (A, False)]),
                               policy([(A, True), (A, True)]), policy([('not-a-guid', True)]),
                               {**policy([(A, True)]), 'solution': 'Other'}])
def test_wrong_incomplete_foreign_or_duplicate_policy_never_writes(bad):
    runtime = Runtime(bad, inventory([(A, 0)]))
    with pytest.raises(RunFailed):
        runtime.run(contract())
    assert runtime.writes == []


def _schema_has_key(value, key):
    if isinstance(value, dict):
        return key in value or any(_schema_has_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_schema_has_key(child, key) for child in value)
    return False


def test_parsejson_uses_recursive_runtime_schema_copy_without_regex_keywords():
    assert activation.SCHEMA['properties']['flows']['items']['properties']['workflowId']['pattern'].startswith('^')
    assert flows.RELEASE_SCHEMA['properties']['zipSha256']['pattern'] == '^[0-9a-f]{64}$'
    assert not _schema_has_key(activation.RUNTIME_SCHEMA, 'pattern')
    assert not _schema_has_key(activation.RUNTIME_SCHEMA, 'patternProperties')
    assert not _schema_has_key(flows.RELEASE_RUNTIME_SCHEMA, 'pattern')
    assert not _schema_has_key(flows.RELEASE_RUNTIME_SCHEMA, 'patternProperties')
    assert activation.RUNTIME_SCHEMA['properties']['version']['enum'] == [1]
    assert activation.RUNTIME_SCHEMA['properties']['flows']['maxItems'] == 100
    assert activation.RUNTIME_SCHEMA['additionalProperties'] is False
    assert activation.validate_policy("@triggerBody()?['manifest']", "'Example'", 'org')[
        'Activation_policy']['inputs']['schema'] == activation.RUNTIME_SCHEMA
    release_parse = flows.c2()['properties']['definition']['actions']['Try']['actions']['Release_descriptor']
    assert release_parse['inputs']['schema'] == flows.RELEASE_RUNTIME_SCHEMA


def test_runtime_schema_removes_nested_patternproperties_without_mutating_source():
    canonical = {"patternProperties": {"^x": {"properties": {
        "id": {"type": "string", "pattern": "^[0-9a-f]+$"}}}},
        "properties": {"count": {"type": "integer", "minimum": 0}}}
    runtime = defs.runtime_json_schema(canonical)
    assert "patternProperties" in canonical
    assert canonical["patternProperties"]["^x"]["properties"]["id"]["pattern"] == "^[0-9a-f]+$"
    assert not _schema_has_key(runtime, "patternProperties")
    assert not _schema_has_key(runtime, "pattern")
    assert runtime["properties"]["count"]["minimum"] == 0


def test_offline_manifest_and_descriptor_verifiers_keep_guid_and_hash_checks():
    with pytest.raises(artifacts.ArtifactError, match='lowercase GUID'):
        artifacts._validate_manifest(policy([('not-a-guid', True)]), 'Example')
    descriptor_schema = flows.RELEASE_SCHEMA
    assert descriptor_schema['properties']['cloudFlowIds']['items']['pattern'].startswith('^')
    assert descriptor_schema['properties']['zipSha256']['pattern'] == '^[0-9a-f]{64}$'


def test_missing_field_and_excessive_batch_are_rejected():
    for bad in ({'version': 1, 'flows': []}, policy([(A, True)] * 101)):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft4Validator(activation.SCHEMA).validate(bad)


def test_empty_solution_requires_explicit_empty_manifest():
    runtime = Runtime(policy([]), [])
    runtime.run(contract())
    assert runtime.writes == []


def test_disables_legacy_first_then_enables_in_manifest_order_and_verifies():
    runtime = Runtime(policy([(C, True), (B, False), (A, True)]), inventory([(A, 0), (B, 1), (C, 0)]))
    runtime.run(contract())
    assert runtime.writes == [(B, 0), (C, 1), (A, 1)]
    assert runtime.results['Observed_states'] == [A + '|1', B + '|0', C + '|1']
    # Second run does not restart anything already in its desired state.
    repeat = Runtime(policy([(C, True), (B, False), (A, True)]), runtime.inventory)
    repeat.run(contract())
    assert repeat.writes == []


def test_failed_disable_prevents_any_activation():
    runtime = Runtime(policy([(A, True), (B, False)]), inventory([(A, 0), (B, 1)]), fail_write=B)
    with pytest.raises(RunFailed, match='Injected'):
        runtime.run(contract())
    assert runtime.writes == []


def test_wrong_readback_is_failure():
    runtime = Runtime(policy([(A, True)]), inventory([(A, 0)]), stale_readback=True)
    with pytest.raises(RunFailed, match='readback'):
        runtime.run(contract())


def test_paginated_inventory_never_activates():
    runtime = Runtime(policy([(A, True)]), inventory([(A, 0)]), next_link='more')
    with pytest.raises(RunFailed, match='paginated'):
        runtime.run(contract())
    assert runtime.writes == []


def test_suspended_is_not_treated_as_desired_off():
    runtime = Runtime(policy([(A, False)]), inventory([(A, 2)]))
    runtime.run(contract())
    assert runtime.writes == [(A, 0)]


def test_import_gate_blocks_source_or_target_flows_but_allows_flowless():
    for source, target in (([{}], []), ([], [{}]), ([{}], [{}])):
        runtime = Runtime(policy([]), target)
        runtime.results['Solution_flows'] = {'value': source}
        with pytest.raises(RunFailed, match='not qualified'):
            runtime.run(activation.block_cloud_imports("'Example'", 'https://example.invalid'))
    runtime = Runtime(policy([]), [])
    runtime.results['Solution_flows'] = {'value': []}
    runtime.run(activation.block_cloud_imports("'Example'", 'https://example.invalid'))


def test_every_policy_action_is_success_chained():
    actions = contract()
    previous = None
    for name, action in actions.items():
        if previous:
            assert action['runAfter'] == {previous: ['Succeeded']}, name
        previous = name
    assert actions['For_each_Enable']['runtimeConfiguration']['concurrency']['repetitions'] == 1
    assert actions['For_each_Disable']['runtimeConfiguration']['concurrency']['repetitions'] == 1


def test_parent_freezes_passes_archives_and_logs_same_manifest():
    actions = flows.c1({})['properties']['definition']['actions']
    main = actions['Main']['actions']
    c2 = main['Import']['actions']['If_RunImport']['actions']['Run_C2_import']['inputs']['body']
    c3 = main['PostImport']['actions']['If_RunPostImport']['actions']['Run_C3_post_import']['inputs']['body']
    assert c2['text_3'] == c3['text_2'] == "@string(body('Activation_policy'))"
    archive = main['Export']['actions']['If_export_release']['actions']['Export_succeeded']['actions']['Archive_activation']
    assert archive['runAfter'] == {'Archive_ZIP': ['Succeeded']}
    assert archive['inputs']['parameters']['body'] == c2['text_3']
    assert 'activationPolicy' in actions['Log']['actions']['Log_entry']['inputs']


def test_direct_children_cannot_skip_policy_or_import_guard():
    c2 = flows.c2()['properties']['definition']['actions']['Try']['actions']
    assert list(c2).index('Check_cloud_import') < list(c2).index('Import_to_target')
    c3 = flows.c3()['properties']['definition']['actions']['Try']['actions']
    assert list(c3).index('Check_policy_coverage') < list(c3).index('For_each_variable')
    assert c3['Reply']['runAfter'] == {'Check_final_states': ['Succeeded']}
    assert 'Off_flows' not in c3


def test_fetch_requests_one_more_than_manifest_limit():
    query = activation.solution_flows('org', "'Example'")['inputs']['parameters']['fetchXml']
    assert 'count="101"' in query and 'page="1"' in query


@pytest.mark.parametrize('annotation', [
    {'@Microsoft.Dynamics.CRM.morerecords': True},
    {'@Microsoft.Dynamics.CRM.fetchxmlpagingcookie': '<cookie/>'},
    {'value': [{}] * 101},
])
def test_fetchxml_truncation_signals_fail_closed(annotation):
    runtime = Runtime(policy([]), [])
    runtime.results['Read'] = {'value': [], **annotation}
    assert runtime.condition(activation.incomplete_inventory('Read')) is True


@pytest.mark.parametrize('enabled,state', [(True, 0), (False, 1)])
def test_failed_update_blocks_later_iterations(enabled, state):
    runtime = Runtime(policy([(A, enabled), (B, enabled)]),
                      inventory([(A, state), (B, state)]), fail_write=A)
    with pytest.raises(RunFailed, match='Injected'):
        runtime.run(contract())
    assert runtime.writes == []
    assert runtime.loops['For_each_Enable' if enabled else 'For_each_Disable']['workflowId'] == B


@pytest.mark.parametrize('run_import,run_post,expected', [
    (False, True, 'TEST'), (True, True, 'DEV'), (True, False, 'DEV'), (False, False, 'DEV'),
])
def test_parent_inventory_selection_with_version_skew(run_import, run_post, expected):
    prechecks = flows.c1({})['properties']['definition']['actions']['Main']['actions']['Prechecks']['actions']
    org = prechecks['Solution_flows']['inputs']['parameters']['organization']
    runtime = Runtime(policy([(A, True)]), inventory([(A, 0)]))
    runtime.results.update(Config={'RunImport': run_import, 'RunPostImport': run_post},
                           Dev_url='DEV', Target_url='TEST')
    assert runtime.expr(org) == expected
    # TEST's policy remains valid even though DEV has an additional unreleased flow.
    if expected == 'TEST':
        runtime.run(activation.validate_policy("@triggerBody()?['manifest']", "'Example'", org))
        runtime.run(activation.apply_policy(org, "'Example'"))
        assert runtime.writes == [(A, 1)]
