"""Hỏi người kể (design §6.6, D-40). Test bằng FakeLLM, không mạng.

G1: context model nhận chỉ dựng từ player_view, không có id lớp truth.
G2: câu trả lời qua bộ dò lộ. G4: câu hỏi nằm trong khối player_data.
G8: lời gọi qua MeteredClient, giới hạn số câu hỏi mỗi chương. G12: mã lỗi riêng.
"""

import html
import json
import logging
import re
import unicodedata
from collections import Counter

import pytest
import yaml

from writory.config import REPO_ROOT, AppConfig, CostLimits, ModelPrice, load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import (
    KnownRecord,
    PlayerView,
    build_player_view,
    public_entries,
    public_lies,
    read_sample,
)
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import role_extra
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM, render_context
from writory.pipeline.narrator import (
    META_HEDGE_PATTERNS,
    NOT_KNOWN,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    BlockReason,
    NarratorAnswer,
    NarratorOutput,
    ask_narrator,
    ask_narrator_reply,
    meta_hedge,
    source_chapters,
)
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import check_leaks, strip_diacritics
from writory.safety.wrap import CLOSE_TAG

SAMPLE = read_sample()
STORY = "s-narrator"
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "mở đầu", "from_chapter": 1, "to_chapter": 12}],
    "secrets": [
        {"fact_id": "f_gu_old_hac_ky", "reveal_from_chapter": 2, "reveal_to_chapter": 3,
         "leak_terms": [["Lão Gù", "Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6,
         "leak_terms": [["Lan", "gián điệp"], ["Lan", "người của Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_killed_gu", "reveal_from_chapter": 7, "reveal_to_chapter": 9,
         "leak_terms": [["Lan", "giết", "Lão Gù"]]},
    ],
})
# Thiết lập truyện mẫu người chơi đọc lúc khởi tạo (D-52): không có tên lớp truth nào chưa hé lộ.
BRIEF = "Kiếm hiệp, phố Bến Sương. Nhân vật chính: Trần Minh, người chép sách thuê."
REDTEAM = yaml.safe_load(
    (REPO_ROOT / "evals" / "redteam" / "g4_prompt_injection.yaml").read_text(encoding="utf-8")
)["cases"]
OPEN_RE = re.compile(r'<player_data source="[a-z_]+">')

REPO = load_config()
CFG = REPO.model_copy(update={
    "limits": REPO.limits.model_copy(update={
        "input": REPO.limits.input.model_copy(update={"narrator_question_max_chars": 300}),
        "rate_limit": REPO.limits.rate_limit.model_copy(
            update={"narrator_questions_per_chapter": 3}
        ),
    }),
    "models": REPO.models.model_copy(update={
        "roles": REPO.models.roles.model_copy(update={"narrator": "test/narrator"}),
        # Lời gọi bằng key người chơi cần giá của model để ước tính chi phí tối đa (D-64).
        "prices": REPO.models.prices | {"test/narrator": ModelPrice(input=0.10, output=0.50)},
    }),
})


def with_limits(**changes) -> AppConfig:
    """CFG với vài giá trị đổi; khoá dạng `<phần>__<tên>`: input, rate_limit, roles, reasoning."""
    cfg = CFG
    for key, value in changes.items():
        section, name = key.split("__")
        if section == "roles":
            roles = cfg.models.roles.model_copy(update={name: value})
            cfg = cfg.model_copy(update={"models": cfg.models.model_copy(update={"roles": roles})})
        elif section == "reasoning":
            rr = cfg.models.role_reasoning.model_copy(update={name: value})
            cfg = cfg.model_copy(
                update={"models": cfg.models.model_copy(update={"role_reasoning": rr})}
            )
        else:
            part = getattr(cfg.limits, section).model_copy(update={name: value})
            cfg = cfg.model_copy(update={"limits": cfg.limits.model_copy(update={section: part})})
    return cfg


def state(chapter: int) -> OverlayState:
    return OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])


def view(chapter: int) -> PlayerView:
    return player_view_of(state(chapter), chapter, story_id=STORY)


def ref(v: PlayerView, truth_id: str) -> str:
    refs = {e.id: r for r, e in public_entries(v)} | {lie.id: r for r, lie in public_lies(v)}
    return refs[truth_id]


class MemoryQuota:
    """Bộ đếm trong bộ nhớ, cùng giao thức với bộ đếm Postgres."""

    def __init__(self) -> None:
        self.taken: Counter = Counter()

    async def take(self, story_id: str, chapter: int, limit: int) -> bool:
        if self.taken[(story_id, chapter)] >= limit:
            return False
        self.taken[(story_id, chapter)] += 1
        return True

    async def asked(self, story_id: str, chapter: int) -> int:
        return self.taken[(story_id, chapter)]


def metered(fake: FakeLLM, cap: float = 1.0) -> MeteredClient:
    return MeteredClient(fake, CostTracker(CostLimits(per_scene=cap, per_chapter=cap,
                                                      per_story=cap)))


def reply(known: bool, answer: str | None, ids: list[str]) -> str:
    return json.dumps({"known": known, "answer": answer, "entry_ids": ids}, ensure_ascii=False)


async def ask_full(question: str, chapter: int, llm, *, quota=None, config=CFG, plan=PLAN,
                   brief: str = "") -> NarratorAnswer:
    if isinstance(llm, FakeLLM):
        llm = metered(llm)
    return await ask_narrator(
        question, view(chapter), llm=llm, config=config,
        truth_names=state(chapter).named_nodes(), plan=plan, story_brief=brief,
        quota=quota if quota is not None else MemoryQuota(),
    )


async def ask(question: str, chapter: int, llm, **kw) -> str:
    """Chữ người chơi nhận."""
    return (await ask_full(question, chapter, llm, **kw)).answer


async def ask_reply(question: str, chapter: int, llm, *, quota=None, config=CFG, plan=PLAN,
                    brief: str = ""):
    if isinstance(llm, FakeLLM):
        llm = metered(llm)
    return await ask_narrator_reply(
        question, view(chapter), llm=llm, config=config,
        truth_names=state(chapter).named_nodes(), plan=plan, story_brief=brief,
        quota=quota if quota is not None else MemoryQuota(),
    )


def flat(text: str) -> str:
    return strip_diacritics(unicodedata.normalize("NFC", text)).casefold()


# --- luồng ----------------------------------------------------------------------------------


