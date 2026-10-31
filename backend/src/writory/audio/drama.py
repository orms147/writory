"""Phần dùng model của bộ viết kịch bản audio (vai `audio`, config/models.yaml; D-151).

Ba loại lời gọi, cả ba trả JSON theo schema (G11) và qua phép kiểm bằng code trước khi dùng:
- `make_ideas`: từ vài tag, đề xuất vài hướng đi ngắn cho admin chọn.
- `make_plan`: từ một hướng đi, lập kế hoạch: nhân vật, bí mật và đoạn lộ, đúng số đoạn code tính từ số phút.
- `write_segment`: viết một đoạn. Ngữ cảnh là kế hoạch, tóm tắt các đoạn trước và vài dòng cuối của đoạn
  liền trước (bộ nhớ của truyện). Code giữ lịch lộ bí mật: bí mật đến hạn phải lộ kèm câu trích có thật
  trong đoạn (như G3), bí mật chưa đến hạn không được báo là đã lộ.

Chữ admin (tag, hướng đi) và mọi chữ model viết từ đó (kế hoạch, tóm tắt, các dòng trước) vào prompt trong
khối dữ liệu (G4), không bao giờ vào vai system.

Schema không có giá trị mặc định hay ràng buộc kiểu `Field(...)` (như `export/shots.py`): OpenRouter gửi schema ở
chế độ `strict`; mọi ràng buộc kiểm bằng code ở `plan_problems`, `segment_problems`.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from writory.audio.render import NARRATOR, Premise, Targets, word_count
from writory.config import AudioScriptLimits, QualityConfig, RetryLimits
from writory.errors import ErrorCode, WritoryError
from writory.graph.package import quote_in_text
from writory.llm.base import LLMClient, Message
from writory.llm.retry import with_json_retries
from writory.quality.checks import check_foreign_script, check_meta_leak
from writory.safety.wrap import DATA_NOTICE, UserAuthored, escape_text, system_message, user_message

PROMPT_VERSION = "audio-2"  # đổi chữ prompt thì tăng số; audio-2: giọng lố hơn (D-152)
ROLE = "audio"
_ID_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
CAST_MIN, CAST_MAX, SECRETS_MAX, BEATS_MAX = 2, 12, 6, 8
ADULT_AGE = 18


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Idea(_Strict):
    title: str
    premise: str  # 3 đến 5 câu
    hooks: list[str]  # cảnh đáng chờ


class ProposeOutput(_Strict):
    ideas: list[Idea]


class CastMember(_Strict):
    id: str
    name: str
    gender: Literal["nam", "nữ", "khác"]
    age: int
    role: str  # vai trong truyện: thiếu gia thật, tiểu thư giả...
    voice: str  # gợi ý giọng đọc cho TTS
    romance: bool  # có tuyến tình cảm: phải đủ tuổi trưởng thành (code kiểm)


class Secret(_Strict):
    id: str
    text: str  # sự thật bị giấu
    reveal_segment: int  # đoạn người nghe biết sự thật, từ 1


class SegmentPlan(_Strict):
    title: str
    beats: list[str]


class PlanOutput(_Strict):
    title: str
    logline: str
    protagonist_id: str  # người kể ngôi thứ nhất
    cast: list[CastMember]
    secrets: list[Secret]
    segments: list[SegmentPlan]
    ending: str


class Line(_Strict):
    speaker: str  # NARRATOR hay id nhân vật
    text: str
    cue: str  # cách đọc ngắn; "" = không có
    sfx: str  # âm thanh trước dòng; "" = không có


class Reveal(_Strict):
    secret_id: str
    quote: str  # câu chép nguyên văn từ chữ của đoạn


class SegmentOutput(_Strict):
    lines: list[Line]
    reveals: list[Reveal]
    summary: str


# --- kiểm bằng code -------------------------------------------------------------------------------


def _bad(problems: Sequence[str], schema: str) -> WritoryError:
    # Lỗi chỉ mang id, số và lý do do code viết; không chép chữ model trả về.
    return WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=f"{schema}: " + "; ".join(problems[:6]))


def idea_problems(output: ProposeOutput, *, count: int) -> list[str]:
    problems = [] if len(output.ideas) == count else [f"cần đúng {count} hướng đi, nhận {len(output.ideas)}"]
    for n, idea in enumerate(output.ideas, 1):
        if not idea.title.strip() or not idea.premise.strip() or not any(h.strip() for h in idea.hooks):
            problems.append(f"hướng đi {n} thiếu title, premise hay hooks")
    return problems


def plan_problems(plan: PlanOutput, *, segments: int) -> list[str]:
    problems: list[str] = []
    if len(plan.segments) != segments:
        problems.append(f"cần đúng {segments} đoạn, nhận {len(plan.segments)}")
    for n, seg in enumerate(plan.segments, 1):
        if not seg.title.strip() or not any(b.strip() for b in seg.beats) or len(seg.beats) > BEATS_MAX:
            problems.append(f"đoạn {n}: cần title và 1..{BEATS_MAX} beats")
    if not CAST_MIN <= len(plan.cast) <= CAST_MAX:
        problems.append(f"cast cần {CAST_MIN}..{CAST_MAX} nhân vật, nhận {len(plan.cast)}")
    ids = [c.id for c in plan.cast]
    names = [c.name.strip().casefold() for c in plan.cast]
    bad_ids = [i for i in ids if not _ID_RE.fullmatch(i) or i == NARRATOR]
    if bad_ids:
        problems.append(f"id nhân vật sai dạng [a-z][a-z0-9_]*: {', '.join(bad_ids[:5])}")
    if len(set(ids)) != len(ids) or len(set(names)) != len(names) or not all(names):
        problems.append("id hay tên nhân vật trùng hay rỗng")
    if plan.protagonist_id not in ids:
        problems.append(f"protagonist_id {plan.protagonist_id!r} không có trong cast")
    for c in plan.cast:
        if c.romance and c.age < ADULT_AGE:
            problems.append(f"{c.id}: có tuyến tình cảm nên phải từ {ADULT_AGE} tuổi, nhận {c.age}")
        if not 0 <= c.age <= 120:
            problems.append(f"{c.id}: tuổi {c.age} không hợp lệ")
    secret_ids = [s.id for s in plan.secrets]
    if len(plan.secrets) > SECRETS_MAX or len(set(secret_ids)) != len(secret_ids):
        problems.append(f"secrets: tối đa {SECRETS_MAX}, id không trùng")
    for s in plan.secrets:
        if not _ID_RE.fullmatch(s.id) or not s.text.strip():
            problems.append(f"bí mật {s.id!r}: id sai dạng hay text rỗng")
        if not 1 <= s.reveal_segment <= segments:
            problems.append(f"bí mật {s.id}: reveal_segment {s.reveal_segment} ngoài 1..{segments}")
    if not plan.title.strip() or not plan.ending.strip():
        problems.append("thiếu title hay ending")
    return problems


def secret_status(plan: PlanOutput, index: int, slipped: Mapping[str, int] | None = None) -> dict[str, str]:
    """Trạng thái từng bí mật ở đoạn `index`: done (đã lộ ở đoạn trước), due (phải lộ ở đoạn này), later.
    `slipped`: id -> đoạn mới, cho bí mật đến hạn mà đoạn của nó vẫn không lộ sau mọi lượt viết lại."""
    out = {}
    for s in plan.secrets:
        due = max(s.reveal_segment, (slipped or {}).get(s.id, 0))
        out[s.id] = "done" if due < index else "due" if due == index else "later"
    return out


@dataclass(frozen=True)
class SegmentCheck:
    hard: list[str]  # lỗi phải viết lại
    length: str | None  # lệch số chữ mục tiêu; hết lượt viết lại thì vẫn nhận và đánh dấu
    words: int
    missing: list[str] = field(default_factory=list)  # bí mật đến hạn đoạn không lộ; hết lượt thì dời sang đoạn sau


def segment_text(output: SegmentOutput) -> str:
    return "\n".join(line.text for line in output.lines)


def segment_problems(output: SegmentOutput, *, plan: PlanOutput, index: int, target_words: int,
                     tolerance: float, quality: QualityConfig,
                     slipped: Mapping[str, int] | None = None) -> SegmentCheck:
    hard: list[str] = []
    speakers = {NARRATOR, *(c.id for c in plan.cast)}
    unknown = sorted({line.speaker for line in output.lines} - speakers)
    if unknown:
        hard.append(f"người nói không có trong cast: {', '.join(unknown[:5])}")
    if not output.lines or any(not line.text.strip() for line in output.lines):
        hard.append("có dòng rỗng hay không có dòng nào")
    text = segment_text(output)
    if check_foreign_script(text, quality):
        hard.append("lẫn chữ khác hệ (chữ Hán hay đoạn chữ Latin không phải tiếng Việt)")
    if check_meta_leak(text):
        hard.append("lẫn chữ của đề bài hay ghi chú của model vào lời đọc")
    if not output.summary.strip():
        hard.append("summary rỗng")
    status = secret_status(plan, index, slipped)
    claimed = {r.secret_id for r in output.reveals}
    for r in output.reveals:
        state = status.get(r.secret_id)
        if state is None:
            hard.append(f"reveals: không có bí mật {r.secret_id!r}")
        elif state == "later":
            hard.append(f"bí mật {r.secret_id} lộ sớm: chưa tới đoạn của nó")
        elif not quote_in_text(r.quote, text):
            hard.append(f"bí mật {r.secret_id}: câu trích không có nguyên văn trong đoạn")
    missing = [sid for sid, state in status.items() if state == "due" and sid not in claimed]
    words = word_count(text)
    low, high = round(target_words * (1 - tolerance)), round(target_words * (1 + tolerance))
    length = None if low <= words <= high else (
        f"đoạn {'quá ngắn' if words < low else 'quá dài'}: {words} chữ, cần khoảng {target_words} ({low}..{high})")
    return SegmentCheck(hard, length, words, missing)


def missing_text(missing: Sequence[str]) -> list[str]:
    return [f"bí mật {sid} phải lộ trong đoạn này (reveals kèm câu trích)" for sid in missing]


# --- đề -------------------------------------------------------------------------------------------

_CONTENT_RULES = (
    "Luật nội dung: nhân vật có tuyến tình cảm đều từ 18 tuổi trở lên; nhân vật dưới 18 tuổi không bao giờ ở "
    "trong cảnh tình cảm; không cảnh tình dục; không nhắm vào người, tổ chức hay sự kiện có thật; bạo lực ở mức "
    "phim truyền hình. Chỉ dùng chữ Việt có dấu, tên nhân vật viết bằng chữ Việt (có thể là tên Hán Việt), "
    "không chữ Hán.")

PROPOSE_SYSTEM_PROMPT = f"""Bạn là biên kịch truyện audio mạng tiếng Việt, chuyên thể loại sảng văn giải trí \
nhẹ đầu óc ("chết não"): hào môn, thiếu gia thật giả, tiểu thư giả, trà xanh, vả mặt, trọng sinh, tổng tài. \
Người dùng đưa vài tag trong khối dữ liệu.

