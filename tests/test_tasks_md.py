"""Keep TASKS.md well-formed: unique IDs, complete cards, small tasks, valid Next up."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "TASKS.md").read_text(encoding="utf-8")
CARD = re.compile(r"^### (NVG-\d+): (.+)$", re.MULTILINE)
SIZES = {"XS", "S", "M"}  # L and bigger must be split into smaller tasks


def cards() -> dict[str, str]:
    matches = list(CARD.finditer(TEXT))
    result = {}
    for match, nxt in zip(matches, [*matches[1:], None], strict=True):
        end = nxt.start() if nxt else len(TEXT)
        body = TEXT[match.end() : end].split("\n## ", 1)[0]
        assert match.group(1) not in result, f"duplicate task ID {match.group(1)}"
        result[match.group(1)] = body
    return result


def test_tasks_exist_and_ids_are_unique():
    assert len(cards()) > 0


def test_every_card_has_metadata_and_acceptance_criteria():
    for task_id, body in cards().items():
        for field in ("**Type:**", "**Priority:**", "**Size:**", "**Status:**", "**Depends on:**"):
            assert field in body, f"{task_id} is missing {field}"
        assert "- [ ]" in body, f"{task_id} has no acceptance criteria"


def test_tasks_are_small():
    for task_id, body in cards().items():
        size = re.search(r"\*\*Size:\*\* (\w+)", body).group(1)
        assert size in SIZES, f"{task_id} has size {size}; split it into smaller tasks"


def test_next_up_points_to_existing_open_tasks():
    section = TEXT.partition("## Next up")[2].split("\n## ", 1)[0]
    refs = re.findall(r"NVG-\d+", section)
    assert refs, "Next up is empty"
    assert set(refs) <= set(cards()), "Next up references unknown tasks"