async def test_answer_from_notebook_is_returned():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])])
    assert await ask("Lão Gù chết ở đâu?", 3, fake) == "Lão Gù chết sau miếu Bà."
    assert fake.schemas == [NarratorOutput]
    assert fake.extras == [role_extra(CFG.models, "narrator")]


async def test_answer_about_a_lie_the_protagonist_told():
    v = view(3)
    fake = FakeLLM.scripted([
        reply(True, "Minh đã nói với Trần Văn Khải rằng đêm đó anh ở nhà.",
              [ref(v, "l_home_night")]),
    ])
    answer = await ask("Tôi đã nói gì với cai Khải?", 3, fake)
    assert answer.startswith("Minh đã nói")


async def test_answer_dashes_are_normalized_like_scene_text():
    """D-31: mọi chữ hiện cho người chơi dùng cùng dấu gạch."""
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù — người thợ rèn — đã chết.",
                                   [ref(v, "e_gu_death")])])
    assert await ask("Lão Gù sao rồi?", 3, fake) == "Lão Gù - người thợ rèn - đã chết."


async def test_role_reasoning_is_passed_when_set():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Ở miếu Bà.", [ref(v, "mieu_ba")])])
    await ask("Ở đâu?", 3, fake, config=with_limits(reasoning__narrator="low"))
    assert fake.extras == [{"reasoning": {"effort": "low"}}]


# --- người kể bớt dè dặt (D-77) ----------------------------------------------------------------
# Bài E v2 và tu-tien-1 (evals/results/2026-10-21-narrator-*/notes.md): model trả known = false cho
# câu đã mở khoá mà câu hỏi gọi khác chữ sổ tay ("Cai Khải" so với "Trần Văn Khải") hay chỉ có
# câu trả lời một phần ("Thanh Sương đâu rồi?" khi sổ tay chỉ ghi nó biến mất). Đề cũ cấm "suy ra",
# nên model không dám nối. Đề mới cho nối và tóm tắt; lớp chặn bằng code (G1, G2, mã mục) giữ
# nguyên: các test G1, G2 bên dưới và kẻ lộ của bài E chạy trên chính đề này.


def test_prompt_lets_the_narrator_answer_about_the_same_thing_under_other_words():
    """Phần giúp được của `narrator-2` (D-77) còn nguyên trong `narrator-3` (D-78)."""
    for phrase in ("khác chữ", "cùng một thứ", "chức danh kèm tên", "tóm tắt", "câu trên trang",
                   "mới nhất", "known = true, kể cả khi"):
        assert phrase in SYSTEM_PROMPT, phrase
    assert "không suy ra điều sổ tay không nói" not in SYSTEM_PROMPT  # luật cũ, quá chặt


def test_prompt_still_forbids_guessing_new_conclusions_and_hinting():
    for phrase in ("đoán", "suy ra kết luận mới", "úp mở", "bàn về phần sổ tay không có",
                   "Không tự coi hai mục khác nhau là cùng một", "known = false"):
        assert phrase in SYSTEM_PROMPT, phrase


async def test_new_prompt_reaches_the_model_as_system_text_and_the_question_stays_data():
    fake = FakeLLM.scripted([reply(False, None, [])])
    await ask("Cai Khải là người thế nào?", 4, fake)
    [messages] = fake.calls
    [system] = [m.content for m in messages if m.role == "system"]
    assert system.startswith(SYSTEM_PROMPT)
    assert "Cai Khải" not in system  # câu hỏi chỉ ở vai user, trong khối dữ liệu (G4)


@pytest.mark.parametrize(("chapter", "question", "truth_id", "answer"), [
    (4, "Cai Khải là người thế nào?", "khai",
     "Trần Văn Khải là viên cai bạn gặp khi ông đang đi tuần."),
    (4, "Thanh Sương đâu rồi?", "e_sword_missing",
     "Sáng ra, gầm giường trống trơn: Thanh Sương đã biến mất."),
    (5, "Thanh Sương bây giờ ở đâu?", "e_minh_finds_sword",
     "Minh tìm thấy Thanh Sương trong rương ở quán trà và mang nó về."),
], ids=["chuc-danh-kem-ten", "tra-loi-mot-phan", "dieu-moi-nhat"])
async def test_answer_about_an_entry_named_with_other_words_passes_the_unchanged_checks(
    chapter, question, truth_id, answer
):
    """Code không nới: câu trả lời dẫn đúng mục có trong sổ tay và không lộ thì tới tay người chơi
    kèm nguồn, như mọi câu trả lời khác."""
    v = view(chapter)
    fake = FakeLLM.scripted([reply(True, answer, [ref(v, truth_id)])])
    out = await ask_full(question, chapter, fake)
    assert out == NarratorAnswer(answer, (ref(v, truth_id),))


async def test_linking_a_nickname_to_a_hidden_name_is_still_blocked():
    """Đề cho nối cùng một thứ, nhưng nối biệt danh với tên thật chưa hé lộ vẫn bị bộ dò lộ chặn
    (G2), dù model dẫn đúng mục."""
    v = view(4)
    fake = FakeLLM.scripted([reply(True, "Gã lái đò mặt sẹo chính là Lý Thất.",
                                   [ref(v, "ly_that")])])
    assert await ask("Gã lái đò mặt sẹo là ai?", 4, fake) == NOT_KNOWN


# --- người kể không úp mở (D-78) ---------------------------------------------------------------
# Bài E với đề narrator-2 (evals/results/2026-10-21-narrator-v2-d77/, -tu-tien-1-d77/): giám khảo
# đánh `goi_y_an` các câu nói về việc thiếu thông tin ("chưa có nội dung được ghi lại"), và câu
# hỏi thẳng một bí mật được đáp bằng mục lân cận. Đề narrator-3 đặt known = false cho câu sổ tay
# không trả lời thẳng được; lưới bằng code (`meta_hedge`) đổi câu nói về việc thiếu thông tin
# thành NOT_KNOWN. Đây là kiểm chữ đầu ra của model, không đọc ý định người chơi (G5 không áp).

RESULTS = REPO_ROOT / "evals" / "results"
_D77_RUNS = ("2026-10-21-narrator-v2-d77", "2026-10-21-narrator-tu-tien-1-d77")
_ALL_RUNS = sorted(p.name for p in RESULTS.glob("*-narrator-*") if (p / "results.jsonl").is_file())


