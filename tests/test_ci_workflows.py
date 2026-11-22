"""GitHub Actions workflows follow the budget and security rules in CLAUDE.md (NVG-8).

The workflows are small and written by us, so a line-based reading is enough;
no YAML parser is added to the dependencies for this. The checks fail closed:
anything written in an unusual way (quoted keys, flow mappings, extra
`permissions` blocks, unknown expressions) is rejected rather than parsed.
These tests catch accidental drift. A pull request can edit them too, so only
repository settings can enforce SHA pinning and allowed actions (NVG-12).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
PATHS_IGNORE = '["**.md", "docs/**"]'
EXPECTED_ON = [
    "  push:",
    "    branches: [main]",
    f"    paths-ignore: {PATHS_IGNORE}",
    "  pull_request:",
    f"    paths-ignore: {PATHS_IGNORE}",
]
# GitHub-hosted runners only: a self-hosted runner would run code from fork
# pull requests on that machine.
ALLOWED_RUNNERS = {"windows-latest"}
# Expressions are never built from event data (titles, branch names, commit
# messages), which would allow script injection.
ALLOWED_EXPRESSIONS = {
    "${{ github.workflow }}",
    "${{ github.ref }}",
    "${{ github.event_name == 'push' }}",
}
# Same form as PIN in .claude/hooks/session_start.py, which reports outdated pins (NVG-11).
PIN = re.compile(
    r"^[ \t]*(?:- )?uses: [A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}(?:/[A-Za-z0-9_./-]{0,200})?"
    r"@[0-9a-f]{40} # v[0-9]{1,6}(?:\.[0-9]{1,6}){0,3}$",
    re.ASCII,
)


def top_level_block(text: str, key: str) -> list[str]:
    """The non-empty lines indented under a top-level `key:` (empty if missing)."""
    lines = text.splitlines()
    try:
        start = lines.index(f"{key}:")
    except ValueError:
        return []
    block = []
    for line in lines[start + 1 :]:
        if line and not line.startswith((" ", "#")):
            break
        if line.strip():
            block.append(line)
    return block


def without_comment_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_ci_workflow_exists():
    assert ROOT / ".github" / "workflows" / "ci.yml" in WORKFLOWS


@pytest.fixture(params=WORKFLOWS, ids=lambda path: path.name)
def workflow(request) -> str:
    return request.param.read_text(encoding="utf-8")


def test_keys_are_written_plainly(workflow):
    for line in without_comment_lines(workflow).splitlines():
        assert not re.match(r"""^\s*(?:- )?["'][^"'\n]*["']\s*:""", line), f"quoted key: {line}"
        assert not re.match(r"^\s*(?:- )?[\w-]+\s+:", line), f"space before colon: {line}"
        assert not re.match(r"^\s*(?:- )?[\w-]+:\s*\{", line), f"flow mapping: {line}"


def test_triggers_are_push_to_main_and_pull_requests_only(workflow):
    assert top_level_block(workflow, "on") == EXPECTED_ON
    for risky in ("schedule", "workflow_run", "pull_request_target", "issue_comment", "matrix"):
        assert risky not in workflow


def test_permissions_are_read_only(workflow):
    assert top_level_block(workflow, "permissions") == ["  contents: read"]
    assert workflow.count("permissions") == 1, "no job-level permissions"
    assert not re.search(r"write", without_comment_lines(workflow))


def test_concurrency_cancels_older_runs(workflow):
    assert "  cancel-in-progress: true" in top_level_block(workflow, "concurrency")


def test_every_job_has_a_timeout_of_at_most_10_minutes(workflow):
    jobs = [line for line in top_level_block(workflow, "jobs") if re.match(r"^  [\w-]+:$", line)]
    timeouts = [int(t) for t in re.findall(r"^    timeout-minutes: (\d+)$", workflow, re.M)]
    assert jobs
    assert len(timeouts) == len(jobs) == workflow.count("timeout-minutes")
    assert all(t <= 10 for t in timeouts)


def test_jobs_run_on_github_hosted_runners(workflow):
    runners = re.findall(r"^    runs-on: (\S+)$", workflow, re.M)
    assert runners
    assert len(runners) == workflow.count("runs-on")
    assert set(runners) <= ALLOWED_RUNNERS


def test_actions_are_pinned_to_commit_shas(workflow):
    # /update-deps compares the "# vX.Y.Z" comment with the action's latest release.
    code = without_comment_lines(workflow)
    uses = [line for line in code.splitlines() if "uses" in line]
    assert uses
    for line in uses:
        assert PIN.match(line), f"not pinned as 'uses: owner/repo@<sha> # vX.Y.Z': {line}"


def test_expressions_are_allowlisted(workflow):
    expressions = set(re.findall(r"\$\{\{.*?\}\}", workflow, re.S))
    assert expressions <= ALLOWED_EXPRESSIONS
    assert "secrets" not in workflow


def test_checkout_does_not_keep_the_token(workflow):
    checkouts = workflow.count("actions/checkout@")
    assert workflow.count("persist-credentials: false") == checkouts


def test_uv_is_verified_and_cached_from_main_only(workflow):
    setups = workflow.count("astral-sh/setup-uv@")
    for setting in (
        "version: latest-known",  # only uv versions whose checksums the pinned release bundles
        "require-checksums: true",
        "enable-cache: auto",  # on, except for risky events such as tags and releases
        "save-cache: ${{ github.event_name == 'push' }}",  # pull requests only restore
        "prune-cache: true",  # the key changes with every version bump: keep uploads small
    ):
        assert workflow.count(setting) == setups, setting


def test_checks_cannot_be_switched_off_quietly(workflow):
    assert "continue-on-error" not in workflow
    # No conditions: a job or step with `if: false` would pass without running.
    assert not re.search(r"^\s*(?:- )?if:", workflow, re.M)


def test_ci_runs_the_local_checks_on_windows():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "    runs-on: windows-latest\n" in ci
    assert any(line.startswith('  UV_LOCKED: "1" ') for line in top_level_block(ci, "env"))
    assert ci.count("UV_LOCKED") == 1, "uv.lock must be used as is"
    for command in (
        "uv sync",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run pytest",
    ):
        assert f"      - run: {command}\n" in ci
