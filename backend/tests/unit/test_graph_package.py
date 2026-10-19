import unicodedata

import pytest
from pydantic import ValidationError

from writory.graph import ChangePackage, CloseSpec, EdgeSpec, NodeSpec, quote_in_text


def test_edge_id_is_deterministic_when_not_given():
    a = EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "gu", "to": "sword", "valid_from_chapter": 1}
    )
    b = EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "gu", "to": "sword", "valid_from_chapter": 1}
    )
    assert a.id == b.id
    assert a.id != EdgeSpec.model_validate(
        {"type": "HOLDS", "from": "gu", "to": "sword", "valid_from_chapter": 2}
    ).id


def test_revealed_to_player_requires_quote():
    # G3: đánh dấu đã hé lộ phải kèm câu trích.
    with pytest.raises(ValidationError):
        EdgeSpec.model_validate(
            {"type": "REVEALED_TO_PLAYER", "from": "f1", "to": "ch1", "valid_from_chapter": 1}
        )
    with pytest.raises(ValidationError):
        EdgeSpec.model_validate(
            {"type": "REVEALED_TO_PLAYER", "from": "f1", "to": "ch1",
             "valid_from_chapter": 1, "quote": "   "}
        )


def test_edge_validity_window_must_be_forward():
    with pytest.raises(ValidationError):
        EdgeSpec.model_validate(
            {"type": "HOLDS", "from": "a", "to": "b",
             "valid_from_chapter": 3, "valid_to_chapter": 3}
        )
    with pytest.raises(ValidationError):
        CloseSpec(type="HOLDS", id="x", valid_to_chapter=0)


@pytest.mark.parametrize("bad", [
    {"id": "x", "label": "Wizard"},                       # nhãn ngoài danh sách
    {"id": "x y", "label": "Character"},                  # id có khoảng trắng
    {"id": "x", "label": "Character", "story_id": "s2"},  # thuộc tính dành riêng
    {"id": "x", "label": "Character", "commit_id": "c"},
    {"id": "x", "label": "Character", "meta": {"a": 1}},  # Neo4j không lưu được map
])
def test_node_spec_rejects_bad_input(bad):
    with pytest.raises(ValidationError):
        NodeSpec.from_flat(bad)


def test_edge_type_is_whitelisted():
    # Tên kiểu cạnh được ghép vào Cypher, nên chỉ nhận danh sách cố định.
    with pytest.raises(ValidationError):
        EdgeSpec.model_validate(
            {"type": "HOLDS]->() DETACH DELETE (n", "from": "a", "to": "b",
             "valid_from_chapter": 1}
        )


def test_package_rejects_duplicate_ids():
    node = {"id": "a", "label": "Character", "props": {"name": "A"}}
    with pytest.raises(ValidationError):
        ChangePackage.model_validate({"commit_id": "c1", "nodes": [node, node]})


def test_quote_in_text_normalizes_unicode_and_whitespace():
    text = "Cô nói:\n  — Em tên Lan,   Phạm Thị Lan."
    decomposed = unicodedata.normalize("NFD", "Em tên Lan, Phạm Thị Lan.")
    assert quote_in_text(decomposed, text)
    assert not quote_in_text("Em tên Lan, Phạm Thị Hoa.", text)
    assert not quote_in_text("", text)