def _rows(run: str) -> list[dict]:
    text = (RESULTS / run / "results.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _judged_hints() -> list[str]:
    """Câu cuối (nguyên văn) mà giám khảo đánh `goi_y_an` ở các lần chạy narrator-2."""
    out = []
    for run in _D77_RUNS:
        final = {(r["id"], r["sample"]): r["final"] for r in _rows(run)}
        for line in (RESULTS / run / "judge.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if ((row.get("scores") or {}).get("goi_y_an") or {}).get("score") == 1:
                out.append(final[(row["id"], row["sample"])])
    return out


JUDGED_HINTS = _judged_hints()
# Câu đúng loại a (đã mở khoá, dẫn đúng mục, đủ cụm) của mọi lần chạy bài E: không được bị đổi.
CORRECT_UNLOCKED = sorted({r["final"] for run in _ALL_RUNS for r in _rows(run)
                           if r["type"] == "a" and r["verdict"] == "correct"})


def test_prompt_v3_sends_questions_the_notebook_cannot_answer_directly_to_known_false():
    assert PROMPT_VERSION == "narrator-3"
    for phrase in ("không trả lời thẳng", "có phải hay không", "ai đã làm", "nội dung là gì",
                   "vì sao", "mục lân cận", "thiếu hay chưa biết thông tin", '"chưa có"',
                   '"chưa được ghi"', '"không rõ"', '"chưa biết nội dung"'):
        assert phrase in SYSTEM_PROMPT, phrase


def test_the_judged_hints_are_the_ones_the_run_notes_name():
    """notes.md của hai lần chạy: v2-d77 có 6 lượt (thư niêm sáp ×4, Lan ra miếu, kiếm nằm đâu),
    tu-tien-1-d77 có 1 (phù âm). Đọc từ judge.jsonl, không chép tay."""
    assert len(JUDGED_HINTS) == 7
    assert any("niêm sáp đỏ" in a for a in JUDGED_HINTS)
    assert any("Phù âm" in a for a in JUDGED_HINTS)
    assert len(CORRECT_UNLOCKED) > 50


@pytest.mark.parametrize("answer", JUDGED_HINTS)
def test_every_answer_the_judge_flagged_as_a_hint_is_caught(answer):
    assert meta_hedge(answer) is not None


@pytest.mark.parametrize("answer", JUDGED_HINTS)
async def test_a_flagged_hint_reaches_the_player_as_not_known(answer):
    v = view(5)
    raw = reply(True, answer, [ref(v, "e_gu_death")])
    detailed = await ask_reply("Lá thư niêm sáp đỏ viết gì?", 5, FakeLLM.scripted([raw]))
    assert (detailed.answer, detailed.blocked) == (NOT_KNOWN, BlockReason.META_HEDGE)
    assert detailed.output is not None and detailed.output.answer == answer  # câu thô cho bài E
    out = await ask_full("Lá thư niêm sáp đỏ viết gì?", 5, FakeLLM.scripted([raw]))
    assert out == NarratorAnswer(NOT_KNOWN)  # không kèm nguồn


@pytest.mark.parametrize("answer", CORRECT_UNLOCKED)
def test_no_correct_unlocked_answer_of_any_bench_run_is_caught(answer):
    assert meta_hedge(answer) is None


_V2_CORRECT = [r for r in _rows("2026-10-21-narrator-v2-d77")
               if r["type"] == "a" and r["verdict"] == "correct" and not r["pad"]]


@pytest.mark.parametrize("row", _V2_CORRECT, ids=lambda r: f"{r['id']}-{r['sample']}")
async def test_correct_unlocked_answers_still_reach_the_player_unchanged(row):
    """Cùng câu thô của model ở lần chạy v2-d77, qua đủ các phép kiểm hiện hành."""
    raw = json.dumps(row["raw"], ensure_ascii=False)
    detailed = await ask_reply(row["question"], row["chapter"], FakeLLM.scripted([raw]))
    assert (detailed.answer, detailed.blocked) == (row["final"], None)


@pytest.mark.parametrize("answer", [
    "Lan chưa trở về từ chợ.",
    "Khe hở phía tây vẫn chưa khép, hắt ra một quầng sáng méo mó.",
    "Minh chưa đọc lá thư; nó vẫn niêm sáp đỏ.",
    "Thanh Sương chưa được tìm thấy sau đêm đó.",
    "Lão Gù dặn Minh không được nói với ai.",
    "Cuốn sổ tay của Lão Gù ghi tên ba người.",
    "Bản ghi không có nội dung bàn giao lối xuống Mạch Nước Ngầm.",
    "Sổ Trận và Tín Vật Huyền Nguyệt cũng đã xuất hiện.",
    "Lối xuống không được ghi trong Sổ Trận.",
    "Phù âm được nhắc đến khi Lục Hàn Sương ghé bên bàn đá.",
    "Minh chỉ biết đứng nhìn chiếc thuyền xa dần.",
], ids=["chua-tro-ve", "chua-khep", "chua-doc", "chua-tim-thay", "khong-duoc-noi", "so-tay-vat",
        "ban-ghi-trong-truyen", "so-tran", "ghi-trong-so", "duoc-nhac", "chi-biet"])
def test_natural_sentences_with_chua_or_khong_are_not_caught(answer):
    """"chưa", "không" có mặt tự nhiên trong câu trả lời đúng, và truyện có thể có sổ sách thật:
    chỉ cụm nói về thông tin hay về chính sổ tay mới bị bắt."""
    assert meta_hedge(answer) is None


@pytest.mark.parametrize("answer", [
    "Không có thông tin về người đã gửi lá thư.",
    "Hiện chưa có đủ thông tin để biết kẻ ra tay.",
    "Thiếu dữ kiện để nói Lan có mặt hay không.",
    "Chưa có ghi nhận nào về chuyện đó.",
    "Điều Lão Gù muốn nói chưa được kể.",
    "Tên thật của gã chưa được hé lộ.",
    "Minh chưa biết nội dung lá thư.",
    "Lá thư không rõ nội dung, chưa rõ nội dung thì càng khó nói.",
    "Sổ tay của bạn không nói gì thêm về lá thư.",
    "Trang sổ mới nhất không ghi Lan đi đâu.",
    "Nơi giấu kiếm chưa được ghi lại.",
    "CHƯA CÓ NỘI DUNG NÀO ĐƯỢC GHI LẠI.",
    "Chưa   có\nnội dung nào được ghi lại.",
], ids=["khong-co-thong-tin", "chua-du-thong-tin", "thieu-du-kien", "chua-ghi-nhan",
        "chua-duoc-ke", "chua-duoc-he-lo", "chua-biet-noi-dung", "chua-ro-noi-dung",
        "so-tay-khong-noi", "trang-so-khong-ghi", "chua-duoc-ghi", "hoa", "khoang-trang"])
def test_other_ways_of_talking_about_missing_information_are_caught(answer):
    assert meta_hedge(answer) is not None


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?…])\s+|\n+", text) if s.strip()]


