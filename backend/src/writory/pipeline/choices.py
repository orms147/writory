"""Tạo 3 lựa chọn cuối chương (design §6.2 bước 6, §6.3; D-37).

G1: model chỉ nhận `PlayerView` của chương vừa ghi (dựng thành sổ tay bằng đúng hàm của người kể,
`render_notebook`) và văn bản cảnh người chơi vừa đọc (đã qua dò lộ). Không nhận `story_plan`, ngữ
cảnh model viết, tên lớp truth hay id nút: mỗi mục được gọi bằng mã công khai của
`graph.public_entries` (`m1`, `m2`, …; D-40), vì id có thể ghép từ tên thật (ví dụ `ly_that`). Code
đổi mã về id khi dựng dữ liệu có cấu trúc.

G2: mọi chữ có thể tới người chơi (chữ lựa chọn, nội dung lời nói dối sẽ vào sổ tay, cảm xúc của
lựa chọn nội tâm) qua `check_leaks` với `scope="player_path"` (D-61): mọi bí mật chưa có trong
player_view đều bị dò, bất kể khoảng lộ, vì chỉ cảnh mới được hé lộ. Trúng một chỗ thì không hiện
bộ lựa chọn nào (`CHOICES_LEAK_BLOCKED`); chương đã ghi xong từ trước, gọi lại hàm này để tạo bộ
mới. Mọi nơi tạo lựa chọn (chương, tạo lại ở `bench_run` và `api/play.py`) đi qua hàm này.

G4: toàn bộ view và văn bản cảnh nằm trong khối dữ liệu, vì view không mang cờ `user_authored`.

G9, D-57: cổng `moderate` kiểm mọi chữ người chơi sẽ thấy (chữ lựa chọn, lời nói dối, cảm xúc)
sau dò lộ, mỗi chuỗi một dòng; bộ kiểm duyệt chấm từng dòng trong một lời gọi (D-79). Vượt mức hay
thuộc loại bị chặn thì không hiện bộ nào, như dò lộ: không tự viết lại, người chơi bấm thử lại để
tạo bộ mới.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from writory.config import RetryLimits
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, EdgeSpec, NodeSpec, PlayerView, public_entries
from writory.graph.package import CloseSpec
from writory.llm.base import LLMClient, Message
from writory.llm.retry import with_json_retries
from writory.pipeline.events import KIND_LABELS, TONE_LABELS, ChoiceKind, PlayerChoice, Tone
from writory.pipeline.narrator import render_notebook
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import check_leaks
from writory.safety.moderate import ModerationResult, Verdict
from writory.safety.wrap import DATA_NOTICE, UserAuthored, system_message, user_message

log = logging.getLogger(__name__)

PROMPT_VERSION = "choices-5"  # đổi chữ prompt thì tăng số (choices-3: STALLED_NOTE, D-98; choices-4: đề v3, D-111; choices-5: REF_NOTE khi thử lại, D-114)
CHOICE_COUNT = 3
MIN_KINDS = 2  # design §6.2 bước 6: tối thiểu 2 loại khác nhau
MIN_CHOICES = 2  # ít nhất từng ấy lựa chọn còn dùng được sau khi bỏ tham chiếu ngoài sổ tay (D-114)


class ChoiceDraft(BaseModel):
    """Một lựa chọn do model trả. Mọi trường bắt buộc (JSON schema strict); không dùng thì null/[]."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ChoiceKind
    text: str
    tone: Tone | None  # chỉ cho lời thoại
    lie_content: str | None  # tone = lie: nội dung lời nói dối
    listeners: list[str]  # ref người nghe; chỉ cho lời thoại
    about: list[str]  # ref các mục lựa chọn nói tới
    feeling: str | None  # chỉ cho nội tâm: cảm xúc hay ý định thầm

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if not self.text.strip():
            raise ValueError("text rỗng")
        if self.kind == "dialogue":
            if self.tone is None or not self.listeners:
                raise ValueError("lời thoại phải có tone và người nghe")
            lie = bool(self.lie_content and self.lie_content.strip())
            if (self.tone == "lie") != lie:
                raise ValueError("lie_content có khi và chỉ khi tone = lie")
        elif self.tone is not None or self.lie_content is not None or self.listeners:
            raise ValueError("tone, lie_content, listeners chỉ dùng cho lời thoại")
        if self.kind == "inner":
            if not (self.feeling and self.feeling.strip()) or not self.about:
                raise ValueError("nội tâm phải có feeling và about")
        elif self.feeling is not None:
            raise ValueError("feeling chỉ dùng cho nội tâm")
        return self


class ChoicesOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    choices: list[ChoiceDraft]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if len(self.choices) != CHOICE_COUNT:
            raise ValueError(f"cần đúng {CHOICE_COUNT} lựa chọn")
        if len({c.kind for c in self.choices}) < MIN_KINDS:
            raise ValueError(f"cần tối thiểu {MIN_KINDS} loại lựa chọn khác nhau")
        return self


@dataclass(frozen=True)
class LieEffect:
    """"Nói dối X với Y": người nói là nhân vật chính (design §6.3)."""

    content: str
    told_to: tuple[str, ...]  # id nhân vật


@dataclass(frozen=True)
class Choice:
    """Lựa chọn phía máy chủ, kèm dữ liệu có cấu trúc để ghi khi người chơi chọn (id nút thật).
    Người chơi chỉ nhận `for_player()`."""

    id: str
    kind: ChoiceKind
    tone: Tone | None
    text: str
    listeners: tuple[str, ...]
    about: tuple[str, ...]
    lie: LieEffect | None
    feeling: str | None

    def for_player(self) -> PlayerChoice:
        return PlayerChoice(
            id=self.id, kind=self.kind, kind_label=KIND_LABELS[self.kind], tone=self.tone,
            tone_label=TONE_LABELS[self.tone] if self.tone else None, text=self.text,
        )


def choice_effects(
    choice: Choice, *, chapter: int, protagonist: str, dead: Collection[str] = (),
    open_feels: Mapping[str, str] | None = None,
) -> ChangePackage:
    """Tác động của lựa chọn lên đồ thị, dựng thành phần mở đầu của gói chương `chapter` (D-55):
    người chơi chọn ở cuối chương N, nên tác động thuộc gói chương N+1 và mọi cạnh mở ở N+1 (D-21).

    - Nói dối: nút `Lie`, cạnh `TOLD` (nhân vật chính → Lie), `TOLD_TO` (Lie → từng người nghe còn
      sống, không kể chính nhân vật chính), `ABOUT` (Lie → các mục nó nói tới). Không còn ai nghe
      được thì không ghi gì (một lời dối không ai nghe không phải lời dối).
    - Nội tâm: `FEELS` từ nhân vật chính tới từng mục, mang `feeling`. `open_feels` (đích → id cạnh
      FEELS đang hiệu lực từ nhân vật chính) cho biết cạnh cũ nào bị cảm xúc mới thay: đóng nó.
    - Nói thật, im lặng, hành động: graph-schema không có chỗ cho chúng, chỉ chữ đi vào đề chương.

    Id của nút và cạnh suy ra từ id lựa chọn và số chương, nên viết lại chương (lần ghi trước lỗi)
    cho đúng cùng gói. Hàm thuần: không đọc đồ thị; người gọi lọc người chết và cạnh FEELS cũ.
    """
    nodes: list[NodeSpec] = []
    edges: list[EdgeSpec] = []
    close: list[CloseSpec] = []

    def edge(kind: str, source: str, target: str, **props: Any) -> EdgeSpec:
        return EdgeSpec(type=kind, source=source, target=target, valid_from_chapter=chapter,
                        props=props)

    if choice.lie is not None:
        hearers = [h for h in choice.lie.told_to if h != protagonist and h not in dead]
        if hearers:
            lie_id = f"lie:{choice.id}"
            nodes.append(NodeSpec(id=lie_id, label="Lie",
                                  props={"chapter": chapter, "content": choice.lie.content}))
            edges.append(edge("TOLD", protagonist, lie_id))
            edges += [edge("TOLD_TO", lie_id, h) for h in hearers]
            edges += [edge("ABOUT", lie_id, a) for a in choice.about]
    if choice.kind == "inner" and choice.feeling:
        for target in choice.about:
            edges.append(edge("FEELS", protagonist, target, feeling=choice.feeling))
            if open_feels and target in open_feels:
                close.append(CloseSpec(type="FEELS", id=open_feels[target], valid_to_chapter=chapter))
    return ChangePackage(commit_id="header", nodes=nodes, edges=edges, close=close)


