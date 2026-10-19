"""Mỗi câu design §7.3 trả đúng đáp án viết tay trong data/sample-story/answers.yaml."""

import pytest
import yaml

from writory.graph import (
    find_characters,
    is_alive,
    item_holder,
    knows,
    overdue_threads,
    player_knowledge_about,
    protagonist_id,
    relationship,
    undiscovered_lies,
)
from writory.graph.sample import DEFAULT_SAMPLE_DIR

pytestmark = pytest.mark.graph

ANSWERS = yaml.safe_load((DEFAULT_SAMPLE_DIR / "answers.yaml").read_text(encoding="utf-8"))


def _ids(case_key, *fields):
    return [
        "-".join(str(case[f]) for f in fields) for case in ANSWERS[case_key]
    ]


@pytest.mark.parametrize("case", ANSWERS["holder"], ids=_ids("holder", "item", "chapter"))
def test_item_holder(driver, sample_story_id, case):
    holder = item_holder(driver, sample_story_id, case["item"], case["chapter"])
    assert holder is not None and holder.id == case["holder"]


@pytest.mark.parametrize(
    "case", ANSWERS["knows"], ids=_ids("knows", "character", "fact", "chapter")
)
def test_knows(driver, sample_story_id, case):
    got = knows(driver, sample_story_id, case["character"], case["fact"], case["chapter"])
    if case["answer"] is None:
        assert got is None
    else:
        assert got is not None
        assert (got.since_chapter, got.how) == (
            case["answer"]["since_chapter"], case["answer"]["how"]
        )


@pytest.mark.parametrize(
    "case", ANSWERS["player_about"], ids=_ids("player_about", "entity", "chapter")
)
def test_player_knowledge_about(driver, sample_story_id, case):
    entries = player_knowledge_about(driver, sample_story_id, case["entity"], case["chapter"])
    assert sorted(e.id for e in entries) == sorted(case["answer"])


@pytest.mark.parametrize(
    "case", ANSWERS["undiscovered_lies"], ids=_ids("undiscovered_lies", "speaker", "chapter")
)
def test_undiscovered_lies(driver, sample_story_id, case):
    lies = undiscovered_lies(driver, sample_story_id, case["speaker"], case["chapter"])
    got = sorted(
        ({"lie": x.id, "told_to": sorted(x.told_to), "chapter": x.chapter} for x in lies),
        key=lambda d: d["lie"],
    )
    want = sorted(
        ({**a, "told_to": sorted(a["told_to"])} for a in case["answer"]),
        key=lambda d: d["lie"],
    )
    assert got == want


@pytest.mark.parametrize(
    "case", ANSWERS["overdue_threads"], ids=_ids("overdue_threads", "chapter")
)
def test_overdue_threads(driver, sample_story_id, case):
    got = overdue_threads(driver, sample_story_id, case["chapter"])
    assert sorted(t.id for t in got) == sorted(case["answer"])


@pytest.mark.parametrize(
    "case", ANSWERS["relationship"], ids=_ids("relationship", "from", "to", "chapter")
)
def test_relationship_over_time(driver, sample_story_id, case):
    rel = relationship(driver, sample_story_id, case["from"], case["to"], case["chapter"])
    assert rel is not None and (rel.kind, rel.score) == (case["kind"], case["score"])


@pytest.mark.parametrize("case", ANSWERS["alive"], ids=_ids("alive", "character", "chapter"))
def test_is_alive(driver, sample_story_id, case):
    assert is_alive(driver, sample_story_id, case["character"], case["chapter"]) is case["alive"]


@pytest.mark.parametrize("case", ANSWERS["find_character"], ids=_ids("find_character", "name"))
def test_find_characters_by_name_or_alias(driver, sample_story_id, case):
    got = find_characters(driver, sample_story_id, case["name"])
    assert sorted(c.id for c in got) == sorted(case["answer"])


def test_protagonist(driver, sample_story_id):
    assert protagonist_id(driver, sample_story_id) == "minh"


def test_chapter_before_story_has_no_holder(driver, sample_story_id):
    assert item_holder(driver, sample_story_id, "sword", 0) is None
