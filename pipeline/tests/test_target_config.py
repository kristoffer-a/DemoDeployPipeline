import copy
import json

import pytest

from pipeline import settings, target


@pytest.fixture
def isolated_target():
    return {
        "mode": "isolated",
        "tenant_id": settings.TENANT,
        "allowed_accounts": ["kriall076@7xpydh.onmicrosoft.com"],
        "environment_id": "33333333-3333-4333-8333-333333333333",
        "organization_url": "https://target.crm.dynamics.com",
        "site_url": "https://7xpydh.sharepoint.com/sites/ALM-Isolated",
        "solution": "ALMPipelineIsolated",
        "publisher": "almsandbox",
        "connections": {"dataverse": "dv-target", "sharepoint": "sp-target"},
        "lists": {"config": "44444444-4444-4444-8444-444444444444",
                  "connections": "55555555-5555-4555-8555-555555555555",
                  "variables": "66666666-6666-4666-8666-666666666666"},
    }


def test_rejects_missing_or_extra_keys(isolated_target):
    malformed = copy.deepcopy(isolated_target)
    del malformed["lists"]
    with pytest.raises(ValueError, match="keys invalid"):
        target.validate(malformed)


def test_rejects_unfilled_example_placeholders(isolated_target):
    candidate = copy.deepcopy(isolated_target)
    candidate["connections"]["dataverse"] = "replace-me-dataverse-id"
    with pytest.raises(ValueError, match="placeholder"):
        target.validate(candidate)
    malformed = {**isolated_target, "unexpected": True}
    with pytest.raises(ValueError, match="keys invalid"):
        target.validate(malformed)


@pytest.mark.parametrize("field,value", [
    ("environment_id", settings.ADMIN_ENV_ID),
    ("organization_url", settings.ADMIN),
    ("site_url", settings.ADMIN_SITE),
    ("solution", "ALMProduction"),
    ("publisher", "adminPublisher"),
    ("publisher", "M365"),
    ("solution", "FlowAdmin-Monitoring"),
    ("solution", "Development"),
])
def test_isolated_rejects_admin_or_production_reuse(isolated_target, field, value):
    candidate = copy.deepcopy(isolated_target)
    candidate[field] = value
    with pytest.raises(ValueError):
        target.validate(candidate)


@pytest.mark.parametrize('field,value', [
    ('solution', "Example' or uniquename eq 'Development"),
    ('publisher', "Example' or uniquename eq 'M365"),
    ('organization_url', 'https://user:password@target.crm.dynamics.com'),
    ('organization_url', 'https://target.crm.dynamics.com/api/data'),
])
def test_profile_rejects_query_injection_and_non_root_organization_urls(isolated_target, field, value):
    candidate = copy.deepcopy(isolated_target)
    candidate[field] = value
    with pytest.raises(ValueError):
        target.validate(candidate)


def test_isolated_rejects_reused_connection_and_list_ids(isolated_target):
    candidate = copy.deepcopy(isolated_target)
    candidate["connections"]["dataverse"] = target.ADMIN_DV_CONN
    with pytest.raises(ValueError, match="ADMIN connections"):
        target.validate(candidate)
    candidate = copy.deepcopy(isolated_target)
    candidate["lists"]["config"] = target.ADMIN_LISTS["config"]
    with pytest.raises(ValueError, match="ADMIN list IDs"):
        target.validate(candidate)


def test_apply_updates_settings_before_definition_build(isolated_target):
    class Settings:
        TENANT = "old"
        ALLOWED_ACCOUNTS = frozenset()
        ADMIN_ENV_ID = "old"
        ADMIN = "old"
        ADMIN_SITE = "old"
        SOLUTION = "old"
        PUBLISHER = "old"
        DV_API, SP_API = "/dv", "/sp"
        DV_KEY, SP_KEY = "dvkey", "spkey"

    s = Settings()
    target.apply(isolated_target, s)
    assert (s.TENANT, s.ADMIN_ENV_ID, s.ADMIN, s.ADMIN_SITE) == (
        isolated_target["tenant_id"], isolated_target["environment_id"],
        isolated_target["organization_url"], isolated_target["site_url"])
    assert next(value for key, value in s.CONN_REFS.items() if key.startswith("alm_PipelineDataverse"))[2] == "dv-target"
    assert s.LIST_VARIABLES == isolated_target["lists"]["variables"]


def test_load_reports_malformed_json(tmp_path):
    path = tmp_path / "target.json"
    path.write_text("{")
    with pytest.raises(ValueError, match="cannot read target config"):
        target.load(path)
