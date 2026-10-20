"""Dữ liệu dùng chung cho test đường đi một chương (pipeline/chapter.py): cấu hình thử, kế hoạch
truyện, văn cảnh, câu trả lời ghi sẵn của model giả, và kho truyện trong bộ nhớ.

Nền: truyện mẫu data/sample-story/ đã commit tới chương 3; pipeline viết chương 4 thành 2 cảnh.
Văn hai cảnh là hai nửa của ch04.md (văn đã kiểm tay), giữ nguyên dấu "—" để kiểm chuẩn hoá (D-31).
"""

import json
import re
import shutil
from collections import deque
from pathlib import Path
from typing import Any

import yaml

from writory.config import REPO_CONFIG_DIR, AppConfig, load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, PlayerView, read_sample
from writory.graph.context import (
    CharacterInfo,
    FactInfo,
    Knower,
    NeighborInfo,
    SecretInfo,
    Text,
    WriterContext,
)
from writory.graph.package import chapter_rule_problems
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import Message
from writory.llm.fake import FakeLLM
from writory.pipeline import choices as choices_mod
from writory.pipeline import extract as extract_mod
from writory.pipeline import scene as scene_mod
from writory.pipeline import summary as summary_mod
from writory.pipeline.extract import Entity
from writory.pipeline.store import entities_from_rows
from writory.pipeline.story_plan import StoryPlan

SAMPLE = read_sample()
COMMITTED_THROUGH = 3
CHAPTER = 4

