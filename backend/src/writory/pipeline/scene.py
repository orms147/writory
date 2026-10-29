"""Dàn ý cảnh và đề cho model viết (design §6.2 bước 1–2, §6.5 mục 3–4; D-36).

Hai vai này được thấy lớp truth (ngữ cảnh `writer_context`, kể cả bí mật) để viết nhất quán; chữ
của chúng chỉ tới người chơi sau khi qua kiểm văn, người canh và bộ dò lộ (D-1).

G4: chữ người chơi (thiết lập truyện, hành động dẫn tới chương) và mọi văn bản cảnh (có thể nhắc lại
chữ người chơi) chỉ vào vai user, bọc bằng `UserAuthored`. Mọi chữ khác không phải hằng của code
(tên và chữ nút do model khởi tạo hay model trích viết, `kind`/`role` của cạnh, id, tên hồi, dàn ý,
đoạn trích lỗi, phần render của `writer_context`, mục tiêu của chương) đi vào vai user qua
`escape_text`, nên không mở hay đóng được khối dữ liệu.

Mục tiêu của chương theo bản kế hoạch (`pipeline.pacing`, D-49) vào cả đề dàn ý lẫn đề viết.
Dàn ý ghi mạch cảnh này gỡ (`resolves`, D-82); đề viết hiện mô tả của các mạch đó.

Đoạn nguyên văn đã hiện trên trang (D-85): vài đoạn của các chương đã ghi, chọn bằng BM25 theo
nhân vật, đồ vật, nơi chốn của cảnh và lựa chọn vừa rồi (`page_query`), để cảnh mới thấy đúng chữ
đã kể (cửa đã mở, ai nói gì) mà đồ thị và tóm tắt không giữ. Đó là chữ người chơi đã đọc và có thể
nhắc lại chữ người chơi, nên luôn bọc `UserAuthored` (G4). Chỉ hai vai này nhận chúng.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from writory.config import REPO_ROOT, QualityConfig
from writory.graph import ChangePackage
from writory.graph.context import ReaderName, WriterContext, render_writer_context
from writory.llm.base import Message
from writory.pipeline.pacing import ChapterGoals, render_chapter_goals, resolvable
from writory.pipeline.passages import Chunk
from writory.quality import check_foreign_script
from writory.safety.leak import ForbiddenName
from writory.safety.wrap import (
    DATA_NOTICE,
    UserAuthored,
    escape_text,
    system_message,
    user_message,
)

# outline-3, writer-3: thêm mục tiêu của chương theo bản kế hoạch (D-49).
# outline-4, writer-4: thêm tóm tắt hai chương gần nhất (D-49).
# outline-5, writer-5: định nghĩa "gỡ mạch"; dàn ý ghi `resolves`, đề viết hiện mạch cảnh gỡ (D-82).
# outline-6, writer-6: mục "Bí mật đã lộ" và câu mạch nhiều vế trong mục tiêu của chương (D-84).
# outline-7, writer-7: đoạn nguyên văn đã hiện trên trang, chọn bằng BM25 (D-85).
# outline-8, writer-8: mục "Tên người đọc chưa được biết", tên người đọc biết cạnh tên thật (D-91).
# outline-9, writer-9: dòng "PHẢI đổi tình thế" khi nhân vật chính ở yên nhiều chương (D-98).
# outline-10, writer-10: đề v3 thành mặc định (D-111).
# outline-11, writer-11: dòng mốc đã xảy ra rồi trong mục tiêu chương (D-116).
OUTLINE_PROMPT_VERSION = "outline-11"  # đổi chữ prompt thì tăng số
WRITER_PROMPT_VERSION = "writer-11"  # writer-2: system prompt có thêm câu ngôi kể (D-51)
# Hướng dẫn văn phong hiện hành (v3, D-111) là system prompt của bước viết (design §6.5 mục 4). Một bản duy nhất,
# dùng chung với bài đo D.
STYLE_GUIDE_PATH = REPO_ROOT / "evals" / "scenarios" / "quality" / "style_guide_vi.md"
MIN_BEATS, MAX_BEATS = 2, 8


def load_style_guide(path: Path = STYLE_GUIDE_PATH) -> str:
    """Bỏ khối chú thích HTML (ghi chú phiên bản, nguồn) như bài đo D."""
    raw = path.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()


class SceneOutline(BaseModel):
    """Đầu ra của vai dàn ý. Mọi trường bắt buộc (JSON schema strict)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    goal: str
    present: list[str]  # id nhân vật có mặt; pipeline lọc theo danh sách được đưa (G11)
    beats: list[str]
    ends_at: str
    resolves: list[str]  # id mạch cảnh này gỡ; pipeline lọc theo mục tiêu của chương (G11, D-82)

    @model_validator(mode="after")
    def _filled(self) -> Self:
        if not self.goal.strip() or not self.ends_at.strip():
            raise ValueError("goal và ends_at không được rỗng")
        if not MIN_BEATS <= len(self.beats) <= MAX_BEATS or any(not b.strip() for b in self.beats):
            raise ValueError(f"beats phải có {MIN_BEATS}–{MAX_BEATS} nhịp, không nhịp nào rỗng")
        return self