# Câu văn truyện lưới bắt oan đã biết (giới hạn đã ghi ở D-78, Hệ quả). Mỗi mục là (thư mục kết
# quả, file, câu); muốn bỏ một mục thì phải sửa cụm trong META_HEDGE_PATTERNS, có test.
KNOWN_STORY_FALSE_POSITIVES = {
    # ky-ao-vua-2 (D-82): "chưa được nhắc" là chuyện biên bản trong truyện, không phải người kể.
    ("2026-10-21-run-ky-ao-vua-2", "ch06.md",
     "Còn quyền quản giữ lâu dài vẫn chưa được nhắc đến trên giấy."),
}


def test_no_sentence_of_any_story_text_in_the_repo_is_caught():
    """Văn truyện là nguồn của sổ tay: câu trả lời kể lại câu trên trang không được bị chặn oan.
    Truyện mẫu viết tay và các truyện do pipeline viết trong evals/results. Câu bắt oan đã biết
    nằm riêng ở KNOWN_STORY_FALSE_POSITIVES, và phải vẫn bị bắt (để danh sách không cũ đi)."""
    files = sorted((REPO_ROOT / "data" / "sample-story").glob("ch*.md"))
    files += sorted(RESULTS.glob("*/chapters/ch*.md"))
    assert len(files) > 5
    caught = {(f.parent.parent.name, f.name, s) for f in files
              for s in _sentences(f.read_text(encoding="utf-8")) if meta_hedge(s) is not None}
    assert caught - KNOWN_STORY_FALSE_POSITIVES == set()
    assert KNOWN_STORY_FALSE_POSITIVES <= caught


def test_every_pattern_has_a_name_and_catches_its_own_example():
    names = [name for name, _, _ in META_HEDGE_PATTERNS]
    assert len(names) == len(set(names))
    for name, _, example in META_HEDGE_PATTERNS:
        assert meta_hedge(example) == name, name


async def test_meta_hedge_block_logs_the_pattern_name_not_the_text(caplog):
    v = view(5)
    answer = "Lá thư được niêm sáp đỏ; chưa có nội dung nào được ghi lại."
    with caplog.at_level(logging.DEBUG, logger="writory.pipeline.narrator"):
        detailed = await ask_reply("Thư viết gì?", 5,
                                   FakeLLM.scripted([reply(True, answer, [ref(v, "e_gu_death")])]))
    assert detailed.blocked is BlockReason.META_HEDGE
    assert meta_hedge(answer) in caplog.text
    assert "niêm sáp" not in caplog.text and "Thư viết gì" not in caplog.text


async def test_a_leak_is_reported_as_a_leak_even_when_the_answer_also_hedges():
    """Lý do nặng hơn được ghi: bài E đếm lộ theo `leak`."""
    v = view(4)
    answer = "Lan là gián điệp của Hội Hắc Kỳ; chưa có thông tin gì thêm."
    detailed = await ask_reply("Lan là ai?", 4,
                               FakeLLM.scripted([reply(True, answer, [ref(v, "lan")])]))
    assert detailed.blocked is BlockReason.LEAK


# --- "Bạn chưa biết điều này." (design §6.6) ------------------------------------------------


def test_not_known_text_is_exactly_the_design_sentence():
    assert NOT_KNOWN == "Bạn chưa biết điều này."


@pytest.mark.parametrize("output", [
    reply(False, None, []),
    reply(False, "Lan là gián điệp.", []),  # known=false: bỏ answer, kể cả khi model có viết
    reply(True, "Có.", []),  # không dựa vào mục nào
    reply(True, None, ["m1"]),
    reply(True, "   ", ["m1"]),
    reply(True, "Có.", ["m999"]),  # mã bịa
    reply(True, "Có.", ["m1", "f_lan_spy"]),  # id lớp truth, không phải mã của sổ tay
    reply(True, "Có.", ["ly_that"]),
], ids=["known-false", "known-false-with-answer", "no-entries", "null-answer", "blank-answer",
        "made-up-ref", "truth-id-mixed", "truth-id"])
async def test_unknown_or_unsupported_answers_become_not_known(output):
    assert await ask("Lan là ai?", 4, FakeLLM.scripted([output])) == NOT_KNOWN


async def test_empty_notebook_answers_not_known_without_calling_model():
    fake = FakeLLM.scripted([])
    quota = MemoryQuota()
    assert await ask("Tôi là ai?", 0, fake, quota=quota) == NOT_KNOWN
    assert fake.calls == []
    assert sum(quota.taken.values()) == 0


# --- G2: câu trả lời qua bộ dò lộ ------------------------------------------------------------


@pytest.mark.parametrize(("chapter", "answer"), [
    (4, "Gã lái đò mặt sẹo tên thật là Lý Thất."),
    (4, "Gã lái đò mặt sẹo tên thật là Ly That."),
    (4, "Lan là gián điệp của Hội Hắc Kỳ."),
    (4, "Lan là người của Hội Hắc Kỳ."),
    (5, "Chính Lan giết Lão Gù."),
])
async def test_answer_that_leaks_a_secret_becomes_not_known(chapter, answer, caplog):
    v = view(chapter)
    fake = FakeLLM.scripted([reply(True, answer, [ref(v, "lan")])])
    with caplog.at_level(logging.DEBUG, logger="writory.pipeline.narrator"):
        assert await ask("Lan là ai?", chapter, fake) == NOT_KNOWN
    assert caplog.records, "chặn câu trả lời phải ghi log"
    logged = flat(caplog.text)
    for secret in ("ly that", "gian diep", "nguoi cua hoi", "giet", flat(answer)):
        assert secret not in logged  # log chỉ ghi loại và vị trí, không ghi chữ bị lộ