# Lần chạy evals/results/2026-10-20-run-tu-tien-1/: cả 6 chương, mọi lời thoại đều "truth". Đề khuyến
# khích đổi sắc thái khi hợp cảnh; code không ép, vì design §6.2 chỉ đòi tối thiểu 2 loại.
TONE_GUIDANCE = """Sắc thái của lời thoại: nói thật không phải mặc định. Khi trong cảnh có người dò hỏi, nghi ngờ, gây sức ép, hoặc nhân vật chính có điều cần giấu, ít nhất một lựa chọn lời thoại phải là "lie" (nói dối, kèm lie_content) hoặc "silence" (im lặng, không trả lời). Khi cảnh không có sức ép như vậy, chọn sắc thái hợp cảnh nhất."""

SYSTEM_PROMPT = f"""Bạn tạo lựa chọn cho người chơi ở cuối một chương truyện tương tác tiếng Việt. Người chơi nhập vai nhân vật chính và chỉ biết những gì có trong khối dữ liệu: sổ tay (các mục người chơi đã biết) và cảnh vừa đọc. Không bịa thêm sự thật về thế giới, không đoán bí mật, không nhắc tới điều không có trong khối dữ liệu.

Tạo đúng 3 lựa chọn cho bước tiếp theo của nhân vật chính, mỗi lựa chọn một hướng khác nhau, hợp với cảnh vừa đọc. Ba lựa chọn phải dẫn tới ba hậu quả khác nhau mà người đọc hình dung được ngay: đổi nơi, đổi người đối diện, hay đổi cái giá phải trả. Không đưa ba cách khác nhau của cùng một việc chờ hay giữ yên. Không chọn lại việc nhân vật vừa làm hay vừa nói trong cảnh. Có ít nhất 2 loại khác nhau; nên đủ cả 3 loại:
- action: một hành động.
- dialogue: một câu nói với người khác; tone là "truth" (nói thật), "lie" (nói dối) hoặc "silence" (im lặng, không trả lời); listeners là mã người nghe; khi nói dối thì lie_content là nội dung lời nói dối, một câu.
- inner: một ý định thầm của nhân vật chính, người khác không biết: một quyết định làm hay giấu điều gì ở bước sau, không phải "tự nhủ" hay "thầm lo". feeling là cảm xúc đi kèm (vài chữ); about là mã người hay điều mà ý định hướng tới.

{TONE_GUIDANCE}

Mỗi lựa chọn:
- text: câu ngắn tiếng Việt mô tả lựa chọn, như người chơi sẽ đọc trên nút bấm. Với lời thoại, ghi ý chính của điều định nói ("Hỏi thẳng Lục ai đưa bản ghi"), không viết sẵn nguyên câu nhân vật sẽ nói.
- about: mã các mục lựa chọn nói tới (có thể rỗng với action, dialogue).
- Chỉ dùng mã mục dạng m1, m2… có trong sổ tay; listeners chỉ là mã của nhân vật.
- Trường không dùng để null (tone, lie_content, feeling) hoặc [] (listeners, about).

Trả về JSON đúng schema."""


# Khi nhân vật chính ở yên một nơi nhiều chương (D-98; lần chạy long-tu-tien-1: ba lựa chọn cuối
# chương 10, 14, 15 đều là "giữ yên, dò thêm"). Chữ cố định của code, cờ chỉ đúng/sai: không mang
# tên nơi chốn hay chữ lớp truth nào (G1).
STALLED_NOTE = """Ghi chú: mấy chương gần đây nhân vật chính chưa rời nơi hiện tại và tình thế chưa đổi. Ít nhất một trong 3 lựa chọn phải là bước vượt khỏi thế giằng co đó (rời nơi này, đối mặt trực tiếp, hỏi thẳng điều đang bị giấu, hay mạo hiểm), không chỉ giữ yên, chờ hay dò thêm."""


# Chỉ gửi khi lượt trước không cứu được vì tham chiếu (D-114). Chữ cố định của code: không nhắc lại chữ
# model đã trả, nên không dội ngược chữ bịa hay chữ có thể mang lệnh vào đề (G4).
REF_NOTE = ("Lần trước bộ lựa chọn bị bỏ vì có mã không nằm trong sổ tay hoặc người nghe không phải nhân "
            "vật. Chỉ dùng mã dạng m1, m2… ghi trong sổ tay; không tự bịa mã, không viết mô tả thay cho "
            "mã. Lời thoại, lời nói dối và nội tâm phải gắn với mã của một nhân vật có trong sổ tay.")