def outline_foreign_script(outline: SceneOutline, quality: QualityConfig) -> list[str]:
    """Tên các trường chữ của dàn ý có lẫn chữ khác hệ (`quality.check_foreign_script`: chữ Hán,
    Nhật, Hàn; chuỗi từ Latin dài). Dàn ý phải viết tiếng Việt (D-51); nơi gọi coi dàn ý như vậy là
    sai schema. Chỉ trả tên trường, không chép chữ (chi tiết lỗi vào log)."""
    fields = [("goal", outline.goal), *((f"beats[{i}]", b) for i, b in enumerate(outline.beats)),
              ("ends_at", outline.ends_at)]
    return [name for name, text in fields if check_foreign_script(text, quality)]


def keep_resolves(outline: SceneOutline, goals: ChapterGoals | None) -> SceneOutline:
    """Chỉ giữ id mạch mà mục tiêu của chương cho gỡ ở chương này (`pacing.resolvable`), bỏ trùng,
    như `present` (G11). Không có mục tiêu thì không mạch nào."""
    allowed = {t.thread_id for t in resolvable(goals)} if goals is not None else set()
    kept = list(dict.fromkeys(r for r in outline.resolves if r in allowed))
    return outline if kept == outline.resolves else outline.model_copy(update={"resolves": kept})


def unplanned_threads(goals: ChapterGoals | None, outlines: Sequence[SceneOutline], *,
                      last_scene: bool) -> list[str]:
    """Cảnh cuối của chương: id mạch ĐẾN HẠN hay QUÁ HẠN chưa gỡ mà không dàn ý nào của chương
    (cảnh trước và cảnh này) ghi trong `resolves` (D-82). Cảnh chưa phải cuối thì còn cảnh sau."""
    if goals is None or not last_scene:
        return []
    planned = {r for o in outlines for r in o.resolves}
    return [t.thread_id for t in goals.threads
            if t.status in ("due", "overdue") and t.thread_id not in planned]


@dataclass(frozen=True)
class EarlierScene:
    """Một cảnh trước trong chương: đã hiện cho người chơi, gói thay đổi chưa ghi."""

    number: int
    text: str
    package: ChangePackage


@dataclass(frozen=True)
class Named:
    """Tên một nút cho prompt, kèm cờ user_authored (G4)."""

    text: str
    user_authored: bool = False


@dataclass(frozen=True)
class PromptTexts:
    """Chữ đề ghi đè, CHỈ cho bộ đo (D-109): đề dàn ý, đề tạo lựa chọn và các câu của mục tiêu chương
    (`pacing.GOAL_DEFAULTS`). Sản phẩm không bao giờ tạo đối tượng này. Là chữ của nhà phát triển,
    nên chỉ vào vai system (hai đề) hoặc là câu cố định của mục tiêu chương; chữ người chơi vẫn chỉ vào
    vai user và được bọc như cũ (G4). None / rỗng = dùng đề mặc định."""

    outline_system: str | None = None
    choices_system: str | None = None
    goal_texts: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneBrief:
    """Phần đề chung cho dàn ý và model viết."""

    chapter: int
    scene: int
    scene_count: int
    min_chars: int
    max_chars: int
    act: str | None
    story_brief: str  # thiết lập truyện người chơi chọn: luôn bọc như dữ liệu
    player_action: str | None  # lựa chọn hoặc hành động tự viết dẫn tới chương (đã qua G5)
    earlier: tuple[EarlierScene, ...]
    goals: ChapterGoals | None = None  # mục tiêu của chương theo bản kế hoạch (D-49)
    # (chương, tóm tắt) của các chương gần nhất, cũ trước (D-49). Chữ do model tóm tắt viết từ văn
    # có chữ người chơi: luôn bọc như dữ liệu (G4).
    summaries: tuple[tuple[int, str], ...] = ()
    # Tên lớp truth mà trang chưa được viết (D-61), từ cùng hàm với bộ dò lộ (D-91).
    forbidden: tuple[ForbiddenName, ...] = ()
    forbidden_max: int | None = None  # số nút tối đa trong mục tên cấm; None = không giới hạn (D-94)
    prompts: PromptTexts | None = None  # chỉ bộ đo (D-109)
    # (chương, câu mở) của các chương gần nhất, cũ trước: chữ đã hiện trên trang, nên luôn bọc như
    # dữ liệu (G4). Chỉ vào đề viết, cảnh 1 (D-110). Rỗng = tắt.
    openings: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class Candidate:
    id: str
    name: Named
    protagonist: bool


