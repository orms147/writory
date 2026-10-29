"""Trích thay đổi đồ thị từ văn bản một chương (design §6.2 bước 3; G3, G11, D-17, D-21, D-22).

Đầu vào: danh mục thực thể đang có (id, nhãn, tên/chữ), các cạnh đang hiệu lực, mạch phải gỡ còn
mở kèm trạng thái hạn (`guard.plan`, như mục tiêu của chương; D-82), văn bản chương.
Đầu ra: `ChangePackage` của chương N. Model chỉ được tham chiếu id trong danh mục (G11). Ngoại lệ
duy nhất: `new_facts`, Fact mới từ trang (D-93), model đặt nhãn tạm `new_<số>`, code kiểm rồi sinh id.

Model trả JSON theo `ExtractOutput`: mọi trường bắt buộc, giá trị trống là null, để dùng được với
JSON schema strict. Code đổi sang `ChangePackage`, kiểm từng cạnh một: cạnh sai quy tắc bị bỏ và
đếm lại (`ExtractResult.rejected`), không làm hỏng cả gói. Một trong các quy tắc: `known_as` trùng
tên hay biệt danh lớp truth của một nút khác thì bỏ cạnh, vì người chơi sẽ biết nút này dưới tên
của nút kia (D-62, `safety.reveal.known_as_conflicts`). `RESOLVED_IN` phải kèm câu trích nguyên văn
như hé lộ (D-82). Bộ trích không được biết dàn ý định gỡ mạch nào, để không ghi gỡ theo ý định.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from writory.graph.commit import needs_known_as
from writory.graph.package import (
    KNOWS_HOW,
    ChangePackage,
    CloseSpec,
    EdgeSpec,
    NodeSpec,
    quote_in_text,
)
from writory.graph.schema import NAMED_LABELS
from writory.llm.base import ChatResult, LLMClient
from writory.pipeline.pacing import ThreadGoal
from writory.pipeline.passages import STOPWORDS, flat
from writory.safety.reveal import known_as_conflicts
from writory.safety.wrap import (
    DATA_NOTICE,
    UserAuthored,
    escape_text,
    system_message,
    user_message,
)

# Đổi chữ prompt thì tăng số. extract-2: luật rút từ lý do bị bỏ ở bài C v1. extract-3: mạch phải
# gỡ đang mở, định nghĩa "gỡ", RESOLVED_IN bắt buộc câu trích (D-82). extract-4: mạch nhiều vế chỉ
# gỡ khi mọi vế có trả lời (D-84). extract-5: KNOWS của nhân vật chính ghi ngay chương trang cho thấy
# nhân vật chính biết, không để sang chương sau (D-92). extract-6: `new_facts` (D-93). extract-7:
# Fact mới chỉ là điều xảy ra hay đúng trong thế giới, có ví dụ đúng và sai (D-95).
PROMPT_VERSION = "extract-7"

# Kiểu cạnh model được trích. FEELS (lựa chọn nội tâm) do bước ghi lựa chọn ghi, không trích.
ExtractEdgeType = Literal[
    "RELATES_TO", "LOCATED_AT", "HOLDS", "MEMBER_OF", "PARTICIPATED_IN", "DIED_IN",
    "KNOWS", "TOLD", "TOLD_TO", "ABOUT", "RESOLVED_IN", "REVEALED_TO_PLAYER",
]
KnowsHow = Literal["chứng kiến", "được kể", "suy ra", "tự biết", "tự làm"]
assert set(KnowsHow.__args__) == set(KNOWS_HOW)


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedEdge(_Out):
    type: ExtractEdgeType
    source: str
    target: str
    kind: str | None  # RELATES_TO: bạn, thù, yêu, thầy trò…
    score: int | None  # RELATES_TO: −100…100
    how: KnowsHow | None  # KNOWS
    told_by: str | None  # KNOWS với how = "được kể"
    quote: str | None  # REVEALED_TO_PLAYER, RESOLVED_IN, KNOWS của nhân vật chính: nguyên văn
    known_as: str | None  # hé lộ nút có tên: tên người chơi thấy, nằm trong quote
    role: str | None  # PARTICIPATED_IN


class NewFact(_Out):
    """Sự thật mới từ trang (D-93). `ref` là nhãn tạm cho các cạnh trong cùng đầu ra; id do code sinh."""

    ref: str
    text: str
    quote: str


class ExtractOutput(_Out):
    edges: list[ExtractedEdge]
    close: list[str]  # id các cạnh đang hiệu lực không còn đúng ở cuối chương
    new_facts: list[NewFact]

    @model_validator(mode="before")
    @classmethod
    def _old_replies(cls, data: Any) -> Any:
        """Trường bắt buộc trong schema gửi model, nhưng trả lời cũ (fixture, bài C) chưa có thì coi
        là rỗng."""
        if isinstance(data, dict) and "new_facts" not in data:
            return {**data, "new_facts": []}
        return data


@dataclass(frozen=True)
class FactRules:
    """Luật Fact mới (D-93), lấy từ `config/limits.yaml` `facts`. `max_new`: còn được tạo bao nhiêu
    trong chương này (0 = tắt)."""

    max_new: int
    max_chars: int
    scene: int
    duplicate_overlap: float
    grounded_min: float
    # Trùng khi Fact mới gần như nằm trọn trong Fact kia VÀ cùng nói về một thực thể (D-95).
    related_overlap: float = 1.0


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    text: str  # tên (nút có tên), chữ của Fact/Event/Lie/Thread, hoặc tiêu đề chương
    aliases: tuple[str, ...] = ()
    user_authored: bool = False

    @classmethod
    def from_node(cls, node_id: str, label: str, props: Mapping[str, Any]) -> "Entity":
        """Mục danh mục từ thuộc tính một nút (lớp truth: tên thật, không phải known_as)."""
        text = (props.get("name") or props.get("text") or props.get("description")
                or props.get("content") or props.get("title") or node_id)
        aliases = tuple(props.get("aliases") or ()) if "name" in props else ()
        return cls(id=node_id, label=label, text=str(text), aliases=aliases,
                   user_authored=bool(props.get("user_authored", False)))


@dataclass(frozen=True)
class OpenEdge:
    id: str
    type: str
    source: str
    target: str


@dataclass
class ExtractResult:
    package: ChangePackage
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (mô tả cạnh, lý do)
    chat: ChatResult | None = None


SYSTEM_PROMPT = """Bạn là người ghi chép đồ thị của một truyện tương tác tiếng Việt. Đọc văn bản một chương và ghi lại những gì THAY ĐỔI hoặc ĐƯỢC HÉ LỘ trong chương đó, dưới dạng cạnh giữa các thực thể.

