# AdminEnv ALM continuation

Start with [`docs/alm/HANDOFF.md`](docs/alm/HANDOFF.md). It is the authoritative checkpoint.

## Security boundary

- Use only `bosso@7xpydh.onmicrosoft.com` in tenant `1c5afb69-a82c-4c81-b2cc-743ce7f91dac`.
- Stop immediately if any other account or tenant appears.
- Do not copy Azure, MSAL, browser, PAC, connection, or token caches between machines.
- Authenticate fresh on the destination machine and keep caches outside this repository.

## Destination-machine bootstrap

1. Clone the repository and install the pinned Power Platform skill bundle revision recorded in `docs/alm/skills-source-revision.txt` under `.tooling/`.
2. Copy `.codex/config.example.toml` to `.codex/config.toml` and replace `<PROJECT_ROOT>` without changing the approved account, tenant, or environment IDs.
3. Authenticate the isolated Azure and FlowAgent MSAL profiles as `bosso@7xpydh.onmicrosoft.com` only.
4. Run `node --test docs/alm/flowagent-auth-policy.test.mjs` before any tenant call.
5. Resume only from the **First action after resume** section in `docs/alm/HANDOFF.md`.

`.tooling/`, browser state, and credential material are intentionally excluded from Git.
