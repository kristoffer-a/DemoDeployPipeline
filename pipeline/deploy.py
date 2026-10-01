"""Deploy pipeline flows to an explicitly configured, isolated target.

Usage: python3 -m pipeline.deploy [--dry-run] [--target-config PATH]
                                   [--solution-version N.N.N.N]
"""
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline import settings as s
from pipeline.defs import validate
from pipeline.flowapi import az_token, flow_api, flow_ids, get_json
from pipeline.flows import FLOWS
from pipeline import target as target_config

OUT = Path(__file__).parent / "definitions"


def api(tok, method, path, body=None, solution=None, query=None):
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json", "OData-Version": "4.0",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    if solution:
        headers["MSCRM.SolutionUniqueName"] = solution
    path = urllib.parse.quote(path, safe="/?&=$(),'@")
    if query:
        path += "?" + urllib.parse.urlencode(query, quote_via=urllib.parse.quote)
    req = urllib.request.Request(f"{s.ADMIN}/api/data/v9.2/{path}", method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code}: {e.read().decode()[:800]}")


def first(tok, path):
    rows = api(tok, "GET", path)["value"]
    return rows[0] if rows else None


def ensure_solution(tok, version="1.0.0.0"):
    pub = first(tok, f"publishers?$filter=uniquename eq '{s.PUBLISHER}'&$select=publisherid")
    if not pub:
        sys.exit(f"STOP: publisher {s.PUBLISHER} not found in ADMIN")
    if not first(tok, f"solutions?$filter=uniquename eq '{s.SOLUTION}'&$select=solutionid"):
        api(tok, "POST", "solutions", {"uniquename": s.SOLUTION, "friendlyname": "ALM Pipeline", "version": version,
                                       "publisherid@odata.bind": f"/publishers({pub['publisherid']})"})
        print(f"created solution {s.SOLUTION}")
    for logical, (display, connector, conn) in s.CONN_REFS.items():
        if not first(tok, f"connectionreferences?$filter=connectionreferencelogicalname eq '{logical}'"
                          "&$select=connectionreferenceid"):
            api(tok, "POST", "connectionreferences", {
                "connectionreferencelogicalname": logical, "connectionreferencedisplayname": display,
                "connectorid": connector, "connectionid": conn}, solution=s.SOLUTION)
            print(f"created connection reference {logical} -> {conn}")


def find_solution_flow(tok, name):
    """Only definition-type cloud flows in ALMPipeline; never choose an arbitrary duplicate."""
    fetch = ET.Element("fetch", {"distinct": "true", "top": "2"})
    entity = ET.SubElement(fetch, "entity", {"name": "workflow"})
    for attr in ("workflowid", "statecode"):
        ET.SubElement(entity, "attribute", {"name": attr})
    filters = ET.SubElement(entity, "filter")
    for attr, value in (("name", name), ("category", "5"), ("type", "1")):
        ET.SubElement(filters, "condition", {"attribute": attr, "operator": "eq", "value": value})
    component = ET.SubElement(entity, "link-entity", {
        "name": "solutioncomponent", "from": "objectid", "to": "workflowid", "link-type": "inner"})
    solution = ET.SubElement(component, "link-entity", {
        "name": "solution", "from": "solutionid", "to": "solutionid", "link-type": "inner"})
    filt = ET.SubElement(solution, "filter")
    ET.SubElement(filt, "condition", {"attribute": "uniquename", "operator": "eq", "value": s.SOLUTION})
    rows = api(tok, "GET", "workflows", query={"fetchXml": ET.tostring(fetch, encoding="unicode")})["value"]
    if len(rows) > 1:
        sys.exit(f"STOP: multiple flows named {name!r} in solution {s.SOLUTION}")
    return rows[0] if rows else None


def ensure_flow(tok, name, cd, activate=True):
    existing = find_solution_flow(tok, name)
    payload = {"clientdata": json.dumps(cd)}
    if existing:
        wid = existing["workflowid"]
        if existing["statecode"] == 1:  # turning off re-validates the stored definition
            api(tok, "PATCH", f"workflows({wid})", {"statecode": 0, "statuscode": 1}, solution=s.SOLUTION)
        api(tok, "PATCH", f"workflows({wid})", payload, solution=s.SOLUTION)
    else:
        payload.update({"name": name, "category": 5, "type": 1, "primaryentity": "none"})
        wid = api(tok, "POST", "workflows", payload, solution=s.SOLUTION)["workflowid"]
    if activate:
        api(tok, "PATCH", f"workflows({wid})", {"statecode": 1, "statuscode": 2}, solution=s.SOLUTION)
    return wid


