"""Biến thể đề "v3" trong repo (D-110): nạp được, giữ mọi luật an toàn và trường đầu ra của đề cũ."""

from writory.pipeline import choices as choices_mod
from writory.pipeline import scene as scene_mod
from writory.pipeline.pacing import GOAL_DEFAULTS
from writory.pipeline.prompt_variants import load_prompt_variant
from writory.pipeline.scene import STYLE_GUIDE_PATH, load_style_guide

V3_GUIDE = STYLE_GUIDE_PATH.with_name("style_guide_vi_v3.md")


def test_variant_v3_loads_and_replaces_the_outline_choices_and_two_goal_sentences():
    v = load_prompt_variant("v3")
    assert v.outline_system and v.choices_system
    assert set(v.goal_texts) == {"push_forward", "milestone_next"}
    assert set(v.goal_texts) <= set(GOAL_DEFAULTS)


def test_v3_outline_keeps_every_old_rule_and_output_field():
    v3 = load_prompt_variant("v3").outline_system
    old = scene_mod.OUTLINE_SYSTEM_PROMPT
    for sentence in old.splitlines():
        if sentence.startswith("- ") and not sentence.startswith(("- beats", "- ends_at")):
            key = sentence[2:40]
            assert key in v3, key
    for field in ("goal", "present", "beats", "ends_at", "resolves"):
        assert f"- {field}:" in v3
    for must in ("KHÔNG để lộ", "không chiều theo", "người đã chết", "không chữ Hán"):
        assert must in v3


def test_v3_choices_keeps_the_schema_words_and_the_player_only_rule():
    v3 = load_prompt_variant("v3").choices_system
    for must in ("action", "dialogue", "inner", "tone", "lie_content", "listeners", "feeling",
                 "about", "m1, m2", "Không bịa thêm sự thật", "chỉ biết những gì có trong khối dữ liệu",
                 "Trả về JSON đúng schema"):
        assert must in v3, must
    assert choices_mod.SYSTEM_PROMPT.splitlines()[0] == v3.splitlines()[0]


def test_v3_style_guide_loads_without_its_comment_and_keeps_the_hard_rules():
    guide = load_style_guide(V3_GUIDE)
    assert "<!--" not in guide and guide.startswith("Bạn là một nhà văn Việt Nam")
    for must in ("Không được nói ra bí mật", "xưng \"tôi\"", "chữ Hán", "- \" (gạch ngang",
                 "Ngoặc kép chỉ dùng", "Xưng hô theo đúng bảng", "Chỉ viết văn bản của cảnh",
                 "Tên nhân vật và địa danh theo quy ước"):
        assert must in guide, must


def test_v3_style_guide_stays_within_twice_the_old_one():
    assert len(load_style_guide(V3_GUIDE)) <= 2 * len(load_style_guide())
