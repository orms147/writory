"""Dependency của API (D-41, D-44). Test thay từng hàm qua `app.dependency_overrides`.

Hàm đọc dữ liệu là `def` thường: FastAPI chạy chúng trong threadpool, nên driver Neo4j và
psycopg (đồng bộ) không chặn event loop. Mặc định nào chưa làm được thì fail closed.

Chưa có đăng nhập (tuần 5): mọi yêu cầu là người chơi dev `DEV_OWNER_ID`, và mọi router dùng các
hàm này chỉ mount khi bật `ENABLE_DEV_ROUTES` (D-41). Đường ống kiểm chủ (truyện, phiên khởi tạo,
key, nhật ký chi phí đều theo `owner_id`) đã có; tuần 5 chỉ cần đổi `get_owner_id`.
"""

import asyncio
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Protocol

import psycopg
from fastapi import Depends, HTTPException, Request
from neo4j import Driver
from pydantic import BaseModel, SecretStr

from writory.config import AppConfig, CostLimits, LimitNotSetError, RateLimits
from writory.db import (
    CostEntry,
    OwnerCosts,
    StoryRecord,
    committed_player_view,
    connect,
    delete_player_key,
    job_lock,
    load_player_key,
    load_story_brief,
    load_story_plan,
    narrator_questions_asked,
    owner_costs,
    pending_cost_estimates,
    record_cost,
    save_player_key,
    settle_cost_estimate,
    setup_spent_usd,
    story_spent_usd,
    take_llm_call,
    take_narrator_question,
)
from writory.db import get_owned_story as db_get_owned_story
from writory.errors import ErrorCode, WritoryError
from writory.graph import PlayerView
from writory.guard.state import Neo4jState
from writory.llm.base import GenerationCost, LLMClient
from writory.llm.cost import CostEstimator, CostTracker, MeteredClient
from writory.llm.ledger import CallCost, PendingEstimate, RecordingClient, settle_estimates
from writory.llm.openrouter import OpenRouterClient
from writory.llm.ratelimit import CallQuota, RateLimitedClient
from writory.pipeline.choices import ChoicesOutput
from writory.pipeline.extract import ExtractOutput
from writory.pipeline.narrator import NarratorCounter, NarratorOutput
from writory.pipeline.scene import SceneOutline
from writory.pipeline.setup import BuildOutput, CharactersOutput, PlotsOutput, SettingsOutput
from writory.pipeline.story_plan import StoryPlan
from writory.pipeline.summary import SummaryOutput
from writory.safety.classify import Classification
from writory.safety.crypto import KeyCipher
from writory.safety.leak import leak_names
from writory.safety.moderate import ModerationOutput

# TODO(G10, tuần 5): bỏ khi có đăng nhập; mọi dòng `dev` đổi sang tài khoản thật (migration 0003).
DEV_OWNER_ID = "dev"


def dev_routes_only(request: Request) -> None:
    """Fail closed: chỉ chạy khi create_app đã bật cờ dev cho chính app này (D-41)."""
    if getattr(request.app.state, "dev_routes_enabled", False) is not True:
        raise HTTPException(status_code=404)


def get_app_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_owner_id() -> str:
    """Người đang dùng. TODO(G10, tuần 5): lấy từ phiên đăng nhập; chưa có thì mọi người là dev."""
    return DEV_OWNER_ID


def get_pg_conn(request: Request) -> Iterator[psycopg.Connection]:
    """Một kết nối Postgres (autocommit) cho mỗi request; đóng sau khi trả lời (với SSE: sau khi
    stream xong hoặc bị huỷ)."""
    conn = connect(request.app.state.settings)
    try:
        yield conn
    finally:
        conn.close()


def get_neo4j_driver(request: Request) -> Driver:
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise RuntimeError("app chưa có Neo4j driver")  # lỗi cấu hình app → INTERNAL_ERROR
    return driver


Config = Annotated[AppConfig, Depends(get_app_config)]
Owner = Annotated[str, Depends(get_owner_id)]
PgConn = Annotated[psycopg.Connection, Depends(get_pg_conn)]
Neo4jDriver = Annotated[Driver, Depends(get_neo4j_driver)]


def get_owned_story(story_id: str, conn: PgConn, owner: Owner) -> StoryRecord:
    """Truyện không có, hoặc của người khác → STORY_NOT_FOUND (404, G10)."""
    return db_get_owned_story(conn, story_id, owner)


OwnedStory = Annotated[StoryRecord, Depends(get_owned_story)]