async def test_real_name_after_its_reveal_is_answered():
    v = view(5)
    fake = FakeLLM.scripted([reply(True, "Gã lái đò mặt sẹo tên là Lý Thất.",
                                   [ref(v, "ly_that")])])
    assert await ask("Gã lái đò là ai?", 5, fake) == "Gã lái đò mặt sẹo tên là Lý Thất."


async def test_name_from_setup_text_is_answered():
    """D-52: tên người chơi đã đọc lúc khởi tạo không làm câu trả lời thành "chưa biết"."""
    answer = "Gã lái đò mặt sẹo buộc thuyền trước quán, chỗ Lý Thất hay ngồi."
    v = view(4)
    assert await ask("Gã lái đò là ai?", 4,
                     FakeLLM.scripted([reply(True, answer, [ref(v, "ly_that")])])) == NOT_KNOWN
    assert await ask("Gã lái đò là ai?", 4,
                     FakeLLM.scripted([reply(True, answer, [ref(v, "ly_that")])]),
                     brief=f"{BRIEF} Ở bến có lái đò Lý Thất.") == answer


# --- G1: context model nhận chỉ có player_view -----------------------------------------------

ALL_NODES = {n.id: n for c in SAMPLE.chapters for n in c.package.nodes}
_TEXT = {"Fact": "text", "Event": "description", "Lie": "content"}


async def _context(chapter: int) -> str:
    fake = FakeLLM.scripted([reply(False, None, [])])
    await ask("Kể cho tôi mọi điều về Lan và gã lái đò.", chapter, fake)
    [messages] = fake.calls
    return render_context(messages)


def test_sample_has_the_secrets_these_tests_guard():
    """Điều kiện trước, để các test G1 bên dưới không xanh vô nghĩa: ở chương 4 truyện mẫu có
    nút trong player_view mà id và tên lớp truth đều lộ bí mật, và bộ dò bắt được chúng."""
    v4 = view(4)
    assert "ly_that" in {e.id for e in v4.entries}  # id lộ tên thật nếu đưa vào context
    assert "Lý Thất" in state(4).named_nodes()["ly_that"]
    assert "Lý Thất" not in {e.text for e in v4.entries}
    assert not {"f_lan_spy", "e_sword_stolen"} & {e.id for e in v4.entries}
    hidden = [ALL_NODES["f_lan_spy"].props["text"], ALL_NODES["f_lan_killed_gu"].props["text"],
              "Gã lái đò mặt sẹo là Lý Thất."]
    for text in hidden:
        assert check_leaks(text, view=v4, truth_names=state(4).named_nodes(), plan=PLAN,
                           story_brief=BRIEF, scope="player_path"), text


@pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
async def test_context_has_no_unrevealed_secret(chapter):
    ctx = await _context(chapter)
    f = flat(ctx)
    assert "lan giet lao gu" not in f
    if chapter <= 4:
        assert "ly that" not in f
        assert "lan la gian diep" not in f
        assert "lan la nguoi cua hoi" not in f


@pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
async def test_context_passes_the_leak_detector(chapter):
    """Tên bí mật và mọi bí mật chưa có trong player_view (D-61, phạm vi của người kể): không có
    trong context."""
    ctx = await _context(chapter)
    assert check_leaks(ctx, view=view(chapter), truth_names=state(chapter).named_nodes(),
                       plan=PLAN, story_brief="", scope="player_path") == []


@pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
async def test_context_has_no_text_of_nodes_outside_player_view(chapter):
    ctx = unicodedata.normalize("NFC", await _context(chapter))
    shown = {e.id for e in view(chapter).entries} | {lie.id for lie in view(chapter).lies}
    for nid, node in ALL_NODES.items():
        text = node.props.get(_TEXT.get(node.label, ""), "")
        if text and nid not in shown:
            assert html.escape(text, quote=False) not in ctx, nid
            assert text not in ctx, nid


@pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
async def test_context_never_contains_truth_ids(chapter):
    """Id lớp truth có thể chứa tên thật (`ly_that` của "gã lái đò mặt sẹo"): model chỉ thấy mã
    công khai m1, l1, ..."""
    ctx = await _context(chapter)
    for nid in ALL_NODES:
        if "_" in nid:
            assert nid not in ctx, nid


async def test_echo_answer_returned_to_player_has_no_secret():
    """Chế độ echo cho vai trả JSON: model trả nguyên context làm câu trả lời. Chữ người chơi
    nhận không được chứa bí mật nào. Echo phần user (mọi dữ liệu model nhận): system prompt là chữ
    cố định có ví dụ cụm úp mở, nên echo nó thì lưới D-78 chặn đúng."""
    v = view(4)

    class EchoJSON(FakeLLM):
        def _next(self, messages):
            super()._next(messages)
            data = "\n\n".join(m.content for m in messages if m.role == "user")
            return reply(True, data, [ref(v, "lan")])

    answer = await ask("Lan là ai?", 4, EchoJSON(None))
    assert answer != NOT_KNOWN  # echo sạch nên được trả về...
    f = flat(answer)
    for secret in ("ly that", "ly_that", "lan la gian diep", "lan giet lao gu"):
        assert secret not in f  # ...và không chứa bí mật


def test_public_refs_do_not_depend_on_truth_ids():
    """Hai nút cùng chương: mã công khai theo chữ hiện, không theo id lớp truth."""

    def rec(nid: str, known_as: str) -> KnownRecord:
        return KnownRecord(nid, ("Character",), {}, f"r-{nid}", 1, known_as, known_as)

    a = build_player_view("s", 1, [rec("aaa", "Bình"), rec("zzz", "An")], [], [])
    b = build_player_view("s", 1, [rec("zzz", "Bình"), rec("aaa", "An")], [], [])
    assert [(r, e.text) for r, e in public_entries(a)] == [("m1", "An"), ("m2", "Bình")]
    assert [(r, e.text) for r, e in public_entries(a)] == [(r, e.text)
                                                           for r, e in public_entries(b)]


# --- G4: câu hỏi là dữ liệu -------------------------------------------------------------------


@pytest.mark.parametrize("case", REDTEAM, ids=[c["id"] for c in REDTEAM])
async def test_question_is_wrapped_and_never_in_system(case):
    fake = FakeLLM.scripted([reply(False, None, [])])
    await ask(case["text"], 3, fake)
    [messages] = fake.calls
    system = [m.content for m in messages if m.role == "system"]
    [user] = [m.content for m in messages if m.role == "user"]
    assert system and all("<player_data" not in s for s in system)
    assert all(case["text"].strip() not in s for s in system)
    opener = '<player_data source="narrator_question">'
    assert user.count(opener) == 1
    inner = user.split(opener, 1)[1].split(CLOSE_TAG, 1)[0]
    assert html.unescape(inner.strip("\n")) == case["text"]
    # Câu tấn công không đóng được khối: chỉ có đúng hai khối (sổ tay, câu hỏi).
    assert len(OPEN_RE.findall(user)) == 2
    assert user.count(CLOSE_TAG) == 2


