"""Repository files that GitHub reads: the security policy (NVG-4), funding (NVG-6)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/cholakhyanerik/nvagik"
SPONSORS_URL = "https://github.com/sponsors/cholakhyanerik"


def test_security_policy_points_to_private_reporting():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert f"{REPO_URL}/security/advisories/new" in policy
    assert "## Supported versions" in policy
    assert "@" not in policy, "no e-mail addresses: reports go through GitHub only"


def test_sponsor_button_points_to_github_sponsors():
    # GitHub reads .github/FUNDING.yml on the default branch for the "Sponsor" button.
    funding = (ROOT / ".github" / "FUNDING.yml").read_text(encoding="utf-8")
    assert funding.splitlines() == ["github: cholakhyanerik"]
    assert SPONSORS_URL in (ROOT / "README.md").read_text(encoding="utf-8")
