# Isolated qualification — October 1, 2026

The candidate is deployed only in TEST `8fcc484b-d74e-e479-84da-ad5a78d6d55b`,
under `ALMQualification` 1.1.0.0. Fixtures use the separate
`ALMQualificationFixtures` solution. ADMIN C1/C2/C3 definitions remain on their
existing release. Diagrams were excluded and were not changed by this work.

## Observed results

| Check | Observed result |
|---|---|
| Independent bootstrap | Three dedicated lists and 17 fields read back successfully; fixture imports off; run `08584107844816500037764567859CU01` |
| Missing, malformed, duplicate, foreign, incomplete policies | Structured C3 failure; negative coverage cases preserved helper off, legacy on, child/parent off |
| Valid policy | Legacy disabled first, helper untouched, child enabled before parent; four states verified; C3 run `08584107778047163346153146597cU14` |
| Unchanged policy | All two disable and two enable write repetitions skipped; run `08584107777420798493842865304CU27` |
| Enable connector failure | Fault clone's first write returned NotFound, second write skipped; child/parent remained off; run `08584107774056735602335545591CU08` |
| Final readback mismatch | Explicit fault clone returned failure instead of reporting success; harness `08584107772065835208770642835CU17` |
| C1 configuration-only | Fixed-input clone skipped export/import, called C3, and wrote the reconciliation log; run `08584107763340532984387476585CU23` |
| C1 invalid policy | Failed with a recorded log; all subsequent stages skipped; run `08584107761021258907649152855CU22` |
| C2 direct cloud import | Structured rejection before ZIP access/import; harness `08584107759509566157103010392CU18` |
| Products provisioning | TEST list `9ca71bdc-8192-4321-85ce-f29ac9d3a7d8`; schema matches DEV's optional Text Title and no visible custom columns |
| Demo baseline | Stored mapping and TEST environment value use that Products ID; `RunImport=false`; ADMIN direct C2 stopped; setup definition and original stopped state restored |

The valid policy was rerun after failure injection to restore child and parent to
their intended enabled states. Completed test harnesses and fault helpers are
stopped. TEST parent/import entry points are stopped; normal C3 remains available.
Nothing was deleted. No solution ZIP import was executed.

Evidence files are in [evidence/2026-10-01](evidence/2026-10-01/scope.json).
They contain run IDs, replies, state/readback records and the generated C3 source
hash, rather than signed output URLs or authentication material. Harness runs can
report Succeeded while C3 returns a Failed response; acceptance checks inspected
the child response, child run and state evidence.

## Runtime findings and corrections

Power Automate rejected regex properties in connector-backed Parse JSON schemas.
Generated runtime schemas now omit those properties; canonical artifact schemas
remain strict. Actual inventory coverage still enforces runtime flow IDs.

SharePoint direct missing-field lookup returned 400. Field provisioning now uses
a complete successful collection query, creates only after an empty result, and
rejects authorization errors, pagination, duplicates and type mismatches. URL
field creation uses `SP.FieldUrlValue` objects. TEST Products defaulted to a
required Title; a guarded adjustment was limited to the exact empty list created
by this qualification. It did not copy records or implement general C5 metadata
migration.

The guarded ADMIN mapping update initially failed without writes because a
nometadata read omitted its ETag. Minimal-metadata reads supplied ETags for the
successful conditional update, run `08584107769506040605031293603CU30`.

## Remaining acceptance boundaries

- User chose a local verifier and disabled imports. Approved hosting, runtime
  authentication, trusted descriptor storage and end-to-end ZIP/sidecar/import
  qualification remain prerequisites for enabling one-click imports.
- Cloud-flow fresh/update import activation remains unqualified and blocked.
- C3 fixture reconciliation used zero environment variables. C1 orchestration and
  logging used a fixed-input clone; actual button input binding and release
  archival remain outside these runs.
- The final-readback failure used a deliberate clone, not an actual concurrent
  editor. Concurrency exclusion remains an operator prerequisite.
- A fresh Playwright session reached Microsoft sign-in for Demo Products. Target
  user/browser acceptance requires interactive sign-in; connector and variable
  checks do not establish successful app use.
- FlowError is now clean on local main `08798c7`. Fresh root checks confirm 48
  regressions and 15 static flow checks. Source/export comparison of the six
  critical flows passes. Its acceptance record still excludes a 901-child load
  test and non-Dataverse Poll connector coverage. Additive operational-readiness
  tooling remains separate; missing typed evidence must not be marked passed.
- Source review/PR merge and module install/upgrade/migration
  qualification remain outstanding. Existing diagram work remains out of scope.

## Final source checks

208 pipeline tests, 10 additive readiness tests, and four authentication-policy
tests pass. Dry-run generation succeeds; whitespace checks pass. FlowError's
48 tests and all 15 static checks were rerun from its clean local main. Remote
CI was not executed during the local qualification phase; the source PR runs
the offline validation workflow. No source branch merge was performed during
qualification.