def build_choice_messages(
    view: PlayerView, *, protagonist_id: str, last_scene_text: str, stalled: bool = False,
    system_prompt: str | None = None,
) -> tuple[list[Message], dict[str, str]]:
    """Tin nhắn cho model tạo lựa chọn và bảng mã công khai → id nút. Chỉ đọc `view` (G1).
    `stalled`: truyện đang đứng yên (D-98), thêm `STALLED_NOTE`. `system_prompt`: chỉ bộ đo (D-109),
    thay `SYSTEM_PROMPT`."""
    entries = public_entries(view)
    refs = {ref: e.id for ref, e in entries}
    me = next((f"[{ref}] {e.text}" for ref, e in entries if e.id == protagonist_id),
              "(chưa có tên trên trang)")
    notebook = f"Nhân vật chính: {me}\n\n{render_notebook(view)}"
    messages = [
        system_message(system_prompt or SYSTEM_PROMPT, DATA_NOTICE),
        user_message(
            f"Sổ tay của người chơi (tới hết chương {view.chapter}):",
            UserAuthored(notebook, "notebook"),
            "Cảnh người chơi vừa đọc:",
            UserAuthored(last_scene_text, "scene_text"),
            *([STALLED_NOTE] if stalled else []),
            "Tạo 3 lựa chọn cho nhân vật chính.",
        ),
    ]
    return messages, refs


def _bad(detail: str) -> WritoryError:
    return WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=f"ChoicesOutput: {detail}")


def _resolve(output: ChoicesOutput, refs: Mapping[str, str], kinds: Mapping[str, str], *,
             chapter: int = 0) -> list[Choice]:
    """Ref → id nút. Ref ngoài sổ tay (bịa ra, hoặc mô tả thay cho mã) hay người nghe không phải nhân
    vật thì bỏ RIÊNG tham chiếu đó, không đoán thêm (G1, D-114). Lựa chọn mất thứ nó bắt buộc phải có
    thì bỏ riêng lựa chọn đó: nội tâm không còn `about` (không có đích cho FEELS), lời nói dối không
    còn người nghe (không ai nghe thì không phải lời dối). Còn dưới `MIN_CHOICES` lựa chọn hay dưới
    `MIN_KINDS` loại thì không cứu được: sai schema (G11), để thử lại. Log chỉ ghi số, không ghi ref."""

    def known(values: list[str]) -> tuple[list[str], int]:
        ok = [refs[v] for v in values if v in refs]
        return list(dict.fromkeys(ok)), len(values) - len(ok)

    choices: list[Choice] = []
    dropped_refs = dropped_choices = 0
    for draft in output.choices:
        about, lost_about = known(draft.about)
        heard, lost_heard = known(draft.listeners)
        listeners = [i for i in heard if kinds[i] == "Character"]
        dropped_refs += lost_about + lost_heard + (len(heard) - len(listeners))
        if (draft.kind == "inner" and not about) or (draft.tone == "lie" and not listeners):
            dropped_choices += 1
            continue
        lie = LieEffect(draft.lie_content.strip(), tuple(listeners)) if draft.tone == "lie" else None
        choices.append(Choice(
            id=f"choice-{uuid.uuid4().hex[:12]}", kind=draft.kind, tone=draft.tone,
            text=draft.text.strip(), listeners=tuple(listeners), about=tuple(about), lie=lie,
            feeling=draft.feeling.strip() if draft.feeling else None,
        ))
    if dropped_refs or dropped_choices:
        log.warning("chương %s: bỏ %d tham chiếu ngoài sổ tay, %d lựa chọn không còn dùng được",
                    chapter, dropped_refs, dropped_choices)
    if len(choices) < MIN_CHOICES or len({c.kind for c in choices}) < MIN_KINDS:
        raise _bad(f"chỉ còn {len(choices)} lựa chọn dùng được sau khi bỏ tham chiếu ngoài sổ tay")
    return choices