@dataclass(frozen=True)
class Rewrite:
    """Lượt viết lại: bản trước và danh sách lỗi (design §6.2 bước 4)."""

    draft: str
    issues: tuple[str, ...]


class _Lines:
    """Gom chữ hệ thống thành khối str; mỗi `UserAuthored` thành một phần riêng (G4)."""

    def __init__(self) -> None:
        self.parts: list[str | UserAuthored] = []
        self._buf: list[str] = []

    def line(self, *pieces: str | UserAuthored) -> None:
        current = ""
        for piece in pieces:
            if isinstance(piece, UserAuthored):
                self._buf.append(current)
                current = ""
                self._flush()
                self.parts.append(piece)
            else:
                current += piece
        self._buf.append(current)

    def extend(self, parts: Iterable[str | UserAuthored]) -> None:
        """Phần dựng sẵn ở nơi khác (render của writer_context): str vẫn được escape."""
        self._flush()
        self.parts.extend(p if isinstance(p, UserAuthored) else escape_text(p) for p in parts)

    def _flush(self) -> None:
        text = "\n".join(self._buf).strip("\n")
        if text:
            self.parts.append(text)
        self._buf = []

    def done(self) -> list[str | UserAuthored]:
        self._flush()
        return self.parts


def _name(named: Named) -> str | UserAuthored:
    return UserAuthored(named.text, "story_data") if named.user_authored else escape_text(named.text)


_EDGE_WORDS = {
    "RELATES_TO": "coi là", "LOCATED_AT": "ở", "HOLDS": "giữ", "MEMBER_OF": "thuộc",
    "PARTICIPATED_IN": "tham gia", "DIED_IN": "chết trong", "KNOWS": "biết", "FEELS": "cảm thấy về",
    "TOLD": "nói", "TOLD_TO": "nói với", "ABOUT": "nói về", "RESOLVED_IN": "được gỡ ở",
    "REVEALED_TO_PLAYER": "hé lộ cho người đọc ở",
}


def _detail(props: Mapping) -> str:
    """`kind`, `role` là chữ tự do của bộ trích (nó đọc văn có chữ người chơi): luôn escape."""
    bits = [f"{k}: {escape_text(str(props[k]))}" for k in ("kind", "score", "how", "role")
            if k in props]
    return f" ({', '.join(bits)})" if bits else ""


def render_changes(
    package: ChangePackage, names: Mapping[str, Named],
    edge_ends: Mapping[str, tuple[str, str, str]],
) -> list[tuple[str | UserAuthored, ...]]:
    """Dòng mô tả gói thay đổi của một cảnh. `edge_ends`: id cạnh → (kiểu, từ, tới), để mô tả
    cạnh bị đóng."""

    def who(node_id: str) -> str | UserAuthored:
        return _name(names[node_id]) if node_id in names else escape_text(node_id)

    lines: list[tuple[str | UserAuthored, ...]] = [
        ("- ", who(e.source), f" {_EDGE_WORDS[e.type]} ", who(e.target), _detail(e.props))
        for e in package.edges
    ]
    for c in package.close:
        if c.id in edge_ends:
            etype, source, target = edge_ends[c.id]
            lines.append(("- không còn: ", who(source), f" {_EDGE_WORDS[etype]} ", who(target)))
        else:
            lines.append((f"- không còn: cạnh {escape_text(c.id)}",))
    return lines or [("- (không có thay đổi nào được ghi nhận)",)]