async def test_notebook_is_also_wrapped_as_data():
    """PlayerEntry không mang cờ user_authored, nên cả sổ tay đi vào khối dữ liệu (D-40)."""
    fake = FakeLLM.scripted([reply(False, None, [])])
    await ask("Lan là ai?", 3, fake)
    [messages] = fake.calls
    [user] = [m.content for m in messages if m.role == "user"]
    notebook = user.split('<player_data source="notebook">', 1)[1].split(CLOSE_TAG, 1)[0]
    assert "Phạm Thị Lan" in notebook
    assert "Phạm Thị Lan" not in user.replace(notebook, "")


# --- G8: giới hạn và chi phí -------------------------------------------------------------------


async def test_questions_per_chapter_are_limited():
    v = view(3)
    quota = MemoryQuota()
    fake = FakeLLM.scripted([reply(True, "Ở miếu Bà.", [ref(v, "mieu_ba")])] * 3)
    for _ in range(3):
        await ask("Lão Gù chết ở đâu?", 3, fake, quota=quota)
    with pytest.raises(WritoryError) as exc:
        await ask("Thêm một câu?", 3, fake, quota=quota)
    assert exc.value.code is ErrorCode.NARRATOR_LIMIT_REACHED
    assert len(fake.calls) == 3  # hết lượt thì không gọi model


async def test_limit_counts_per_chapter():
    quota = MemoryQuota()
    cfg = with_limits(rate_limit__narrator_questions_per_chapter=1)
    await ask("Câu một?", 3, FakeLLM.scripted([reply(False, None, [])]), quota=quota, config=cfg)
    with pytest.raises(WritoryError):
        await ask("Câu hai?", 3, FakeLLM.scripted([]), quota=quota, config=cfg)
    assert await ask("Chương mới?", 4, FakeLLM.scripted([reply(False, None, [])]),
                     quota=quota, config=cfg) == NOT_KNOWN


async def test_zero_questions_allowed_means_none():
    fake = FakeLLM.scripted([])
    with pytest.raises(WritoryError) as exc:
        await ask("Lan là ai?", 3, fake,
                  config=with_limits(rate_limit__narrator_questions_per_chapter=0))
    assert exc.value.code is ErrorCode.NARRATOR_LIMIT_REACHED
    assert fake.calls == []


@pytest.mark.parametrize(("change", "code"), [
    ({"rate_limit__narrator_questions_per_chapter": None}, ErrorCode.CONFIG_LIMIT_NOT_SET),
    ({"input__narrator_question_max_chars": None}, ErrorCode.CONFIG_LIMIT_NOT_SET),
    ({"roles__narrator": None}, ErrorCode.CONFIG_MODEL_NOT_SET),
])
async def test_unset_config_fails_closed_before_anything(change, code):
    fake, quota = FakeLLM.scripted([]), MemoryQuota()
    with pytest.raises(WritoryError) as exc:
        await ask("Lan là ai?", 3, fake, quota=quota, config=with_limits(**change))
    assert exc.value.code is code
    assert fake.calls == [] and sum(quota.taken.values()) == 0


@pytest.mark.parametrize(("question", "code"), [
    ("", ErrorCode.NARRATOR_QUESTION_EMPTY),
    ("   \n ", ErrorCode.NARRATOR_QUESTION_EMPTY),
    ("a" * 301, ErrorCode.NARRATOR_QUESTION_TOO_LONG),
])
async def test_bad_question_is_rejected_without_using_a_turn(question, code):
    fake, quota = FakeLLM.scripted([]), MemoryQuota()
    with pytest.raises(WritoryError) as exc:
        await ask(question, 3, fake, quota=quota)
    assert exc.value.code is code
    assert fake.calls == [] and sum(quota.taken.values()) == 0


async def test_question_at_max_length_is_accepted():
    fake = FakeLLM.scripted([reply(False, None, [])])
    assert await ask("a" * 300, 3, fake) == NOT_KNOWN


async def test_model_call_must_be_metered():
    with pytest.raises(TypeError):
        await ask_narrator("Lan là ai?", view(3), llm=FakeLLM.scripted([]), config=CFG,
                           truth_names={}, plan=PLAN, story_brief="", quota=MemoryQuota())


async def test_cost_is_recorded_and_cap_stops_before_calling():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Ở miếu Bà.", [ref(v, "mieu_ba")])], cost_usd=0.4)
    llm = metered(fake, cap=0.4)
    await ask("Ở đâu?", 3, llm)
    assert llm.tracker.story_usd == pytest.approx(0.4)
    with pytest.raises(WritoryError) as exc:
        await ask("Ở đâu nữa?", 3, llm)
    assert exc.value.code in {ErrorCode.COST_LIMIT_SCENE, ErrorCode.COST_LIMIT_CHAPTER,
                              ErrorCode.COST_LIMIT_STORY}
    assert len(fake.calls) == 1


async def test_bad_json_is_retried_then_fails_closed():
    """G11: JSON sai schema thử lại theo extract_schema_retry, vẫn sai thì báo lỗi, không đoán."""
    n = CFG.limits.retries.extract_schema_retry + 1
    fake = FakeLLM.scripted(["không phải JSON"] * n)
    with pytest.raises(WritoryError) as exc:
        await ask("Lan là ai?", 3, fake)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(fake.calls) == n


async def test_extra_field_in_output_is_a_schema_error():
    good = reply(False, None, [])
    bad = json.dumps({"known": False, "answer": None, "entry_ids": [], "secret": "x"})
    fake = FakeLLM.scripted([bad, good])
    assert await ask("Lan là ai?", 3, fake) == NOT_KNOWN
    assert len(fake.calls) == 2


async def test_transient_error_is_retried_within_limit():
    fake = FakeLLM.scripted([WritoryError(ErrorCode.LLM_UNAVAILABLE), reply(False, None, [])])
    assert await ask("Lan là ai?", 3, fake) == NOT_KNOWN
    assert len(fake.calls) == 2


