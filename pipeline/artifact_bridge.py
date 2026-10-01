"""Power Automate actions that require verification of the exact import/export bytes."""
import os
from urllib.parse import urlparse

from pipeline.defs import fail_steps


def verification_action(zip_content, manifest, solution, version, descriptor=None):
    endpoint = os.environ.get("ALM_ARTIFACT_VERIFIER_URL", "")
    if not endpoint:
        return {"type": "Scope", "actions": fail_steps("Artifact_verifier_unconfigured",
                "Artifact verifier is not configured; imports and release archiving are blocked.")}
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("ALM_ARTIFACT_VERIFIER_URL must be an approved HTTPS URL without embedded credentials")
    body = {"zipBase64": zip_content, "manifest": manifest, "solution": solution, "solutionVersion": version}
    if descriptor is not None:
        body["descriptor"] = descriptor
    return {"type": "Http", "inputs": {"method": "POST", "uri": endpoint,
             "headers": {"Authorization": "@parameters('$artifactVerifierAuthorization')",
                         "Content-Type": "application/json"},
             "body": body, "retryPolicy": {"type": "none"}},
            "runtimeConfiguration": {"secureData": {"properties": ["inputs", "outputs"]}}}


def add_authorization_parameter(cd):
    # Never bake authentication values into source, generated definitions or solution exports.
    # Hosting must provide an approved runtime secure-parameter/connection configuration.
    cd["properties"]["definition"]["parameters"]["$artifactVerifierAuthorization"] = {
        "type": "SecureString", "defaultValue": ""}
    return cd
