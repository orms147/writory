import copy

from writory.graph import EdgeSpec, read_sample, validate_sample


def test_sample_story_has_five_chapters_with_unique_commits():
    sample = read_sample()
    assert [c.number for c in sample.chapters] == [1, 2, 3, 4, 5]
    assert len({c.package.commit_id for c in sample.chapters}) == 5
    assert all(len(c.text) > 500 for c in sample.chapters)


def test_sample_story_is_consistent():
    # Mọi câu trích có thật trong chương, mọi cạnh trỏ tới nút đã khai, mọi `close` trỏ tới cạnh có thật.
    assert validate_sample(read_sample()) == []


def test_validate_sample_catches_invented_quote():
    sample = read_sample()
    broken = copy.deepcopy(sample)
    ch = broken.chapters[4]
    bad = EdgeSpec.model_validate({
        "type": "REVEALED_TO_PLAYER", "from": "f_lan_killed_gu", "to": "ch5",
        "valid_from_chapter": 5, "quote": "Lan đã giết Lão Gù.",
    })
    ch.package = ch.package.model_copy(update={"edges": [*ch.package.edges, bad]})
    problems = validate_sample(broken)
    assert any("Lan đã giết Lão Gù." in p for p in problems)


def test_validate_sample_catches_reference_to_later_node():
    sample = read_sample()
    broken = copy.deepcopy(sample)
    ch = broken.chapters[0]
    bad = EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "minh", "to": "hac_ky_letter", "valid_from_chapter": 1}
    )
    ch.package = ch.package.model_copy(update={"edges": [*ch.package.edges, bad]})
    assert any("hac_ky_letter" in p for p in validate_sample(broken))
