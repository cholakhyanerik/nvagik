---
name: next-task
description: Start work in Nvagik: apply the session-start checks (system Python, dependencies), pick the next task from TASKS.md, split it if needed, and implement it following CLAUDE.md. Use at the start of a session or when the owner says to continue working.
---

# Pick up and do the next task

## 1. Session checks (rules 5 and 6)

Read the SessionStart hook report in your context. If it is missing, run `py -3 .claude/hooks/session_start.py` and read the `additionalContext` it prints.

- Python or dependency drift reported: run `/update-deps` (or the `deps-updater` agent) first and finish it with `/finish-task`.
- PyPI unreachable: note it, continue, and recheck later in the session.
- Commits behind origin: `git pull --rebase` first.

## 2. Choose the task

Open `TASKS.md` and take the first task in "Next up" that:

- is `To Do` (skip `Blocked (owner)`), and
- whose `Depends on` tasks no longer appear in the file (deleted means done).

If "Next up" is empty or stale, rebuild it from the backlog by priority (`P0` first) and phase order.

## 3. Prepare

- If the task is bigger than `S` or vague, split it into smaller cards with `/add-task` before coding.
- Set its `Status` to `In Progress`.
- Read the code and docs it touches. Write down a short plan (3 to 7 steps) for yourself.

## 4. Implement

- Test first for logic (pure functions, models, DSP); offscreen pytest-qt tests for widgets.
- Follow CLAUDE.md: speed first, audio callback rule, lazy imports, `tr()` for every user-facing string with Armenian and Russian translations, theme tokens for every color and font, Windows only, uv only.
- A bug you run into is fixed now with a regression test (rule 10); an unrelated improvement becomes a new card.
- Decide unclear details yourself and record them in `docs/DECISIONS.md` (rule 1).

## 5. Finish

Run `/finish-task`. Then go back to step 2 with the next task while the session continues.
