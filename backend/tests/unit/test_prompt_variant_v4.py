"""Biến thể đề lựa chọn "v4" (evals/scenarios/prompts/v4/): ba lựa chọn nhắm ba trục khác nhau, ít
nhất một lựa chọn rời khỏi trục xung đột chính. Chỉ bộ đo nạp (D-109); mã mặc định không đổi."""

from writory.pipeline import choices as choices_mod
from writory.pipeline.prompt_variants import CHOICES_FILE, PROMPTS_DIR, load_prompt_variant

# Mọi từ mà schema và luật người-chơi-only của đề mặc định cần; biến thể thay nguyên system prompt
# nên phải tự giữ đủ (test cùng danh sách ở test_default_prompts_v3.py).
SCHEMA_WORDS = ("action", "dialogue", "inner", "tone", "lie_content", "listeners", "feeling",
                "about", "m1, m2", "Không bịa thêm sự thật", "chỉ biết những gì có trong khối dữ liệu",
                "Trả về JSON đúng schema")
V3_RULES = ("Không đưa ba cách khác nhau của cùng một việc chờ hay giữ yên",
            "Không chọn lại việc nhân vật vừa làm hay vừa nói trong cảnh",
            "không viết sẵn nguyên câu nhân vật sẽ nói")


def test_v4_replaces_only_the_choices_system_prompt():
    variant = load_prompt_variant("v4")
    assert variant.overrides() == ["choices_system"]
    assert variant.outline_system is None and not variant.goal_texts
    assert set(variant.files) == {CHOICES_FILE}
    assert (PROMPTS_DIR / "v4" / CHOICES_FILE).is_file()


def test_v4_asks_for_three_different_axes_and_one_choice_off_the_main_conflict():
    prompt = load_prompt_variant("v4").choices_system
    for rule in ("ba TRỤC khác nhau",
                 "Trục mối nguy", "Trục quan hệ", "Trục mục tiêu",
                 "Trục xung đột chính là",
                 "ít nhất một lựa chọn rời khỏi trục này",
                 "Không dùng ba cách khác nhau của cùng một mối nguy"):
        assert rule in prompt, rule


def test_v4_keeps_the_schema_words_the_v3_rules_and_the_tone_guidance():
    prompt = load_prompt_variant("v4").choices_system
    for word in SCHEMA_WORDS:
        assert word in prompt, word
    for rule in V3_RULES:
        assert rule in prompt, rule
    assert choices_mod.TONE_GUIDANCE in prompt


def test_the_default_choices_prompt_is_not_touched_by_v4():
    assert "TRỤC" not in choices_mod.SYSTEM_PROMPT
    assert choices_mod.PROMPT_VERSION == "choices-5"
