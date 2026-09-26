# Agent instructions (Claude Code and ChatGPT/Codex)

1. Read `README.md`, then `docs/alm/HANDOFF.md`. Do not read `history/` unless the user asks for a specific file.
2. Work on your own branch in your own git worktree. Never commit directly to `main`; merge through a PR or with the user's approval.
3. Tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac` only. Accounts `kriall076@7xpydh.onmicrosoft.com` (default) or `bosso@7xpydh.onmicrosoft.com` (same tenant, same permissions). Stop if anything else appears.
4. Don't touch FlowAdmin* solutions, publisher M365/ms365, solution `Development`, or SharePoint lists Environments / Settings / Flow* in ADMIN (another project).
5. Change flows only through `pipeline/`: tests (`python3 -m pytest pipeline/tests -q`) → `python3 -m pipeline.deploy` → update `docs/alm/diagrams/alm-pipeline.drawio` and its version stamp in the same commit.
6. Keep one current handoff: update `docs/alm/HANDOFF.md` in place; move superseded docs to a dated folder in `history/`.
7. Commit only when the user asks. Never delete tenant resources without the user's yes.
