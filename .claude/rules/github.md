---
paths:
  - ".github/**"
  - "SECURITY.md"
  - "tests/test_ci_workflows.py"
---

# GitHub: Actions and security settings

## Actions budget (rule 12)

Minutes are shared with the owner's private repositories, so this repository adds as little load as possible.

- Verify locally first (tests, ruff). CI is a safety net, not the place to experiment.
- Trigger only on pushes to `main` and on pull requests. Skip docs-only changes (`paths-ignore: ['**.md', 'docs/**']`).
- No `schedule`, no matrix builds unless a task needs them.
- Every workflow sets `concurrency` with `cancel-in-progress: true` and `timeout-minutes` (≤ 10), caches uv, pins actions to commit SHAs and has `permissions: contents: read`.
- Standard GitHub-hosted runners are free for public repositories. Keep the habits anyway: they protect the private repositories that share the quota.
- The only workflow is `ci.yml`: one `windows-latest` job running `uv sync`, `ruff check`, `ruff format --check` and `pytest`, with a pruned uv cache that only pushes to `main` save.
- Pins look like `uses: owner/repo@<full sha> # vX.Y.Z`. `/update-deps` refreshes them; the SessionStart hook reports outdated ones.
- `tests/test_ci_workflows.py` enforces these rules for every workflow file. It also rejects `${{ }}` expressions outside an allowlist, self-hosted runners, `continue-on-error`, `if:` conditions, secrets and unusual YAML spellings.

## Repository security settings (rule 4)

Claude Code's permission check refuses changes to these settings, so the owner applies them. You only check them.

| Setting | Check | Expected |
| --- | --- | --- |
| Dependabot alerts, secret scanning, push protection | `gh api repos/cholakhyanerik/nvagik --jq .security_and_analysis` | enabled; Dependabot security-update PRs are off on purpose (docs/DECISIONS.md) |
| Private vulnerability reporting | `gh api repos/cholakhyanerik/nvagik/private-vulnerability-reporting` | enabled |
| Full-SHA action pins | `gh api repos/cholakhyanerik/nvagik/actions/permissions --jq .sha_pinning_required` | `true` |
| Allowed actions | `gh api repos/cholakhyanerik/nvagik/actions/permissions/selected-actions` | GitHub-owned plus `astral-sh/setup-uv`, mirrored in `tests/test_ci_workflows.py` |
| Fork pull request runs | `gh api repos/cholakhyanerik/nvagik/actions/permissions/fork-pr-contributor-approval --jq .approval_policy` | `all_external_contributors` |