def _head(out: _Lines, brief: SceneBrief) -> None:
    act = f"; hồi: {escape_text(brief.act)}" if brief.act else ""  # tên hồi do model khởi tạo đặt
    out.line(f"Chương {brief.chapter}, cảnh {brief.scene}/{brief.scene_count}{act}. "
             f"Độ dài cảnh: từ {brief.min_chars} đến {brief.max_chars} ký tự.")
    out.line("Thiết lập truyện do người chơi chọn:", UserAuthored(brief.story_brief, "story_setup"))
    if brief.summaries:
        out.line("Tóm tắt các chương trước (ghi chú cho người viết, không phải văn của truyện; "
                 "cảnh này nối tiếp từ đó, không lặp lại):")
        for number, text in brief.summaries:
            out.line(f"Chương {number}:", UserAuthored(text, "chapter_summary"))
    if brief.player_action:
        out.line("Lựa chọn của người chơi dẫn tới chương này:",
                 UserAuthored(brief.player_action, "player_action"))


def _earlier(out: _Lines, brief: SceneBrief, names: Mapping[str, Named],
             edge_ends: Mapping[str, tuple[str, str, str]]) -> None:
    if not brief.earlier:
        return
    out.line("## Các cảnh trước trong chương này (người đọc đã đọc)")
    for scene in brief.earlier:
        out.line(f"### Cảnh {scene.number}", UserAuthored(scene.text, "scene_text"))
        out.line(f"Thay đổi đã ghi nhận ở cảnh {scene.number} (chưa ghi vào đồ thị):")
        for line in render_changes(scene.package, names, edge_ends):
            out.line(*line)


def page_query(brief: SceneBrief, ctx: WriterContext, outline: SceneOutline | None = None) -> str:
    """Câu hỏi cho kho đoạn (D-85): nhân vật có mặt (tên, biệt danh, nơi đứng, đồ cầm), nút lân cận
    gần, lựa chọn vừa rồi của người chơi và, khi đã có dàn ý, mục tiêu, nhịp và chỗ kết của cảnh.
    Chỉ dùng để chấm điểm BM25 trên chữ đã hiện; không vào prompt hay tới người chơi."""
    parts: list[str] = [brief.player_action] if brief.player_action else []
    for c in ctx.present:
        parts += [c.name, *c.aliases]
        if c.location is not None:
            parts.append(c.location.value)
        parts += [h.value for h in c.holds]
    parts += [n.text for n in ctx.neighbors if n.hops <= 1]
    if outline is not None:
        parts += [outline.goal, *outline.beats, outline.ends_at]
    return "\n".join(parts)


def _quotes(out: _Lines, quotes: Sequence[Chunk]) -> None:
    if not quotes:
        return
    out.line("## Đoạn đã hiện trên trang liên quan (nguyên văn; chỉ để giữ nhất quán chi tiết: cửa "
             "mở hay đóng, ai đứng đâu, ai đã nói gì, đồ vật ở đâu. Không chép lại, không lặp nhịp)")
    for q in quotes:
        out.line(f"### Chương {q.chapter}", UserAuthored(q.text, "page_quote"))


def _openings(out: _Lines, brief: SceneBrief) -> None:
    if not brief.openings or brief.scene != 1:
        return
    out.line("## Câu mở của các chương trước (đã hiện trên trang; chỉ để KHÔNG lặp lại: câu mở và "
             "động tác mở chương này phải khác)")
    for number, text in brief.openings:
        out.line(f"### Chương {number}", UserAuthored(text, "page_quote"))


def _scene_rank(ctx: WriterContext) -> dict[str, int]:
    """Nút liên quan tới cảnh: 0 = nhân vật có mặt, đồ vật đang liệt kê và người giữ hay nơi của
    chúng; 1 = nút lân cận trong ngữ cảnh. Nút khác không có trong bảng (xếp sau, D-94)."""
    rank = {n.id: 1 for n in ctx.neighbors}
    for i in ctx.items:
        rank |= {x: 0 for x in (i.id, i.holder_id, i.place_id) if x is not None}
    rank |= {c.id: 0 for c in ctx.present}
    return rank


