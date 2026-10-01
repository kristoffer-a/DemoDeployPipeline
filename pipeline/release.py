"""Import the exact locally verified release bytes into an isolated target.

This qualification route is independent of C1/C2. Cloud-flow packages remain
blocked until import-time activation is qualified; no token or write is needed
for the default offline plan.
"""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from pipeline import artifacts, deploy, settings, target
from pipeline.flowapi import az_token


def prepare(zip_path, manifest_path, descriptor_path, solution, version):
    """Read each input once; return the bytes inspected, rather than reopening for import."""
    content = Path(zip_path).read_bytes()
    manifest = artifacts.load_json(manifest_path)
    expected = artifacts.load_json(descriptor_path)
    observed = artifacts.verify_descriptor_bytes(content, manifest, expected, solution, version)
    return content, manifest, observed


def component_parameters(data):
    if not isinstance(data, dict) or set(data) != {"connections", "variables"}:
        raise ValueError("bindings must contain connections and variables arrays")
    result = []
    for collection, fields, entity in (
        ("connections", {"logicalName", "connectionId", "connectorId"}, "connectionreference"),
        ("variables", {"schemaName", "value"}, "environmentvariablevalue"),
    ):
        rows = data[collection]
        if not isinstance(rows, list):
            raise ValueError(f"{collection} must be an array")
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != fields or any(
                    not isinstance(v, str) or not v for v in row.values()):
                raise ValueError(f"invalid {collection} binding")
            name = row["logicalName" if collection == "connections" else "schemaName"]
            if name in seen:
                raise ValueError(f"duplicate {collection} binding: {name}")
            seen.add(name)
            mapped = ({"connectionreferencelogicalname": name,
                       "connectionid": row["connectionId"], "connectorid": row["connectorId"]}
                      if collection == "connections" else {"schemaname": name, "value": row["value"]})
            result.append({"@odata.type": "Microsoft.Dynamics.CRM." + entity, **mapped})
    return result


def cloud_inventory(token, solution, api=deploy.api):
    fetch = ET.Element("fetch", {"distinct": "true", "count": "101", "page": "1"})
    entity = ET.SubElement(fetch, "entity", {"name": "workflow"})
    ET.SubElement(entity, "attribute", {"name": "workflowid"})
    filters = ET.SubElement(entity, "filter")
    for attr, value in (("category", "5"), ("type", "1")):
        ET.SubElement(filters, "condition", {"attribute": attr, "operator": "eq", "value": value})
    link = ET.SubElement(entity, "link-entity", {
        "name": "solutioncomponent", "from": "objectid", "to": "workflowid"})
    link = ET.SubElement(link, "link-entity", {"name": "solution", "from": "solutionid", "to": "solutionid"})
    filters = ET.SubElement(link, "filter")
    ET.SubElement(filters, "condition", {"attribute": "uniquename", "operator": "eq", "value": solution})
    rows = api(token, "GET", "workflows", query={"fetchXml": ET.tostring(fetch, encoding="unicode")})
    if (rows.get("@odata.nextLink") or rows.get("@Microsoft.Dynamics.CRM.morerecords")
            or rows.get("@Microsoft.Dynamics.CRM.fetchxmlpagingcookie") or len(rows["value"]) > 100):
        raise ValueError("target cloud-flow inventory is incomplete")
    return rows["value"]


def import_verified(content, manifest, descriptor, config, bindings, *, api=deploy.api, sleep=time.sleep,
                    token_provider=az_token, timeout=1800):
    """Fail before writes for unqualified cloud-flow packages or target upgrades."""
    artifacts.verify_descriptor_bytes(content, manifest, descriptor, descriptor["solution"], descriptor["solutionVersion"])
    target.validate(config)
    if config["mode"] != "isolated":
        raise ValueError("verified import currently supports isolated qualification targets only")
    if descriptor["cloudFlowIds"]:
        raise ValueError("cloud-flow import activation is not qualified; import remains blocked")
    parameters = component_parameters(bindings)
    target.apply(config, settings)
    token = token_provider(settings.ADMIN)
    call = api
    inventory = cloud_inventory(token, descriptor["solution"], api=call)
    if inventory:
        raise ValueError("target solution contains cloud flows; import remains blocked")
    response = call(token, "POST", "ImportSolutionAsync", {
        "CustomizationFile": base64.b64encode(content).decode("ascii"),
        "OverwriteUnmanagedCustomizations": False, "PublishWorkflows": False,
        "ComponentParameters": parameters,
    })
    job = response["AsyncOperationId"]
    deadline = time.monotonic() + timeout
    while True:
        status = call(token, "GET", f"asyncoperations({job})?$select=statecode,statuscode,message,friendlymessage")
        if status["statecode"] == 3:
            if status["statuscode"] != 30:
                raise RuntimeError(f"import job {job} failed: " + str(status.get("friendlymessage") or status.get("message")))
            break
        if time.monotonic() >= deadline:
            raise TimeoutError(f"import job {job} still pending; inspect it before retrying")
        sleep(10)
    name, version = descriptor["solution"], descriptor["solutionVersion"]
    installed = call(token, "GET", "solutions", query={
        "$filter": f"uniquename eq '{name}'", "$select": "uniquename,version,ismanaged"})["value"]
    if len(installed) != 1 or installed[0]["version"] != version or installed[0]["ismanaged"] is not True:
        raise RuntimeError("import completed but installed solution identity/version/managed state did not match")
    return {"status": "Succeeded", "asyncOperationId": job, "importJobKey": response.get("ImportJobKey"),
            "artifact": descriptor, "targetEnvironment": config["environment_id"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("zip", "manifest", "descriptor", "solution", "version", "target-config", "bindings"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--exclusive-window", action="store_true",
                        help="operator has excluded other deployments and target-state edits")
    parser.add_argument("--log", help="required durable result log when applying")
    args = parser.parse_args()
    record = {"startedAt": datetime.now(timezone.utc).isoformat(), "status": "Planned"}
    try:
        content, manifest, descriptor = prepare(args.zip, args.manifest, args.descriptor, args.solution, args.version)
        config = target.load(args.target_config)
        bindings = artifacts.load_json(args.bindings)
        component_parameters(bindings)
        record.update({"artifact": descriptor, "targetEnvironment": config["environment_id"]})
        if args.apply:
            if not args.exclusive_window or not args.log:
                raise ValueError("--apply requires --exclusive-window and --log; exclude concurrent deployment first")
            record.update(import_verified(content, manifest, descriptor, config, bindings))
        print(json.dumps(record, indent=2))
    except (ValueError, RuntimeError, TimeoutError, OSError, KeyError, SystemExit) as exc:
        record.update({"status": "Failed", "error": str(exc)})
        raise SystemExit("STOP: " + str(exc)) from exc
    finally:
        if args.apply and args.log:
            record["finishedAt"] = datetime.now(timezone.utc).isoformat()
            artifacts._write_json_atomic(Path(args.log), record)


if __name__ == "__main__":
    main()