def lock_story(story: OwnedStory, conn: PgConn) -> Iterator[None]:
    """Giữ khoá của truyện tới khi yêu cầu kết thúc: dùng cho đường gọi model đổi trạng thái truyện
    (tạo lại lựa chọn, ô tự viết). Đang có việc khác trên truyện, kể cả viết chương: STORY_BUSY
    ngay, không gọi model (G8, D-56). Cùng khoá với viết chương (`api/play.get_chapter_job`)."""
    with job_lock(conn, "story", story.id):
        yield


def lock_narrator(story: OwnedStory, conn: PgConn) -> Iterator[None]:
    """Một câu hỏi người kể mỗi truyện tại một thời điểm (G8, D-56). Khoá riêng, không chặn và
    không bị chặn bởi việc viết chương, vì hỏi người kể không mất lượt truyện."""
    with job_lock(conn, "narrator", story.id):
        yield


def get_player_view(story: OwnedStory, conn: PgConn, driver: Neo4jDriver) -> PlayerView:
    """player_view ở chương đã commit (D-6)."""
    return committed_player_view(conn, driver, story.id)


def get_truth_names(story: OwnedStory, driver: Neo4jDriver) -> Mapping[str, tuple[str, ...]]:
    """Tên lớp truth, CHỈ cho bộ dò lộ (G2), theo đúng quy tắc của `leak_names` (D-48). Không bao
    giờ đưa vào phản hồi hay context model."""
    return leak_names(Neo4jState(driver, story.id))


def get_story_brief(story: OwnedStory, conn: PgConn) -> str:
    """Thiết lập truyện người chơi đã đọc lúc khởi tạo (`stories.brief`), CHỈ cho bộ dò lộ (G2):
    tên có trong đó là chữ đã thấy (D-52). Truyện không có (nạp tay) thì rỗng: bộ dò chỉ chặt
    hơn, không lỏng hơn."""
    return load_story_brief(conn, story.id) or ""


StoryBrief = Annotated[str, Depends(get_story_brief)]


def get_story_plan(story: OwnedStory, conn: PgConn) -> StoryPlan:
    """Bản kế hoạch ẩn (D-44). Truyện không có kế hoạch thì fail closed: không có nó thì không chạy
    đủ bộ dò lộ (G2) và người canh, nên không trả lời, không viết."""
    plan = load_story_plan(conn, story.id)
    if plan is None:
        raise RuntimeError(f"truyện {story.id} không có story_plan")  # → INTERNAL_ERROR
    return plan


# --- key người chơi (G7) -----------------------------------------------------------------------


class KeyStore(Protocol):
    """Key đã mã hoá của người đang dùng. Không bao giờ thấy key gốc."""

    def load(self) -> bytes | None: ...
    def save(self, token: bytes) -> None: ...
    def delete(self) -> bool: ...


class PostgresKeyStore:
    def __init__(self, conn: psycopg.Connection, owner_id: str) -> None:
        self._conn = conn
        self._owner = owner_id

    def load(self) -> bytes | None:
        return load_player_key(self._conn, self._owner)

    def save(self, token: bytes) -> None:
        save_player_key(self._conn, self._owner, token)

    def delete(self) -> bool:
        return delete_player_key(self._conn, self._owner)


def get_key_store(conn: PgConn, owner: Owner) -> KeyStore:
    return PostgresKeyStore(conn, owner)


def get_key_cipher(request: Request) -> KeyCipher:
    """Dựng trong create_app khi bật router dev; khoá sai thì app không khởi động (D-11)."""
    return request.app.state.key_cipher


Keys = Annotated[KeyStore, Depends(get_key_store)]
Cipher = Annotated[KeyCipher, Depends(get_key_cipher)]


# --- nhật ký chi phí (G8) ----------------------------------------------------------------------


class CostLedger(Protocol):
    def record(self, entry: CostEntry, *, story_id: str | None = None,
               setup_id: str | None = None, chapter: int | None = None) -> None: ...
    def story_spent(self, story_id: str) -> float: ...
    def setup_spent(self, setup_id: str) -> float: ...
    # Dòng ước tính có id generation, để tra lại chi phí thật (D-64).
    def pending_estimates(self, *, story_id: str | None = None, setup_id: str | None = None,
                          limit: int) -> list[PendingEstimate]: ...
    def settle_estimate(self, row_id: int, cost: GenerationCost) -> None: ...
    def owner_costs(self, now: datetime) -> OwnerCosts: ...


