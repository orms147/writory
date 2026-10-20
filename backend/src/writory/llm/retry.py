"""Thử lại có giới hạn cứng (G8, G11). Số lần lấy từ config/limits.yaml, do nơi gọi truyền vào.

Mỗi loại lỗi có số lần riêng (D-14): lỗi mạng theo `retries.llm_transient`, JSON sai schema theo
`retries.extract_schema_retry`. Nơi gọi phải nói rõ thử lại loại nào (`retry_on`).

Không chờ giữa các lần thử: không phụ thuộc thời gian, và lỗi tần suất (429) không được thử lại.
"""

from collections.abc import Awaitable, Callable

from writory.errors import ErrorCode, WritoryError

RETRY_TRANSIENT = frozenset({ErrorCode.LLM_UNAVAILABLE})
RETRY_SCHEMA = frozenset({ErrorCode.LLM_BAD_RESPONSE})


async def with_retries[T](
    op: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    retry_on: frozenset[ErrorCode],
) -> T:
    """Chạy `op` tối đa `1 + max_retries` lần. Chỉ thử lại lỗi có mã trong `retry_on`."""
    if max_retries < 0:
        raise ValueError(f"max_retries phải >= 0, nhận {max_retries}")
    last: WritoryError | None = None
    for _ in range(max_retries + 1):
        try:
            return await op()
        except WritoryError as e:
            if e.code not in retry_on:
                raise
            last = e
    raise WritoryError(
        ErrorCode.RETRY_LIMIT_REACHED,
        detail=f"{max_retries + 1} lần thử đều lỗi; lỗi cuối: {last}",
    ) from last


async def with_json_retries[T](
    op: Callable[[], Awaitable[T]], *, schema_retries: int, transient_retries: int
) -> T:
    """Lời gọi trả JSON theo schema: hai lớp lồng nhau (D-14). Lớp trong thử lại JSON sai schema
    (`retries.extract_schema_retry`), lớp ngoài thử lại lỗi mạng (`retries.llm_transient`)."""

    async def schema_layer() -> T:
        return await with_retries(op, max_retries=schema_retries, retry_on=RETRY_SCHEMA)

    return await with_retries(schema_layer, max_retries=transient_retries,
                              retry_on=RETRY_TRANSIENT)
