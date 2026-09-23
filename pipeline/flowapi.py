"""Tokens (tenant-guarded) and Flow API run-output reads."""
import json
import subprocess
import sys
import urllib.request

from pipeline.settings import ADMIN_ENV_ID, TENANT

FLOW_API = f"https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/{ADMIN_ENV_ID}"


def az_token(resource):
    acct = json.loads(subprocess.check_output(["az", "account", "show", "-o", "json"]))
    if acct["tenantId"] != TENANT:
        sys.exit(f"STOP: az tenant is {acct['tenantId']}, expected {TENANT}")
    return subprocess.check_output(["az", "account", "get-access-token", "--resource", resource,
                                    "--query", "accessToken", "-o", "tsv"], text=True).strip()


def get_json(url, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
        return json.loads(r.read())


def flow_ids():
    """Power Automate flow id by display name, for flows in ADMIN."""
    tok = az_token("https://service.flow.microsoft.com")
    rows = get_json(f"{FLOW_API}/flows?api-version=2016-11-01", tok)["value"]
    return {f["properties"]["displayName"]: f["name"] for f in rows}


def action_outputs(flow, run, action):
    tok = az_token("https://service.flow.microsoft.com")
    meta = get_json(f"{FLOW_API}/flows/{flow}/runs/{run}/actions/{action}?api-version=2016-11-01", tok)
    link = meta["properties"].get("outputsLink")
    return get_json(link["uri"]) if link else {"status": meta["properties"].get("status")}


if __name__ == "__main__":
    print(json.dumps(action_outputs(*sys.argv[1:4]), indent=1))
