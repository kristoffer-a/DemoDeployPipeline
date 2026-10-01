import json

import pytest

from pipeline import bootstrap, defs, products_fixture, settings as s


@pytest.fixture
def source_fields():
    # Matches the captured Products schema's relevant shape: Title is the only
    # writable visible custom-facing field; hidden non-base system fields remain.
    return [
        {"InternalName": "Title", "TypeAsString": "Text", "Required": False,
         "Hidden": False, "ReadOnlyField": False, "FromBaseType": True},
        {"InternalName": "ContentType", "TypeAsString": "Computed", "Required": False,
         "Hidden": False, "ReadOnlyField": True, "FromBaseType": True},
        {"InternalName": "Attachments", "TypeAsString": "Attachments", "Required": False,
         "Hidden": False, "ReadOnlyField": False, "FromBaseType": True},
        {"InternalName": "_CommentFlags", "TypeAsString": "Lookup", "Required": False,
         "Hidden": True, "ReadOnlyField": True, "FromBaseType": False},
    ]


@pytest.fixture
def target_config(tmp_path):
    path = tmp_path / "target.json"
    path.write_text(json.dumps({
        "mode": "isolated", "tenant_id": "1c5afb69-a82c-4c81-b2cc-743ce7f91dac",
        "allowed_accounts": ["kriall076@7xpydh.onmicrosoft.com"],
        "environment_id": bootstrap.TEST_ENV_ID, "organization_url": bootstrap.TEST_ORG,
        "site_url": bootstrap.TEST_SITE, "solution": "ALMQualification", "publisher": "almqualification",
        "connections": {"dataverse": bootstrap.TEST_DV_CONN, "sharepoint": bootstrap.TEST_SP_CONN},
    }))
    return path


def _walk(level):
    for name, action in level.items():
        yield name, action
        if isinstance(action.get("actions"), dict):
            yield from _walk(action["actions"])
        branch = action.get("else")
        if isinstance(branch, dict) and isinstance(branch.get("actions"), dict):
            yield from _walk(branch["actions"])


def test_build_is_valid_and_verifies_complete_title_field_readback(source_fields, target_config):
    bootstrap.configure_from_target_config(target_config)
    cd = products_fixture.build(source_fields)
    assert defs.validate(cd) == []
    actions = cd["properties"]["definition"]["actions"]
    assert "Ensure_list_Products" in actions
    assert actions["Readback_Products_fields"]["inputs"]["parameters"]["parameters/uri"].endswith(
        "$select=InternalName,TypeAsString,Required,Hidden,ReadOnlyField,FromBaseType&$top=5000")
    assert "Title" in actions["Find_Products_Title"]["inputs"]["where"]
    checks = actions["Check_Products_schema"]["expression"]["and"]
    assert {"equals": ["@first(body('Find_Products_Title'))?['TypeAsString']", "Text"]} in checks
    assert {"equals": ["@first(body('Find_Products_Title'))?['Required']", False]} in checks
    assert {"equals": ["@length(body('Find_Products_custom_visible_fields'))", 0]} in checks
    assert actions["Results"]["inputs"]["listId"] == "@body('Readback_list_Products')?['Id']"
    assert actions["Results"]["inputs"]["failMessage"] == "@variables('FailMessage')"
    assert actions["Stop_on_failure"]["else"]["actions"]["Terminate_failed"]["inputs"]["runStatus"] == "Failed"
    json.dumps(cd)


def test_schema_rejects_visible_custom_columns_and_invalid_title(source_fields):
    custom = [*source_fields, {"InternalName": "ProductCode", "TypeAsString": "Text", "Required": False,
                               "Hidden": False, "ReadOnlyField": False, "FromBaseType": False}]
    with pytest.raises(ValueError, match="does not migrate custom visible columns"):
        products_fixture._validate_source_fields(custom)
    bad_title = [dict(field, Required=True) if field["InternalName"] == "Title" else field
                 for field in source_fields]
    with pytest.raises(ValueError, match="optional Text Title"):
        products_fixture._validate_source_fields(bad_title)


