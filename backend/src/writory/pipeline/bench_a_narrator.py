"""Bài đo A, hai hệ người kể: đo độ đúng của đúng đường người kể của sản phẩm (D-143).

Khác sáu hệ bộ nhớ (`bench_a_systems`): không dựng ngữ cảnh cho một model trả lời chung, mà hỏi
`pipeline.narrator.ask_narrator_reply` như người chơi hỏi ở chương N: sổ tay từ `player_view` (D-40,
D-59), mã công khai, kiểm mã mục, bộ dò lộ, lưới úp mở. Chỉ khác nhau ở đoạn trên trang:

  narrator        đề `narrator-3`: chỉ sổ tay (`limits.narrator_pages.top_k` ép về 0).
  narrator_pages  đề `narrator-4`: sổ tay cộng đoạn BM25 trên văn chương 1..N (`limits.narrator_pages`
                  như sản phẩm; phải đang bật).

Hai hệ chỉ chạy khi nêu tên ở `--systems` (không thuộc bộ mặc định của run.yaml) và chỉ trên truyện
do pipeline viết (`story: run`): bộ dò lộ lúc chạy cần kế hoạch và thiết lập truyện của lần chạy
(`bench_e_story.load_run_story`). `player_view` dựng bằng `OverlayState` từ các gói chương như bài E,
không cần Neo4j. Câu "Bạn chưa biết điều này." tính là kiêng. Mỗi lượt ghi thêm lý do code chặn và
lộ theo bộ chấm chặt của bài E (`bench_e.Scorer`), kèm cờ chuỗi trúng có nằm trên trang đã đọc không.
"""

import html
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from writory.config import AppConfig, ConfigError
from writory.llm.base import Message
from writory.pipeline.bench_a_data import (
    BenchData,
    Question,
    _resolve_run_dir,
    oracle_answer,
    score_answer,
    wrong_answer,
)
from writory.pipeline.bench_e import (
    ChapterState,
    Scorer,
    _Unlimited,
    chapter_state,
    on_page,
    parse_narrator_messages,
)
from writory.pipeline.bench_e_story import Story, load_run_story
from writory.pipeline.narrator import (
    NOT_KNOWN,
    NarratorReply,
    ask_narrator_reply,
    build_messages,
    prompt_version,
    select_passages,
    system_parts,
)
from writory.pipeline.notebook import select_notebook
from writory.pipeline.passages import flat

NARRATOR_SYSTEMS = ("narrator", "narrator_pages")
NARRATOR_LABELS = {
    "narrator": "Người kể, chỉ sổ tay (narrator-3)",
    "narrator_pages": "Người kể, sổ tay + đoạn trên trang (narrator-4)",
}


def variant_config(system: str, config: AppConfig) -> AppConfig:
    """Config của hệ: `narrator` tắt đoạn trên trang; `narrator_pages` dùng đúng số của sản phẩm."""
    pages = config.limits.narrator_pages
    if system == "narrator":
        off = pages.model_copy(update={"top_k": 0})
        return config.model_copy(update={"limits": config.limits.model_copy(
            update={"narrator_pages": off})})
    if system == "narrator_pages":
        if not pages.top_k:
            raise ConfigError("hệ narrator_pages cần limits.narrator_pages.top_k > 0 (đang tắt)")
        return config
    raise ValueError(f"hệ người kể không biết: {system}")


def prompt_versions(config: AppConfig) -> dict[str, str | None]:
    """Đề của từng hệ, cho dấu vân tay: `narrator_pages` None khi config đang tắt đoạn trên trang."""
    on = bool(config.limits.narrator_pages.top_k)
    return {"narrator": prompt_version(variant_config("narrator", config)),
            "narrator_pages": prompt_version(config) if on else None}


def prompt_sha_parts() -> str:
    """Chữ vai system của cả hai đề, để băm vào dấu vân tay."""
    return "\n".join([*system_parts(False), *system_parts(True)])


@dataclass(frozen=True)
class NarratorSide:
    """Những gì hai hệ người kể cần ngoài dữ liệu bài A: truyện theo cách bài E đọc (kế hoạch, thiết
    lập truyện, gói, văn) và bộ chấm lộ chặt của bài E."""

    story: Story
    scorer: Scorer
    states: dict[int, ChapterState]

    @classmethod
    def load(cls, data: BenchData) -> "NarratorSide":
        story = run_story(data)
        assert story.plan is not None and story.brief is not None
        return cls(story, Scorer.build(story, story.plan, story.brief), {})

    def state(self, chapter: int) -> ChapterState:
        if chapter not in self.states:
            self.states[chapter] = chapter_state(self.story, chapter)
        return self.states[chapter]


