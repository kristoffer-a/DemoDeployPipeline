"""Explicit, guarded deployment target configuration."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = {"mode", "tenant_id", "allowed_accounts", "environment_id", "organization_url", "site_url",
            "solution", "publisher", "connections", "lists"}
CONNECTIONS = {"dataverse", "sharepoint"}
LISTS = {"config", "connections", "variables"}
_GUID = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
APPROVED_TENANT = "1c5afb69-a82c-4c81-b2cc-743ce7f91dac"
APPROVED_ACCOUNTS = frozenset({"kriall076@7xpydh.onmicrosoft.com", "bosso@7xpydh.onmicrosoft.com"})
ADMIN_ENVIRONMENT = "f2280ea5-6793-e664-8f21-ea3ba6a4cb5c"
ADMIN_ORG = "https://adminorg774eae27.crm17.dynamics.com"
ADMIN_SITE = "https://7xpydh.sharepoint.com/sites/ALM-Admin"
ADMIN_SOLUTION = "ALMPipeline"
ADMIN_PUBLISHER = "almspike"
ADMIN_DV_CONN = "shared-commondataser-88f9738e"
ADMIN_SP_CONN = "shared-sharepointonl-a0f00819"
ADMIN_LISTS = {
    "config": "049eba5a-700e-44db-9d2b-4e95c3af51b6",
    "connections": "bc640935-9503-44de-87d1-699d65c8d351",
    "variables": "1ffc8ca3-1458-423b-81cb-49226b41664f",
}


def load(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read target config {path}: {exc}") from exc
    validate(data)
    return data


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("target config must be a JSON object")
    missing = sorted(REQUIRED - data.keys())
    extra = sorted(data.keys() - REQUIRED)
    if missing or extra:
        raise ValueError(f"target config keys invalid (missing={missing}, extra={extra})")
    if data["mode"] not in ("legacy-admin", "isolated"):
        raise ValueError("mode must be legacy-admin or isolated")
    for key in ("tenant_id", "environment_id"):
        if not isinstance(data[key], str) or not _GUID.fullmatch(data[key]):
            raise ValueError(f"{key} must be a GUID")
    for key in ("organization_url", "site_url"):
        parsed = urlparse(data[key]) if isinstance(data[key], str) else None
        if (not parsed or parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment
                or parsed.username or parsed.password or parsed.port):
            raise ValueError(f"{key} must be an HTTPS base URL")
        if key == 'organization_url' and parsed.path not in ('', '/'):
            raise ValueError('organization_url must be an organization root URL')
    org_host = urlparse(data["organization_url"]).hostname.lower()
    site_host = urlparse(data["site_url"]).hostname.lower()
    if not re.fullmatch(r"[a-z0-9-]+\.crm(?:[0-9]+)?\.dynamics\.com", org_host):
        raise ValueError("organization_url must use a Power Platform Dynamics host")
    if site_host != "7xpydh.sharepoint.com":
        raise ValueError("site_url must use the approved tenant SharePoint host")
    if not isinstance(data["allowed_accounts"], list) or not data["allowed_accounts"] or any(
            not isinstance(x, str) or "@" not in x for x in data["allowed_accounts"]):
        raise ValueError("allowed_accounts must be a non-empty list of account names")
    if data["tenant_id"].lower() != APPROVED_TENANT:
        raise ValueError("target tenant_id must match the approved tenant")
    if not set(data["allowed_accounts"]).issubset(APPROVED_ACCOUNTS):
        raise ValueError("allowed_accounts must be drawn from the approved account allowlist")
    for key in ("solution", "publisher"):
        if not isinstance(data[key], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', data[key]):
            raise ValueError(f"{key} must be a Power Platform unique name")
    for key, required in (("connections", CONNECTIONS), ("lists", LISTS)):
        value = data[key]
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError(f"{key} must contain exactly {sorted(required)}")
        if any(not isinstance(item, str) or not item.strip() for item in value.values()):
            raise ValueError(f"{key} values must be non-empty strings")
        if any(item.lower().startswith(("replace_", "replace-me", "your_")) for item in value.values()):
            raise ValueError(f"{key} contains an unfilled example placeholder")
    if any(not _GUID.fullmatch(item) for item in data["lists"].values()):
        raise ValueError("lists values must be GUIDs")
    if data["mode"] == "legacy-admin":
        expected = {
            "tenant_id": APPROVED_TENANT, "allowed_accounts": sorted(APPROVED_ACCOUNTS),
            "environment_id": ADMIN_ENVIRONMENT, "organization_url": ADMIN_ORG,
            "site_url": ADMIN_SITE, "solution": ADMIN_SOLUTION, "publisher": ADMIN_PUBLISHER,
            "connections": {"dataverse": ADMIN_DV_CONN, "sharepoint": ADMIN_SP_CONN},
            "lists": ADMIN_LISTS,
        }
        if any(data[key] != value for key, value in expected.items()):
            raise ValueError("legacy-admin config must exactly match the baked-in ADMIN target")
    if data["mode"] == "isolated":
        forbidden = ("admin", "prod", "production")
        if any(word in data[k].lower() for k in ("solution", "publisher") for word in forbidden):
            raise ValueError("isolated mode rejects production/ADMIN solution or publisher names")
        org = urlparse(data["organization_url"])
        site = urlparse(data["site_url"])
        if "admin" in org.hostname.lower() or any(x in org.hostname.lower() for x in ("prod", "production")):
            raise ValueError("isolated mode rejects ADMIN organization URL")
        if ("admin" in site.path.lower() or any(x in site.path.lower() for x in ("prod", "production"))
                or any(x in site.hostname.lower() for x in ("admin", "prod", "production"))):
            raise ValueError("isolated mode rejects ADMIN SharePoint site")
        if data["solution"].lower() == "development" or data["solution"].lower().startswith("flowadmin"):
            raise ValueError("isolated mode rejects reserved FlowAdmin*/Development solutions")
        if data["publisher"].lower() in {"m365", "ms365"}:
            raise ValueError("isolated mode rejects reserved M365/ms365 publishers")
        # Tenant/environment values, connector IDs and lists must be target-specific and explicit;
        # an isolated target cannot silently inherit ADMIN constants.
        if data["environment_id"].lower() == ADMIN_ENVIRONMENT:
            raise ValueError("isolated mode cannot reuse the configured ADMIN environment")
        if any(v in {ADMIN_DV_CONN, ADMIN_SP_CONN} for v in data["connections"].values()):
            raise ValueError("isolated mode cannot reuse ADMIN connections")
        if any(v in set(ADMIN_LISTS.values()) for v in data["lists"].values()):
            raise ValueError("isolated mode cannot reuse ADMIN list IDs")
        if len(set(data["connections"].values())) != len(CONNECTIONS) or len(set(data["lists"].values())) != len(LISTS):
            raise ValueError("target connections and list IDs must be unique")


def apply(data, settings):
    """Apply validated target values before flow definitions are built."""
    settings.TENANT = data["tenant_id"]
    settings.ALLOWED_ACCOUNTS = frozenset(data["allowed_accounts"])
    settings.ADMIN_ENV_ID = data["environment_id"]
    settings.ADMIN = data["organization_url"].rstrip("/")
    settings.ADMIN_SITE = data["site_url"].rstrip("/")
    settings.SOLUTION = data["solution"]
    settings.PUBLISHER = data["publisher"]
    settings.DV_CONN = data["connections"]["dataverse"]
    settings.SP_CONN = data["connections"]["sharepoint"]
    suffix = "" if data["mode"] == "legacy-admin" else "_" + re.sub(r"[^a-zA-Z0-9_]", "_", data["solution"])
    dv_logical, sp_logical = "alm_PipelineDataverse" + suffix, "alm_PipelineSharePoint" + suffix
    settings.CONN_REFS = {
        dv_logical: ("ALM Pipeline Dataverse" + suffix, settings.DV_API, settings.DV_CONN),
        sp_logical: ("ALM Pipeline SharePoint" + suffix, settings.SP_API, settings.SP_CONN),
    }
    settings.FLOW_REFS = {
        settings.DV_KEY: (dv_logical, settings.DV_API),
        settings.SP_KEY: (sp_logical, settings.SP_API),
    }
    settings.LIST_CONFIG = data["lists"]["config"]
    settings.LIST_CONNECTIONS = data["lists"]["connections"]
    settings.LIST_VARIABLES = data["lists"]["variables"]
