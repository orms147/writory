"""Đề "v3" là đề mặc định của sản phẩm (D-111): đề của mã mang luật của v3, giữ mọi luật an toàn và
trường đầu ra của đề cũ, và ba cờ ngữ cảnh bật ở `config/limits.yaml`."""

from writory.config import load_config
from writory.pipeline import choices as choices_mod
from writory.pipeline import scene as scene_mod
from writory.pipeline.pacing import GOAL_DEFAULTS
from writory.pipeline.scene import STYLE_GUIDE_PATH, load_style_guide


def test_the_three_context_flags_are_on_in_the_repo_config():
    c = load_config().limits.context
    assert c.character_personality_max_chars == 240
    assert c.previous_openings == 2 and c.previous_opening_max_chars == 160
    assert c.unplanned_chapter_goal is True


def test_the_repo_config_with_the_flags_on_has_no_config_problem():
    from writory.pipeline.chapter import config_problems
    assert config_problems(load_config()) == []


def test_outline_prompt_carries_the_v3_rules_and_keeps_every_old_field_and_safety_rule():
    prompt = scene_mod.OUTLINE_SYSTEM_PROMPT
    for v3_rule in ("Mỗi cảnh phải đổi ít nhất một điều chỉ ra được",
                    "Nhịp đầu của chương là hậu quả hay phản ứng ngay sau lựa chọn của người chơi",
                    "Trong mỗi chương nhân vật chính làm ít nhất một việc không thể rút lại",
                    "Không có hai nhịp cùng một lập trường",
                    "Không phải lúc mọi người đứng chờ."):
        assert v3_rule in prompt, v3_rule
    for field in ("goal", "present", "beats", "ends_at", "resolves"):
        assert f"- {field}:" in prompt
    for must in ("KHÔNG để lộ", "không chiều theo", "người đã chết", "không chữ Hán",
                 "Mạch ĐẾN HẠN hay QUÁ HẠN"):
        assert must in prompt, must


def test_choices_prompt_carries_the_v3_rules_and_keeps_the_schema_words_and_the_player_only_rule():
    prompt = choices_mod.SYSTEM_PROMPT
    for v3_rule in ("Không đưa ba cách khác nhau của cùng một việc chờ hay giữ yên",
                    "Không chọn lại việc nhân vật vừa làm hay vừa nói trong cảnh",
                    "nói thật không phải mặc định",
                    "không viết sẵn nguyên câu nhân vật sẽ nói"):
        assert v3_rule in prompt, v3_rule
    for must in ("action", "dialogue", "inner", "tone", "lie_content", "listeners", "feeling",
                 "about", "m1, m2", "Không bịa thêm sự thật", "chỉ biết những gì có trong khối dữ liệu",
                 "Trả về JSON đúng schema"):
        assert must in prompt, must
    assert choices_mod.TONE_GUIDANCE in prompt


def test_goal_defaults_carry_the_v3_sentences_and_keep_the_other_keys():
    assert GOAL_DEFAULTS["push_forward"].endswith(
        "Ký, ghi, đặt xuống hay hẹn để sau không tính là tình thế mới.")
    assert GOAL_DEFAULTS["milestone_next"].startswith(
        "Mốc kế tiếp, chương này đưa vào một sự kiện hay áp lực cụ thể")
    assert {"milestone_gap", "standstill", "secret_note", "revealed_note",
            "thread_note"} <= set(GOAL_DEFAULTS)
    assert "{place}" in GOAL_DEFAULTS["standstill"] and "{chapters}" in GOAL_DEFAULTS["standstill"]


def test_default_style_guide_is_the_v3_guide_without_its_comment_and_keeps_the_hard_rules():
    assert not STYLE_GUIDE_PATH.with_name("style_guide_vi_v3.md").exists()
    guide = load_style_guide()
    assert "<!--" not in guide and guide.startswith("Bạn là một nhà văn Việt Nam")
    for v3_rule in ("## Mỗi cảnh đổi một điều", "## Kết cảnh và mở chương", "## Xung đột có giá"):
        assert v3_rule in guide, v3_rule
    for must in ("Không được nói ra bí mật", "xưng \"tôi\"", "chữ Hán", "- \" (gạch ngang",
                 "Ngoặc kép chỉ dùng", "Xưng hô theo đúng bảng", "Chỉ viết văn bản của cảnh",
                 "Tên nhân vật và địa danh theo quy ước"):
        assert must in guide, must


def test_default_style_guide_comment_says_it_is_the_current_version():
    raw = STYLE_GUIDE_PATH.read_text(encoding="utf-8")
    comment = raw[:raw.index("-->")]
    assert "D-111" in comment and "Chưa là mặc định" not in comment


def test_no_v3_variant_directory_is_left_in_the_repo():
    assert not (STYLE_GUIDE_PATH.parents[1] / "prompts" / "v3").exists()