def test_source_fields_loader_rejects_duplicate_names_and_malformed_json(tmp_path, source_fields):
    malformed = tmp_path / "bad.json"
    malformed.write_text("{")
    with pytest.raises(ValueError, match="cannot read"):
        products_fixture.load_source_fields(malformed)
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps({"value": [*source_fields, dict(source_fields[0])]}))
    with pytest.raises(ValueError, match="duplicate InternalName"):
        products_fixture.load_source_fields(duplicate)


def test_generator_fails_closed_without_isolated_target_and_pins_site(source_fields, monkeypatch):
    monkeypatch.setattr(s, "ADMIN_SITE", "https://7xpydh.sharepoint.com/sites/ALM-Admin")
    with pytest.raises(ValueError, match="apply the isolated test-eu target config"):
        products_fixture.build(source_fields)
    with pytest.raises(ValueError, match="pinned"):
        products_fixture.build(source_fields, "https://7xpydh.sharepoint.com/sites/ALM-Admin")


def test_generator_rejects_admin_connection_reference(source_fields, target_config, monkeypatch):
    bootstrap.configure_from_target_config(target_config)
    monkeypatch.setitem(s.FLOW_REFS, s.SP_KEY, ("alm_PipelineSharePoint", s.SP_API))
    with pytest.raises(ValueError, match="outside the test-eu target"):
        products_fixture.build(source_fields)


def test_generated_flow_only_creates_list_and_never_writes_items(source_fields, target_config, tmp_path):
    bootstrap.configure_from_target_config(target_config)
    cd = products_fixture.build(source_fields)
    actions = cd["properties"]["definition"]["actions"]
    requests = [action for _, action in _walk(actions) if action.get("type") == "OpenApiConnection"]
    methods = [r["inputs"]["parameters"].get("parameters/method") for r in requests]
    assert methods.count("POST") == 1
    assert "PATCH" not in methods and "DELETE" not in methods
    uris = [r["inputs"]["parameters"].get("parameters/uri", "") for r in requests]
    assert all("/items" not in uri for uri in uris)
    assert all("ALMQConnections" not in uri and "ALMQConfig" not in uri for uri in uris)
    output = tmp_path / "flow.json"
    assert products_fixture.write_definition(output, source_fields) == output
    assert json.loads(output.read_text()) == cd


def test_title_adjustment_requires_exact_owned_empty_list_and_no_previous_failure(source_fields, target_config):
    bootstrap.configure_from_target_config(target_config)
    with pytest.raises(ValueError, match='explicitly provisioned'):
        products_fixture.build(source_fields, provisioned_list_id='11111111-1111-4111-8111-111111111111')
    cd = products_fixture.build(source_fields, provisioned_list_id=products_fixture.PROVISIONED_PRODUCTS_LIST_ID)
    a = cd['properties']['definition']['actions']
    guard = a['Check_Products_provisioned_identity']['expression']['and']
    assert {'equals': ["@body('Readback_Products_provisioned_identity')?['ItemCount']", 0]} in guard
    assert {'equals': ["@body('Readback_Products_provisioned_identity')?['Id']",
                       products_fixture.PROVISIONED_PRODUCTS_LIST_ID]} in guard
    check = a['Check_Products_Title_adjustment_preconditions']
    assert {'equals': ["@empty(variables('FailMessage'))", True]} in check['expression']['and']
    write = check['actions']['If_Products_Title_is_required']['actions']['Update_Products_Title_required']
    p = write['inputs']['parameters']
    assert json.loads(p['parameters/body']) == {'__metadata': {'type': 'SP.Field'}, 'Required': False}
    assert p['parameters/headers']['X-HTTP-Method'] == 'MERGE'
    assert all('/items' not in x['inputs']['parameters'].get('parameters/uri','')
               for _,x in _walk(a) if x.get('type') == 'OpenApiConnection')
