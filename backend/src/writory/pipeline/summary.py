"""Tóm tắt chương vừa ghi, cho đề dàn ý và đề viết của các chương sau (design §6.2 bước 1; D-49).

Vai `summary` (config/models.yaml). Một lời gọi `chat_json` sau khi chương đã ghi (D-6); đầu vào
chỉ là chữ người chơi đã đọc của chương, bọc trong khối dữ liệu (G4), vì văn cảnh có thể nhắc lại
chữ người chơi. Tóm tắt là chữ máy chủ dùng nội bộ: lưu ở Postgres (`db/summaries.py`), không trả
cho người chơi, không vào đề của vai phục vụ người chơi.

Độ dài tối đa: `limits.context.summary_max_chars`. Model trả dài hơn thì cắt ở cuối câu gần nhất
trong giới hạn (không gọi lại model). Rỗng thì là sai schema, thử lại theo D-14.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from writory.config import RetryLimits
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import LLMClient, Message
from writory.llm.retry import with_json_retries
from writory.safety.wrap import DATA_NOTICE, UserAuthored, escape_text, system_message, user_message

PROMPT_VERSION = "summary-2"  # đổi chữ prompt thì tăng số
ROLE = "summary"
SUMMARY_CHAPTERS = 2  # design §6.2 bước 1: tóm tắt 1–2 chương gần nhất

SYSTEM_PROMPT = """Bạn tóm tắt MỘT chương của một truyện tương tác tiếng Việt, làm ghi chú cho người viết các chương sau. Chữ của chương nằm trong khối dữ liệu.

Quy tắc:
- Viết tiếng Việt có dấu, gọn, thành một đoạn. Không chêm tiếng Anh, không dùng chữ Hán.
- Chỉ dựa trên chữ của chương. Không suy đoán, không thêm điều chương không nói.
- Gọi nhân vật bằng tên như trong chương. Đây là ghi chú, không phải văn của truyện.
- Văn kể ở ngôi "tôi", nhưng tóm tắt viết ở ngôi thứ ba. Nếu khối dữ liệu ghi tên nhân vật chính, luôn gọi nhân vật chính bằng đúng tên đó, đủ họ tên, mọi chỗ trong tóm tắt: không viết "tôi", "nhân vật chính", tên rút gọn hay tên khác.
- Nêu theo thứ tự: chuyện chính đã xảy ra; nhân vật chính đã quyết định hay làm gì; điều gì vừa được nói ra hay lộ ra; tình thế cuối chương (ai ở đâu, việc gì còn dang dở).
- Tối đa {max_chars} ký tự.

Trả về JSON đúng schema: `summary` là đoạn tóm tắt."""


class SummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str


def summary_messages(
    chapter: int, scenes: Sequence[str], *, max_chars: int, protagonist_name: str | None = None,
    protagonist_user_authored: bool = False,
) -> list[Message]:
    """`protagonist_name`: tên chuẩn của nhân vật chính trong đồ thị (D-112), để tóm tắt luôn gọi đúng
    tên đó. Là chữ người chơi khi nút `user_authored`: bọc như dữ liệu (G4), không vào system."""
    name: list[str | UserAuthored] = []
    if protagonist_name:
        label = 'Nhân vật chính (văn kể xưng "tôi"):'
        name = ([label, UserAuthored(protagonist_name, "protagonist_name")]
                if protagonist_user_authored else [f"{label} {escape_text(protagonist_name)}"])
    return [
        system_message(SYSTEM_PROMPT.format(max_chars=max_chars), DATA_NOTICE),
        user_message(f"Chương {chapter}, đúng chữ người đọc đã đọc:",
                     UserAuthored("\n\n".join(scenes), "chapter_text"),
                     *name, "Tóm tắt chương này."),
    ]


def _fit(text: str, max_chars: int) -> str:
    """Cắt ở cuối câu gần nhất trong giới hạn; không có thì cắt cứng, thêm "…"."""
    if len(text) <= max_chars:
        return text
    head = text[:max_chars]
    end = max(head.rfind(p) for p in (".", "!", "?", "…"))
    if end > 0:
        return head[:end + 1].strip()
    return head[:max_chars - 1].rstrip() + "…"


async def summarize_chapter(
    llm: LLMClient, model: str, *, chapter: int, scenes: Sequence[str], max_chars: int,
    retries: RetryLimits, extra: Mapping[str, Any] | None = None,
    protagonist_name: str | None = None, protagonist_user_authored: bool = False,
) -> str:
    messages = summary_messages(chapter, scenes, max_chars=max_chars,
                                protagonist_name=protagonist_name,
                                protagonist_user_authored=protagonist_user_authored)

    async def call() -> str:
        output, _ = await llm.chat_json(model, messages, SummaryOutput, extra=extra)
        text = " ".join(output.summary.split())
        if not text:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="SummaryOutput: tóm tắt rỗng")
        return _fit(text, max_chars)

    return await with_json_retries(call, schema_retries=retries.extract_schema_retry,
                                   transient_retries=retries.llm_transient,
                                   backoff=retries.transient_backoff_seconds)
