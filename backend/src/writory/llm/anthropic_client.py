"""Client Claude (Anthropic API) cho BỘ ĐO (D-145): `AnthropicClient` theo giao diện của `llm/openrouter.py`.

Chỉ bộ đo dùng nó: sản phẩm chạy bằng key OpenRouter của người chơi (D-2) và từ chối id model `anthropic-api/...`
(`config.product_model_problems`). Id trong config có tiền tố `anthropic-api/` (khác `anthropic/` của OpenRouter,
để sản phẩm vẫn dùng được các model Claude qua OpenRouter); tiền tố bị bỏ khi gửi.

Theo skill claude-api (tra 30/10/2026), dùng SDK `anthropic` (nhóm `eval`, nạp lúc cần); chưa đối chiếu với lời gọi
thật của lớp này:
- Messages API: `system` ở đầu yêu cầu (không phải một message), `max_tokens` bắt buộc, không prefill. Key chỉ ở header
  do SDK gắn; chữ lỗi qua `anthropic_error` đã bỏ key.
- Claude Haiku 5.5: thinking là adaptive, bật sẵn; độ sâu qua `output_config.effort` (low đến max, mặc định medium);
  `temperature`, `top_p`, `top_k` bị từ chối nên không gửi. Mức `none` của config thành `thinking: disabled`; `minimal`
  thành `low` (Anthropic không có mức này).
- JSON theo schema: `output_config.format = {type: json_schema, schema}` (cùng `strict_schema` với Meta).
- `usage` có `input_tokens` (chưa cache), `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens` (gồm
  token suy luận, không tách riêng). Chi phí = token x giá trong config; bảng giá dài áp cho CẢ lời gọi khi prompt vượt
  ngưỡng (`ModelPrice.long_prompt`).
- Schema quá lớn cho structured output (lượt thử thật: `BuildOutput` bị 400 "compiled grammar is too large"): client
  lùi về schema trong `system`, không dùng `output_config.format`, và nhớ tên schema đó để lần sau đi thẳng; pydantic
  vẫn kiểm câu trả lời (G11). Lời gọi 400 chưa tạo ra gì nên không bị tính tiền.
- Thử lại do dự án làm (`llm/retry.py`): SDK dựng với `max_retries=0`.
"""

import json
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx2
from pydantic import BaseModel, SecretStr

from writory.config import (
    ANTHROPIC_MODEL_PREFIX,
    ConfigError,
    ModelPrice,
    is_anthropic_model,
)
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
from writory.llm.meta import strict_schema
from writory.llm.openrouter import _Deadline, _note_sent

_ERROR_MESSAGE_MAX_CHARS = 400
_PASS_THROUGH = frozenset({"max_tokens"})
_DROPPED = frozenset({"provider"})  # của OpenRouter
_CORE = frozenset({"model", "messages", "system", "stream", "output_config", "thinking"})
_SAMPLING = frozenset({"temperature", "top_p", "top_k"})  # Claude Haiku 5.5 từ chối giá trị khác mặc định
_EFFORT = {"minimal": "low", "low": "low", "medium": "medium", "high": "high"}
_STOP = {"end_turn": "stop", "stop_sequence": "stop", "pause_turn": "stop", "max_tokens": "length"}
# Lỗi xảy ra trước khi yêu cầu rời máy (httpx2 là thư viện HTTP của SDK): chắc chắn chưa tới nhà cung cấp.
_NOT_SENT = (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.PoolTimeout, httpx2.UnsupportedProtocol)


def anthropic_error(e: Any, secret: str = "") -> WritoryError:
    """Lỗi của SDK `anthropic` thành mã của dự án; chữ lỗi không bao giờ mang key (G7). Dùng chung với giám khảo
    bài F/D (`bench_d._anthropic_create`). Lỗi kết nối: `trace.sent` báo yêu cầu đã rời máy chưa."""
    import anthropic

    if isinstance(e, anthropic.APIStatusError):
        status = e.status_code
        code = {400: ErrorCode.LLM_REQUEST_INVALID, 401: ErrorCode.LLM_AUTH_FAILED,
                402: ErrorCode.LLM_INSUFFICIENT_CREDITS, 403: ErrorCode.LLM_AUTH_FAILED,
                408: ErrorCode.LLM_UNAVAILABLE, 429: ErrorCode.LLM_RATE_LIMITED}.get(status)
        code = code or (ErrorCode.LLM_UNAVAILABLE if status >= 500 else ErrorCode.LLM_REQUEST_INVALID)
        message = e.message.replace(secret, "[key]") if secret else e.message
        return WritoryError(code, detail=f"HTTP {status}: {message}"[:_ERROR_MESSAGE_MAX_CHARS])
    if isinstance(e, anthropic.APIConnectionError):
        if isinstance(e.__cause__, _NOT_SENT):
            _note_sent(False)
        return WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__)
    raise e


