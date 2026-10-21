"""Model giả cho lời gọi kiểm duyệt (G9, D-57, D-79), dùng chung cho test pipeline và API.

Lời gọi kiểm duyệt (schema `ModerationOutput`, và `ChoicesModerationOutput` của bộ lựa chọn) có
hàng đợi riêng: không lẫn vào kịch bản của các vai khác (thứ tự dàn ý → viết → trích …) và không nằm
trong `calls` của model bọc. Hết hàng đợi thì cho qua (findings rỗng). Test về kiểm duyệt đặt hàng
đợi riêng và đọc `moderation_calls`.

Đầu vào người chơi được kiểm `moderation.input_votes` lần (D-79), mỗi lần lấy một câu trong hàng
đợi; lần nào báo chặn thì dừng. Bộ lựa chọn trả theo từng dòng: câu ghi sẵn dạng `findings` (của
`moderation_reply`) được đặt cho dòng 1, các dòng khác rỗng, để kịch bản cũ giữ nguyên ý. Test về
cấu trúc theo dòng dùng `lines_reply`.

`CaseModerator` cho bộ câu G9: trả đúng `findings` mong đợi của câu có chữ trong khối dữ liệu
(oracle), hoặc một bộ `findings` cố định cho mọi lời gọi.
"""

import html
import json
import re
from collections import deque
from collections.abc import AsyncIterator, Iterable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, Usage
from writory.safety.moderate import LINES_HEADER_RE, ChoicesModerationOutput, ModerationOutput

MODERATION_SCHEMAS = (ModerationOutput, ChoicesModerationOutput)
_BLOCK_RE = re.compile(r'<player_data source="moderated_text">\n(.*?)\n</player_data>', re.DOTALL)
_NUMBER_RE = re.compile(r"^\[\d+\] ")


def moderation_reply(*findings: tuple[str, str], reason: str = "lý do ngắn") -> str:
    """`findings`: (category, intensity), ví dụ ("gore", "extreme")."""
    return json.dumps(
        {"findings": [{"category": c, "intensity": i} for c, i in findings], "reason": reason},
        ensure_ascii=False,
    )


def lines_reply(n: int, flagged: Mapping[int, Iterable[tuple[str, str]]] | None = None, *,
                reason: str = "lý do ngắn") -> str:
    """Câu trả lời theo dòng cho bộ lựa chọn: đúng một mục cho mỗi dòng 1..n."""
    flagged = flagged or {}
    return json.dumps({"lines": [
        {"line": i, "findings": [{"category": c, "intensity": s} for c, s in flagged.get(i, ())]}
        for i in range(1, n + 1)
    ], "reason": reason}, ensure_ascii=False)


ALLOW = moderation_reply()


def line_count(messages: Sequence[Message]) -> int:
    """Số dòng của bộ lựa chọn, đọc từ dòng đầu (chữ của code, ngoài khối dữ liệu)."""
    user = next(m.content for m in messages if m.role == "user")
    found = LINES_HEADER_RE.search(user)
    if found is None:
        raise AssertionError("lời gọi kiểm duyệt bộ lựa chọn thiếu dòng đếm số dòng")
    return int(found.group(1))


def as_lines_reply(item: str, n: int) -> str:
    """Câu dạng `findings` → dạng theo dòng (findings ở dòng 1). Câu khác giữ nguyên."""
    try:
        data = json.loads(item)
    except json.JSONDecodeError:
        return item
    if not isinstance(data, dict) or "findings" not in data:
        return item
    findings = [(f["category"], f["intensity"]) for f in data["findings"]]
    return lines_reply(n, {1: findings}, reason=data.get("reason", "lý do ngắn"))


class ModerationScript:
    """Hàng đợi câu trả lời kiểm duyệt + nhật ký lời gọi. Dùng trong model giả bất kỳ."""

    def __init__(self, replies: Iterable[str | Exception] = (), *,
                 cost_usd: float | None = 0.0) -> None:
        self.replies = deque(replies)
        self.cost_usd = cost_usd
        self.moderation_calls: list[list[Message]] = []
        self.moderation_extras: list[Mapping[str, Any] | None] = []
        self.moderation_schemas: list[type[BaseModel]] = []

    def answer(self, model: str, messages: list[Message], extra,
               schema: type[BaseModel] = ModerationOutput) -> ChatResult:
        self.moderation_calls.append(list(messages))
        self.moderation_extras.append(extra)
        self.moderation_schemas.append(schema)
        item = self.replies.popleft() if self.replies else ALLOW
        if isinstance(item, Exception):
            raise item
        if schema is ChoicesModerationOutput:
            item = as_lines_reply(item, line_count(messages))
        return ChatResult(text=item, usage=Usage(cost_usd=self.cost_usd), model=model,
                          finish_reason="stop")


class ModeratedLLM(LLMClient):
    """Bọc một model giả: lời gọi kiểm duyệt do `ModerationScript` trả lời, mọi lời gọi khác chuyển
    nguyên cho model bọc. Thuộc tính khác (calls, schemas, …) đọc thẳng từ model bọc."""

    def __init__(self, inner: LLMClient, replies: Iterable[str | Exception] = (), *,
                 cost_usd: float | None = 0.0) -> None:
        self.inner = inner
        self.script = ModerationScript(replies, cost_usd=cost_usd)

    @property
    def moderation_calls(self) -> list[list[Message]]:
        return self.script.moderation_calls

    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        if response_schema in MODERATION_SCHEMAS:
            return self.script.answer(model, messages, extra, response_schema)
        return await self.inner.chat(model, messages, response_schema=response_schema, extra=extra)

    def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        return self.inner.stream(model, messages)


def _key(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.split("\n") if line.strip())


class CaseModerator(LLMClient):
    """Model giả cho bộ câu G9, chỉ đọc messages. `cases`: trả `findings` mong đợi của câu có chữ
    trong khối dữ liệu (oracle; bộ lựa chọn: đặt ở dòng 1). `constant`: mọi lời gọi trả cùng
    `findings`. Đếm lời gọi trong `calls`, schema trong `schemas`."""

    def __init__(self, cases: Iterable[dict] = (), *,
                 constant: Sequence[tuple[str, str]] | None = None,
                 cost_usd: float | None = 0.0) -> None:
        self.findings: dict[tuple[str, ...], list[tuple[str, str]]] = {}
        for case in cases:
            found = [(f["category"], f["intensity"]) for f in case["expected"]["findings"]]
            key = _key(case["text"])
            if self.findings.setdefault(key, found) != found:
                raise ValueError(f"hai câu cùng chữ mà khác findings: {case['id']}")
        self.constant = list(constant) if constant is not None else None
        self.cost_usd = cost_usd
        self.calls: list[list[Message]] = []
        self.schemas: list[type[BaseModel] | None] = []

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        self.calls.append(list(messages))
        self.schemas.append(response_schema)
        user = next(m.content for m in messages if m.role == "user")
        block = html.unescape(_BLOCK_RE.search(user).group(1))
        if response_schema is ChoicesModerationOutput:
            block = "\n".join(_NUMBER_RE.sub("", line) for line in block.split("\n"))
        found = self.constant if self.constant is not None else self.findings[_key(block)]
        if response_schema is ChoicesModerationOutput:
            text = lines_reply(line_count(messages), {1: found})
        else:
            text = moderation_reply(*found)
        return ChatResult(text=text, usage=Usage(cost_usd=self.cost_usd), model=model,
                          finish_reason="stop")

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError("kiểm duyệt không dùng stream")
        yield  # pragma: no cover