Đề xuất các hướng đi khác nhau rõ rệt cho một truyện audio một người kể đọc. Mỗi hướng đi:
- title: tên truyện ngắn, gợi tò mò.
- premise: 3 đến 5 câu: nhân vật chính là ai, bị đối xử bất công thế nào, bí mật hay cú lật lớn nhất, cái kết hả hê.
- hooks: 2 đến 4 cảnh đáng chờ (vả mặt, lật mặt, bóc trần) khiến người nghe muốn nghe tới cuối.
{_CONTENT_RULES} Trả JSON đúng schema."""

PLAN_SYSTEM_PROMPT = f"""Bạn là biên kịch truyện audio mạng tiếng Việt thể loại sảng văn ("chết não"): nhịp \
nhanh, mâu thuẫn rõ, phản diện đáng ghét, nhân vật chính lật kèo và vả mặt hả hê. Từ hướng đi trong khối dữ liệu, \
lập kế hoạch cho MỘT truyện audio một người kể đọc.

Kế hoạch gồm:
- title; logline (1 đến 2 câu).
- protagonist_id: id nhân vật chính. Truyện kể ngôi thứ nhất: người kể là nhân vật chính, xưng "tôi".
- cast: {CAST_MIN} đến {CAST_MAX} nhân vật (nên 4 đến 8). id viết thường không dấu (a-z, 0-9, _), không trùng, \
không dùng "{NARRATOR}"; name là tên tiếng Việt, không trùng nhau; gender; age (số); role: vai trong truyện; \
voice: gợi ý giọng đọc cho TTS (trầm ấm, the thé, ngọt giả tạo...); romance: true nếu có tuyến tình cảm.
- secrets: 1 đến {SECRETS_MAX - 1} bí mật hay cú lật, mỗi cái có id, text (sự thật bị giấu) và reveal_segment \
(đoạn người nghe biết sự thật). Rải các cú lật, để cú lớn nhất gần cuối.
- segments: ĐÚNG số đoạn được giao, theo thứ tự; mỗi đoạn có title và 2 đến 6 beats (nhịp ngắn). Đoạn 1 mở bằng \
một câu móc ngay trong 30 giây đầu. Mỗi đoạn có ít nhất một cảnh mâu thuẫn hay vả mặt và kết bằng một câu treo, \
trừ đoạn cuối. Đoạn cuối gỡ mọi mạch và để phản diện trả giá bằng một màn mất mặt công khai trước mọi người, không chỉ bằng thủ tục giấy tờ.
- ending: cái kết, 1 đến 2 câu.
Giọng thể loại: lố và đã tai. Phản diện kiêu căng, khinh người ra mặt; trà xanh diễn sâu (giả yếu đuối, rơm rớm nước mắt, đổ lỗi khéo); người xung quanh a dua theo kẻ mạnh rồi quay ngoắt khi gió đổi chiều. Nhân vật chính nói ít, lạnh, mỗi câu đáp trả là một cú vả.
{_CONTENT_RULES} Trả JSON đúng schema."""

SEGMENT_SYSTEM_PROMPT = f"""Bạn viết lời cho một truyện audio tiếng Việt thể loại sảng văn ("chết não"), một \
người kể đọc qua TTS. Kế hoạch, hướng đi, tóm tắt các đoạn trước và các dòng cuối của đoạn trước nằm trong khối \
dữ liệu.

