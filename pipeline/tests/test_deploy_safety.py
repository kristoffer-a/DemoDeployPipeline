import json
import urllib.parse
import xml.etree.ElementTree as ET
from unittest.mock import Mock

import pytest

from pipeline import deploy, flowapi, settings as s


@pytest.mark.parametrize('account', sorted(s.ALLOWED_ACCOUNTS))
def test_approved_accounts_can_request_token(monkeypatch, account):
    call = Mock(side_effect=[json.dumps({'tenantId': s.TENANT, 'user': {'name': account.upper(), 'type': 'user'}}).encode(), 'token'])
    monkeypatch.setattr(flowapi.subprocess, 'check_output', call)
    assert flowapi.az_token('resource') == 'token'
    assert call.call_count == 2


@pytest.mark.parametrize('tenant,user', [
    ('wrong-tenant', {'name': next(iter(s.ALLOWED_ACCOUNTS)), 'type': 'user'}),
    (s.TENANT, {'name': 'someone@example.com', 'type': 'user'}),
    (s.TENANT, {'name': next(iter(s.ALLOWED_ACCOUNTS)), 'type': 'servicePrincipal'}),
    (s.TENANT, {}),
])
def test_unapproved_context_never_requests_token(monkeypatch, tenant, user):
    call = Mock(return_value=json.dumps({'tenantId': tenant, 'user': user}).encode())
    monkeypatch.setattr(flowapi.subprocess, 'check_output', call)
    with pytest.raises(SystemExit, match='STOP'):
        flowapi.az_token('resource')
    assert call.call_count == 1


def test_lookup_is_solution_scoped_type_scoped_and_xml_escaped(monkeypatch):
    call = Mock(return_value={'value': []})
    monkeypatch.setattr(deploy, 'api', call)
    name = 'Flow & "quoted" <name>'
    assert deploy.find_solution_flow('token', name) is None
    root = ET.fromstring(call.call_args.kwargs['query']['fetchXml'])
    assert root.get('top') == '2'
    conditions = {c.get('attribute'): c.get('value') for c in root.findall('.//condition')}
    assert conditions == {'name': name, 'category': '5', 'type': '1', 'uniquename': s.SOLUTION}
    assert root.find('.//link-entity[@name="solutioncomponent"]').get('to') == 'workflowid'
    assert root.find('.//link-entity[@name="solution"]') is not None


def test_duplicate_flow_fails_before_any_write(monkeypatch):
    call = Mock(return_value={'value': [{'workflowid': 'a'}, {'workflowid': 'b'}]})
    monkeypatch.setattr(deploy, 'api', call)
    with pytest.raises(SystemExit, match='multiple flows'):
        deploy.ensure_flow('token', 'duplicate', {})
    assert call.call_count == 1
    assert call.call_args.args[1] == 'GET'


def test_update_only_touches_resolved_member_with_solution_header(monkeypatch):
    call = Mock(side_effect=[{'value': [{'workflowid': 'inside', 'statecode': 1}]}, {}, {}, {}])
    monkeypatch.setattr(deploy, 'api', call)
    assert deploy.ensure_flow('token', 'flow', {'definition': 'new'}) == 'inside'
    for request in call.call_args_list[1:]:
        assert request.args[1:3] == ('PATCH', 'workflows(inside)')
        assert request.kwargs['solution'] == s.SOLUTION


def test_missing_member_creates_in_solution_instead_of_adopting_global_match(monkeypatch):
    call = Mock(side_effect=[{'value': []}, {'workflowid': 'new'}, {}])
    monkeypatch.setattr(deploy, 'api', call)
    assert deploy.ensure_flow('token', 'same name outside', {}) == 'new'
    assert call.call_args_list[1].args[1] == 'POST'
    assert call.call_args_list[1].kwargs['solution'] == s.SOLUTION


def test_fetch_query_survives_url_encoding(monkeypatch):
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"value": []}'
    def open_(request):
        captured.append(request)
        return Response()
    monkeypatch.setattr(deploy.urllib.request, 'urlopen', open_)
    query = '<fetch><condition value="A &amp; B"/></fetch>'
    deploy.api('token', 'GET', 'workflows', query={'fetchXml': query})
    decoded = urllib.parse.parse_qs(urllib.parse.urlsplit(captured[0].full_url).query)
    assert decoded == {'fetchXml': [query]}


def test_failed_auth_does_not_overwrite_deployed_snapshots(monkeypatch, tmp_path):
    out = tmp_path / 'deployed'
    out.mkdir()
    snapshot = out / 'ALM_C1.json'
    snapshot.write_text('historical snapshot')
    monkeypatch.setattr(deploy, 'OUT', out)
    config = tmp_path / 'isolated.json'
    config.write_text(json.dumps({
        'mode': 'isolated', 'tenant_id': s.TENANT,
        'allowed_accounts': [next(iter(s.ALLOWED_ACCOUNTS))],
        'environment_id': '33333333-3333-4333-8333-333333333333',
        'organization_url': 'https://target.crm.dynamics.com',
        'site_url': 'https://7xpydh.sharepoint.com/sites/ALM-Isolated',
        'solution': 'ALMPipelineIsolated', 'publisher': 'almsandbox',
        'connections': {'dataverse': 'dv-target', 'sharepoint': 'sp-target'},
        'lists': {'config': '44444444-4444-4444-8444-444444444444',
                  'connections': '55555555-5555-4555-8555-555555555555',
                  'variables': '66666666-6666-4666-8666-666666666666'},
    }))
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--target-config', str(config)])
    monkeypatch.setattr(deploy, 'az_token', Mock(side_effect=SystemExit('STOP')))
    with pytest.raises(SystemExit):
        deploy.main()
    assert snapshot.read_text() == 'historical snapshot'
    assert list(out.iterdir()) == [snapshot]


