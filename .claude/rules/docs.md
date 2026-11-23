---
paths:
  - "CLAUDE.md"
  - ".claude/rules/**"
  - "README.md"
  - "CONTRIBUTING.md"
  - "tests/test_claude_md.py"
  - "tests/test_repo_files.py"
---

# CLAUDE.md, rules files, README and CONTRIBUTING

## CLAUDE.md (rule 15)

- Target about 200 lines. `tests/test_claude_md.py` fails above 400 lines or 30,000 characters; the SessionStart hook reports when it is over 200 lines.
- It holds only the owner's rules, the architecture and pointers to the details.
- Security rules stay in CLAUDE.md, even detailed ones: the Security section, PRIVATE.md, the guard's literal-text gotcha, contributors' pull requests, and anything else that must hold for every command. A path-scoped file loads only when a matching file is read, and even that is not guaranteed. The test checks that the Security section keeps its key phrases.
- The owner's rules keep their numbers: hooks, skills and docs cite them. The test checks that they are numbered 1, 2, 3, ... and that every "rule N" cited in the repository exists.
- No `@path` imports: an imported file loads at startup and saves nothing. The test rejects them.
- No history ("since version X", "added in NVG-N"): that lives in CHANGELOG and git.
- CI skips docs-only pushes, so the local `uv run pytest` before every commit is what catches a CLAUDE.md that grew too long.

## Rules files (`.claude/rules/*.md`)

- One file per area. Each starts with frontmatter that lists the files it is for:

  ```markdown
  ---
  paths:
    - "src/nvagik/audio/**"
  ---
  ```

- `paths:` is required: a rules file without it loads into every session.
- Every pattern must match at least one file in the repository, or the rule never loads. No `{a,b}` braces: write two patterns.
- The test checks both, that the "Where the details are" table in CLAUDE.md lists every rules file, and that every rules file named anywhere in the repository exists. It also checks that the `#anchor` links in CLAUDE.md and README.md point to real headings.
- A new feature note or gotcha goes into the matching file. A new area gets a new file and a row in that table.
- An agent prompt or skill that depends on a rules file names it, instead of relying on it being loaded.

## CONTRIBUTING.md

- A short public summary of the rules for outside contributors.
- When a rule, a command, the commit format or the CI checks change, update it too.
- `tests/test_repo_files.py` checks its commit types against CLAUDE.md, its checks against the `run:` steps of `ci.yml`, its Python version against `.python-version` and its links against git's file list.