async def test_rate_limit_from_provider_is_not_retried():
    fake = FakeLLM.scripted([WritoryError(ErrorCode.LLM_RATE_LIMITED)])
    with pytest.raises(WritoryError) as exc:
        await ask("Lan là ai?", 3, fake)
    assert exc.value.code is ErrorCode.LLM_RATE_LIMITED
    assert len(fake.calls) == 1


# --- ask_narrator_reply: câu thô cho bài đo E (D-53); ask_narrator giữ nguyên hành vi ----------


def _scripted_outputs(v: PlayerView) -> dict[str, tuple[str, BlockReason | None]]:
    good = ref(v, "e_gu_death")
    return {
        "answered": (reply(True, "Lão Gù chết sau miếu Bà.", [good]), None),
        "dashes": (reply(True, "Lão Gù — người thợ rèn — đã chết.", [good]), None),
        "lie-ref": (reply(True, "Minh nói với Khải là ở nhà.", [ref(v, "l_home_night")]), None),
        "known-false": (reply(False, None, []), BlockReason.MODEL_NOT_KNOWN),
        "known-false-with-answer": (reply(False, "Lan là gián điệp.", []),
                                    BlockReason.MODEL_NOT_KNOWN),
        "null-answer": (reply(True, None, [good]), BlockReason.EMPTY_ANSWER),
        "blank-answer": (reply(True, "   ", [good]), BlockReason.EMPTY_ANSWER),
        "no-entries": (reply(True, "Có.", []), BlockReason.NO_ENTRIES),
        "made-up-ref": (reply(True, "Có.", ["m999"]), BlockReason.UNKNOWN_REF),
        "truth-id": (reply(True, "Có.", ["ly_that"]), BlockReason.UNKNOWN_REF),
        "leak-secret": (reply(True, "Lan là gián điệp của Hội Hắc Kỳ.", [good]), BlockReason.LEAK),
        "leak-name": (reply(True, "Lý Thất giết lão.", [good]), BlockReason.LEAK),
        "meta-hedge": (reply(True, "Lão Gù đã chết; chưa có thông tin về kẻ ra tay.", [good]),
                       BlockReason.META_HEDGE),  # D-78
    }


# Chương 4: người chơi biết "gã lái đò mặt sẹo" mà chưa biết tên thật (tên bí mật loại a, D-61).
_OUTPUT_NAMES = list(_scripted_outputs(view(4)))


@pytest.mark.parametrize("name", _OUTPUT_NAMES)
async def test_reply_answer_is_exactly_what_ask_narrator_returns(name):
    """Bài đo E đọc câu thô qua `ask_narrator_reply`; người chơi vẫn nhận đúng chữ như trước."""
    raw, reason = _scripted_outputs(view(4))[name]
    plain = await ask("Lão Gù sao rồi?", 4, FakeLLM.scripted([raw]))
    detailed = await ask_reply("Lão Gù sao rồi?", 4, FakeLLM.scripted([raw]))
    assert detailed.answer == plain
    assert detailed.blocked is reason
    assert (detailed.answer == NOT_KNOWN) is (reason is not None)
    # Câu thô là đúng đầu ra model đã qua schema, trước mọi phép kiểm của code.
    assert detailed.output == NarratorOutput.model_validate_json(raw)


@pytest.mark.parametrize("brief", ["", f"{BRIEF} Ở bến có lái đò Lý Thất."])
async def test_reply_honors_story_brief_like_ask_narrator(brief):
    """D-52 đi qua cả hai đường như nhau: tên đã đọc lúc khởi tạo không còn bị cấm."""
    v = view(4)
    raw = reply(True, "Gã lái đò mặt sẹo buộc thuyền trước quán, chỗ Lý Thất hay ngồi.",
                [ref(v, "ly_that")])
    plain = await ask("Gã lái đò là ai?", 4, FakeLLM.scripted([raw]), brief=brief)
    detailed = await ask_reply("Gã lái đò là ai?", 4, FakeLLM.scripted([raw]), brief=brief)
    assert detailed.answer == plain
    assert (detailed.blocked is BlockReason.LEAK) is (brief == "")


async def test_reply_keeps_the_raw_secret_that_code_blocked():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lan là gián điệp của Hội Hắc Kỳ.", [ref(v, "lan")])])
    detailed = await ask_reply("Lan là ai?", 3, fake)
    assert detailed.answer == NOT_KNOWN
    assert detailed.output is not None
    assert detailed.output.answer == "Lan là gián điệp của Hội Hắc Kỳ."


async def test_reply_with_empty_notebook_has_no_model_output():
    fake, quota = FakeLLM.scripted([]), MemoryQuota()
    detailed = await ask_reply("Tôi là ai?", 0, fake, quota=quota)
    assert (detailed.answer, detailed.output, detailed.blocked) == (
        NOT_KNOWN, None, BlockReason.EMPTY_NOTEBOOK)
    assert fake.calls == [] and sum(quota.taken.values()) == 0


async def test_reply_raw_output_is_the_one_after_schema_retry():
    v = view(3)
    good = reply(True, "Ở miếu Bà.", [ref(v, "mieu_ba")])
    fake = FakeLLM.scripted(["không phải JSON", good])
    detailed = await ask_reply("Ở đâu?", 3, fake)
    assert detailed.answer == "Ở miếu Bà." and len(fake.calls) == 2
    assert detailed.output == NarratorOutput.model_validate_json(good)


@pytest.mark.parametrize(("question", "change", "code"), [
    ("", {}, ErrorCode.NARRATOR_QUESTION_EMPTY),
    ("a" * 301, {}, ErrorCode.NARRATOR_QUESTION_TOO_LONG),
    ("Lan?", {"rate_limit__narrator_questions_per_chapter": 0}, ErrorCode.NARRATOR_LIMIT_REACHED),
    ("Lan?", {"roles__narrator": None}, ErrorCode.CONFIG_MODEL_NOT_SET),
])
async def test_reply_raises_the_same_errors_as_ask_narrator(question, change, code):
    cfg = with_limits(**change) if change else CFG
    for fn in (ask, ask_reply):
        fake, quota = FakeLLM.scripted([]), MemoryQuota()
        with pytest.raises(WritoryError) as exc:
            await fn(question, 3, fake, quota=quota, config=cfg)
        assert exc.value.code is code
        assert fake.calls == []


