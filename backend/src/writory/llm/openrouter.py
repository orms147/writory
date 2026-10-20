"""Client OpenRouter qua httpx.

Theo docs openrouter.ai (tra ngày 19/10/2026; chưa đối chiếu với lời gọi thật):
- POST {base}/chat/completions, kiểu OpenAI.
- `usage` luôn có trong phản hồi, `usage.cost` tính bằng credit; credit lấy USD làm đơn vị
  (D-10 coi 1 credit = 1 USD).
- Stream: SSE, dòng bắt đầu bằng ":" là comment, usage nằm ở chunk cuối trước `data: [DONE]`.
  Lỗi giữa chừng tới dưới dạng chunk có trường `error`, HTTP vẫn 200.
- Lỗi: {"error": {"code", "message", "metadata"}}; có thể tới cả khi HTTP 200.
"""

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import (
    ChatResult,
    LLMClient,
    Message,
    StreamDone,
    StreamEvent,
    TextDelta,
    Usage,
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
    return Usage(
        prompt_tokens=raw.get("prompt_tokens") or 0,
        completion_tokens=raw.get("completion_tokens") or 0,
        cost_usd=float(cost) if isinstance(cost, int | float) else None,
    )


def _bad_response(detail: str) -> WritoryError:
    return WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=detail)


class OpenRouterClient(LLMClient):
    def __init__(
        self,
        api_key: SecretStr,
        *,
        http: httpx.AsyncClient | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        self._url = base_url.rstrip("/") + "/chat/completions"

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
        try:
            resp = await self._http.post(self._url, json=body, headers=self._headers())
        except httpx.HTTPError as e:
            raise WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__) from None
        try:
            data = resp.json()
        except ValueError:
            data = None
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
        )

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        body = self._body(model, messages, stream=True)
        usage: Usage | None = None
        try:
            async with self._http.stream(
                "POST", self._url, json=body, headers=self._headers()
            ) as resp:
                if resp.status_code != 200:
                    raw = await resp.aread()
                    try:
                        data = json.loads(raw)
                    except ValueError:
                        data = None
                    raise _error_from(resp.status_code, data) or _bad_response(
                        f"HTTP {resp.status_code}"
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue  # dòng trống, comment ": OPENROUTER PROCESSING", trường SSE khác
                    payload = line.removeprefix("data:").strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        raise _bad_response("chunk SSE không phải JSON") from None
                    if error := _error_from(200, chunk):
                        raise error
                    if chunk.get("usage"):
                        usage = _usage(chunk["usage"])
                    for choice in chunk.get("choices") or []:
                        content = (choice.get("delta") or {}).get("content")
                        if content:
                            yield TextDelta(content)
        except httpx.HTTPError as e:
            raise WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__) from None
        yield StreamDone(usage or Usage(cost_usd=None))