def _long_tier(price: ModelPrice, prompt_tokens: int) -> bool:
    return price.long_prompt is not None and prompt_tokens > price.long_prompt.over_tokens


def cost_of(price: ModelPrice, *, fresh: int, cache_read: int, cache_write: int, output: int) -> float:
    """USD của một lời gọi: bảng giá dài áp cho cả lời gọi khi tổng token vào vượt ngưỡng của nó."""
    tier = price.long_prompt if _long_tier(price, fresh + cache_read + cache_write) else None
    rate_in = tier.input if tier else price.input
    rate_out = tier.output if tier else price.output
    rate_read = (tier.cached_in if tier else price.cached_in)
    rate_write = (tier.cache_write_in if tier else price.cache_write_in)
    rate_read = rate_in if rate_read is None else rate_read
    rate_write = rate_in if rate_write is None else rate_write
    return (fresh * rate_in + cache_read * rate_read + cache_write * rate_write + output * rate_out) / 1e6


class AnthropicClient(LLMClient):
    def __init__(self, api_key: SecretStr, prices: Mapping[str, ModelPrice], *, sdk: Any = None,
                 workspace_id: SecretStr | None = None, deadline_s: float | None = None,
                 default_max_tokens: int = 16000) -> None:
        """`prices`: giá theo id có tiền tố `anthropic-api/` (`config.models.prices`). `sdk`: client `anthropic` có sẵn
        (test); không có thì dựng `AsyncAnthropic`. `workspace_id`: cần khi key không gắn với workspace nào.
        `default_max_tokens`: Messages API bắt buộc `max_tokens` mà một số bộ đo không truyền."""
        self._key = api_key
        self._prices = prices
        self._workspace_id = workspace_id
        self._deadline_s = deadline_s
        self._default_max_tokens = default_max_tokens
        self._prompt_schemas: set[str] = set()  # schema bị từ chối là quá lớn: đưa vào system, không vào format
        if sdk is None:
            try:
                import anthropic
            except ImportError:
                raise ConfigError("thiếu gói anthropic: chạy `uv sync --group eval`") from None
            sdk = anthropic.AsyncAnthropic(api_key=api_key.get_secret_value(), max_retries=0)
        self._sdk = sdk

    def _price(self, model: str) -> ModelPrice:
        if not is_anthropic_model(model):
            raise WritoryError(ErrorCode.CONFIG_MODEL_NOT_SET,
                               detail=f"AnthropicClient chỉ nhận model có tiền tố {ANTHROPIC_MODEL_PREFIX!r}, "
                                      f"nhận {model!r}")
        price = self._prices.get(model)
        if price is None:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET,
                               detail=f"config/models.yaml không có giá (prices) cho model {model}: chi phí chỉ "
                                      "tính được từ token x giá")
        return price

    def _params(self, model: str, messages: list[Message], response_schema: type[BaseModel] | None,
                extra: Mapping[str, Any] | None, *, stream: bool = False, in_prompt: bool = False) -> dict[str, Any]:
        extra = dict(extra or {})
        clash = sorted(set(extra) & _CORE)
        if clash:
            raise ValueError(f"extra không được ghi đè trường lõi: {', '.join(clash)}")
        sampling = sorted(set(extra) & _SAMPLING)
        if sampling:
            raise ValueError(f"AnthropicClient không gửi {', '.join(sampling)}: Claude Haiku 5.5 từ chối")
        unknown = sorted(set(extra) - _PASS_THROUGH - _DROPPED - {"reasoning"})
        if unknown:
            raise ValueError(f"AnthropicClient không biết tham số extra {', '.join(unknown)}")
        if messages and messages[-1].role == "assistant":
            raise ValueError("AnthropicClient không nhận prefill: lượt cuối của messages phải là user")
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        if in_prompt and response_schema is not None:
            schema = json.dumps(response_schema.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
            system += ("\n\nTrả lời CHỈ bằng một đối tượng JSON hợp lệ với JSON Schema sau, không thêm chữ nào khác, "
                       f"không dùng khối mã:\n{schema}")
        params: dict[str, Any] = {
            "model": model.removeprefix(ANTHROPIC_MODEL_PREFIX),
            "max_tokens": extra.get("max_tokens", self._default_max_tokens),
            "messages": [{"role": m.role, "content": m.content} for m in messages if m.role != "system"],
        }
        if system:
            params["system"] = system
        output: dict[str, Any] = {}
        reasoning = extra.get("reasoning")
        effort = reasoning.get("effort") if isinstance(reasoning, Mapping) else None
        if effort == "none":
            params["thinking"] = {"type": "disabled"}
        elif effort is not None:
            output["effort"] = _EFFORT[str(effort)]
        if response_schema is not None and not in_prompt:
            output["format"] = {"type": "json_schema", "schema": strict_schema(response_schema)}
        if output:
            params["output_config"] = output
        if stream:
            params["stream"] = True
        return params

    def _options(self) -> dict[str, Any]:
        return {"workspace_id": self._workspace_id.get_secret_value()} if self._workspace_id else {}

    @staticmethod
    def _usage(raw: Any, price: ModelPrice) -> Usage:
        fresh = raw.input_tokens or 0
        read = getattr(raw, "cache_read_input_tokens", None) or 0
        write = getattr(raw, "cache_creation_input_tokens", None) or 0
        output = raw.output_tokens or 0
        return Usage(prompt_tokens=fresh + read + write, completion_tokens=output,
                     cost_usd=cost_of(price, fresh=fresh, cache_read=read, cache_write=write, output=output),
                     cached_tokens=read)

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        price = self._price(model)
        secret = self._key.get_secret_value()
        name = response_schema.__name__ if response_schema is not None else None
        in_prompt = name in self._prompt_schemas
        for _attempt in range(2):
            params = self._params(model, messages, response_schema, extra, in_prompt=in_prompt)
            _note_sent(True)
            deadline = _Deadline(self._deadline_s)
            try:
                async with deadline.step():
                    msg = await self._sdk.messages.create(**params, **self._options())
            except WritoryError:
                raise
            except Exception as e:  # noqa: BLE001 — lỗi SDK; `anthropic_error` ném lại cái không nhận ra
                err = anthropic_error(e, secret)
                if name is None or in_prompt or "grammar is too large" not in err.detail:
                    raise err from None
                self._prompt_schemas.add(name)  # thử lại một lần với schema trong system
                in_prompt = True
                continue
            return self._result(msg, price)
        raise AssertionError("không tới được")  # pragma: no cover — vòng lặp luôn return hoặc raise

    def _result(self, msg: Any, price: ModelPrice) -> ChatResult:
        if msg.stop_reason == "refusal":
            raise WritoryError(ErrorCode.LLM_CONTENT_BLOCKED, detail="Claude từ chối trả lời (stop_reason refusal)")
        text = next((b.text for b in msg.content if b.type == "text" and b.text), None)
        if text is None:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail=f"thiếu khối text trong phản hồi (stop_reason {msg.stop_reason})")
        return ChatResult(text=text, usage=self._usage(msg.usage, price), model=msg.model,
                          finish_reason=_STOP.get(msg.stop_reason, msg.stop_reason))

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        price = self._price(model)
        params = self._params(model, messages, None, None)
        secret = self._key.get_secret_value()
        _note_sent(True)
        deadline = _Deadline(self._deadline_s)
        try:
            async with self._sdk.messages.stream(**params, **self._options()) as stream:
                texts = stream.text_stream.__aiter__()
                while True:
                    async with deadline.step():
                        text = await anext(texts, None)
                    if text is None:
                        break
                    yield TextDelta(text)
                async with deadline.step():
                    final = await stream.get_final_message()
        except WritoryError:
            raise
        except Exception as e:  # noqa: BLE001 — như `chat`
            raise anthropic_error(e, secret) from None
        yield StreamDone(self._usage(final.usage, price))
