"""Client Meta Model API cho BỘ ĐO (D-140): `MetaClient` theo giao diện của `llm/openrouter.py`.

Chỉ bộ đo dùng nó: sản phẩm cho người chơi chạy bằng key OpenRouter của họ (D-2) và từ chối id model
`meta/...` (`config.product_model_problems`). Id model trong config có tiền tố `meta/`; tiền tố bị bỏ khi gửi.

Theo tài liệu Meta Model API (dev.meta.ai/docs/features/chat-completion, tra 30/10/2026) và MetaProvider của bài F
(D-108); chưa đối chiếu với lời gọi thật của lớp này:
- POST {base}/chat/completions, kiểu OpenAI, bearer. Key chỉ nằm trong header.
- `reasoning_effort`: minimal, low, medium, high, xhigh (docs còn ghi `max` ở bản đo bài F); `none` bị từ chối
  (HTTP 400) nên mức `none` của config thành `minimal`.
- Trần output là `max_tokens` (docs: `max_completion_tokens` là tên mới, `max_tokens` là bí danh còn nhận; bài F đã
  chạy thật với `max_tokens`).
- `usage` chỉ có token (`prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`), không có chi
  phí: chi phí = token x giá trong config (`models.prices`, USD / 1 triệu token; token suy luận đã nằm trong
  `completion_tokens`, tính giá token ra).
- Lỗi: HTTP status + khung lỗi kiểu OpenAI; 504 `gateway_timeout` khi lời gọi không stream chạy quá lâu.
- Stream có (SSE, `stream: true`) nhưng docs không nói chunk có `usage` hay không, mà thiếu token thì không tính
  được chi phí: `stream` gọi MỘT lần không stream rồi trả một `TextDelta` và `StreamDone`.
"""

import copy
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from writory.config import META_MODEL_PREFIX, ModelPrice, is_meta_model
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
from writory.llm.openrouter import _NETWORK_ERRORS, _Deadline, _note_sent, _unavailable

META_BASE_URL = "https://api.meta.ai/v1"
_ERROR_MESSAGE_MAX_CHARS = 400
# `extra` đi thẳng vào thân yêu cầu; `reasoning` đổi thành `reasoning_effort`, `provider` (của OpenRouter) bỏ.
_PASS_THROUGH = frozenset({"max_tokens", "temperature", "top_p"})
_DROPPED = frozenset({"provider"})
_CORE = frozenset({"model", "messages", "stream", "response_format"})
# Từ khoá kiểm giá trị mà chế độ strict của nhiều nhà cung cấp từ chối; pydantic kiểm lại câu trả lời nên bỏ.
_UNSUPPORTED_KEYWORDS = frozenset({
    "default", "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minItems", "maxItems", "pattern", "format", "examples", "multipleOf",
})