def run_story(data: BenchData) -> Story:
    """Truyện của đề theo cách bài E đọc; truyện mẫu thì lỗi cấu hình."""
    if data.questions.story != "run" or data.questions.run_dir is None:
        raise ConfigError("hệ người kể chỉ chạy trên truyện do pipeline viết (`story: run`): "
                          "truyện mẫu không có kế hoạch truyện cho bộ dò lộ")
    return load_run_story(_resolve_run_dir(data.questions.run_dir))


def story_hashes(data: BenchData) -> dict[str, str] | None:
    """Hash các file bài A không tự khoá mà hai hệ người kể đọc (lựa chọn khởi tạo, meta của lần
    chạy); None với truyện mẫu."""
    if data.questions.story != "run":
        return None
    return {k: v for k, v in run_story(data).hashes.items()
            if k in ("run/setup.json", "run/meta.json")}


def seen_pages(data: BenchData, chapter: int) -> dict[int, str]:
    """Văn chương 1..`chapter`: đúng những gì người chơi đã đọc khi hỏi ở chương này."""
    return {c: t for c, t in data.story.items() if c <= chapter}


async def ask(q: Question, system: str, *, data: BenchData, side: NarratorSide, llm: Any,
              config: AppConfig) -> NarratorReply:
    state = side.state(q.ask_chapter)
    return await ask_narrator_reply(
        q.question, state.view, llm=llm, config=variant_config(system, config),
        truth_names=state.truth_names, plan=side.story.plan, story_brief=side.story.brief or "",
        quota=_Unlimited(), pages=seen_pages(data, q.ask_chapter))


def row_fields(q: Question, system: str, reply: NarratorReply, *, data: BenchData,
               side: NarratorSide, config: AppConfig) -> dict[str, Any]:
    """Cột của một lượt người kể trong results.jsonl, cùng khoá chấm với các hệ bộ nhớ."""
    names = data.state_at(q.ask_chapter).named_nodes()
    if reply.answer == NOT_KNOWN:
        verdict: dict[str, Any] = {"correct": False, "abstained": True, "parsed": None}
        leaks: list[dict[str, Any]] = []
    else:
        verdict = score_answer(q, reply.answer, names)
        read = "\n".join(seen_pages(data, q.ask_chapter).values())
        leaks = [h | {"on_page": on_page(h["term"], read)}
                 for h in side.scorer.leaks(reply.answer, side.state(q.ask_chapter), q.question)]
    return {
        "answer": reply.answer, **verdict, "context_chars": reply.prompt_chars,
        "narrator_prompt": prompt_version(variant_config(system, config)),
        "raw": reply.output.model_dump() if reply.output else None,
        "blocked": reply.blocked.value if reply.blocked else None,
        "final_leaks": leaks,
        "passages": [[c.chapter, c.index] for _, c in reply.passages],
        "shown": len(reply.shown), "total": reply.total,
    }


def messages_for(q: Question, system: str, *, data: BenchData, side: NarratorSide,
                 config: AppConfig) -> list[Message]:
    """Đúng tin nhắn người kể sẽ gửi (cho lệnh `plan` ước chi phí)."""
    cfg = variant_config(system, config)
    view = side.state(q.ask_chapter).view
    passages = (select_passages(q.question, view, seen_pages(data, q.ask_chapter),
                                cfg.limits.narrator_pages)
                if cfg.limits.narrator_pages.top_k else None)
    return build_messages(q.question, view,
                          select_notebook(q.question, view, cfg.limits.narrator_notebook), passages)


# --- model giả ------------------------------------------------------------------------------------

_REF = re.compile(r"^\[([mlt]\d+)\] ", re.MULTILINE)
_BLOCK = re.compile(r'<player_data source="(?:notebook|page_passages)">\n(.*?)\n</player_data>',
                    re.DOTALL)


def fake_reply(data: BenchData, messages: Sequence[Message], mode: str,
               names: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Model giả cho hai hệ người kể. `oracle`: trả đáp án gốc, dẫn mã đầu tiên đã gửi, khi mọi câu
    trích bằng chứng có trong sổ tay hay đoạn nó nhận (trần nếu đọc hoàn hảo); còn không thì không
    biết. `null`: luôn không biết. `wrong`: luôn một câu sai. Chỉ đọc messages."""
    chapter, question = parse_narrator_messages(messages)
    q = next(x for x in data.questions.questions
             if x.ask_chapter == chapter and x.question == question)
    user = next(m.content for m in messages if m.role == "user")
    seen = flat(" ".join(html.unescape(b) for b in _BLOCK.findall(user)))
    refs = _REF.findall("\n".join(html.unescape(b) for b in _BLOCK.findall(user)))
    unknown = {"known": False, "answer": None, "entry_ids": []}
    if mode == "null" or not refs:
        return unknown
    if mode == "wrong":
        return {"known": True, "answer": wrong_answer(q, names), "entry_ids": refs[:1]}
    if all(flat(ev.quote) in seen for ev in q.evidence):
        return {"known": True, "answer": oracle_answer(q, names), "entry_ids": refs[:1]}
    return unknown
