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
from writory.safety.wrap import DATA_NOTICE, UserAuthored, system_message, user_message

PROMPT_VERSION = "summary-1"  # đổi chữ prompt thì tăng số
ROLE = "summary"
SUMMARY_CHAPTERS = 2  # design §6.2 bước 1: tóm tắt 1–2 chương gần nhất

SYSTEM_PROMPT = """Bạn tóm tắt MỘT chương của một truyện tương tác tiếng Việt, làm ghi chú cho người viết các chương sau. Chữ của chương nằm trong khối dữ liệu.

Quy tắc:
- Viết tiếng Việt có dấu, gọn, thành một đoạn. Không chêm tiếng Anh, không dùng chữ Hán.
- Chỉ dựa trên chữ của chương. Không suy đoán, không thêm điều chương không nói.
- Gọi nhân vật bằng tên như trong chương. Đây là ghi chú, không phải văn của truyện.
- Nêu theo thứ tự: chuyện chính đã xảy ra; nhân vật chính đã quyết định hay làm gì; điều gì vừa được nói ra hay lộ ra; tình thế cuối chương (ai ở đâu, việc gì còn dang dở).
- Tối đa {max_chars} ký tự.

Trả về JSON đúng schema: `summary` là đoạn tóm tắt."""


class SummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str


def summary_messages(chapter: int, scenes: Sequence[str], *, max_chars: int) -> list[Message]:
    return [
        system_message(SYSTEM_PROMPT.format(max_chars=max_chars), DATA_NOTICE),
        user_message(f"Chương {chapter}, đúng chữ người đọc đã đọc:",
                     UserAuthored("\n\n".join(scenes), "chapter_text"),
                     "Tóm tắt chương này."),
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
) -> str:
    messages = summary_messages(chapter, scenes, max_chars=max_chars)

    async def call() -> str:
        output, _ = await llm.chat_json(model, messages, SummaryOutput, extra=extra)
        text = " ".join(output.summary.split())
        if not text:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="SummaryOutput: tóm tắt rỗng")
        return _fit(text, max_chars)

    return await with_json_retries(call, schema_retries=retries.extract_schema_retry,
                                   transient_retries=retries.llm_transient)