def build(ids, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, make in FLOWS:
        cd = make(ids)
        errors = validate(cd)
        if errors:
            sys.exit(f"STOP: {name} failed validation:\n  " + "\n  ".join(errors))
        (out_dir / (name.split(" - ")[0].replace(" ", "_") + ".json")).write_text(json.dumps(cd, indent=2))
        out[name] = cd
    return out


def require_parent_quiescent(name, required=False):
    """Stop rollout when any run of the target parent is still active."""
    flow_tok = az_token("https://service.flow.microsoft.com")
    root = flow_api()
    base = f"{root}/flows"

    def pages(url):
        result = []
        visited = set()
        while url:
            if url in visited or len(visited) >= 1000:
                sys.exit("STOP: Flow API pagination repeated or exceeded its safety limit")
            visited.add(url)
            parsed = urllib.parse.urlsplit(url)
            allowed = urllib.parse.urlsplit(base)
            if (parsed.scheme != "https" or parsed.netloc != allowed.netloc
                    or not (parsed.path == allowed.path or parsed.path.startswith(allowed.path + "/"))):
                sys.exit("STOP: Flow API returned a pagination URL outside the configured environment")
            page = get_json(url, flow_tok)
            if not isinstance(page, dict) or not isinstance(page.get("value"), list):
                sys.exit("STOP: Flow API returned a malformed inventory or run-history page")
            result.extend(page["value"])
            next_url = page.get("nextLink")
            url = urllib.parse.urljoin(url, next_url) if next_url else None
        return result

    rows = pages(f"{base}?api-version=2016-11-01")
    if any(not isinstance(row, dict) for row in rows):
        sys.exit("STOP: Flow API returned a malformed flow inventory")
    matches = [row for row in rows if row.get("properties", {}).get("displayName") == name]
    if len(matches) > 1:
        sys.exit(f"STOP: multiple Power Automate flows named {name!r}; cannot prove parent is quiescent")
    if not matches:
        if required:
            sys.exit("STOP: existing parent is absent from Flow API; cannot prove it is quiescent")
        return
    flow = matches[0]["name"]
    url = f"{base}/{urllib.parse.quote(flow, safe='')}/runs?api-version=2016-11-01&$top=50"
    runs = pages(url)
    active = []
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("properties"), dict):
            sys.exit("STOP: Flow API returned malformed parent run history")
        status = run["properties"].get("status", "Unknown")
        if status not in {"Succeeded", "Failed", "Cancelled", "Canceled", "TimedOut", "Aborted", "Skipped"}:
            active.append((run.get("name", "?"), status))
    if active:
        sample = ", ".join(f"{run_id}:{status}" for run_id, status in active[:5])
        sys.exit(f"STOP: parent has active runs ({sample}); wait for completion and rerun")


def set_solution_version(tok, version):
    solution = first(tok, f"solutions?$filter=uniquename eq '{s.SOLUTION}'&$select=solutionid")
    if not solution:
        sys.exit(f"STOP: solution {s.SOLUTION} disappeared before version update")
    api(tok, "PATCH", f"solutions({solution['solutionid']})", {"version": version})


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    config_path = None
    version = "1.1.0.0"
    if "--target-config" in args:
        pos = args.index("--target-config")
        if pos + 1 >= len(args) or args[pos + 1].startswith("--"):
            sys.exit("STOP: --target-config requires a path")
        config_path = args[pos + 1]
    if "--solution-version" in args:
        pos = args.index("--solution-version")
        if pos + 1 >= len(args):
            sys.exit("STOP: --solution-version requires a value")
        version = args[pos + 1]
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        sys.exit("STOP: --solution-version must have four numeric components")
    allowed_args = {"--dry-run", "--target-config", "--solution-version"}
    values = {config_path, version}
    if any(arg not in allowed_args and arg not in values for arg in args):
        sys.exit("STOP: unknown deployment argument")
    if config_path:
        try:
            target_data = target_config.load(config_path)
            target_config.apply(target_data, s)
        except ValueError as exc:
            sys.exit(f"STOP: {exc}")
    else:
        target_data = None
    # Validate and retain target-bound definitions in a temporary directory. ADMIN snapshots
    # stay historical evidence and are never overwritten by a candidate deployment.
    target_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", s.SOLUTION)
    out_dir = Path(tempfile.mkdtemp(prefix=f"alm-defs-{target_slug}-"))
    build({}, out_dir)
    print(f"wrote {len(FLOWS)} definitions to {out_dir}")
    if dry_run:
        return
    if not target_data or target_data["mode"] != "isolated":
        sys.exit("STOP: live deployment requires an explicitly configured isolated target; "
                 "the baked-in ADMIN target is available for dry-run only until qualification")
    tok = az_token(s.ADMIN)
    ensure_solution(tok, version)
    ids = {}
    # Pause the parent before replacing either child. This prevents a running parent
    # definition from invoking newly changed child contracts. On any failure it stays off.
    parent = find_solution_flow(tok, s.C1_NAME)
    parent_was_active = bool(parent and parent.get("statecode") == 1)
    if parent_was_active:
        api(tok, "PATCH", f"workflows({parent['workflowid']})", {"statecode": 0, "statuscode": 1},
            solution=s.SOLUTION)
    try:
        require_parent_quiescent(s.C1_NAME, required=bool(parent))
        for name, make in FLOWS:
            if name == s.C1_NAME:
                continue
            ids[name] = ensure_flow(tok, name, make(ids))
        # Build parent against the newly resolved child workflow IDs, but keep it inactive
        # until every update has succeeded.
        parent_factory = next(factory for flow_name, factory in FLOWS if flow_name == s.C1_NAME)
        ids[s.C1_NAME] = ensure_flow(tok, s.C1_NAME, parent_factory(ids), activate=False)
    except BaseException as exc:
        raise SystemExit(f"STOP: rollout incomplete; parent {s.C1_NAME!r} remains disabled. "
                         f"Repair the reported flow error, inspect child state, then rerun explicitly. {exc}")
    build(ids, out_dir)
    set_solution_version(tok, version)
    api(tok, "PATCH", f"workflows({ids[s.C1_NAME]})", {"statecode": 1, "statuscode": 2}, solution=s.SOLUTION)
    pa = flow_ids()
    for name, wid in ids.items():
        print(f"{name}: workflowid={wid} flow={pa.get(name, '?')}")


if __name__ == "__main__":
    main()
