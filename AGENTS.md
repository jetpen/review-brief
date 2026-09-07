# Agent Instructions

## Execution approvals

For this repository, the user has authorized automatic approval for:

- all Python heredoc executions;
- all `gh` CLI commands.

Apply this authorization in every session working in this repository. It does not authorize unrelated commands or broaden approval for other repositories.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository using root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.