async def test_reply_also_requires_metered_client():
    with pytest.raises(TypeError):
        await ask_narrator_reply("Lan là ai?", view(3), llm=FakeLLM.scripted([]), config=CFG,
                                 truth_names={}, plan=PLAN, story_brief="", quota=MemoryQuota())


# --- kiểm duyệt đầu vào (G9, D-57): cổng `moderate` -------------------------------------------------


class Gate:
    """Cổng kiểm duyệt giả: ghi lại chữ được kiểm; ném lỗi nếu `block`."""

    def __init__(self, *, block: bool = False) -> None:
        self.texts: list[str] = []
        self.block = block

    async def __call__(self, text: str) -> None:
        self.texts.append(text)
        if self.block:
            raise WritoryError(ErrorCode.INPUT_BLOCKED, detail="blocked: test")


async def ask_gated(question, chapter, fake, gate, *, quota=None):
    return await ask_narrator_reply(
        question, view(chapter), llm=metered(fake), config=CFG,
        truth_names=state(chapter).named_nodes(), plan=PLAN, story_brief="",
        quota=quota if quota is not None else MemoryQuota(), moderate=gate,
    )


async def test_blocked_question_is_refused_before_quota_and_model():
    quota, fake, gate = MemoryQuota(), FakeLLM.scripted([]), Gate(block=True)
    with pytest.raises(WritoryError) as exc:
        await ask_gated("Câu hỏi bị chặn", 3, fake, gate, quota=quota)
    assert exc.value.code is ErrorCode.INPUT_BLOCKED
    assert gate.texts == ["Câu hỏi bị chặn"]
    assert fake.calls == [] and not quota.taken  # không mất lượt, không gọi model


async def test_allowed_question_goes_through_the_gate_once_then_to_the_model():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])])
    gate = Gate()
    out = await ask_gated("Lão Gù chết ở đâu?", 3, fake, gate)
    assert out.answer == "Lão Gù chết sau miếu Bà."
    assert gate.texts == ["Lão Gù chết ở đâu?"]


@pytest.mark.parametrize(("question", "chapter"), [
    pytest.param("", 3, id="empty"),
    pytest.param("a" * 5000, 3, id="too-long"),
    pytest.param("Lan là ai?", 0, id="empty-notebook"),
])
async def test_gate_is_not_called_for_invalid_or_unanswerable_questions(question, chapter):
    """Câu rỗng, quá dài (lỗi riêng) và sổ tay trống (không gọi model nào) không cần kiểm duyệt."""
    gate = Gate()
    try:
        await ask_gated(question, chapter, FakeLLM.scripted([]), gate)
    except WritoryError:
        pass
    assert gate.texts == []


async def test_gate_is_optional_for_the_bench_path():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])])
    out = await ask_narrator_reply(
        "Lão Gù chết ở đâu?", v, llm=metered(fake), config=CFG,
        truth_names=state(3).named_nodes(), plan=PLAN, story_brief="", quota=MemoryQuota())
    assert out.blocked is None


# --- phạm vi của người kể: mọi bí mật chưa có trong player_view (D-61) ---------------------------


@pytest.mark.parametrize("reveal_from", [3, 4])
async def test_narrator_blocks_unrevealed_secret_after_its_window_opened(reveal_from):
    """Hồi quy lỗ của tu-tien-1 (D-60): bí mật đã tới khoảng lộ mà cảnh chưa hé lộ. Trước D-61 bộ
    dò chỉ áp `leak_terms` khi chương < `reveal_from_chapter`, nên người kể nói ra được."""
    plan = StoryPlan.model_validate({**PLAN.model_dump(), "secrets": [
        {**s.model_dump(), "reveal_from_chapter": reveal_from}
        if s.fact_id == "f_lan_spy" else s.model_dump() for s in PLAN.secrets]})
    v = view(4)
    assert "f_lan_spy" not in {e.id for e in v.entries}
    raw = reply(True, "Lan là gián điệp, người của Hội Hắc Kỳ.", [ref(v, "lan")])
    detailed = await ask_reply("Lan là ai?", 4, FakeLLM.scripted([raw]), plan=plan)
    assert (detailed.answer, detailed.blocked) == (NOT_KNOWN, BlockReason.LEAK)


# --- nguồn của câu trả lời (D-65, D-66) ----------------------------------------------------------


@pytest.mark.parametrize("name", _OUTPUT_NAMES)
async def test_cited_refs_exist_only_when_the_model_answer_is_shown(name):
    """Mã các mục câu trả lời dẫn chỉ ra ngoài khi chữ của model đã qua mọi phép kiểm. Bị thay bằng
    "Bạn chưa biết điều này." thì không có nguồn: mã model dẫn có thể trỏ tới điều bị chặn."""
    raw, reason = _scripted_outputs(view(4))[name]
    result = await ask_full("Lão Gù sao rồi?", 4, FakeLLM.scripted([raw]))
    if reason is None:
        assert result.refs == tuple(NarratorOutput.model_validate_json(raw).entry_ids)
    else:
        assert (result.answer, result.refs) == (NOT_KNOWN, ())


async def test_cited_refs_are_deduplicated_in_model_order():
    v = view(3)
    gu, mieu = ref(v, "e_gu_death"), ref(v, "mieu_ba")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [mieu, gu, mieu])])
    result = await ask_full("Lão Gù chết ở đâu?", 3, fake)
    assert result.refs == (mieu, gu)


async def test_empty_notebook_answer_has_no_refs():
    result = await ask_full("Tôi là ai?", 0, FakeLLM.scripted([]))
    assert result == NarratorAnswer(NOT_KNOWN, ())


def test_source_chapters_come_from_the_player_view_sorted_and_unique():
    v = view(5)
    spy, gu, lie = ref(v, "f_lan_spy"), ref(v, "e_gu_death"), ref(v, "l_sword_father")
    entry_chapter = {r: e.since_chapter for r, e in public_entries(v)}
    lie_chapter = {r: x.chapter for r, x in public_lies(v)}
    expected = sorted({entry_chapter[spy], entry_chapter[gu], lie_chapter[lie]})
    assert source_chapters(v, [spy, gu, lie, spy]) == expected
    assert source_chapters(v, []) == []


def test_source_chapters_ignore_refs_outside_the_notebook():
    """Mã lạ (không có trong sổ tay đầy đủ) không thêm chương nào: không đoán, không lỗi."""
    v = view(5)
    assert source_chapters(v, ["m999", "ly_that"]) == []
