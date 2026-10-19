"""Thử lại có giới hạn cứng (G8, G11). Số lần lấy từ config/limits.yaml, do nơi gọi truyền vào.

Không chờ giữa các lần thử: không phụ thuộc thời gian, và lỗi tần suất (429) không được thử lại.
"""

from collections.abc import Awaitable, Callable

from writory.errors import ErrorCode, WritoryError

RETRYABLE = frozenset({ErrorCode.LLM_UNAVAILABLE, ErrorCode.LLM_BAD_RESPONSE})


async def with_retries[T](op: Callable[[], Awaitable[T]], *, max_retries: int) -> T:
    """Chạy `op` tối đa `1 + max_retries` lần. Chỉ thử lại lỗi trong RETRYABLE."""
    if max_retries < 0:
        raise ValueError(f"max_retries phải >= 0, nhận {max_retries}")
    last: WritoryError | None = None
    for _ in range(max_retries + 1):
        try:
            return await op()
        except WritoryError as e:
            if e.code not in RETRYABLE:
                raise
            last = e
    raise WritoryError(
        ErrorCode.RETRY_LIMIT_REACHED,
        detail=f"{max_retries + 1} lần thử đều lỗi; lỗi cuối: {last}",
    ) from last
