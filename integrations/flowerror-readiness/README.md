# FlowError readiness checker

Additive offline tooling prepared separately while FlowError's active chat finishes
its scanner and notification changes. This directory does not replace FlowError
source, deployment metadata or acceptance records.

Run against an explicit checkout:

```sh
python3 integrations/flowerror-readiness/tools/check_readiness.py \
  --root /Users/kristoffer/.codex/worktrees/dataverse-failurescan-review/FlowError
python3 -m unittest discover -s integrations/flowerror-readiness/tests -v
```

The checker compares editable flow source, workflow metadata, unpacked solution
definitions and fresh source-hash-bound acceptance evidence. Missing evidence
fails closed. Scanner desired states must come from a passed coverage record;
observed live state alone does not establish the desired release state.

Use `docs/acceptance-evidence.template.json` as a starting point for FlowError's
`docs/acceptance-evidence.json`. Its unknown cases must remain unknown until
controlled runtime evidence exists. Do not copy it over an existing evidence file.

Transfer these additive files into FlowError only after its current work is
reconciled. They make no live calls and cannot qualify runtime behavior themselves.
