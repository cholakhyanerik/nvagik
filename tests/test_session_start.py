"""SessionStart hook: the GitHub security line (private reports and Dependabot alerts)."""

import importlib.util
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "session_start.py"


@pytest.fixture(scope="module")
def hook():
    spec = importlib.util.spec_from_file_location("nvagik_session_start", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_gh(monkeypatch, hook, reports: str | None, alerts: str | None) -> list[tuple]:
    calls = []

    def run(*args, timeout=10):
        calls.append(args)
        endpoint = args[3]
        return reports if endpoint.startswith(f"{hook.REPO}/security-advisories") else alerts

    monkeypatch.setattr(hook, "run", run)
    return calls


def test_nothing_waiting(monkeypatch, hook):
    calls = fake_gh(monkeypatch, hook, "0\n", "0\n")
    assert "no private vulnerability reports waiting" in hook.github_security_status()
    assert all(call[:3] == ("gh", "api", "--paginate") for call in calls)


def test_waiting_reports_and_alerts_are_actions(monkeypatch, hook):
    fake_gh(monkeypatch, hook, "2\n1\n", "3\n")  # --paginate prints one count per page
    status = hook.github_security_status()
    assert "3 private vulnerability report(s) waiting" in status
    assert "within 7 days" in status
    assert "3 open Dependabot alert(s)" in status
    assert status.count("ACTION") == 2


@pytest.mark.parametrize(("reports", "alerts"), [(None, "0"), ("0", None), ("oops", "0")])
def test_gh_failure_is_reported_not_raised(monkeypatch, hook, reports, alerts):
    fake_gh(monkeypatch, hook, reports, alerts)
    assert hook.github_security_status().startswith("GitHub security: could not check")