# Kế hoạch thử, giống tests/unit/test_leak.py: có leak_terms cho bộ dò lộ.
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "phát triển", "from_chapter": 1, "to_chapter": 12}],
    "secrets": [
        {"fact_id": "f_gu_old_hac_ky", "reveal_from_chapter": 2, "reveal_to_chapter": 3,
         "leak_terms": [["Lão Gù", "Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6,
         "leak_terms": [["Lan", "gián điệp"], ["Lan", "người của Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_killed_gu", "reveal_from_chapter": 7, "reveal_to_chapter": 9,
         "leak_terms": [["Lan", "giết", "Lão Gù"]]},
    ],
})

_BODY = SAMPLE.chapters[CHAPTER].text.split("\n", 1)[1].strip()
_CUT = _BODY.index("Đêm đó Minh ngủ say")
SCENE_1 = _BODY[:_CUT].strip()
SCENE_2 = _BODY[_CUT:].strip()
assert "—" in SCENE_1

# Câu sáo ngữ có trong config/quality.yaml: kiểm văn bắt, mức viết lại.
CLICHE = "Thời gian như ngừng trôi."
SCENE_1_CLICHE = SCENE_1.replace("Cô ở lại thêm một lúc", CLICHE + " Cô ở lại thêm một lúc")
# Lộ bí mật f_lan_spy (khoảng lộ 5–6) ở chương 4: bộ dò lộ bắt, mức chặn.
LEAK_SENTENCE = "Minh không ngờ Lan là gián điệp."
SCENE_1_LEAK = SCENE_1.replace("Cô ở lại thêm một lúc", LEAK_SENTENCE + " Cô ở lại thêm một lúc")
# Thẻ suy luận lọt vào văn (D-30): mức chặn.
SCENE_1_META = "</think>\n" + SCENE_1

# Chuỗi lớp truth ở chương 4 mà người chơi chưa biết (G1): không được tới model tạo lựa chọn.
TRUTH_AT_4 = (
    "Lan là gián điệp của Hội Hắc Kỳ",
    "Lan giết Lão Gù",
    "để lão không kịp nói",
    "Lý Thất",
    "trốn một cuộc hôn nhân",
    "đừng tin người lạ",
    "Ai đã giết Lão Gù",
    "KHÔNG để lộ",
    "f_lan_spy",
    "f_lan_killed_gu",
    "ly_that",
    "l_lan_cover",
    "t_gu_warning",
)


# --- cấu hình thử -------------------------------------------------------------------------------

_TRIAL = {
    "limits": {"cost_usd": {"per_scene": 1.0, "per_chapter": 2.0, "per_story": 10.0},
               "context": {"writer_max_neighbors": 10}},
    "models": {"roles": {"outline": "test/outline", "choices": "test/choices"}},
    "quality": {"repetition": {"ngram_words": 6, "max_repeats": 2},
                "foreign_script": {"latin_run_min_words": 3},
                # Văn cảnh thử lấy từ truyện mẫu, kể ngôi thứ ba (D-51: ngôi theo config).
                "narration": {"person": "third"}},
    "story_lengths": {"chapter_chars": {"min": 1000, "max": 10000}},
    "guard": {"relationship": {"max_score_jump_without_event": 50}},
}
# Cảnh của model giả `bench_run.DryRunLLM` kể ngôi thứ nhất như config thật (D-51).
FIRST_PERSON = {"quality": {"narration": {"person": "first"}}}


def _merge(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def make_config(tmp_path: Path, **overrides: dict) -> AppConfig:
    """Bản sao config/ thật với các ngưỡng thử (config thật còn null). `overrides` theo tên file,
    ví dụ `limits={"cost_usd": {"per_scene": 0.03}}`."""
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    for stem, change in _merge(_TRIAL, overrides).items():
        path = target / f"{stem}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        path.write_text(yaml.safe_dump(_merge(data, change), allow_unicode=True), encoding="utf-8")
    return load_config(target)


# --- model giả --------------------------------------------------------------------------------


class ScriptedLLM(FakeLLM):
    """FakeLLM.scripted, thêm một kiểu câu trả lời: hàm nhận messages trả chuỗi (để câu trả lời
    dùng được ref do pipeline đặt, ví dụ ref của mục trong player_view)."""

    def __init__(self, responses, *, cost_usd: float | None = 0.0) -> None:
        super().__init__([], cost_usd=cost_usd)
        self._script = deque(responses)
        self.models: list[str] = []  # song song với `calls`

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        self.models.append(model)
        return await super().chat(model, messages, response_schema=response_schema, extra=extra)

    def _next(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        if not self._script:
            raise AssertionError("ScriptedLLM: hết câu trả lời ghi sẵn")
        item = self._script.popleft()
        if isinstance(item, Exception):
            raise item
        return item(messages) if callable(item) else item


def role_of(messages: list[Message]) -> str:
    """Vai của một lời gọi, nhận ra qua system prompt."""
    system = messages[0].content
    for role, prompt in (
        ("outline", scene_mod.OUTLINE_SYSTEM_PROMPT),
        ("extract", extract_mod.SYSTEM_PROMPT),
        ("choices", choices_mod.SYSTEM_PROMPT),
        ("summary", summary_mod.SYSTEM_PROMPT),
    ):
        if system.startswith(prompt[:60]):
            return role
    return "writer"


def calls_of(llm: FakeLLM, role: str) -> list[list[Message]]:
    return [c for c in llm.calls if role_of(c) == role]


def unavailable() -> WritoryError:
    return WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="giả lập")


# --- câu trả lời ghi sẵn ------------------------------------------------------------------------


def outline_reply(present=("minh", "lan"), beats=None) -> str:
    return json.dumps({
        "goal": "Lan tới thăm Minh, để lộ rằng cô biết thanh kiếm là của Lão Gù",
        "present": list(present),
        "beats": beats or ["Lan mang cháo tới gác", "Lan hỏi về thanh kiếm", "Lan về khi mưa ngớt"],
        "ends_at": "Lan rời gác",
    }, ensure_ascii=False)


_EDGE_NULLS = {"kind": None, "score": None, "how": None, "told_by": None, "quote": None,
               "known_as": None, "role": None}


def extract_reply(edges=(), close=()) -> str:
    return json.dumps({"edges": [_EDGE_NULLS | e for e in edges], "close": list(close)},
                      ensure_ascii=False)


# Cảnh 1: Lan lộ ra là biết Minh nói dối về thanh kiếm (gói vàng ch4).
EXTRACT_1 = extract_reply([{"type": "KNOWS", "source": "lan", "target": "l_sword_father",
                            "how": "suy ra"}])
# Cảnh 2: gã lái đò mặt sẹo ra mắt; Lan giữ kiếm (đóng cạnh Minh giữ kiếm).
EXTRACT_2 = extract_reply(
    [{"type": "REVEALED_TO_PLAYER", "source": "ly_that", "target": "ch4",
      "quote": "một gã lái đò mặt sẹo buộc thuyền ngay trước quán trà",
      "known_as": "gã lái đò mặt sẹo"},
     {"type": "HOLDS", "source": "lan", "target": "sword"}],
    close=["holds_sword_minh_2"],
)
# Người chết hành động: Lão Gù chết ở chương 3 (người canh, mức viết lại).
EXTRACT_DEAD_HOLDS = extract_reply([{"type": "HOLDS", "source": "gu", "target": "sealed_letter"}])


def _refs(messages: list[Message]) -> dict[str, str]:
    """Chữ hiện → mã công khai, đọc từ sổ tay trong tin nhắn gửi model tạo lựa chọn."""
    text = messages[-1].content
    return {m.group(2).strip(): m.group(1)
            for m in re.finditer(r"^\[(m\d+)\] [^:\n]+: ([^(\n;]+)", text, re.MULTILINE)}


def choices_reply(*, action_text: str = "Xuống bến hỏi chuyện gã lái đò mặt sẹo."):
    def reply(messages: list[Message]) -> str:
        refs = _refs(messages)
        lan, sword = refs["Phạm Thị Lan"], refs["Thanh Sương"]
        return json.dumps({"choices": [
            {"kind": "action", "text": action_text, "tone": None, "lie_content": None,
             "listeners": [], "about": [refs["gã lái đò mặt sẹo"]], "feeling": None},
            {"kind": "dialogue", "text": "Nói với Lan rằng kiếm đã gửi cai Khải giữ.",
             "tone": "lie", "lie_content": "Thanh Sương đang ở chỗ cai Khải",
             "listeners": [lan], "about": [sword], "feeling": None},
            {"kind": "inner", "text": "Thầm nghĩ Lan biết nhiều hơn cô nói.", "tone": None,
             "lie_content": None, "listeners": [], "about": [lan], "feeling": "nghi ngờ"},
        ]}, ensure_ascii=False)
    return reply


SUMMARY_TEXT = "Lan mang cháo tới gác, hỏi về thanh kiếm; đêm đó Thanh Sương biến mất."


def summary_reply(text: str = SUMMARY_TEXT) -> str:
    return json.dumps({"summary": text}, ensure_ascii=False)


# Tóm tắt chương vừa ghi (D-49): lời gọi ngay sau bước ghi, trước bước lựa chọn.
SUMMARY = summary_reply()


def full_script(*, scene_1=SCENE_1, scene_2=SCENE_2, choices=None) -> list[Any]:
    """Thứ tự lời gọi của một chương 2 cảnh không viết lại: hai cảnh, tóm tắt, lựa chọn."""
    return [outline_reply(), scene_1, EXTRACT_1,
            outline_reply(), scene_2, EXTRACT_2,
            SUMMARY, choices or choices_reply()]


def final_chapter_script() -> list[Any]:
    """Chương cuối của kế hoạch: hai cảnh, không tóm tắt, không lựa chọn (D-50)."""
    return full_script()[:6]


# --- kho truyện trong bộ nhớ --------------------------------------------------------------------


def writer_context_ch4(story_id: str, present_ids) -> WriterContext:
    """Ngữ cảnh lớp truth dựng tay (giống writer_context trên truyện mẫu): có bí mật, để test G1
    chứng minh model tạo lựa chọn không nhận được chúng."""
    people = {
        "minh": CharacterInfo("minh", "Trần Minh", ("Minh",), True, None,
                              (Text("lá thư niêm sáp đỏ", False),), False),
        "lan": CharacterInfo("lan", "Phạm Thị Lan", ("Lan", "cô Lan"), True,
                             Text("quán trà đầu bến", False), (), False),
        "khai": CharacterInfo("khai", "Trần Văn Khải", ("Khải",), True, None, (), False),
    }
    lan = Text("Phạm Thị Lan", False)
    return WriterContext(
        story_id=story_id, as_of_chapter=3, writing_chapter=4,
        present=tuple(people[i] for i in present_ids if i in people),
        relations=(),
        known_facts=(FactInfo("f_lan_spy", "Lan là gián điệp của Hội Hắc Kỳ, tới phố Bến Sương "
                              "để tìm thanh kiếm Thanh Sương", (Knower("lan", lan, 0, "tự biết"),),
                              False),),
        open_lies=(),
        secrets=(SecretInfo("f_lan_killed_gu", "Lan giết Lão Gù sau miếu Bà để lão không kịp nói "
                            "Lan là người của Hội Hắc Kỳ", 7, 9, "not_yet", None, False),),
        neighbors=(NeighborInfo("gu", "Character", "Hồ Sĩ Bằng", ("Lão Gù",), 1, False, False),
                   NeighborInfo("ly_that", "Character", "Lý Thất", ("gã lái đò mặt sẹo",), 2,
                                True, False),
                   NeighborInfo("khai", "Character", "Trần Văn Khải", ("Khải",), 1, True, False)),
        open_threads=(),
    )


class MemoryStore:
    """Kho truyện trong bộ nhớ, cùng giao thức `ChapterStore` với GraphStore (Neo4j + Postgres).
    Ghi chương kiểm như `commit_chapter`: thứ tự chương, quy tắc D-21, id tham chiếu có thật."""

    def __init__(self, story_id: str = "mem-story", through: int = COMMITTED_THROUGH,
                 *, pending: bool = False, summaries: dict[int, str] | None = None) -> None:
        self.story_id = story_id
        self.packages: list[ChangePackage] = [
            c.package for c in SAMPLE.chapters if c.number <= through
        ]
        self.committed = through
        self.pending = pending
        self.commits: list[tuple[int, list[str], ChangePackage]] = []
        self.context_calls: list[tuple[int, tuple[str, ...]]] = []
        self.saved_summaries: dict[int, str] = dict(summaries or {})

    def summaries(self, chapters) -> dict[int, str]:
        return {c: self.saved_summaries[c] for c in chapters if c in self.saved_summaries}

    def save_summary(self, chapter: int, text: str) -> None:
        assert chapter <= self.committed, (chapter, self.committed)  # chỉ sau khi ghi chương
        self.saved_summaries.setdefault(chapter, text)

    def committed_chapter(self) -> int | None:
        return self.committed

    def has_pending(self) -> bool:
        return self.pending

    def state(self) -> OverlayState:
        return OverlayState(EmptyState(), self.packages)

    def catalogue(self) -> list[Entity]:
        rows = self.state().nodes([n.id for p in self.packages for n in p.nodes])
        return entities_from_rows(rows)

    def writer_context(self, as_of_chapter, present_ids, plan, *, max_neighbors) -> WriterContext:
        self.context_calls.append((as_of_chapter, tuple(present_ids)))
        return writer_context_ch4(self.story_id, present_ids)

    def commit(self, number: int, scenes: list[str], package: ChangePackage) -> None:
        assert number == self.committed + 1, (number, self.committed)
        assert chapter_rule_problems(package, number) == []
        known = {n.id for p in [*self.packages, package] for n in p.nodes}
        missing = {x for e in package.edges for x in (e.source, e.target)} - known
        assert not missing, missing
        self.packages.append(package)
        self.committed = number
        self.commits.append((number, scenes, package))

    def player_view(self, chapter: int) -> PlayerView:
        return player_view_of(self.state(), chapter, story_id=self.story_id)


# --- truyện mới từ bước khởi tạo (D-38) ---------------------------------------------------------

SETUP_PC_NAME = "Lục Thanh Vân"  # tên người chơi chọn: chữ người chơi, không phải bí mật (D-48)


def setup_chapter_0(*, protagonist_aliases: tuple[str, ...] = ()) -> tuple[ChangePackage, StoryPlan]:
    """Gói chương 0 + kế hoạch do `setup.to_story_setup` dựng từ tests/fixtures/setup/: nhân vật
    chính `protagonist` mang `user_authored: true`, người chơi chưa biết gì. `protagonist_aliases`:
    biệt danh model gán cho nhân vật chính (có thể là bí mật)."""
    from writory.pipeline.setup import (
        PROTAGONIST_ID,
        BuildOutput,
        CharacterOption,
        to_story_setup,
    )

    raw = (Path(__file__).parent / "fixtures" / "setup" / "build_story.json").read_text(
        encoding="utf-8")
    setup = to_story_setup(
        BuildOutput.model_validate_json(raw),
        protagonist=CharacterOption(name=SETUP_PC_NAME, personality="Ít nói, cố chấp.",
                                    backstory="Con trai một thợ rèn; cha mất năm cậu mười hai."),
        commit_id="setup-c0", level=load_config().story_lengths.levels["short"],
    )
    package = setup.package
    if protagonist_aliases:
        nodes = [n.model_copy(update={"props": {**n.props, "aliases": list(protagonist_aliases)}})
                 if n.id == PROTAGONIST_ID else n for n in package.nodes]
        package = package.model_copy(update={"nodes": nodes})
    return package, setup.plan


# --- kho truyện bất kỳ trong bộ nhớ --------------------------------------------------------------------


class OverlayStore:
    """Kho truyện trong bộ nhớ cho truyện bất kỳ (bắt đầu từ chương 0 do người gọi ghi), cùng
    giao thức với kho Neo4j + Postgres của lệnh chạy cả truyện (`bench_run.RunStore`). Đọc qua
    `OverlayState` thật. `writer_context` dựng tối giản: nhân vật có mặt + nhân vật khác làm lân
    cận."""

    def __init__(self, story_id: str = "mem-run") -> None:
        self.story_id = story_id
        self.packages: list[ChangePackage] = []
        self.committed: int | None = None
        self.created: str | None = None
        self.deleted = False
        self.commits: list[tuple[int, list[str]]] = []
        self.saved_summaries: dict[int, str] = {}

    def summaries(self, chapters) -> dict[int, str]:
        return {c: self.saved_summaries[c] for c in chapters if c in self.saved_summaries}

    def save_summary(self, chapter: int, text: str) -> None:
        self.saved_summaries.setdefault(chapter, text)

    def create_story(self, length_level: str) -> None:
        self.created = length_level

    def delete_story(self) -> None:
        self.deleted = True

    def committed_chapter(self) -> int | None:
        return self.committed

    def has_pending(self) -> bool:
        return False

    def state(self) -> OverlayState:
        return OverlayState(EmptyState(), self.packages)

    def catalogue(self) -> list[Entity]:
        return entities_from_rows(self.state().nodes([n.id for p in self.packages for n in p.nodes]))

    def writer_context(self, as_of_chapter, present_ids, plan, *, max_neighbors) -> WriterContext:
        rows = {i: r for i, r in self.state().nodes([e.id for e in self.catalogue()]).items()
                if r.label == "Character"}

        def ua(i):
            return bool(rows[i].props.get("user_authored"))

        present = tuple(
            CharacterInfo(i, rows[i].props["name"], tuple(rows[i].props.get("aliases", ())), True,
                          None, (), ua(i))
            for i in present_ids if i in rows
        )
        neighbors = tuple(
            NeighborInfo(i, "Character", r.props["name"], tuple(r.props.get("aliases", ())), 1,
                         True, ua(i))
            for i, r in rows.items() if i not in present_ids
        )
        return WriterContext(self.story_id, as_of_chapter, as_of_chapter + 1, present, (), (), (),
                             (), neighbors, ())

    def commit(self, number: int, scenes: list[str], package: ChangePackage) -> None:
        expected = 0 if self.committed is None else self.committed + 1
        assert number == expected, (number, expected)
        assert chapter_rule_problems(package, number) == []
        self.packages.append(package)
        self.committed = number
        self.commits.append((number, scenes))

    def player_view(self, chapter: int) -> PlayerView:
        return player_view_of(self.state(), chapter, story_id=self.story_id)