Viết đoạn được giao, đúng số chữ được giao (tính mọi chữ trong text), dưới dạng danh sách dòng (lines):
- speaker "{NARRATOR}" cho lời kể. Người kể là nhân vật chính, xưng "tôi", câu ngắn, nhiều cảm xúc, như đang kể \
cho người nghe.
- speaker là id nhân vật cho lời thoại nói thành tiếng, kể cả lời của nhân vật chính (dùng id của nhân vật \
chính). Trước lời thoại, lời kể phải cho người nghe biết ai nói, vì TTS chỉ có một giọng, trừ khi đã quá rõ.
- text: chỉ chữ để đọc thành tiếng, tiếng Việt có dấu. Không markdown, không emoji, không ghi chú trong ngoặc. Viết \
số bằng chữ khi đọc lên tự nhiên hơn.
- cue: cách đọc ngắn ("lạnh lùng", "nghẹn ngào"), "" nếu không cần. sfx: âm thanh nền ngắn trước dòng đó ("tiếng \
cửa đóng sầm"), "" nếu không cần.
Bám các nhịp của đoạn và giữ đúng mọi điều đã xảy ra ở các đoạn trước. Mỗi bí mật có trạng thái: "phải lộ trong \
đoạn này" thì viết cảnh người nghe biết rõ sự thật đó và ghi vào reveals (secret_id, và quote là một câu chép \
nguyên văn từ text của đoạn cho thấy sự thật lộ ra); "chưa được lộ" thì chỉ gieo nghi ngờ, không nói ra, không ghi \
vào reveals; "đã lộ" thì không lộ lại như chuyện mới. Kết đoạn bằng một câu treo khiến người nghe muốn nghe tiếp, \
trừ đoạn cuối: đoạn cuối khép truyện theo cái kết của kế hoạch.
Giọng sảng văn ("chết não"), lố và đã tai: câu ngắn, nhịp dồn. Phản diện và trà xanh lộ rõ thói xấu qua lời thoại (khoe khoang, mỉa mai, giả vờ yếu đuối, đổ lỗi). Mỗi đoạn có ít nhất một màn vả mặt trước đám đông: nhân vật chính đáp bằng một câu đanh hay tung một bằng chứng đúng lúc, kẻ ác tái mặt, đám đông xôn xao rồi đổi thái độ. Người kể được bình luận cay và hả hê với người nghe ("Tôi suýt bật cười.", "Cô ta còn chưa biết mình sắp mất gì."). Trừng phạt phải là cảnh mất mặt rõ ràng trước mọi người, không kết khô bằng biên bản hay kiểm toán.
summary: tóm tắt đoạn vừa viết, 3 đến 5 câu, ghi rõ ai biết gì, ai ở đâu, quan hệ đổi thế nào.
{_CONTENT_RULES} Trả JSON đúng schema."""

_STATUS_TEXT = {"done": "đã lộ", "due": "phải lộ trong đoạn này", "later": "chưa được lộ"}


def propose_messages(tags: str, *, count: int) -> list[Message]:
    return [system_message(PROPOSE_SYSTEM_PROMPT, DATA_NOTICE),
            user_message("Tag của người dùng:", UserAuthored(tags, "audio_tags"),
                         f"Đề xuất đúng {count} hướng đi.")]


def plan_messages(premise: Premise, targets: Targets) -> list[Message]:
    return [system_message(PLAN_SYSTEM_PROMPT, DATA_NOTICE),
            user_message("Hướng đi:", UserAuthored(premise.text, "audio_premise"),
                         f"Lập kế hoạch cho truyện đọc khoảng {targets.minutes} phút: đúng {targets.segments} đoạn, "
                         f"mỗi đoạn khoảng {targets.words_per_segment} chữ.")]


def _plan_block(plan: PlanOutput, index: int, status: Mapping[str, str]) -> str:
    lines = [f"Tên truyện: {plan.title}", f"Logline: {plan.logline}",
             f"Nhân vật chính (người kể, xưng tôi): {plan.protagonist_id}", "Nhân vật:"]
    lines += [f"- {c.id}: {c.name}, {c.gender}, {c.age} tuổi, {c.role}" for c in plan.cast]
    if plan.secrets:
        lines.append("Bí mật:")
        lines += [f"- {s.id} [{_STATUS_TEXT[status[s.id]]}]: {s.text}" for s in plan.secrets]
    lines.append("Các đoạn:")
    for n, seg in enumerate(plan.segments, 1):
        mark = "  <- ĐOẠN ĐANG VIẾT" if n == index else ""
        lines.append(f"{n}. {seg.title}{mark}")
        if n == index:
            lines += [f"   - {b}" for b in seg.beats]
    lines.append(f"Kết: {plan.ending}")
    return "\n".join(lines)


def segment_messages(plan: PlanOutput, *, premise: Premise, targets: Targets, index: int,
                     summaries: Sequence[str], recent_lines: Sequence[Mapping[str, Any]],
                     notes: Sequence[str] = (), slipped: Mapping[str, int] | None = None) -> list[Message]:
    """`notes`: ghi chú của code cho lần viết lại (vì sao bản trước bị trả lại). `slipped`: như `secret_status`."""
    names = {NARRATOR: "Người kể", **{c.id: c.name for c in plan.cast}}
    status = secret_status(plan, index, slipped)
    due = [sid for sid, s in status.items() if s == "due"]
    later = [sid for sid, s in status.items() if s == "later"]
    title = plan.segments[index - 1].title if index <= len(plan.segments) else ""
    parts: list[str | UserAuthored] = [
        f"Viết đoạn {index}/{targets.segments}: {escape_text(title)}",
        f"Số chữ mục tiêu: khoảng {targets.words_per_segment} chữ.",
        f"Bí mật phải lộ trong đoạn này (id): {', '.join(due) or 'không có'}.",
        f"Bí mật chưa được lộ (id): {', '.join(later) or 'không có'}.",
        "Kế hoạch:", UserAuthored(_plan_block(plan, index, status), "audio_plan"),
        "Hướng đi gốc:", UserAuthored(premise.text, "audio_premise"),
    ]
    if summaries:
        parts += ["Tóm tắt các đoạn trước:", UserAuthored("\n".join(summaries), "audio_story_so_far")]
    if recent_lines:
        parts += ["Các dòng cuối của đoạn trước (viết tiếp liền mạch từ đây):",
                  UserAuthored("\n".join(f"{names.get(str(r['speaker']), r['speaker'])}: {r['text']}"
                                         for r in recent_lines), "audio_recent_lines")]
    if index == targets.segments:
        parts.append("Đây là đoạn cuối: khép truyện theo cái kết của kế hoạch.")
    if notes:
        parts.append("Bản trước bị trả lại vì: " + escape_text("; ".join(notes)) + ". Viết lại cả đoạn cho đúng.")
    return [system_message(SEGMENT_SYSTEM_PROMPT, DATA_NOTICE), user_message(*parts)]


# --- gọi model ------------------------------------------------------------------------------------


async def make_ideas(llm: LLMClient, model: str, tags: str, *, count: int, retries: RetryLimits,
                     schema_retries: int, extra: Mapping[str, Any] | None = None) -> list[Idea]:
    messages = propose_messages(tags, count=count)

    async def call() -> list[Idea]:
        output, _ = await llm.chat_json(model, messages, ProposeOutput, extra=extra)
        problems = idea_problems(output, count=count)
        if problems:
            raise _bad(problems, "ProposeOutput")
        return list(output.ideas)

    return await with_json_retries(call, schema_retries=schema_retries,
                                   transient_retries=retries.llm_transient,
                                   backoff=retries.transient_backoff_seconds)


async def make_plan(llm: LLMClient, model: str, premise: Premise, targets: Targets, *, retries: RetryLimits,
                    schema_retries: int, extra: Mapping[str, Any] | None = None) -> PlanOutput:
    messages = plan_messages(premise, targets)

    async def call() -> PlanOutput:
        output, _ = await llm.chat_json(model, messages, PlanOutput, extra=extra)
        problems = plan_problems(output, segments=targets.segments)
        if problems:
            raise _bad(problems, "PlanOutput")
        return output

    return await with_json_retries(call, schema_retries=schema_retries,
                                   transient_retries=retries.llm_transient,
                                   backoff=retries.transient_backoff_seconds)


@dataclass(frozen=True)
class SegmentResult:
    output: SegmentOutput
    words: int
    length_off: bool
    missed: tuple[str, ...] = ()  # bí mật đến hạn mà đoạn không lộ: nơi gọi dời sang đoạn sau


async def write_segment(
    llm: LLMClient, model: str, plan: PlanOutput, *, premise: Premise, targets: Targets, index: int,
    summaries: Sequence[str], recent_lines: Sequence[Mapping[str, Any]], limits: AudioScriptLimits,
    quality: QualityConfig, retries: RetryLimits, extra: Mapping[str, Any] | None = None,
    slipped: Mapping[str, int] | None = None, extra_notes: Sequence[str] = (),
) -> SegmentResult:
    """Viết lại có ghi chú khi bản trước sai, tối đa `limits.schema_retries` lần. Hết lượt (hay chạm trần giữa
    chừng) mà bản gần nhất chỉ lệch độ dài hay chỉ thiếu bí mật đến hạn thì nhận nó, đánh dấu `length_off`,
    `missed`; lỗi khác thì báo lỗi như mọi lời gọi JSON. `extra_notes`: ghi chú của nơi gọi cho mọi lần viết (ví dụ
    vì sao bản trước bị kiểm duyệt chặn)."""
    tolerance = limits.require("length_tolerance")
    notes: list[str] = list(extra_notes)
    usable: list[SegmentResult] = []

    async def call() -> SegmentResult:
        messages = segment_messages(plan, premise=premise, targets=targets, index=index, summaries=summaries,
                                    recent_lines=recent_lines, notes=notes, slipped=slipped)
        output, _ = await llm.chat_json(model, messages, SegmentOutput, extra=extra)
        check = segment_problems(output, plan=plan, index=index, target_words=targets.words_per_segment,
                                 tolerance=tolerance, quality=quality, slipped=slipped)
        problems = check.hard + missing_text(check.missing) + ([check.length] if check.length else [])
        if problems:
            if not check.hard:
                usable.append(SegmentResult(output, check.words, bool(check.length), tuple(check.missing)))
            notes[:] = [*extra_notes, *problems]
            raise _bad(problems, "SegmentOutput")
        return SegmentResult(output, check.words, False)

    try:
        return await with_json_retries(call, schema_retries=limits.require("schema_retries"),
                                       transient_retries=retries.llm_transient,
                                       backoff=retries.transient_backoff_seconds)
    except WritoryError as e:
        # Hết lượt thử lại thì `with_retries` báo RETRY_LIMIT_REACHED; chạm trần giữa chừng là COST_LIMIT_STORY. Bản
        # gần nhất chỉ lệch độ dài hay chỉ thiếu bí mật đến hạn đã trả tiền và vẫn dùng được.
        if e.code in (ErrorCode.LLM_BAD_RESPONSE, ErrorCode.RETRY_LIMIT_REACHED,
                      ErrorCode.COST_LIMIT_STORY) and usable:
            return usable[-1]
        raise