def _write_isolated_config(path):
    path.write_text(json.dumps({
        'mode': 'isolated', 'tenant_id': s.TENANT,
        'allowed_accounts': [next(iter(s.ALLOWED_ACCOUNTS))],
        'environment_id': '33333333-3333-4333-8333-333333333333',
        'organization_url': 'https://target.crm.dynamics.com',
        'site_url': 'https://7xpydh.sharepoint.com/sites/ALM-Isolated',
        'solution': 'ALMPipelineIsolated', 'publisher': 'almsandbox',
        'connections': {'dataverse': 'dv-target', 'sharepoint': 'sp-target'},
        'lists': {'config': '44444444-4444-4444-8444-444444444444',
                  'connections': '55555555-5555-4555-8555-555555555555',
                  'variables': '66666666-6666-4666-8666-666666666666'},
    }))


def test_live_deploy_refuses_baked_in_admin_target(monkeypatch):
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy'])
    monkeypatch.setattr(deploy, 'build', Mock(return_value={}))
    with pytest.raises(SystemExit, match='requires an explicitly configured isolated target'):
        deploy.main()


def test_child_failure_leaves_parent_disabled(monkeypatch, tmp_path):
    config = tmp_path / 'isolated.json'
    _write_isolated_config(config)
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--target-config', str(config)])
    monkeypatch.setattr(deploy, 'build', Mock(return_value={}))
    monkeypatch.setattr(deploy, 'az_token', Mock(return_value='token'))
    monkeypatch.setattr(deploy, 'ensure_solution', Mock())
    monkeypatch.setattr(deploy, 'find_solution_flow', Mock(return_value={'workflowid': 'parent-id', 'statecode': 1}))
    calls = []
    monkeypatch.setattr(deploy, 'api', Mock(side_effect=lambda *a, **kw: calls.append((a, kw)) or {}))
    monkeypatch.setattr(deploy, 'FLOWS', [
        (s.C2_NAME, lambda ids: {}), (s.C3_NAME, lambda ids: {}), (s.C1_NAME, lambda ids: {})])
    monkeypatch.setattr(deploy, 'ensure_flow', Mock(side_effect=RuntimeError('child patch failed')))
    with pytest.raises(SystemExit, match='parent .* remains disabled'):
        deploy.main()
    assert len(calls) == 1
    assert calls[0][0][1] == 'PATCH'
    assert calls[0][0][2] == 'workflows(parent-id)'
    assert calls[0][0][3] == {'statecode': 0, 'statuscode': 1}


def test_active_parent_run_stops_rollout(monkeypatch):
    monkeypatch.setattr(deploy, 'flow_api', lambda: 'https://flows.example/environment')
    monkeypatch.setattr(deploy, 'az_token', Mock(return_value='flow-token'))
    get = Mock(side_effect=[
        {'value': [{'name': 'flow-id', 'properties': {'displayName': s.C1_NAME}}]},
        {'value': [{'name': 'run-id', 'properties': {'status': 'Running'}}]},
    ])
    monkeypatch.setattr(deploy, 'get_json', get)
    with pytest.raises(SystemExit, match='parent has active runs'):
        deploy.require_parent_quiescent(s.C1_NAME)
    assert get.call_count == 2


def test_parent_run_pagination_rejects_external_url(monkeypatch):
    monkeypatch.setattr(deploy, 'flow_api', lambda: 'https://flows.example/environment')
    monkeypatch.setattr(deploy, 'az_token', Mock(return_value='flow-token'))
    get = Mock(side_effect=[
        {'value': [{'name': 'flow-id', 'properties': {'displayName': s.C1_NAME}}]},
        {'value': [], 'nextLink': 'https://attacker.example/steal-token'},
    ])
    monkeypatch.setattr(deploy, 'get_json', get)
    with pytest.raises(SystemExit, match='outside the configured environment'):
        deploy.require_parent_quiescent(s.C1_NAME)
    assert get.call_count == 2


def test_known_parent_missing_from_flow_api_blocks_rollout(monkeypatch):
    monkeypatch.setattr(deploy, 'flow_api', lambda: 'https://flows.example/environment')
    monkeypatch.setattr(deploy, 'az_token', Mock(return_value='flow-token'))
    monkeypatch.setattr(deploy, 'get_json', Mock(return_value={'value': []}))
    with pytest.raises(SystemExit, match='cannot prove it is quiescent'):
        deploy.require_parent_quiescent(s.C1_NAME, required=True)


def test_repeating_flow_api_page_blocks_rollout(monkeypatch):
    monkeypatch.setattr(deploy, 'flow_api', lambda: 'https://flows.example/environment')
    monkeypatch.setattr(deploy, 'az_token', Mock(return_value='flow-token'))
    get = Mock(return_value={'value': [], 'nextLink': '?api-version=2016-11-01'})
    monkeypatch.setattr(deploy, 'get_json', get)
    with pytest.raises(SystemExit, match='pagination repeated'):
        deploy.require_parent_quiescent(s.C1_NAME)
    assert get.call_count == 1