Quy tắc:
- Chỉ dùng id có trong danh mục thực thể. Không bịa id.
- Chỉ ghi điều xảy ra hoặc được hé lộ trong CHƯƠNG NÀY; điều đã đúng từ trước (đã có trong danh sách cạnh đang hiệu lực) thì không ghi lại.
- Một cạnh đang hiệu lực không còn đúng ở cuối chương (đồ vật đổi chủ, đổi chỗ ở, quan hệ đổi) thì ghi id của nó vào `close` và ghi cạnh mới thay thế.
- Mọi trường không dùng thì để null.

Kiểu cạnh:
- RELATES_TO (nhân vật → nhân vật): B là gì của A lúc này; `kind` (bạn, thù, yêu, thầy trò, người quen…) và `score` từ -100 đến 100. Có hướng: ghi riêng mỗi chiều nếu cả hai đổi.
- LOCATED_AT (nhân vật/đồ vật → nơi chốn), HOLDS (nhân vật → đồ vật đang giữ), MEMBER_OF (nhân vật → phe).
- PARTICIPATED_IN (nhân vật → sự kiện), `role` nếu rõ; DIED_IN (nhân vật → sự kiện nhân vật chết).
- KNOWS (nhân vật → sự thật/sự kiện/lời nói dối): nhân vật biết điều đó từ chương này. `how` là một trong: "chứng kiến", "được kể", "suy ra", "tự biết", "tự làm". Nếu "được kể" thì `told_by` là id người kể. KNOWS tới một lời nói dối nghĩa là biết đó là lời dối.
- TOLD (người nói → lời nói dối) và TOLD_TO (lời nói dối → người nghe).
- ABOUT (sự thật/sự kiện → thực thể mà nó nói về).
- RESOLVED_IN (mạch → nút chương này): một mạch, cài cắm hay câu hỏi bỏ ngỏ được gỡ trong chương này; xem mục "Gỡ mạch".
- REVEALED_TO_PLAYER (thực thể → nút chương này): điều người chơi được thấy trên trang ở chương này, theo góc nhìn nhân vật chính.

Hé lộ cho người chơi:
- Mỗi thực thể trong danh mục xuất hiện trên trang LẦN ĐẦU ở chương này (chưa có cạnh REVEALED_TO_PLAYER trong danh sách cạnh đang hiệu lực) thì ghi một cạnh REVEALED_TO_PLAYER tới nút chương này. Đã hé lộ ở chương trước thì không ghi lại.
- Không đánh dấu hé lộ một bí mật mà trang chỉ gợi ý hay để người đọc đoán. Chỉ ghi khi trang nói rõ điều đó.

Nhân vật chính biết gì (KNOWS):
- KNOWS của nhân vật chính phải được ghi ngay ở chương này khi trang cho thấy nhân vật chính biết: nghe người khác nói ra, tự thấy, tự đọc hay tự suy ra một sự thật, sự kiện hay lời nói dối có trong danh mục. Ghi ngay ở chương này; đừng để sang chương sau, kể cả khi điều ấy còn được nhắc lại nhiều lần về sau.
- Sự thật mà trang vừa hé lộ cho người đọc (REVEALED_TO_PLAYER tới một sự thật) trong lúc nhân vật chính có mặt và nghe thấy thì ghi thêm KNOWS từ nhân vật chính tới sự thật đó, kèm `quote`. Hé lộ cho người đọc và nhân vật chính biết là hai cạnh khác nhau, cần cả hai.
- `how`: "được kể" (kèm `told_by`) nếu người khác nói ra với nhân vật chính; "chứng kiến" nếu tự thấy; "suy ra" nếu tự nối các chi tiết.
- Không ghi KNOWS cho điều trang chỉ để người đọc đoán, hay điều chỉ nhân vật khác biết khi nhân vật chính không có mặt.