class PostgresCostLedger:
    def __init__(self, conn: psycopg.Connection, owner_id: str) -> None:
        self._conn = conn
        self._owner = owner_id

    def record(self, entry: CostEntry, *, story_id: str | None = None,
               setup_id: str | None = None, chapter: int | None = None) -> None:
        record_cost(self._conn, owner_id=self._owner, entry=entry, story_id=story_id,
                    setup_id=setup_id, chapter=chapter)

    def story_spent(self, story_id: str) -> float:
        return story_spent_usd(self._conn, story_id)

    def setup_spent(self, setup_id: str) -> float:
        return setup_spent_usd(self._conn, setup_id)

    def pending_estimates(self, *, story_id: str | None = None, setup_id: str | None = None,
                          limit: int) -> list[PendingEstimate]:
        return [PendingEstimate(row_id, gen_id) for row_id, gen_id in pending_cost_estimates(
            self._conn, story_id=story_id, setup_id=setup_id, limit=limit)]

    def settle_estimate(self, row_id: int, cost: GenerationCost) -> None:
        settle_cost_estimate(self._conn, row_id, cost_usd=cost.cost_usd,
                             prompt_tokens=cost.prompt_tokens,
                             completion_tokens=cost.completion_tokens)

    def owner_costs(self, now: datetime) -> OwnerCosts:
        """Số người này đã trả (`/player/costs`, D-66); tháng theo UTC của `now`."""
        return owner_costs(self._conn, self._owner, now=now)


def get_cost_ledger(conn: PgConn, owner: Owner) -> CostLedger:
    return PostgresCostLedger(conn, owner)


# Vai của một lời gọi, đoán theo schema JSON; không schema là model viết. Dùng để ghi nhật ký.
ROLE_OF_SCHEMA: dict[type[BaseModel], str] = {
    SceneOutline: "outline",
    ExtractOutput: "extract",
    ChoicesOutput: "choices",
    NarratorOutput: "narrator",
    Classification: "classify",
    SettingsOutput: "setup",
    PlotsOutput: "setup",
    CharactersOutput: "setup",
    BuildOutput: "setup",
    SummaryOutput: "summary",  # tóm tắt chương (D-49)
    ModerationOutput: "moderate",  # kiểm duyệt nội dung (G9, D-57)
}


def role_of_schema(schema: type[BaseModel] | None) -> str:
    if schema is None:
        return "writer"
    return ROLE_OF_SCHEMA.get(schema, schema.__name__)


# --- client model trả bằng key người chơi (D-2) ------------------------------------------------

LLMFactory = Callable[[SecretStr], LLMClient]


def get_llm_factory(request: Request) -> LLMFactory:
    """Client OpenRouter dùng chung một httpx.AsyncClient của app (đóng lúc tắt app)."""
    http = getattr(request.app.state, "openrouter_http", None)
    if http is None:
        raise RuntimeError("app chưa có httpx client cho OpenRouter")
    return lambda api_key: OpenRouterClient(api_key, http=http)


# --- giới hạn tần suất (G8, D-56) ---------------------------------------------------------------

Clock = Callable[[], float]


def get_clock() -> Clock:
    """Giờ cho bộ đếm tần suất (giây kể từ epoch). Test thay bằng đồng hồ giả."""
    return time.time


class PostgresCallQuota:
    """Lượt gọi model mỗi phút của một người chơi, đếm trong Postgres (`db.take_llm_call`).
    Giới hạn đọc từ config mỗi lần xin: chưa đặt (null) thì CONFIG_LIMIT_NOT_SET, không phải vô hạn."""

    def __init__(self, conn: psycopg.Connection, owner_id: str, limits: RateLimits,
                 clock: Clock) -> None:
        self._conn = conn
        self._owner = owner_id
        self._limits = limits
        self._clock = clock

    async def take(self) -> bool:
        try:
            limit = self._limits.require("llm_calls_per_minute_per_user")
        except LimitNotSetError as e:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None
        return await asyncio.to_thread(take_llm_call, self._conn, self._owner, limit,
                                       now=self._clock())


def get_call_quota(conn: PgConn, owner: Owner, config: Config,
                   clock: Annotated[Clock, Depends(get_clock)]) -> CallQuota:
    return PostgresCallQuota(conn, owner, config.limits.rate_limit, clock)


# Số dòng ước tính tra lại theo id mỗi nhóm lời gọi (D-64): đủ cho vài lời gọi bị huỷ của một
# chương, không để một yêu cầu tốn hàng chục lượt tra.
SETTLE_LOOKUPS_PER_OPEN = 5


@dataclass(frozen=True)
class _ScopedEstimates:
    """Dòng ước tính của đúng một truyện hoặc một phiên khởi tạo (`ledger.EstimateBook`)."""

    ledger: "CostLedger"
    story_id: str | None
    setup_id: str | None

    def pending(self, limit: int) -> list[PendingEstimate]:
        return self.ledger.pending_estimates(story_id=self.story_id, setup_id=self.setup_id,
                                             limit=limit)

    def settle(self, row_id: int, cost: GenerationCost) -> None:
        self.ledger.settle_estimate(row_id, cost)


