"""check_meta_leak (D-30): thẻ suy luận hoặc chữ của prompt lọt vào văn bản cảnh. Không gọi LLM."""

import unicodedata
from pathlib import Path

import pytest

from writory.config import REPO_ROOT
from writory.quality import IssueKind, check_meta_leak

FIXTURES = Path(__file__).parents[1] / "fixtures" / "quality" / "clean"
SAMPLE_STORY = sorted((REPO_ROOT / "data" / "sample-story").glob("ch*.md"))

# Nguyên văn đầu cảnh MiMo 2.6 Pro viết ở pilot bài D (evals/results/2026-10-19-quality-pilot/).
PILOT_LEAK = (
    "Viết cảnh theo dàn ý, ngôi thứ ba bám Lạc Vân, cổ phong vừa phải, không lộ bí mật (chỉ "
    "gieo nhẹ ở viên đan thứ hai/thái độ Tần Mặc).</think_36a8b94076c558de0938f7e4f3cd4f18c5490ca0>"
    "Tần Mặc mở nắp lọ ngọc, rót viên đan ra lòng bàn tay."
)


def excerpts(text: str) -> list[str]:
    return [i.excerpt for i in check_meta_leak(text)]


def test_pilot_leak_is_caught_at_every_marker():
    issues = check_meta_leak(PILOT_LEAK)
    assert {i.kind for i in issues} == {IssueKind.META_LEAK}
    found = excerpts(PILOT_LEAK)
    assert "theo dàn ý" in found
    assert "ngôi thứ ba" in found
    assert "không lộ bí mật" in found
    assert "</think_36a8b94076c558de0938f7e4f3cd4f18c5490ca0>" in found


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<think>Cần đủ năm nhịp.</think>\nLạc Vân ngồi xuống.", ["<think>", "</think>"]),
        ("<thinking>\nkế hoạch\n</thinking>Mưa rơi.", ["<thinking>", "</thinking>"]),
        ("<reasoning>…</reasoning> Trời tối.", ["<reasoning>", "</reasoning>"]),
        ("<think\nLạc Vân ngồi xuống.", ["<think"]),
        ("Cảnh viết theo dàn ý được giao.", ["theo dàn ý"]),
        ("Kể ở NGÔI THỨ NHẤT, giọng tưng tửng.", ["NGÔI THỨ NHẤT"]),
        ("Giữ đúng bảng xưng hô: đệ, sư huynh.", ["bảng xưng hô"]),
        ("Bí mật (người viết được biết; không được để lộ).", ["người viết được biết"]),
    ],
)
def test_markers_are_reported_with_their_text(text, expected):
    assert excerpts(text) == expected


def test_decomposed_unicode_is_normalised_before_matching():
    text = unicodedata.normalize("NFD", "Viết theo dàn ý.")
    assert excerpts(text) == ["theo dàn ý"]


@pytest.mark.parametrize(
    "text",
    [
        "Nam ngồi lập dàn ý cho bài văn nghị luận, bút gõ lên bàn.",
        "Anh nghĩ một lúc rồi gật đầu.",
        "Cô viết chữ think big lên bảng, cả lớp cười.",
        "Bí mật ấy không lộ ra ngoài suốt ba năm.",
        "Hắn nhìn cái giá: a < b, rõ ràng thế.",
        "— Sư huynh, đệ uống rồi.",
    ],
)
def test_near_misses_are_clean(text):
    assert check_meta_leak(text) == []


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.txt")) + SAMPLE_STORY, ids=lambda p: p.name)
def test_clean_prose_has_no_meta_leak(path: Path):
    assert check_meta_leak(path.read_text(encoding="utf-8")) == []
