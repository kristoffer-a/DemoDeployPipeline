"""Print the Demo solution's state in TEST: solution, variable values, bindings, flow states."""
import json
import urllib.parse

from pipeline import settings as s
from pipeline.flowapi import az_token, get_json

TEST = s.TEST_ORG


def q(tok, path):
    return get_json(f"{TEST}/api/data/v9.2/{urllib.parse.quote(path, safe='/?&=$(),')}", tok)["value"]


def main():
    tok = az_token(TEST)
    print(json.dumps({
        "solution": q(tok, "solutions?$filter=uniquename eq 'Demo'&$select=version,ismanaged,modifiedon"),
        "lastImport": q(tok, "importjobs?$select=solutionname,completedon,progress&$orderby=createdon desc&$top=1"),
        "variables": [{"schemaname": v["EnvironmentVariableDefinitionId"]["schemaname"], "value": v["value"]}
                      for v in q(tok, "environmentvariablevalues?$select=value"
                                      "&$expand=EnvironmentVariableDefinitionId($select=schemaname)")
                      if v["EnvironmentVariableDefinitionId"]["schemaname"].startswith("dev_")],
        "bindings": q(tok, "connectionreferences?$filter=startswith(connectionreferencelogicalname,'dev_')"
                           "&$select=connectionreferencelogicalname,connectionid"),
        "flows": q(tok, "workflows?$filter=category eq 5&$select=name,statecode"),
    }, indent=1))


if __name__ == "__main__":
    main()
