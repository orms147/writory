"""Client OpenRouter qua httpx.

Theo docs openrouter.ai (tra ngày 19/10/2026; chưa đối chiếu với lời gọi thật):
- POST {base}/chat/completions, kiểu OpenAI.
- `usage` luôn có trong phản hồi, `usage.cost` tính bằng credit; credit lấy USD làm đơn vị
  (D-10 coi 1 credit = 1 USD).
- Stream: SSE, dòng bắt đầu bằng ":" là comment, usage nằm ở chunk cuối trước `data: [DONE]`.
  Lỗi giữa chừng tới dưới dạng chunk có trường `error`, HTTP vẫn 200.
- Lỗi: {"error": {"code", "message", "metadata"}}; có thể tới cả khi HTTP 200.

Token cache (tra ngày 22/10/2026, D-96): `usage.prompt_tokens_details.cached_tokens` là "số token
đọc từ cache" (use-cases/usage-accounting, features/prompt-caching); `cache_write_tokens` chỉ có ở
model có cache tường minh. Phản hồi không có trường này thì `cached_tokens` là None, không phải 0.

Id generation và tra chi phí theo id (tra ngày 21/10/2026, D-64; chưa đối chiếu với lời gọi thật):
- Header `X-Generation-Id` có ở mọi endpoint (api-reference/streaming); `id` của thân phản hồi là
  id generation (use-cases/usage-accounting). Status và header được gửi ngay khi nhà cung cấp nhận
  yêu cầu, kể cả lời gọi không stream (api-reference/errors). Vì vậy `chat` đọc header trước rồi
  mới đọc thân: lời gọi bị huỷ hay đứt khi đang chờ thân vẫn biết id (`CallTrace`).
- GET {base}/generation?id=<id> (api-reference/get-a-generation): `data.total_cost` (USD),
  `data.tokens_prompt`, `data.tokens_completion`; 404 khi không có. Docs không nói generation có
  sau bao lâu, nên 404 được coi là "chưa có, tra lại sau".
- Lời gọi không stream bị huỷ vẫn bị tính tiền đủ; stream bị huỷ chỉ dừng tính tiền với nhà cung
  cấp hỗ trợ (api-reference/streaming).
"""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from writory.config import AppConfig, LimitNotSetError
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import (
    ChatResult,
    GenerationCost,
    LLMClient,
    Message,
    StreamDone,
    StreamEvent,
    TextDelta,
    Usage,
    current_trace,
    valid_generation_id,
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
APP_TITLE = "WriTory"  # header phải là ASCII
_ERROR_MESSAGE_MAX_CHARS = 300

_STATUS_TO_CODE = {
    400: ErrorCode.LLM_REQUEST_INVALID,
    401: ErrorCode.LLM_AUTH_FAILED,
    402: ErrorCode.LLM_INSUFFICIENT_CREDITS,
    403: ErrorCode.LLM_CONTENT_BLOCKED,
    408: ErrorCode.LLM_UNAVAILABLE,
    # 409 không có trong trang lỗi của OpenRouter (tra 22/10/2026). Thấy một lần, thân rỗng, sau
    # 0,08 giây, khi lời gọi giống hệt lời gọi trước đó vừa thành công (D-94): xử như lỗi tạm.
    409: ErrorCode.LLM_UNAVAILABLE,
    429: ErrorCode.LLM_RATE_LIMITED,
}


def _code_for_status(status: int) -> ErrorCode:
    if status in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[status]
    if status >= 500:
        return ErrorCode.LLM_UNAVAILABLE
    return ErrorCode.LLM_REQUEST_INVALID


def _error_from(status: int, data: Any) -> WritoryError | None:
    """Lỗi từ HTTP status hoặc trường `error` trong thân phản hồi; None nếu không lỗi."""
    err = data.get("error") if isinstance(data, dict) else None
    if err is None and status < 400:
        return None
    err = err if isinstance(err, dict) else {}
    body_code = err.get("code", status)
    message = str(err.get("message", ""))[:_ERROR_MESSAGE_MAX_CHARS]
    if isinstance(body_code, int):
        mapped = _code_for_status(body_code)
    else:  # lỗi giữa stream mang mã chuỗi, ví dụ "server_error"
        mapped = _code_for_status(status if status >= 400 else 500)
    return WritoryError(mapped, detail=f"HTTP {status}, error.code={body_code}: {message}")


def _usage(raw: Any) -> Usage:
    raw = raw if isinstance(raw, dict) else {}
    cost = raw.get("cost")
    details = raw.get("prompt_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    return Usage(
        prompt_tokens=raw.get("prompt_tokens") or 0,
        completion_tokens=raw.get("completion_tokens") or 0,
        cost_usd=float(cost) if isinstance(cost, int | float) else None,
        # Chỉ nhận số nguyên không âm; bool là int trong Python nên loại ra.
        cached_tokens=(cached if isinstance(cached, int) and not isinstance(cached, bool)
                       and cached >= 0 else None),
    )


def _bad_response(detail: str) -> WritoryError:
    return WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=detail)