def _context(out: _Lines, brief: SceneBrief, ctx: WriterContext) -> None:
    """Ngữ cảnh lớp truth, tên người đọc biết cạnh tên thật, rồi mục tên cấm (D-91)."""
    reader = {f.node_id: ReaderName(f.shown_as, f.user_authored) for f in brief.forbidden}
    out.extend(render_writer_context(ctx, reader))
    if not brief.forbidden:
        return
    by_node: dict[str, list[ForbiddenName]] = {}
    for f in brief.forbidden:
        by_node.setdefault(f.node_id, []).append(f)
    omitted = 0
    if brief.forbidden_max is not None and len(by_node) > brief.forbidden_max:
        # Trần chỉ cắt đề, không cắt bộ dò lộ (D-94): giữ nút có mặt, rồi nút liên quan tới cảnh.
        rank = _scene_rank(ctx)
        kept = sorted(by_node, key=lambda n: rank.get(n, 2))[:brief.forbidden_max]
        omitted = sum(len(v) for n, v in by_node.items() if n not in kept)
        by_node = {n: by_node[n] for n in kept}
    out.line("## Tên người đọc chưa được biết (không viết ra trên trang)")
    out.line("Các tên dưới đây là sự thật của thế giới nhưng người đọc chưa được biết. Trang viết ra "
             "tên đó, kể cả viết thường hay không dấu, thì cảnh bị chặn. Gọi bằng tên người đọc "
             "đã biết, hoặc tả bằng vai và dáng vẻ.")
    for found in by_node.values():
        head = found[0]
        terms: list[str | UserAuthored] = []
        for i, f in enumerate(found):
            terms += [", " if i else "", "«", _name(Named(f.term, f.user_authored)), "»"]
        if head.shown_as is None:
            out.line("- Chưa hé lộ; không viết tên ", *terms)
        else:
            out.line("- Người đọc biết là «", _name(Named(head.shown_as, head.user_authored)),
                     "»; không viết ", *terms)
    if omitted:
        out.line(f"- Và {omitted} tên khác của nhân vật, nơi chốn hay đồ vật ít liên quan tới cảnh "
                 "này; cũng không được viết nếu chưa chắc người đọc đã biết.")


def _goals(out: _Lines, brief: SceneBrief, *, thread_ids: bool = False) -> None:
    """Mục tiêu của chương (D-49). `render_chapter_goals` đã escape chữ của model và bọc chữ
    người chơi, nên các phần đi thẳng vào `line`, không escape lần nữa."""
    if brief.goals is not None:
        texts = brief.prompts.goal_texts if brief.prompts is not None else None
        out.line(*render_chapter_goals(brief.goals, scene=brief.scene,
                                       scene_count=brief.scene_count, thread_ids=thread_ids,
                                       texts=texts))


OUTLINE_SYSTEM_PROMPT = """Bạn lập dàn ý cho MỘT cảnh của một truyện tương tác tiếng Việt. Người chơi nhập vai nhân vật chính; truyện kể theo góc nhìn nhân vật chính. Bạn được biết sự thật của thế giới, kể cả bí mật, để dàn ý nhất quán; dàn ý không được làm lộ bí mật trước khoảng lộ.

Quy tắc:
- Cảnh nối tiếp đúng những gì đã xảy ra: các cảnh trước trong chương, và lựa chọn của người chơi dẫn tới chương này. Cảnh sau bắt đầu SAU nhịp cuối của cảnh trước; không lặp lại việc đã làm hay câu đã hỏi.
- Nhịp đầu của chương là hậu quả hay phản ứng ngay sau lựa chọn của người chơi. Đừng dựng lại việc người chơi đã chọn và đừng chép lại lời họ chọn.
- Mỗi cảnh phải đổi ít nhất một điều chỉ ra được: ai biết gì, ai giữ vật gì, ai ở đâu, quan hệ nào đổi, ai bị thương hay bị bắt, thời hạn nào bắt đầu chạy. Một văn bản được ghi, đọc, ký hay đặt xuống bàn, hoặc hai bên hẹn để sau, không tính là thay đổi.
- Trong mỗi chương nhân vật chính làm ít nhất một việc không thể rút lại (mất, lộ, bỏ đi, ra tay), không chỉ chờ hay trả lời.
- Hành động của người chơi vượt luật thế giới hay vượt khả năng nhân vật thì cho nó thất bại hoặc phải trả giá một cách hợp lý; không chiều theo.
- Tôn trọng mục "Sự thật cần tôn trọng": người đã chết không xuất hiện hay hành động; điều chỉ một số người biết thì người khác không nói ra.
- Bí mật ghi "KHÔNG để lộ" chỉ được gợi bằng manh mối mơ hồ.
- Không thêm nhân vật, nơi chốn hay đồ vật quan trọng mới.

Đầu ra JSON đúng schema, mọi chữ viết bằng tiếng Việt có dấu (không chữ Hán, không tiếng Anh):
- goal: mục tiêu của cảnh, một câu.
- present: id các nhân vật có mặt, chỉ lấy từ danh sách "Nhân vật có thể có mặt"; luôn có nhân vật chính.
- beats: 3 đến 6 nhịp theo thứ tự, mỗi nhịp một câu: một việc làm hoặc một đòn đối đáp có hậu quả (ai làm gì, ai nói gì và điều đó làm tình thế nhích đi đâu). Không có hai nhịp cùng một lập trường. Tối đa một nhịp thủ tục (ghi, đối chiếu, xác nhận) mỗi cảnh. Người có mặt có mục tiêu riêng: ghi ai muốn gì từ ai.
- ends_at: khoảnh khắc cuối cảnh, một câu: điều gì vừa xảy ra hay vừa tới khiến tình thế khác lúc đầu cảnh. Không phải lúc mọi người đứng chờ.
- resolves: id các mạch cảnh này gỡ trên trang, chỉ lấy id ghi trong mục "Mạch phải gỡ trước khi kết truyện". Mạch ĐẾN HẠN hay QUÁ HẠN mà các cảnh trước chưa gỡ thì cảnh cuối của chương phải gỡ, và phải có nhịp gỡ nó trong beats. Không gỡ mạch nào thì để []."""


