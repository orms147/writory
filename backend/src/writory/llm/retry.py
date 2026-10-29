"""Thử lại có giới hạn cứng (G8, G11). Số lần lấy từ config/limits.yaml, do nơi gọi truyền vào.

Mỗi loại lỗi có số lần riêng (D-14): lỗi mạng theo `retries.llm_transient`, JSON sai schema theo
`retries.extract_schema_retry`. Nơi gọi phải nói rõ thử lại loại nào (`retry_on`).

Không chờ giữa các lần thử: không phụ thuộc thời gian, và lỗi tần suất (429) không được thử lại.
"""

import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from writory.errors import ErrorCode, WritoryError

log = logging.getLogger(__name__)

RETRY_TRANSIENT = frozenset({ErrorCode.LLM_UNAVAILABLE, ErrorCode.LLM_TIMEOUT})
RETRY_SCHEMA = frozenset({ErrorCode.LLM_BAD_RESPONSE})


# Móc báo "thân trả lời bị từ chối" (D-115). CHỈ bộ đo cài (`bench_run`): app không bao giờ cài, nên
# không giữ thân trả lời nào (G7). Không cài thì không làm gì.
RejectionHook = Callable[[WritoryError], None]
_REJECTION_HOOK: ContextVar[RejectionHook | None] = ContextVar("writory_rejection_hook",
                                                                default=None)


@contextmanager
def watch_rejections(hook: RejectionHook) -> Iterator[None]:
    """Trong khối này, mỗi lần một lời gọi bị từ chối vì sai schema hay sai quy tắc sau schema
    (`LLM_BAD_RESPONSE`, kể cả lần cuối trước khi hết lượt thử) thì gọi `hook(lỗi)`. Hook lỗi không
    đổi kết quả của lời gọi."""
    token = _REJECTION_HOOK.set(hook)
    try:
        yield
    finally:
        _REJECTION_HOOK.reset(token)


def _heard(e: WritoryError) -> None:
    hook = _REJECTION_HOOK.get()
    if hook is None or e.code not in RETRY_SCHEMA:
        return
    try:
        hook(e)
    except Exception as err:  # noqa: BLE001 — móc của bộ đo không được làm hỏng lời gọi
        log.warning("móc báo thân bị từ chối lỗi (%s)", type(err).__name__)


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
            _heard(e)
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
