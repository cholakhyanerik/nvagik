# Decisions

Decisions made while building Nvagik, newest first. CLAUDE.md rule 1: when something is unclear, choose the most reasonable option, record it here with the reason, and continue. Open product questions live in the [README](../README.md#open-questions) until a decision task in [TASKS.md](../TASKS.md) closes them.

| Date | Decision | Why |
| --- | --- | --- |
| 2026-11-21 | Each finished task bumps PATCH, each finished phase bumps MINOR, the Store release is 1.0.0. | The owner wants a version and CHANGELOG entry after every task; phases map naturally to minor versions. |
| 2026-11-21 | Steps that spend money, sign agreements or need the owner's identity are `Blocked (owner)` tasks, the only exception to full autonomy. | The agent cannot legally or financially act for the owner; everything else is prepared so the owner only clicks. |
| 2026-11-21 | Subagents use `model: inherit` with no `effort` key, plus `CLAUDE_CODE_SUBAGENT_EFFORT=inherit` in project settings. | The owner wants subagents on the session's model and effort. Agent frontmatter accepts `inherit` for the model but only fixed levels for effort; leaving effort unset makes agents follow the session (verified in Claude Code 2.1.329). |
| 2026-11-21 | Dev tooling: pytest for tests, ruff for lint and format (rules include `PERF` and `S`). | Standard, fast, uv-friendly; the performance and security rule sets match the project's top priorities. |
| 2026-11-21 | Claude hooks are stdlib-only Python scripts run with `py -3`. | Same language as the project; works before `uv sync` and keeps reporting the system Python version (rule 5). |
| 2026-11-21 | Business and bank details live in the git-ignored `PRIVATE.md`; a hook blocks committing its values. | The repository is public, and leaked history is practically impossible to remove. |
| 2026-11-21 | Commits use the GitHub noreply e-mail (global git config); history was rewritten once to remove the personal e-mail. | Privacy of the owner in a public repository. |
| 2026-11-21 | Repository is public at `cholakhyanerik/nvagik`, default branch `main`. | Open repository is a core principle of the project. |
| 2026-11-21 | Product name: Nvagik (backups: Yergik, Dzaynik). | See the name availability check in the README. |