def outline_messages(
    brief: SceneBrief, ctx: WriterContext, candidates: Sequence[Candidate],
    names: Mapping[str, Named], edge_ends: Mapping[str, tuple[str, str, str]],
    quotes: Sequence[Chunk] = (),
) -> list[Message]:
    out = _Lines()
    _head(out, brief)
    _context(out, brief, ctx)
    _quotes(out, quotes)
    out.line("## Nhân vật có thể có mặt (id | tên)")
    for c in candidates:
        mark = " (nhân vật chính)" if c.protagonist else ""
        # Id giữ nguyên để model chép lại vào `present`; ID_PATTERN không cho `<`, `&`.
        out.line(f"- {c.id} | ", _name(c.name), mark)
    _earlier(out, brief, names, edge_ends)
    _goals(out, brief, thread_ids=True)
    system = (brief.prompts.outline_system if brief.prompts is not None else None)
    return [system_message(system or OUTLINE_SYSTEM_PROMPT, DATA_NOTICE),
            user_message(*out.done())]


def writer_messages(
    style_guide: str, brief: SceneBrief, ctx: WriterContext, outline: SceneOutline,
    names: Mapping[str, Named], edge_ends: Mapping[str, tuple[str, str, str]],
    rewrite: Rewrite | None = None, quotes: Sequence[Chunk] = (),
) -> list[Message]:
    out = _Lines()
    _head(out, brief)
    _context(out, brief, ctx)
    _quotes(out, quotes)
    _openings(out, brief)
    _earlier(out, brief, names, edge_ends)
    _goals(out, brief)
    out.line("## Dàn ý cảnh này (các nhịp, theo thứ tự)")
    out.line(f"Mục tiêu: {escape_text(outline.goal)}")
    for i, beat in enumerate(outline.beats, 1):
        out.line(f"{i}. {escape_text(beat)}")
    out.line(f"Kết cảnh: {escape_text(outline.ends_at)}")
    by_id = {t.thread_id: t for t in brief.goals.threads} if brief.goals is not None else {}
    resolved = [by_id[r] for r in outline.resolves if r in by_id]
    if resolved:
        out.line("Cảnh này gỡ mạch (trên trang phải có câu trả lời rõ hoặc quyết định dứt khoát, "
                 "là một bước mới chứ không lặp lại nhịp cũ):")
        for t in resolved:
            out.line("- ", _name(Named(t.description, t.user_authored)))
    if rewrite is not None:
        out.line("## Bản viết trước bị trả lại", UserAuthored(rewrite.draft, "draft"))
        out.line("Lỗi cần sửa:")
        for issue in rewrite.issues:
            out.line(f"- {escape_text(issue)}")
        out.line("Viết lại toàn bộ cảnh theo dàn ý, sửa hết các lỗi trên.")
    return [system_message(style_guide, DATA_NOTICE), user_message(*out.done())]
