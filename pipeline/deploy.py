"""Deploy the pipeline flows into ADMIN as solution-aware cloud flows.

Usage: python3 -m pipeline.deploy [--dry-run]
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from pipeline import settings as s
from pipeline.defs import validate
from pipeline.flowapi import az_token, flow_ids
from pipeline.flows import FLOWS

OUT = Path(__file__).parent / "definitions"


def api(tok, method, path, body=None, solution=None):
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json", "OData-Version": "4.0",
               "Content-Type": "application/json", "Prefer": "return=representation"}
    if solution:
        headers["MSCRM.SolutionUniqueName"] = solution
    path = urllib.parse.quote(path, safe="/?&=$(),'@")
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


def ensure_solution(tok):
    pub = first(tok, f"publishers?$filter=uniquename eq '{s.PUBLISHER}'&$select=publisherid")
    if not pub:
        sys.exit(f"STOP: publisher {s.PUBLISHER} not found in ADMIN")
    if not first(tok, f"solutions?$filter=uniquename eq '{s.SOLUTION}'&$select=solutionid"):
        api(tok, "POST", "solutions", {"uniquename": s.SOLUTION, "friendlyname": "ALM Pipeline", "version": "1.0.0.0",
                                       "publisherid@odata.bind": f"/publishers({pub['publisherid']})"})
        print(f"created solution {s.SOLUTION}")
    for logical, (display, connector, conn) in s.CONN_REFS.items():
        if not first(tok, f"connectionreferences?$filter=connectionreferencelogicalname eq '{logical}'"
                          "&$select=connectionreferenceid"):
            api(tok, "POST", "connectionreferences", {
                "connectionreferencelogicalname": logical, "connectionreferencedisplayname": display,
                "connectorid": connector, "connectionid": conn}, solution=s.SOLUTION)
            print(f"created connection reference {logical} -> {conn}")


def ensure_flow(tok, name, cd):
    existing = first(tok, f"workflows?$filter=name eq '{name}' and category eq 5&$select=workflowid,statecode")
    payload = {"clientdata": json.dumps(cd)}
    if existing:
        wid = existing["workflowid"]
        if existing["statecode"] == 1:  # turning off re-validates the stored definition
            api(tok, "PATCH", f"workflows({wid})", {"statecode": 0, "statuscode": 1})
        api(tok, "PATCH", f"workflows({wid})", payload)
    else:
        payload.update({"name": name, "category": 5, "type": 1, "primaryentity": "none"})
        wid = api(tok, "POST", "workflows", payload, solution=s.SOLUTION)["workflowid"]
    api(tok, "PATCH", f"workflows({wid})", {"statecode": 1, "statuscode": 2})
    return wid


def build(ids):
    OUT.mkdir(exist_ok=True)
    out = {}
    for name, make in FLOWS:
        cd = make(ids)
        errors = validate(cd)
        if errors:
            sys.exit(f"STOP: {name} failed validation:\n  " + "\n  ".join(errors))
        (OUT / (name.split(" - ")[0].replace(" ", "_") + ".json")).write_text(json.dumps(cd, indent=2))
        out[name] = cd
    return out


def main():
    build({})
    print(f"wrote {len(FLOWS)} definitions to {OUT}")
    if "--dry-run" in sys.argv:
        return
    tok = az_token(s.ADMIN)
    ensure_solution(tok)
    ids = {}
    for name, make in FLOWS:  # children first: C1 needs their workflowids
        ids[name] = ensure_flow(tok, name, make(ids))
    build(ids)
    pa = flow_ids()
    for name, wid in ids.items():
        print(f"{name}: workflowid={wid} flow={pa.get(name, '?')}")


if __name__ == "__main__":
    main()