Gỡ mạch (RESOLVED_IN):
- Một mạch được gỡ khi trang trả lời rõ câu hỏi chính của mạch, hoặc khi nhân vật đưa ra quyết định mà mạch đòi. Chi tiết phụ còn bỏ ngỏ không giữ mạch mở: câu hỏi chính đã có câu trả lời, hay quyết định đã được nói ra, thì ghi gỡ.
- Mạch có nhiều vế (mô tả nối bằng "và", hay đòi cả tìm hiểu lẫn quyết định) chỉ gỡ khi trang trả lời MỌI vế. Một vế của mạch không phải chi tiết phụ: mới trả lời một vế, mới có thoả thuận tạm, hay quyết định còn để ngỏ phần lâu dài thì CHƯA gỡ.
- Chỉ nhắc lại điều đã biết từ chương trước, chỉ gợi ý, hay hứa sẽ làm rõ sau thì KHÔNG phải gỡ.
- Mục "Mạch phải gỡ đang mở" (nếu có) liệt kê các mạch truyện phải gỡ, kèm hạn: soát từng mạch trong đó với văn bản chương. Trạng thái hạn chỉ để biết mạch nào cần soát kỹ, không phải lý do để ghi gỡ.
- RESOLVED_IN bắt buộc có `quote`: câu trên trang trả lời câu hỏi chính hay nói ra quyết định đó.

Câu trích (`quote`):
- Bắt buộc với REVEALED_TO_PLAYER, với RESOLVED_IN, và với KNOWS mà người biết là nhân vật chính. Không có câu trích thì KHÔNG ghi cạnh đó.
- Chép NGUYÊN VĂN một đoạn ngắn liền mạch trong chương (một câu là đủ); không sửa chữ, không ghép hai đoạn, không thêm dấu ba chấm.
- Hé lộ một nhân vật, nơi chốn, đồ vật hay phe thì `known_as` là cái tên người chơi đọc thấy trên trang, CHÉP Y NGUYÊN từ bên trong `quote` (cùng chữ hoa, cùng dấu). Không dùng tên thật nếu trang chỉ gọi bằng biệt danh.

Sự thật mới (`new_facts`):
- Chỉ ghi điều ĐÃ XẢY RA hay ĐÚNG trong thế giới truyện mà trang nêu cụ thể: ai làm gì với ai, vật ở đâu, ai hứa hay đòi gì, ai nói gì (nội dung lời nói), ai phát hiện điều gì ở đâu. Mỗi sự thật một việc.
- KHÔNG ghi: ý định, quyết định, cảm nghĩ, nhận xét, đánh giá hay suy đoán của nhân vật chính hay của ai khác ("quyết định…", "cho rằng…", "nghĩ…", "có căn cứ…", "nhớ…", "lo…"); điều trang chỉ gợi ý; và điều danh mục đã có, kể cả bí mật đã lộ, dù diễn đạt khác (dùng id có sẵn trong KNOWS); hai sự thật cùng nói về một việc.
- Ví dụ ĐÚNG: "Lan đưa gói trà cho Minh trước khi rời quán." "Lão Gù hứa giữ kín chuyện thanh kiếm." "Khải đòi Minh trả lại chiếc nhẫn trước đêm nay."
- Ví dụ SAI: "Minh quyết định không nói với Lan." (quyết định) "Minh nghĩ Lan đang giấu điều gì." (suy đoán) "Minh nhớ nét chữ trên mảnh giấy." (cảm nghĩ) "Lan làm việc cho Hội Hắc Kỳ" khi danh mục đã có sự thật "Lan là gián điệp của Hội Hắc Kỳ" (trùng, dù diễn đạt khác).
- Mỗi sự thật mới có `ref` (new_1, new_2…), `text` và `quote`. `text` là MỘT câu ngắn, trung tính, một dòng, chỉ nêu điều trang đã nói bằng chữ của trang, không thêm suy đoán hay chi tiết. `quote` chép NGUYÊN VĂN từ chương.
- Dùng `ref` như một id trong các cạnh. Mỗi sự thật mới BẮT BUỘC có ít nhất một cạnh ABOUT (sự thật mới → thực thể trong danh mục mà nó nói về) và một cạnh KNOWS (người biết → sự thật mới; nhân vật chính biết thì KNOWS cần `quote` như mọi KNOWS của nhân vật chính). Thiếu một trong hai thì sự thật mới bị bỏ.
- Không ghi REVEALED_TO_PLAYER cho sự thật mới: code tự ghi. Số sự thật mới tối đa cho chương này ghi ở cuối đề; có thể để `new_facts` rỗng.