class PlayerLLM:
    """Dựng client model cho một nhóm lời gọi, trả bằng key của người chơi; không bao giờ dùng key
    của chủ dự án. Key chỉ được đọc và giải mã khi thật sự cần gọi model, rồi chỉ đi vào client
    model (G7). Mọi lời gọi được ghi vào nhật ký chi phí, và trần mỗi truyện tính cả số đã tiêu.
    Mọi lời gọi cũng xin một lượt tần suất của người chơi trước khi tới model (G8, D-56).

    D-64: mọi lời gọi gửi kèm `max_tokens` của `estimator`; lời gọi không có usage (bị huỷ, đứt,
    thiếu usage.cost) ghi chi phí tối đa, đánh dấu ước tính. Trước lời gọi đầu của nhóm, các dòng
    ước tính có id generation của cùng truyện (hay phiên) được tra lại bằng client của chính key
    người chơi; lượt tra không phải lời gọi model nên không xin lượt tần suất."""

    def __init__(self, *, keys: KeyStore, cipher: KeyCipher, factory: LLMFactory,
                 ledger: CostLedger, limits: CostLimits, quota: CallQuota,
                 estimator: CostEstimator) -> None:
        self._keys = keys
        self._cipher = cipher
        self._factory = factory
        self._ledger = ledger
        self._limits = limits
        self._quota = quota
        self._estimator = estimator

    def open(self, *, story_id: str | None = None, setup_id: str | None = None,
             chapter: int | None = None) -> tuple[LLMClient, CostTracker]:
        """Client đã gắn nhật ký (chưa gắn trần) và bộ đếm trần, cho nơi tự dựng MeteredClient
        (ChapterRun). Lời gọi khởi tạo tính theo phiên; lời gọi của truyện tính theo truyện."""
        if (story_id is None) == (setup_id is None):
            raise ValueError("cần đúng một trong story_id, setup_id")
        token = self._keys.load()
        if token is None:
            raise WritoryError(ErrorCode.PLAYER_KEY_MISSING, detail="người chơi chưa lưu key")
        raw = self._factory(self._cipher.decrypt(token))
        inner = RateLimitedClient(raw, self._quota)

        def sink(cost: CallCost) -> None:
            self._ledger.record(
                CostEntry(cost.role, cost.model, cost.prompt_tokens, cost.completion_tokens,
                          cost.cost_usd, estimated=cost.estimated,
                          generation_id=cost.generation_id),
                story_id=story_id, setup_id=setup_id, chapter=chapter,
            )

        book = _ScopedEstimates(self._ledger, story_id, setup_id)

        async def settle() -> None:
            await settle_estimates(book, raw.generation_cost, limit=SETTLE_LOOKUPS_PER_OPEN)

        spent = (self._ledger.story_spent(story_id) if story_id is not None
                 else self._ledger.setup_spent(setup_id))
        tracker = CostTracker(self._limits, story_spent_usd=spent)
        client = RecordingClient(inner, sink, role_of=role_of_schema, estimator=self._estimator,
                                 settle=settle)
        return client, tracker

    def metered(self, **kw) -> MeteredClient:
        llm, tracker = self.open(**kw)
        return MeteredClient(llm, tracker)


def get_player_llm(
    keys: Keys, cipher: Cipher, factory: Annotated[LLMFactory, Depends(get_llm_factory)],
    ledger: Annotated[CostLedger, Depends(get_cost_ledger)], config: Config,
    quota: Annotated[CallQuota, Depends(get_call_quota)],
) -> PlayerLLM:
    return PlayerLLM(keys=keys, cipher=cipher, factory=factory, ledger=ledger,
                     limits=config.limits.cost_usd, quota=quota,
                     estimator=CostEstimator.from_config(config))


PlayerLLMs = Annotated[PlayerLLM, Depends(get_player_llm)]


def get_narrator_llm(story: OwnedStory, llm: PlayerLLMs) -> MeteredClient:
    """Hỏi người kể: key người chơi; chi phí tính vào truyện, ở chương đang đọc."""
    return llm.metered(story_id=story.id, chapter=story.committed_chapter or 0)


class PostgresNarratorQuota:
    """Bộ đếm câu hỏi người kể trong Postgres (`db.take_narrator_question`); đọc lại số lượt đã
    giữ để báo số câu còn lại (`db.narrator_questions_asked`, D-66)."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    async def take(self, story_id: str, chapter: int, limit: int) -> bool:
        return await asyncio.to_thread(take_narrator_question, self._conn, story_id, chapter,
                                       limit)

    async def asked(self, story_id: str, chapter: int) -> int:
        return await asyncio.to_thread(narrator_questions_asked, self._conn, story_id, chapter)


def get_narrator_quota(conn: PgConn) -> NarratorCounter:
    return PostgresNarratorQuota(conn)
