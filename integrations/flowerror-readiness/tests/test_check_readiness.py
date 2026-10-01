import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "check_readiness.py"
spec = importlib.util.spec_from_file_location("check_readiness", TOOL)
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class AcceptanceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "flows").mkdir()
        (self.root / "docs").mkdir()
        for name in readiness.SOURCE_FLOWS:
            (self.root / "flows" / f"{name}.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def records(self):
        hashes = readiness.source_hashes(self.root)
        now = datetime.now(timezone.utc).isoformat()
        records = {case: {
            "result": "passed", "source_hashes": hashes, "environment": "ADMIN-test",
            "executed_at": now, "owner": "tester", "run_ids": ["run-1"],
            "evidence_links": ["evidence-ref"]
        } for case in readiness.REQUIRED_ACCEPTANCE}
        records["coverage-and-heartbeat-routing"]["desired_scanner_states"] = {
            "MON-FailureScan": 0, "MON-FailureScan-Dataverse": 1
        }
        return records

    def write_manifest(self, states=None):
        states = states or {"MON-FailureScan": 0, "MON-FailureScan-Dataverse": 1}
        manifest = {}
        for index, name in enumerate(sorted(readiness.SOURCE_FLOWS)):
            manifest[name] = {
                "workflowid": f"00000000-0000-0000-0000-{index + 1:012d}",
                "statecode": states.get(name, 1), "solution": "FlowAdminMonitoring"
            }
        (self.root / "flows" / "_workflow-ids.json").write_text(json.dumps(manifest), encoding="utf-8")
        return manifest

    def check(self, cases):
        (self.root / "docs" / "acceptance-evidence.json").write_text(
            json.dumps({"cases": cases}), encoding="utf-8")
        errors, warnings = [], []
        readiness.check_acceptance(self.root, errors, warnings, 30)
        return errors

    def test_absent_evidence_does_not_certify_acceptance(self):
        errors, warnings = [], []
        readiness.check_acceptance(self.root, errors, warnings, 30)
        self.assertTrue(any("live acceptance is unknown" in e for e in errors))

    def test_matching_fresh_records_satisfy_acceptance_gate(self):
        self.assertEqual([], self.check(self.records()))

    def test_stale_source_hash_and_unpassed_case_are_rejected(self):
        cases = self.records()
        cases["replay-60"]["source_hashes"] = {}
        cases["overlong-run-id"]["result"] = "unknown"
        errors = self.check(cases)
        self.assertTrue(any("replay-60" in e and "hashes" in e for e in errors))
        self.assertTrue(any("overlong-run-id" in e and "expected passed" in e for e in errors))

    def test_missing_source_is_reported_without_hashing_crash(self):
        (self.root / "flows" / "MON-HandleIncident.json").unlink()
        self.assertNotIn("MON-HandleIncident", readiness.source_hashes(self.root))
        errors = []
        readiness.check_cloud_sources(self.root, errors)
        self.assertTrue(any("MON-HandleIncident" in e and "missing" in e for e in errors))

    def test_malformed_evidence_is_reported_without_crashing(self):
        (self.root / "docs" / "acceptance-evidence.json").write_text("{broken", encoding="utf-8")
        errors, warnings = [], []
        readiness.check_acceptance(self.root, errors, warnings, 30)
        readiness.check_manifest(self.root, errors, warnings)
        self.assertTrue(any("cannot read valid JSON" in e for e in errors))

    def test_undeclared_host_connection_name_is_rejected(self):
        for name in readiness.SOURCE_FLOWS:
            flow = {"properties": {"connectionReferences": {}, "definition": {"actions": {}}}}
            (self.root / "flows" / f"{name}.json").write_text(json.dumps(flow), encoding="utf-8")
        target = self.root / "flows" / "MON-FailureScan.json"
        flow = json.loads(target.read_text())
        flow["properties"]["definition"]["actions"] = {
            "Call": {"inputs": {"host": {"connectionName": "undeclared_ref"}}}
        }
        target.write_text(json.dumps(flow), encoding="utf-8")
        errors = []
        readiness.check_cloud_sources(self.root, errors)
        self.assertTrue(any("host.connectionName" in e and "undeclared_ref" in e for e in errors))

    def test_export_lookup_uses_manifest_workflowid_and_detects_changed_export(self):
        name = "MON-FailureScan"
        workflowid = "aabbccdd-1122-3344-5566-77889900aabb"
        manifest = {name: {"workflowid": workflowid, "solution": "FlowAdminMonitoring"}}
        (self.root / "flows" / "_workflow-ids.json").write_text(json.dumps(manifest), encoding="utf-8")
        source = {"properties": {"definition": {"actions": {"A": {"type": "Compose"}}, "triggers": {}}, "connectionReferences": {}}}
        (self.root / "flows" / f"{name}.json").write_text(json.dumps(source), encoding="utf-8")
        export_dir = self.root / "solution" / "FlowAdminMonitoring" / "Workflows"
        export_dir.mkdir(parents=True)
        # Export display names can differ; stable workflow GUID suffix locates the component.
        (export_dir / "LocalizedDisplayName-AABBCCDD11223344556677889900AABB.json").write_text(json.dumps(source), encoding="utf-8")
        errors = []
        readiness.compare_exports(self.root, errors)
        self.assertFalse(any("MON-FailureScan:" in e and "differs" in e for e in errors))
        changed = json.loads((export_dir / "LocalizedDisplayName-AABBCCDD11223344556677889900AABB.json").read_text())
        changed["properties"]["definition"]["actions"]["A"]["type"] = "Different"
        (export_dir / "LocalizedDisplayName-AABBCCDD11223344556677889900AABB.json").write_text(json.dumps(changed), encoding="utf-8")
        errors = []
        readiness.compare_exports(self.root, errors)
        self.assertTrue(any("MON-FailureScan" in e and "definition" in e for e in errors))

    def test_manifest_scanner_states_follow_hash_bound_coverage_record(self):
        manifest = self.write_manifest({"MON-FailureScan": 1, "MON-FailureScan-Dataverse": 0})
        cases = self.records()
        cases["coverage-and-heartbeat-routing"]["desired_scanner_states"] = {
            "MON-FailureScan": 0, "MON-FailureScan-Dataverse": 1
        }
        (self.root / "docs" / "acceptance-evidence.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
        errors, warnings = [], []
        readiness.check_manifest(self.root, errors, warnings)
        self.assertTrue(any("manifest state mismatch" in e and "MON-FailureScan" in e for e in errors))
        self.assertTrue(any("manifest state mismatch" in e and "MON-FailureScan-Dataverse" in e for e in errors))

    def test_malformed_manifest_entry_is_reported_without_crashing(self):
        (self.root / 'flows' / '_workflow-ids.json').write_text(json.dumps({'MON-FailureScan': 'bad'}))
        errors, warnings = [], []
        readiness.check_manifest(self.root, errors, warnings)
        self.assertTrue(any('must be an object' in e for e in errors))

    def test_duplicate_keys_and_invalid_encoding_are_rejected(self):
        p = self.root / 'docs' / 'acceptance-evidence.json'
        p.write_text('{"cases":{},"cases":{}}')
        errors = []
        self.assertIsNone(readiness.safe_load(p, 'evidence', errors))
        self.assertTrue(any('duplicate JSON key' in e for e in errors))
        p.write_bytes(b'\xff')
        self.assertIsNone(readiness.safe_load(p, 'evidence', []))


if __name__ == "__main__":
    unittest.main()
