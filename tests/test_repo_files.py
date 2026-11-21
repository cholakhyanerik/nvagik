"""Repository files that GitHub reads: the security policy (NVG-4)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/cholakhyanerik/nvagik"


def test_security_policy_points_to_private_reporting():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert f"{REPO_URL}/security/advisories/new" in policy
    assert "## Supported versions" in policy
    assert "@" not in policy, "no e-mail addresses: reports go through GitHub only"
