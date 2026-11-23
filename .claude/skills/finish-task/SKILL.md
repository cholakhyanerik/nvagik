---
name: finish-task
description: Nvagik Definition of done. Run after finishing every task or bug fix: verify, review, update TASKS.md, CHANGELOG.md, version, README.md, CLAUDE.md and .claude/rules/, then commit, tag, push without asking, and clean up junk. Use whenever a TASKS.md task is complete.
---

# Finish a task

Implements CLAUDE.md rules 3, 9, 10, 11 and 12. Do every step, in order, without asking the owner.

## 1. Verify

```sh
uv run ruff format .
uv run ruff check .
uv run pytest
```

All must pass. Anything that fails is a bug: fix it now (rule 10) and add a regression test. If PyPI is unreachable, add `--offline` after `uv`.

## 2. Review

Spawn reviewers for what the change touched (they inherit the session's model and effort), in parallel where possible:

- Any code change: `code-reviewer`.
- Parsing, subprocesses, plugins, networking, dependencies, CI or `.claude/hooks`: `security-auditor`.
- Startup, audio engine, DSP, drawing or other hot paths: `performance-auditor`.
- Windows, dialogs, widgets or theme: `ui-ux-reviewer`.
- New or changed user-facing text: `i18n-translator`.

Fix every confirmed finding. Ideas that don't belong to this task become TASKS.md cards. Rerun step 1 if code changed.

## 3. Update the documents (all in English)

1. **TASKS.md:** delete the finished task's card and its line in "Next up"; add new cards for improvements found (use `/add-task`); refill "Next up" with up to 7 open tasks whose dependencies are done and that no contributor has claimed (the "skip" list in the SessionStart "GitHub claims" line).
2. **Version:** `uv version --bump patch` for a task; `uv version --bump minor` for a phase exit task; `uv version 1.0.0` for the release.
3. **CHANGELOG.md:** add `## [X.Y.Z] - YYYY-MM-DD` under `## [Unreleased]` with `Added` / `Changed` / `Fixed` / `Removed` / `Security` sections, mention task IDs, move any lines left under `## [Unreleased]` (from merged pull requests, see CONTRIBUTING.md) into the new version, and add the compare link at the bottom (`[X.Y.Z]: https://github.com/cholakhyanerik/nvagik/compare/vPREV...vX.Y.Z`).
4. **README.md:** update the status line, features, commands or anything the task changed.
5. **`.claude/rules/` and CLAUDE.md** (rule 15): conventions, commands and gotchas learned in this task go into the matching `.claude/rules/*.md` file (a new area gets a new file with `paths:` and a row in CLAUDE.md's "Where the details are"). CLAUDE.md changes only for an owner's rule, an architecture rule, a security rule (those always stay in CLAUDE.md) or a pointer, and stays at about 200 lines (`.claude/rules/docs.md`). Improve skills or agents if a step was unclear. Record decisions in `docs/DECISIONS.md`.

Run `uv run pytest` again (it checks the CHANGELOG entry and the TASKS.md format).

## 4. Commit, tag, push

```sh
git add -A
git status --short   # check nothing unexpected is staged
git commit -F - <<'EOF'
<type>(<scope>): <summary> (NVG-<id>)

<what changed and why, wrapped at 72 columns>

<attribution trailer required by the harness, if any>
EOF
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main --follow-tags
```

The guard hook scans the commit and the push. If it blocks, remove the leak; never bypass it.

If the push changed more than Markdown and `docs/`, watch the CI run (it takes a few seconds to appear; `gh run watch` needs a run ID outside a terminal). Write the SHA and the ID into the commands literally:

```sh
gh run list --workflow ci.yml --commit <sha> --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch <id> --exit-status --compact
```

A failed run is a bug: fix it now (rule 10).

## 5. Clean up

```sh
py -3 scripts/clean.py
git status --short   # must be empty
```

Also delete any temporary files you created outside the repository for this task (scratchpad files you no longer need).

## 6. Report to the owner (in Russian)

A few short lines: what was done, the new version, the commit link (`https://github.com/cholakhyanerik/nvagik/commit/<sha>`), any `Blocked (owner)` steps, and what comes next.
