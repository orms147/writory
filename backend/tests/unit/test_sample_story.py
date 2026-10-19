import copy

from writory.graph import EdgeSpec, read_sample, validate_sample


def test_sample_story_has_five_chapters_with_unique_commits():
    sample = read_sample()
    # Chương 0 là thế giới lúc khởi tạo, không có văn bản (D-21).
    assert [c.number for c in sample.chapters] == [0, 1, 2, 3, 4, 5]
    assert len({c.package.commit_id for c in sample.chapters}) == 6
    assert sample.chapters[0].text == ""
    assert all(len(c.text) > 500 for c in sample.chapters[1:])


def test_sample_story_is_consistent():
    # Mọi câu trích có thật trong chương, mọi cạnh trỏ tới nút đã khai, mọi `close` trỏ tới cạnh có thật.
    assert validate_sample(read_sample()) == []


def test_validate_sample_catches_invented_quote():
    sample = read_sample()
    broken = copy.deepcopy(sample)
    ch = broken.chapters[5]
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
    ch = broken.chapters[1]
    bad = EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "minh", "to": "hac_ky_letter", "valid_from_chapter": 1}
    )
    ch.package = ch.package.model_copy(update={"edges": [*ch.package.edges, bad]})
    assert any("hac_ky_letter" in p for p in validate_sample(broken))


def test_validate_sample_requires_known_as_for_named_nodes():
    # D-17: hé lộ một Character/Item/Location/Faction phải nói người chơi biết nó dưới tên nào.
    sample = read_sample()
    broken = copy.deepcopy(sample)
    ch = broken.chapters[1]
    bad = EdgeSpec.model_validate({
        "type": "REVEALED_TO_PLAYER", "from": "hac_ky", "to": "ch1",
        "valid_from_chapter": 1, "id": "reveal_hac_ky_no_name", "quote": "Đầu bến có một quán trà mới mở.",
    })
    ch.package = ch.package.model_copy(update={"edges": [*ch.package.edges, bad]})
    assert any("reveal_hac_ky_no_name" in p and "known_as" in p for p in validate_sample(broken))


def test_validate_sample_enforces_chapter_rule():
    # D-21: gói chương 2 không được mở cạnh từ chương 1.
    sample = read_sample()
    broken = copy.deepcopy(sample)
    ch = broken.chapters[2]
    bad = EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "khai", "to": "sword", "valid_from_chapter": 1, "id": "backdated"}
    )
    ch.package = ch.package.model_copy(update={"edges": [*ch.package.edges, bad]})
    assert any("backdated" in p for p in validate_sample(broken))