def _ensure_no_leak(choices: list[Choice], *, view: PlayerView,
                    truth_names: Mapping[str, tuple[str, ...]], plan: StoryPlan,
                    story_brief: str) -> None:
    hits = [
        (i, h)
        for i, c in enumerate(choices, 1)
        for text in (c.text, c.lie.content if c.lie else None, c.feeling)
        if text
        for h in check_leaks(text, view=view, truth_names=truth_names, plan=plan,
                             story_brief=story_brief, scope="player_path")
    ]
    if hits:
        # Log và lỗi chỉ ghi loại và vị trí, không ghi chữ bị lộ (D-26).
        where = ", ".join(f"lựa chọn {i}: {h.kind.value}@{h.start}-{h.end}" for i, h in hits)
        log.warning("chương %s: chặn bộ lựa chọn (%s)", view.chapter, where)
        raise WritoryError(ErrorCode.CHOICES_LEAK_BLOCKED,
                           detail=f"chương {view.chapter}: {len(hits)} chỗ trúng ({where})")


# Cổng kiểm duyệt nội dung (G9, D-57): nhận mọi chữ người chơi sẽ thấy trong bộ lựa chọn.
ChoicesGate = Callable[[str], Awaitable[ModerationResult]]


def _player_facing_text(choices: list[Choice]) -> str:
    """Mọi chuỗi của bộ lựa chọn có thể tới người chơi: chữ lựa chọn, nội dung lời nói dối (vào sổ
    tay), cảm xúc thầm của lựa chọn nội tâm. Mỗi chuỗi đúng một dòng (xuống dòng bên trong gộp
    thành khoảng trắng): kiểm duyệt chấm từng dòng như một hành động sẽ xảy ra (D-79)."""
    parts: list[str] = []
    for c in choices:
        parts.append(c.text)
        if c.lie is not None:
            parts.append(c.lie.content)
        if c.feeling:
            parts.append(c.feeling)
    return "\n".join(" ".join(part.split()) for part in parts)


async def _ensure_allowed(choices: list[Choice], moderate: ChoicesGate, chapter: int) -> None:
    """Bộ lựa chọn vượt mức hay thuộc loại bị chặn thì không hiện bộ nào (như dò lộ, D-37): chương
    đã ghi, người chơi bấm thử lại để tạo bộ mới. Log chỉ ghi kết luận và loại, không ghi chữ."""
    result = await moderate(_player_facing_text(choices))
    if result.verdict is not Verdict.ALLOW:
        cats = ", ".join(c.value for c in result.categories)
        log.warning("chương %s: chặn bộ lựa chọn (kiểm duyệt: %s [%s])", chapter,
                    result.verdict.value, cats)
        raise WritoryError(ErrorCode.CHOICES_LEAK_BLOCKED,
                           detail=f"chương {chapter}: kiểm duyệt {result.verdict.value} [{cats}]")


async def make_choices(
    llm: LLMClient, model: str, *, view: PlayerView, protagonist_id: str, last_scene_text: str,
    truth_names: Mapping[str, tuple[str, ...]], plan: StoryPlan, story_brief: str,
    retries: RetryLimits, extra: Mapping[str, Any] | None = None,
    moderate: ChoicesGate | None = None, stalled: bool = False, system_prompt: str | None = None,
) -> list[Choice]:
    """`view`: player_view ở chương vừa ghi. `stalled`: truyện đứng yên (D-98). `truth_names`, `plan`, `story_brief` (thiết lập truyện
    người chơi đã đọc, D-52) chỉ dùng cho bộ dò lộ bằng code, không bao giờ vào prompt. `moderate`:
    cổng kiểm duyệt nội dung (G9); đường của người chơi phải truyền."""
    messages, refs = build_choice_messages(view, protagonist_id=protagonist_id,
                                           last_scene_text=last_scene_text, stalled=stalled,
                                           system_prompt=system_prompt)
    kinds = {e.id: e.kind for e in view.entries}

    unusable = False  # lượt trước hỏng vì tham chiếu: lượt sau nhắc một câu cố định

    async def call() -> list[Choice]:
        nonlocal unusable
        sent = [*messages, user_message(REF_NOTE)] if unusable else messages
        output, _ = await llm.chat_json(model, sent, ChoicesOutput, extra=extra)
        try:
            return _resolve(output, refs, kinds, chapter=view.chapter)
        except WritoryError:
            unusable = True
            raise

    choices = await with_json_retries(call, schema_retries=retries.extract_schema_retry,
                                      transient_retries=retries.llm_transient)
    _ensure_no_leak(choices, view=view, truth_names=truth_names, plan=plan,
                    story_brief=story_brief)
    if moderate is not None:
        await _ensure_allowed(choices, moderate, view.chapter)
    return choices