Không ghi trùng: mỗi bộ (kiểu, từ, tới) chỉ một cạnh.
"""


def _entity_line(e: Entity) -> list[str | UserAuthored]:
    # Tên/chữ nút do model khởi tạo hay model trích viết: ngoài khối dữ liệu thì escape (G4).
    # Id giữ nguyên để model chép lại được: ID_PATTERN không cho `<`, `&`, nên id không tạo được thẻ.
    head = f"- {e.id} | {e.label} | "
    aliases = f" (gọi là: {', '.join(e.aliases)})" if e.aliases else ""
    if e.user_authored:
        return [head, UserAuthored(e.text + aliases, "entity")]
    return [head + escape_text(e.text + aliases)]


# Trạng thái hạn của mạch phải gỡ, cho bộ trích (D-82). `later` (chưa tới khoảng gỡ) không liệt kê.
_THREAD_STATUS = {"overdue": "quá hạn", "due": "đến hạn ở chương này", "open": "trong khoảng gỡ"}


def _window(low: int | None, high: int | None) -> str:
    if low is None or high is None:
        return "trước khi kết truyện"
    return f"chương {low}" if low == high else f"chương {low}–{high}"


def _thread_lines(threads: Sequence[ThreadGoal]) -> list[str | UserAuthored]:
    """Mục "Mạch phải gỡ đang mở". Mô tả do model khởi tạo viết thì escape; mạch người chơi viết
    thì bọc (G4). Rỗng thì không có mục: bài C (truyện mẫu, không kế hoạch) không bị nhắc sai."""
    listed = [t for t in threads if t.status in _THREAD_STATUS]
    if not listed:
        return []
    parts: list[str | UserAuthored] = [
        "Mạch phải gỡ đang mở (id | hạn gỡ | trạng thái | mô tả):"]
    for t in listed:
        head = (f"- {t.thread_id} | {_window(t.from_chapter, t.to_chapter)} | "
                f"{_THREAD_STATUS[t.status]} | ")
        if t.user_authored:
            parts += [head, UserAuthored(t.description, "thread")]
        else:
            parts.append(head + escape_text(t.description))
    return parts


def build_messages(
    *, chapter: int, chapter_id: str, protagonist_id: str, chapter_text: str,
    entities: list[Entity], open_edges: list[OpenEdge], threads: Sequence[ThreadGoal] = (),
    fact_rules: "FactRules | None" = None,
):
    parts: list[str | UserAuthored] = [
        f"Chương: {chapter} (id nút chương: {chapter_id}). Nhân vật chính: {protagonist_id}.",
        "Danh mục thực thể (id | nhãn | tên hoặc nội dung):",
    ]
    for e in entities:
        parts += _entity_line(e)
    parts.append("Cạnh đang hiệu lực trước chương này (id | kiểu | từ → tới):")
    parts += [f"- {o.id} | {o.type} | {o.source} → {o.target}" for o in open_edges] or ["- (không có)"]
    parts += _thread_lines(threads)
    if fact_rules is not None and fact_rules.max_new > 0:
        parts.append(f"Sự thật mới: còn được ghi tối đa {fact_rules.max_new} sự thật mới trong chương "
                     f"này, mỗi `text` dài tối đa {fact_rules.max_chars} ký tự.")
    else:
        parts.append("Sự thật mới: không ghi (new_facts để rỗng).")
    # Văn bản chương có thể chứa chữ người chơi (tên, hành động tự viết): luôn bọc như dữ liệu (G4).
    parts += ["Văn bản chương:", UserAuthored(chapter_text, "chapter_text")]
    return [system_message(SYSTEM_PROMPT, DATA_NOTICE), user_message(*parts)]


def _node(known: dict[str, Entity], node_id: str, protagonist_id: str) -> dict:
    """Dạng `needs_known_as` cần (graph/commit.py)."""
    return {"labels": [known[node_id].label], "protagonist": node_id == protagonist_id}


_REF = re.compile(r"^new_\d+$")
_MIN_FACT_CHARS = 8


def _syllables(text: str) -> set[str]:
    return {t for t in flat(text).split() if t not in STOPWORDS}


def _overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _human_protagonist(text: str, protagonist: Entity | None) -> str:
    """Model hay chép id nội bộ ("protagonist") vào chữ Fact; sổ tay sẽ hiện chữ tiếng Anh. Đổi thành
    "nhân vật chính", trừ khi id là một phần tên thật (truyện mẫu: id `minh`, tên Trần Minh)."""
    if protagonist is None:
        return text
    pid = protagonist.id
    names = flat(" ".join((protagonist.text, *protagonist.aliases)))
    if pid.casefold() in names.split():
        return text
    out = re.sub(rf"\b{re.escape(pid)}\b", "nhân vật chính", text, flags=re.IGNORECASE)
    return out[:1].upper() + out[1:] if out != text and text[:1].isupper() else out


def _covered(new: set[str], old: set[str]) -> float:
    """Phần âm tiết của Fact MỚI đã nằm trong Fact cũ. Một chiều có chủ đích: Fact cụ thể hơn, chứa trọn
    Fact cũ cộng thêm chi tiết (điều khoản, nơi chốn), có độ phủ thấp nên được giữ."""
    return len(new & old) / len(new) if new else 0.0


@dataclass
class _FactPlan:
    nodes: dict[str, NodeSpec] = field(default_factory=dict)  # id sinh ra → nút
    quotes: dict[str, str] = field(default_factory=dict)  # id sinh ra → câu trích
    ids: dict[str, str] = field(default_factory=dict)  # ref → id (mới, hoặc Fact cũ nếu trùng)
    remapped: set[str] = field(default_factory=set)  # ref trùng Fact đã có
    dropped: set[str] = field(default_factory=set)  # ref bị bỏ
    rejected: list[tuple[str, str]] = field(default_factory=list)


def _plan_new_facts(
    facts: Sequence[NewFact], rules: FactRules | None, *, chapter: int,
    known: Mapping[str, Entity], chapter_text: str, about_of: Mapping[str, set[str]],
    protagonist_id: str = "",
) -> _FactPlan:
    """Kiểm từng Fact mới bằng code (D-93): câu trích nguyên văn (G3), một câu ngắn bám trang, không
    trùng Fact đã có, kể cả bí mật đã lộ, hay trùng Fact mới khác trong chương (trùng thì dùng lại id
    cũ), dưới trần mỗi chương. Trùng là Jaccard âm tiết từ `duplicate_overlap`, hoặc một Fact gần như
    nằm trọn trong Fact kia (`related_overlap`, đo trên Fact mới) và cùng ABOUT một thực thể (D-95: hai
    ngưỡng này bắt các cặp nói lại của lần phát lại D-93, không bắt hai Fact chỉ chung vài từ, cũng không
    bắt Fact cụ thể hơn Fact cũ). Id do code
    sinh. Chữ chép tên người chơi viết thì đánh dấu `user_authored` (G4)."""
    plan = _FactPlan()
    page = _syllables(chapter_text)
    theirs = {e.id: _syllables(e.text) for e in known.values() if e.label == "Fact"}
    mine: dict[str, set[str]] = {}
    player_names = [flat(n) for e in known.values() if e.user_authored for n in (e.text, *e.aliases)]
    refs: set[str] = set()
    for f in facts:
        desc = f"Fact mới {f.ref}"

        def drop(why: str, ref: str = f.ref, desc: str = desc) -> None:
            plan.dropped.add(ref)
            plan.rejected.append((desc, why))

        if rules is None or rules.max_new <= 0:
            drop("hết trần Fact mới của chương, hoặc tính năng đang tắt (D-93)")
        elif not _REF.fullmatch(f.ref) or f.ref in known or f.ref in refs:
            drop("ref phải dạng new_<số>, không trùng id có sẵn hay ref khác")
        else:
            refs.add(f.ref)
            text = f.text.strip()
            tokens = _syllables(text)
            if "\n" in text or not _MIN_FACT_CHARS <= len(text) <= rules.max_chars:
                drop(f"chữ phải một dòng dài {_MIN_FACT_CHARS}–{rules.max_chars} ký tự")
            elif not quote_in_text(f.quote, chapter_text):
                drop("câu trích không có nguyên văn trong chương (G3)")
            elif (same := next((i for i, t in {**theirs, **mine}.items()
                                if _overlap(tokens, t) >= rules.duplicate_overlap
                                or (_covered(tokens, t) >= rules.related_overlap
                                    and about_of.get(f.ref, set()) & about_of.get(i, set()))),
                               None)) is not None:
                plan.ids[f.ref] = same
                plan.remapped.add(f.ref)
                plan.rejected.append((desc, f"trùng Fact {same}, dùng lại id đó"))
            elif not tokens or len(tokens & page) / len(tokens) < rules.grounded_min:
                drop("chữ Fact không bám trang (nhiều từ không có trên trang)")
            else:
                if len(plan.nodes) >= rules.max_new:
                    drop("vượt trần Fact mới mỗi chương (config)")
                else:
                    n = 1
                    while (fid := f"fact_c{chapter}s{rules.scene}_{n}") in known or fid in plan.nodes:
                        n += 1
                    props: dict[str, Any] = {
                        "text": _human_protagonist(text, known.get(protagonist_id))}
                    if any(name and name in flat(text) for name in player_names):
                        props["user_authored"] = True
                    plan.nodes[fid] = NodeSpec(id=fid, label="Fact", props=props)
                    plan.quotes[fid] = f.quote
                    plan.ids[f.ref] = fid
                    mine[fid] = tokens
    return plan


def to_package(
    output: ExtractOutput, *, chapter: int, commit_id: str, protagonist_id: str,
    chapter_text: str, entities: list[Entity], open_edges: list[OpenEdge],
    threads: Sequence[ThreadGoal] = (), fact_rules: FactRules | None = None,
) -> tuple[ChangePackage, list[tuple[str, str]]]:
    """Đổi đầu ra của model thành `ChangePackage`; cạnh sai quy tắc bị bỏ, kèm lý do.
    `threads`: mạch phải gỡ chưa gỡ kèm trạng thái hạn (`ChapterGoals.threads`). `RESOLVED_IN` của
    mạch trong đó còn `later` (chưa tới khoảng gỡ) bị bỏ (D-84); mạch ngoài danh sách không đổi."""
    known = {e.id: e for e in entities}
    existing = set(known)  # id có sẵn trước khi thêm Fact mới
    # Thực thể mỗi Fact nói về: Fact có sẵn theo cạnh ABOUT đang hiệu lực, Fact mới theo cạnh trong đầu ra.
    about_of: dict[str, set[str]] = {}
    for o in open_edges:
        if o.type == "ABOUT":
            about_of.setdefault(o.source, set()).add(o.target)
    for x in output.edges:
        if x.type == "ABOUT":
            about_of.setdefault(x.source, set()).add(x.target)
    plan = _plan_new_facts(output.new_facts, fact_rules, chapter=chapter, known=known,
                           chapter_text=chapter_text, about_of=about_of, protagonist_id=protagonist_id)
    for fid, node in plan.nodes.items():
        known[fid] = Entity(fid, "Fact", node.props["text"],
                            user_authored=bool(node.props.get("user_authored")))
    not_yet = {t.thread_id: t for t in threads if t.status == "later"}
    # Tên lớp truth của mọi nút có tên, kể cả tên người chơi viết: để bắt `known_as` của nút khác.
    names = {e.id: (e.text, *e.aliases) for e in entities if e.label in NAMED_LABELS}
    open_by_id = {o.id: o for o in open_edges}
    rejected: list[tuple[str, str]] = list(plan.rejected)
    open_knows = {(o.source, o.target) for o in open_edges if o.type == "KNOWS"}
    edges: list[EdgeSpec] = []
    seen: set[str] = set()
    for x in output.edges:
        desc = f"{x.type} {x.source}→{x.target}"
        refs_used = {i for i in (x.source, x.target, x.told_by) if i in plan.dropped}
        if refs_used:
            rejected.append((desc, f"Fact mới bị bỏ: {sorted(refs_used)}"))
            continue
        if x.type == "ABOUT" and x.source in plan.remapped:
            continue  # Fact trùng: dùng lại Fact cũ, nó đã có ABOUT riêng
        x = x.model_copy(update={
            "source": plan.ids.get(x.source, x.source), "target": plan.ids.get(x.target, x.target),
            "told_by": plan.ids.get(x.told_by, x.told_by) if x.told_by else None})
        missing = [i for i in (x.source, x.target, x.told_by) if i is not None and i not in known]
        if missing:
            rejected.append((desc, f"id không có trong danh mục: {missing}"))
            continue
        if x.type == "KNOWS" and (x.source, x.target) in open_knows:
            # Hai KNOWS đang hiệu lực giữa cùng hai nút làm hỏng truy vấn một-cạnh (D-95).
            rejected.append((desc, "đã có KNOWS đang hiệu lực giữa hai nút này"))
            continue
        if ((x.source in plan.nodes and x.type != "ABOUT") or x.told_by in plan.nodes
                or (x.target in plan.nodes and x.type != "KNOWS")):
            rejected.append((desc, "Fact mới chỉ làm nguồn của ABOUT và đích của KNOWS (D-93)"))
            continue
        if x.quote is not None and not quote_in_text(x.quote, chapter_text):
            rejected.append((desc, "câu trích không có nguyên văn trong chương (G3)"))
            continue
        if x.type == "KNOWS" and x.source == protagonist_id and not x.quote:
            # G3: người chơi chỉ biết điều có trên trang; thiếu bằng chứng thì không ghi.
            rejected.append((desc, "nhân vật chính biết mà không có câu trích (G3)"))
            continue
        if x.type == "RESOLVED_IN" and not x.quote:
            # Gỡ mạch phải có bằng chứng trên trang, để không ghi gỡ giả (D-82).
            rejected.append((desc, "gỡ mạch mà không có câu trích (D-82)"))
            continue
        if x.type == "RESOLVED_IN" and x.source in not_yet:
            # Bộ trích lấy mạch từ danh mục dù mạch không có trong mục "đang mở" (D-84).
            t = not_yet[x.source]
            window = _window(t.from_chapter, t.to_chapter)
            rejected.append((desc, f"mạch phải gỡ chưa tới khoảng gỡ, {window} (D-84)"))
            continue
        props = {
            k: v for k, v in (("kind", x.kind), ("score", x.score), ("how", x.how),
                              ("told_by", x.told_by), ("quote", x.quote), ("role", x.role))
            if v is not None
        }
        if needs_known_as(x.type, _node(known, x.source, protagonist_id),
                          _node(known, x.target, protagonist_id)):
            if not x.known_as:
                rejected.append((desc, "hé lộ nút có tên mà thiếu known_as (D-17)"))
                continue
            node = x.source if x.type == "REVEALED_TO_PLAYER" else x.target
            others = known_as_conflicts(x.known_as, node, names)
            if others:
                rejected.append((desc, f"known_as là tên của nút khác: {others} (D-62)"))
                continue
            props["known_as"] = x.known_as
        try:
            spec = EdgeSpec.model_validate(
                {"type": x.type, "from": x.source, "to": x.target, "valid_from_chapter": chapter,
                 "props": props}
            )
        except ValidationError as e:
            rejected.append((desc, "; ".join(err["msg"] for err in e.errors(include_url=False))))
            continue
        if spec.id in seen:
            rejected.append((desc, "trùng cạnh trong cùng gói"))
            continue
        seen.add(spec.id)
        edges.append(spec)
    # Fact mới phải có ABOUT tới thực thể có sẵn và KNOWS; thiếu thì bỏ cả Fact và cạnh của nó (D-93).
    for fid in list(plan.nodes):
        lacking = [name for name, ok in (
            ("ABOUT", any(e.type == "ABOUT" and e.source == fid and e.target in existing
                          for e in edges)),
            ("KNOWS", any(e.type == "KNOWS" and e.target == fid for e in edges))) if not ok]
        if lacking:
            rejected.append((f"Fact mới {fid}", f"thiếu {' và '.join(lacking)} hợp lệ: bỏ Fact"))
            del plan.nodes[fid]
            gone = [e for e in edges if fid in (e.source, e.target)]
            seen -= {e.id for e in gone}
            edges = [e for e in edges if e not in gone]
    # Fact mới lấy từ trang nên mặc định đã hé lộ cho người chơi, kèm chính câu trích của nó. Bí mật chỉ
    # đến từ khởi tạo: đường này không tạo được (D-93).
    for fid in plan.nodes:
        edges.append(EdgeSpec.model_validate({
            "type": "REVEALED_TO_PLAYER", "from": fid, "to": f"ch{chapter}",
            "valid_from_chapter": chapter, "props": {"quote": plan.quotes[fid]}}))
    # Người kể tự thú chuyện của chính mình thì chính trang chứng minh họ biết (D-92). Đồ thị chương 0
    # hay thiếu người biết (bí mật "Trần Mặc bán tin" chỉ cho người khác biết), nên người canh báo
    # `teller_does_not_know`, cạnh KNOWS "được kể" bị cắt và cảnh bị viết lại oan. Chỉ khi điều kể
    # nói về chính người kể: có ABOUT tới họ, hay họ tham gia sự kiện mà điều đó nói về. Người thứ ba
    # kể bí mật của người khác thì giữ luật cũ: đó đúng là chuyện người canh phải bắt.
    links = [(o.type, o.source, o.target) for o in open_edges]
    links += [(e.type, e.source, e.target) for e in edges]
    about: dict[str, set[str]] = {}
    for kind, source, target in links:
        if kind == "ABOUT":
            about.setdefault(source, set()).add(target)
    took_part = {(source, target) for kind, source, target in links if kind == "PARTICIPATED_IN"}
    knowers = {(source, target) for kind, source, target in links if kind == "KNOWS"}
    for e in list(edges):
        teller = e.props.get("told_by")  # chỉ KNOWS "được kể" có (EdgeSpec)
        if (e.type != "KNOWS" or not isinstance(teller, str) or teller == protagonist_id
                or known[teller].label != "Character" or (teller, e.target) in knowers):
            continue
        subjects = about.get(e.target, set())
        if teller not in subjects and not any(
                (teller, x) in took_part for x in (*subjects, e.target)):
            continue
        spec = EdgeSpec.model_validate({"type": "KNOWS", "from": teller, "to": e.target,
                                        "valid_from_chapter": chapter, "props": {"how": "tự biết"}})
        if spec.id not in seen:  # bộ trích đã tự ghi KNOWS cho người kể (cùng id)
            seen.add(spec.id)
            edges.append(spec)
    close: list[CloseSpec] = []
    for cid in dict.fromkeys(output.close):
        if cid not in open_by_id:
            rejected.append((f"close {cid}", "không phải cạnh đang hiệu lực"))
            continue
        close.append(CloseSpec(type=open_by_id[cid].type, id=cid, valid_to_chapter=chapter))
    # Đồ vật chỉ có một chỗ (D-90): có người giữ thì hết "ở nơi", đặt xuống nơi thì hết "được giữ".
    # Model hay ghi cạnh mới mà quên đóng cạnh kia, nên đóng bằng code.
    closed = {c.id for c in close}
    for e in edges:
        if e.type == "HOLDS":
            opposite, item = "LOCATED_AT", e.target
        elif e.type == "LOCATED_AT" and known[e.source].label == "Item":
            opposite, item = "HOLDS", e.source
        else:
            continue
        for o in open_edges:
            if o.type != opposite or o.id in closed:
                continue
            if (o.source if opposite == "LOCATED_AT" else o.target) == item:
                close.append(CloseSpec(type=o.type, id=o.id, valid_to_chapter=chapter))
                closed.add(o.id)
    edges, close = _one_place_for_protagonist(edges, close, open_edges, protagonist_id, chapter,
                                              rejected)
    return (ChangePackage(commit_id=commit_id, nodes=list(plan.nodes.values()), edges=edges,
                          close=close), rejected)


def _one_place_for_protagonist(
    edges: list[EdgeSpec], close: list[CloseSpec], open_edges: Sequence[OpenEdge],
    protagonist_id: str, chapter: int, rejected: list[tuple[str, str]],
) -> tuple[list[EdgeSpec], list[CloseSpec]]:
    """Nhân vật chính luôn có đúng một nơi ở hiện tại sau mỗi gói (D-112, như D-90 cho đồ vật).
    long-tu-tien-2: bộ trích đóng nơi ở ở ch7 mà không mở cạnh mới, 11 chương không có nơi ở và cờ
    `standstill` (D-98) mù. Làm bằng code vì model hay ghi cạnh mới mà quên đóng cạnh cũ, hoặc ngược lại:
    - nơi mới thì đóng nơi cũ; hai nơi mới trong một gói thì giữ nơi ghi sau cùng;
    - đóng nơi cũ mà không mở nơi mới thì giữ nơi cũ (bỏ lệnh đóng);
    - nói lại nơi đang ở thì bỏ cạnh mới (nó đặt lại `valid_from`, cờ đếm lại từ đầu) và bỏ lệnh đóng."""
    here = [o for o in open_edges if o.type == "LOCATED_AT" and o.source == protagonist_id]
    desc = "LOCATED_AT {}→{}".format
    moves = [e for e in edges if e.type == "LOCATED_AT" and e.source == protagonist_id]
    staying = {o.target: o for o in here}
    kept_moves = []
    for e in moves:
        if e.target in staying:
            rejected.append((desc(e.source, e.target), "đã ở nơi này (D-112)"))
        else:
            kept_moves.append(e)
    for e in kept_moves[:-1]:
        rejected.append((desc(e.source, e.target), "hai nơi ở cùng lúc: giữ nơi ghi sau cùng (D-112)"))
    dropped = {id(e) for e in moves} - {id(e) for e in kept_moves[-1:]}
    edges = [e for e in edges if id(e) not in dropped]
    ids = {o.id for o in here}
    if kept_moves:  # đi tới nơi mới: mọi nơi cũ đóng lại
        have = {c.id for c in close}
        close = [*close, *(CloseSpec(type="LOCATED_AT", id=o.id, valid_to_chapter=chapter)
                           for o in here if o.id not in have)]
        return edges, close
    for c in close:
        if c.id in ids:
            rejected.append((f"close {c.id}", "nhân vật chính phải có một nơi ở: giữ nơi cũ (D-112)"))
    return edges, [c for c in close if c.id not in ids]


def without_facts(package: ChangePackage, fact_ids: set[str]) -> ChangePackage:
    """Bỏ các Fact mới này cùng mọi cạnh đi ra hay đi tới chúng (D-93)."""
    if not fact_ids:
        return package
    return package.model_copy(update={
        "nodes": [n for n in package.nodes if n.id not in fact_ids],
        "edges": [e for e in package.edges if not {e.source, e.target} & fact_ids]})


def orphan_facts(package: ChangePackage) -> set[str]:
    """Id Fact mới trong gói mà không cạnh KNOWS nào còn trỏ tới (D-93): người canh có thể cắt KNOWS
    sau bước trích, mà Fact không ai biết thì không nên ghi."""
    known = {e.target for e in package.edges if e.type == "KNOWS"}
    return {n.id for n in package.nodes if n.label == "Fact" and n.id not in known}


async def extract_changes(
    llm: LLMClient, model: str, *, chapter: int, chapter_id: str, commit_id: str,
    protagonist_id: str, chapter_text: str, entities: list[Entity], open_edges: list[OpenEdge],
    threads: Sequence[ThreadGoal] = (), extra: Mapping[str, Any] | None = None,
    fact_rules: FactRules | None = None,
) -> ExtractResult:
    """Một lời gọi model. Lỗi schema để nơi gọi thử lại theo RETRY_SCHEMA (G11, D-14).
    `threads`: mạch phải gỡ chưa gỡ, kèm trạng thái hạn (`ChapterGoals.threads`, D-82).
    `fact_rules`: luật Fact mới (D-93); None = tắt."""
    messages = build_messages(
        chapter=chapter, chapter_id=chapter_id, protagonist_id=protagonist_id,
        chapter_text=chapter_text, entities=entities, open_edges=open_edges, threads=threads,
        fact_rules=fact_rules,
    )
    output, chat = await llm.chat_json(model, messages, ExtractOutput, extra=extra)
    package, rejected = to_package(
        output, chapter=chapter, commit_id=commit_id, protagonist_id=protagonist_id,
        chapter_text=chapter_text,
        entities=entities, open_edges=open_edges, threads=threads, fact_rules=fact_rules,
    )
    return ExtractResult(package=package, rejected=rejected, chat=chat)