def strict_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Schema JSON của pydantic ở dạng `strict`: mọi object đóng (`additionalProperties: false`), mọi thuộc tính
    bắt buộc, bỏ từ khoá kiểm giá trị. Câu trả lời vẫn được pydantic kiểm đầy đủ sau đó (G11)."""
    tree = copy.deepcopy(schema.model_json_schema())

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in _UNSUPPORTED_KEYWORDS & node.keys():
                del node[key]
            props = node.get("properties")
            if isinstance(props, dict):
                node["additionalProperties"] = False
                node["required"] = list(props)
            for key, value in node.items():
                if key in ("properties", "$defs", "definitions") and isinstance(value, dict):
                    for sub in value.values():  # tên thuộc tính không phải từ khoá schema
                        walk(sub)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(tree)
    return tree


def reasoning_effort(extra: Mapping[str, Any]) -> str | None:
    """Mức suy luận của config (`extra["reasoning"]["effort"]`, như OpenRouter) thành `reasoning_effort` của Meta."""
    reasoning = extra.get("reasoning")
    effort = reasoning.get("effort") if isinstance(reasoning, Mapping) else None
    if effort is None:
        return None
    return "minimal" if effort == "none" else str(effort)


def meta_error(status: int, body: Any, text: str, secret: str) -> WritoryError:
    """Lỗi HTTP của Meta thành mã của dự án; chữ lỗi không bao giờ mang key (G7). Dùng chung với giám khảo bài F."""
    err = body.get("error") if isinstance(body, dict) else None
    message = str(err.get("message", "")) if isinstance(err, dict) else text
    code = {400: ErrorCode.LLM_REQUEST_INVALID, 401: ErrorCode.LLM_AUTH_FAILED,
            402: ErrorCode.LLM_INSUFFICIENT_CREDITS, 403: ErrorCode.LLM_AUTH_FAILED,
            408: ErrorCode.LLM_UNAVAILABLE, 429: ErrorCode.LLM_RATE_LIMITED}.get(status)
    code = code or (ErrorCode.LLM_UNAVAILABLE if status >= 500 else ErrorCode.LLM_REQUEST_INVALID)
    scrubbed = message.replace(secret, "[key]") if secret else message
    return WritoryError(code, detail=f"HTTP {status}: {scrubbed}"[:_ERROR_MESSAGE_MAX_CHARS])


class MetaClient(LLMClient):
    def __init__(self, api_key: SecretStr, prices: Mapping[str, ModelPrice], *,
                 http: httpx.AsyncClient | None = None, base_url: str = META_BASE_URL,
                 deadline_s: float | None = None) -> None:
        """`prices`: giá theo id model có tiền tố `meta/` (`config.models.prices`). `deadline_s`: hạn tổng mỗi lời
        gọi (D-113), như `OpenRouterClient`."""
        self._key = api_key
        self._prices = prices
        self._deadline_s = deadline_s
        self._http = http or httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        self._url = base_url.rstrip("/") + "/chat/completions"

    def _price(self, model: str) -> ModelPrice:
        if not is_meta_model(model):
            raise WritoryError(ErrorCode.CONFIG_MODEL_NOT_SET,
                               detail=f"MetaClient chỉ nhận model có tiền tố {META_MODEL_PREFIX!r}, nhận {model!r}")
        price = self._prices.get(model)
        if price is None:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET,
                               detail=f"config/models.yaml không có giá (prices) cho model {model}: "
                                      "chi phí của Meta chỉ tính được từ token x giá")
        return price

    @staticmethod
    def _body(model: str, messages: list[Message], response_schema: type[BaseModel] | None,
              extra: Mapping[str, Any] | None) -> dict[str, Any]:
        body: dict[str, Any] = {"model": model.removeprefix(META_MODEL_PREFIX),
                                "messages": [m.model_dump() for m in messages]}
        if response_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": response_schema.__name__, "strict": True, "schema": strict_schema(response_schema)}}
        extra = dict(extra or {})
        clash = sorted(set(extra) & _CORE)
        if clash:
            raise ValueError(f"extra không được ghi đè trường lõi: {', '.join(clash)}")
        unknown = sorted(set(extra) - _PASS_THROUGH - _DROPPED - {"reasoning"})
        if unknown:
            raise ValueError(f"MetaClient không biết tham số extra {', '.join(unknown)}")
        body.update({k: v for k, v in extra.items() if k in _PASS_THROUGH})
        if (effort := reasoning_effort(extra)) is not None:
            body["reasoning_effort"] = effort
        return body

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        price = self._price(model)
        body = self._body(model, messages, response_schema, extra)
        secret = self._key.get_secret_value()
        _note_sent(True)
        deadline = _Deadline(self._deadline_s)
        try:
            async with deadline.step():
                resp = await self._http.post(self._url, json=body,
                                             headers={"Authorization": f"Bearer {secret}"})
        except _NETWORK_ERRORS as e:
            raise _unavailable(e) from None
        try:
            data = resp.json()
        except ValueError:
            data = None
        if resp.status_code != 200:
            raise meta_error(resp.status_code, data, resp.text, secret)
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail="phản hồi Meta không đúng dạng chat completion") from None
        if not isinstance(text, str) or not text:
            if message.get("refusal"):
                raise WritoryError(ErrorCode.LLM_CONTENT_BLOCKED, detail="Meta từ chối trả lời")
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="thiếu choices[0].message.content")
        served, finish = data.get("model"), choice.get("finish_reason")
        return ChatResult(text=text, usage=self._usage(data.get("usage"), price),
                          model=served if isinstance(served, str) else None,
                          finish_reason=finish if isinstance(finish, str) else None)

    @staticmethod
    def _usage(raw: Any, price: ModelPrice) -> Usage:
        if not isinstance(raw, dict) or not isinstance(raw.get("prompt_tokens"), int) \
                or not isinstance(raw.get("completion_tokens"), int):
            return Usage(cost_usd=None)
        prompt, completion = raw["prompt_tokens"], raw["completion_tokens"]
        details = raw.get("prompt_tokens_details")
        cached = details.get("cached_tokens") if isinstance(details, dict) else None
        cached = cached if isinstance(cached, int) and not isinstance(cached, bool) and 0 <= cached <= prompt else None
        fresh = prompt - (cached or 0)
        cost = (fresh * price.input + (cached or 0) * (price.input if price.cached_in is None else price.cached_in)
                + completion * price.output) / 1e6
        out = raw.get("completion_tokens_details")
        reasoning = out.get("reasoning_tokens") if isinstance(out, dict) else None
        if not (isinstance(reasoning, int) and not isinstance(reasoning, bool) and reasoning >= 0):
            reasoning = None
        return Usage(prompt_tokens=prompt, completion_tokens=completion, cost_usd=cost, cached_tokens=cached,
                     reasoning_tokens=reasoning)

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        result = await self.chat(model, messages)
        yield TextDelta(result.text)
        yield StreamDone(result.usage)