# Lỗi httpx xảy ra trước khi yêu cầu rời máy: chắc chắn chưa tới nhà cung cấp, không tốn tiền.
_NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout,
             httpx.UnsupportedProtocol)


def _note_sent(sent: bool) -> None:
    if (trace := current_trace()) is not None:
        trace.sent = sent


def _note_generation_id(value: object) -> str | None:
    """Báo id generation (nếu đúng dạng) cho nơi ghi chi phí; giữ id đầu tiên."""
    gen_id = valid_generation_id(value)
    trace = current_trace()
    if gen_id is not None and trace is not None and trace.generation_id is None:
        trace.generation_id = gen_id
    return gen_id


def call_deadline(config: AppConfig) -> int:
    """Hạn tổng một lời gọi, giây (`limits.llm_call.deadline_seconds`, D-113). Chưa đặt (null) là lỗi,
    không phải vô hạn: nơi dựng client gọi hàm này rồi truyền vào `deadline_s`."""
    try:
        return config.limits.llm_call.require("deadline_seconds")
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None


class _Deadline:
    """Hạn tổng của MỘT lời gọi, tính từ lúc tạo (D-113). `httpx.Timeout` chỉ là hạn từng lần đọc/ghi:
    máy chủ nhỏ giọt byte (hay giữ kết nối bằng dòng chú thích) thì nó không bao giờ hết. Dùng
    `asyncio.timeout_at` thật, nên test nhảy đồng hồ của vòng lặp thay vì chờ.

    `step()` bọc từng lần chờ riêng (với stream, mỗi lần đọc một dòng): hết hạn thì huỷ đúng lần chờ
    đó, không bao giờ huỷ mã của người dùng stream giữa hai lần `yield`."""

    def __init__(self, seconds: float | None) -> None:
        self.seconds = seconds
        self._end = asyncio.get_running_loop().time() + seconds if seconds is not None else None

    @asynccontextmanager
    async def step(self) -> AsyncIterator[None]:
        scope = asyncio.timeout_at(self._end) if self._end is not None else asyncio.timeout(None)
        try:
            async with scope:
                yield
        except TimeoutError:
            # `TimeoutError` cũng là lớp con của OSError (lỗi socket): chỉ hạn của chính ta mới là
            # LLM_TIMEOUT, còn lại để lớp mạng xử như cũ.
            if not scope.expired():
                raise
            raise WritoryError(ErrorCode.LLM_TIMEOUT,
                               detail=f"quá hạn tổng {self.seconds:g} giây") from None


# Lỗi mạng: httpx bọc phần lớn, nhưng `ssl.SSLError` và lỗi socket (OSError) từ tầng anyio đi qua
# không bọc; để lọt thì thành INTERNAL_ERROR, không thử lại (D-97, hồi quy long-tu-tien-1).
_NETWORK_ERRORS = (httpx.HTTPError, OSError)


def _unavailable(e: httpx.HTTPError | OSError) -> WritoryError:
    if isinstance(e, _NOT_SENT):
        _note_sent(False)
    return WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__)


