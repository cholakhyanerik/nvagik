---
name: add-task
description: Write, split, update or remove cards in Nvagik's TASKS.md (Jira/Trello-style backlog to 1.0). Use whenever new work, an improvement or a follow-up appears, when a task is too big, or when finishing a task.
---

# Maintain TASKS.md

TASKS.md must always be current (CLAUDE.md rule 9). `tests/test_tasks_md.py` checks its format.

## Bug or task?

- A **bug or defect** found while working is fixed in the current session with a regression test. It is **not** added to TASKS.md (rule 10).
- **New features, improvements, follow-ups and ideas** become cards.

## Card format

```markdown
### NVG-<id>: <short imperative title>
**Type:** Story · **Priority:** P1 · **Size:** S · **Status:** To Do · **Depends on:** NVG-100, NVG-104
- [ ] <observable acceptance criterion>
- [ ] <test or measurement that proves it>
```

- **ID:** next free number in the epic's hundred (1–99 setup and decisions, 100 Phase 0, 200 Phase 1, 300 Phase 2, 400 Phase 3, 500 Phase 4, 600 Phase 5, 700 Phase 6, 800 Release). Never reuse an ID.
- **Type:** `Story` (user-visible), `Task` (technical), `Spike` (time-boxed research with a recorded result), `Decision` (recorded in docs/DECISIONS.md), `Chore` (repo housekeeping).
- **Priority:** `P0` blocks the current phase, `P1` needed for 1.0, `P2` needed for 1.0 but can wait, `P3` nice to have.
- **Size:** `XS` ≤ 1 h, `S` ≤ half a day, `M` ≤ 1 day. Anything bigger must be split; prefer `XS`/`S`.
- **Status:** `To Do`, `In Progress`, or `Blocked (owner)` (only for money, agreements or the owner's identity; write the exact steps in the card).
- **Depends on:** task IDs or `—`.
- **Acceptance criteria:** 1 to 3 checkable bullets; at least one names a test or measurement.

## Splitting

Split by user-visible slice (model, then UI, then playback), not by layer for its own sake. Each piece must leave the app working (no half-features on `main`). Replace the big card with the new ones in the same section and fix any `Depends on` references.

## Housekeeping

- Delete a card when its task is done (the CHANGELOG keeps the history) and remove it from "Next up".
- Keep "Next up" at up to 7 open tasks whose dependencies are done, in the order they should be worked on.
- Keep sections in roadmap order. Phase 7 ("parity") work is out of scope until 1.0 ships.