class OpenRouterClient(LLMClient):
    def __init__(
        self,
        api_key: SecretStr,
        *,
        http: httpx.AsyncClient | None = None,
        base_url: str = DEFAULT_BASE_URL,
        deadline_s: float | None = None,
    ) -> None:
        """`deadline_s`: hạn tổng mỗi lời gọi (`call_deadline(config)`, D-113); None = không hạn tổng,
        chỉ hạn từng lần đọc/ghi của httpx (các bộ đo cũ chưa nối)."""
        self._key = api_key
        self._deadline_s = deadline_s
        self._http = http or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        base = base_url.rstrip("/")
        self._url = base + "/chat/completions"
        self._generation_url = base + "/generation"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._key.get_secret_value()}",
            "X-Title": APP_TITLE,
        }

    @staticmethod
    def _body(
        model: str,
        messages: list[Message],
        *,
        stream: bool,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
        }
        if response_schema is not None:
            # Chưa kiểm: model/nhà cung cấp nào nhận `strict` với schema pydantic sinh ra.
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": response_schema.model_json_schema(),
                },
            }
        if response_schema is not None:
            # D-100: một model có nhiều nhà cung cấp, có nơi không hỗ trợ structured_outputs; đòi
            # nhà cung cấp nhận đủ tham số của yêu cầu. Người gọi đặt `provider` riêng thì theo họ.
            body["provider"] = {"require_parameters": True}
        if extra:
            clash = sorted(set(extra) & {"model", "messages", "stream", "response_format"})
            if clash:
                raise ValueError(f"extra không được ghi đè trường lõi: {', '.join(clash)}")
            body.update(extra)
        return body

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        body = self._body(
            model, messages, stream=False, response_schema=response_schema, extra=extra
        )
        _note_sent(True)
        deadline = _Deadline(self._deadline_s)
        try:
            # Header trước thân: id generation có ngay khi nhà cung cấp nhận yêu cầu (D-64).
            async with deadline.step(), self._http.stream(
                "POST", self._url, json=body, headers=self._headers()
            ) as resp:
                header_id = _note_generation_id(resp.headers.get("x-generation-id"))
                raw = await resp.aread()
        except _NETWORK_ERRORS as e:
            raise _unavailable(e) from None
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        body_id = _note_generation_id(data.get("id")) if isinstance(data, dict) else None
        if error := _error_from(resp.status_code, data):
            raise error
        if data is None:
            raise _bad_response(f"HTTP {resp.status_code}: thân phản hồi không phải JSON")
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise _bad_response("thiếu choices[0].message.content") from None
        if not isinstance(text, str):
            raise _bad_response("choices[0].message.content không phải chuỗi")
        served = data.get("model")
        finish = choice.get("finish_reason") if isinstance(choice, dict) else None
        return ChatResult(
            text=text,
            usage=_usage(data.get("usage")),
            model=served if isinstance(served, str) else None,
            finish_reason=finish if isinstance(finish, str) else None,
            generation_id=header_id or body_id,
        )

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        body = self._body(model, messages, stream=True)
        usage: Usage | None = None
        gen_id: str | None = None
        _note_sent(True)
        deadline = _Deadline(self._deadline_s)
        try:
            async with AsyncExitStack() as stack:
                async with deadline.step():
                    resp = await stack.enter_async_context(self._http.stream(
                        "POST", self._url, json=body, headers=self._headers()))
                gen_id = _note_generation_id(resp.headers.get("x-generation-id"))
                if resp.status_code != 200:
                    async with deadline.step():
                        raw = await resp.aread()
                    try:
                        data = json.loads(raw)
                    except ValueError:
                        data = None
                    raise _error_from(resp.status_code, data) or _bad_response(
                        f"HTTP {resp.status_code}"
                    )
                lines = resp.aiter_lines()
                while True:
                    async with deadline.step():
                        line = await anext(lines, None)  # None: hết thân phản hồi
                    if line is None:
                        break
                    if not line.startswith("data:"):
                        continue  # dòng trống, comment ": OPENROUTER PROCESSING", trường SSE khác
                    payload = line.removeprefix("data:").strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        raise _bad_response("chunk SSE không phải JSON") from None
                    if gen_id is None and isinstance(chunk, dict):
                        gen_id = _note_generation_id(chunk.get("id"))
                    if error := _error_from(200, chunk):
                        raise error
                    if chunk.get("usage"):
                        usage = _usage(chunk["usage"])
                    for choice in chunk.get("choices") or []:
                        content = (choice.get("delta") or {}).get("content")
                        if content:
                            yield TextDelta(content)
        except _NETWORK_ERRORS as e:
            raise _unavailable(e) from None
        yield StreamDone(usage or Usage(cost_usd=None), generation_id=gen_id)

    async def generation_cost(self, generation_id: str) -> GenerationCost | None:
        """Chi phí thật của một generation (GET /generation, D-64). None: chưa có hoặc không có
        (404). Lỗi khác ra mã như lời gọi chat; không lỗi nào mang key (G7)."""
        if valid_generation_id(generation_id) is None:
            raise ValueError("id generation sai dạng")
        deadline = _Deadline(self._deadline_s)
        try:
            async with deadline.step():
                resp = await self._http.get(self._generation_url, params={"id": generation_id},
                                            headers=self._headers())
        except _NETWORK_ERRORS as e:
            raise WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__) from None
        if resp.status_code == 404:
            return None
        try:
            data = resp.json()
        except ValueError:
            data = None
        if error := _error_from(resp.status_code, data):
            raise error
        info = data.get("data") if isinstance(data, dict) else None
        cost = info.get("total_cost") if isinstance(info, dict) else None
        if isinstance(cost, bool) or not isinstance(cost, int | float) or cost < 0:
            raise _bad_response("generation: thiếu data.total_cost hợp lệ")
        prompt, completion = info.get("tokens_prompt"), info.get("tokens_completion")
        return GenerationCost(
            cost_usd=float(cost),
            prompt_tokens=prompt if isinstance(prompt, int) and prompt >= 0 else 0,
            completion_tokens=completion if isinstance(completion, int) and completion >= 0
            else 0,
        )
