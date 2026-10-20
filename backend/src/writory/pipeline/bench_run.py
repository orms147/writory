"""Chạy cả một truyện từ dòng lệnh (design §12, mốc tuần 2; D-42, D-43). Cách chạy: docs/eval.md.

Đường đi đúng như người chơi: khởi tạo (`pipeline.setup`; ở mỗi bước có 3 lựa chọn, tự chọn bằng
`random.Random(seed)`) → ghi chương 0 → lặp `ChapterRun` tới chương cuối của kế hoạch (hoặc
`--chapters`). Hết chương thì tự chọn một lựa chọn làm hành động dẫn tới chương sau. Cảnh hay bộ
lựa chọn bị chặn, hoặc model trả sai sau mọi lần thử lại của pipeline: "bấm thử lại" tối đa
`player_retries` lần, như người chơi. Lỗi khác (trần, key, cấu hình) dừng ngay.

Kết quả ở `evals/results/<ngày>-run-<nhãn>/`, tách theo người được thấy:
- File chung chỉ có chữ người chơi thấy (văn cảnh đã kiểm, lựa chọn, câu lỗi G12) và số đếm, mã
  lỗi, loại lỗi: meta.json, setup.json, events.jsonl, chapters/, calls.jsonl, report.json,
  summary.md. Không có bản kế hoạch, id nút, góp ý của người canh hay chi tiết lỗi.
- truth_dump.json: kế hoạch, gói thay đổi từng chương, đồ thị cuối, dàn ý, góp ý viết lại, cạnh
  bộ trích bỏ, chi tiết lỗi (đã redact). Để chấm tay.

Trần: `--budget` (USD) cho cả lần chạy. Trước mỗi lời gọi giữ chỗ chi phí tối đa của lời gọi đó
(giá trong đề × token vào ước tính + `max_tokens_per_call` × giá ra), như bài D, nên không vượt
trần; `max_tokens_per_call` được gửi kèm mọi lời gọi để con số tối đa là thật (D-43). Trần trong
config/limits.yaml (cảnh, chương, truyện) vẫn áp như khi chơi.

Key: chỉ OPENROUTER_API_KEY, đọc bằng `quality.bench_d.load_keys`; không in, không ghi (G7).
`--dry-run`: model giả, không key, không gọi model; vẫn cần Neo4j + Postgres (docker compose).
"""

import argparse
import asyncio
import hashlib
import json
import logging
import math
import random
import re
import sys
import time
import traceback
import uuid
from collections import Counter, defaultdict
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    ValidationError,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from writory.config import REPO_CONFIG_DIR, REPO_ROOT, AppConfig, ConfigError, load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage
from writory.graph.schema import EDGE_TYPES
from writory.llm.base import (
    ChatResult,
    LLMClient,
    Message,
    StreamEvent,
    Usage,
    require_model,
    role_extra,
)
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM
from writory.pipeline import choices as choices_mod
from writory.pipeline import extract as extract_mod
from writory.pipeline import scene as scene_mod
from writory.pipeline import setup as setup_mod
from writory.pipeline.chapter import (
    CHAPTER_ROLES,
    ChapterOutcome,
    ChapterRequest,
    ChapterRun,
    config_problems,
    writer_tier,
)
from writory.pipeline.choices import Choice, ChoicesOutput, make_choices
from writory.pipeline.events import ChoicesReady, PlayerChoice, error_event
from writory.pipeline.extract import ExtractOutput
from writory.pipeline.scene import SceneOutline, load_style_guide
from writory.pipeline.setup import (
    BuildOutput,
    CharactersOutput,
    Naming,
    PlotsOutput,
    PovMode,
    SettingsOutput,
    StoryChoices,
    StoryTags,
    build_story,
    propose_characters,
    propose_plots,
    propose_settings,
    story_brief,
)
from writory.pipeline.store import ChapterStore, GraphStore
from writory.pipeline.story_plan import StoryPlan
from writory.quality.bench_d import (  # một chỗ cho giữ chỗ ngân sách, key, trạng thái git
    EST_CHARS_PER_TOKEN,
    Budget,
    BudgetExceeded,
    Store,
    _maybe_billed,
    git_state,
    load_keys,
)
from writory.safety.leak import leak_names
from writory.safety.redact import install_log_redaction, redact

log = logging.getLogger(__name__)

DEFAULT_SCENARIO = REPO_ROOT / "evals" / "scenarios" / "story_run" / "tu-tien-ngan.yaml"
RESULTS_DIR = REPO_ROOT / "evals" / "results"
EXIT_OK, EXIT_CONFIG, EXIT_BUDGET, EXIT_ABORT = 0, 1, 2, 3

# Lỗi mà người chơi gặp thì bấm thử lại (câu G12 của các mã này đều bảo bấm thử lại).
RETRYABLE = frozenset({
    ErrorCode.SCENE_LEAK_BLOCKED, ErrorCode.CHOICES_LEAK_BLOCKED, ErrorCode.LLM_BAD_RESPONSE,
    ErrorCode.RETRY_LIMIT_REACHED, ErrorCode.LLM_UNAVAILABLE, ErrorCode.STORY_SETUP_INVALID,
})
RUN_ROLES = ("setup", *CHAPTER_ROLES, "writer")
SETUP_STEPS = ("settings", "plots", "characters", "build")


# --- đề ----------------------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Price(BaseModel):
    """USD / 1 triệu token, chỉ để giữ chỗ ngân sách."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    input: NonNegativeFloat = Field(alias="in")
    output: NonNegativeFloat = Field(alias="out")


class RunScenario(_Strict):
    """Đề một lần chạy, khai trước trong evals/scenarios/story_run/ (D-42)."""

    version: PositiveInt
    tags: StoryTags
    length_level: str
    naming: Naming
    pov: PovMode = "protagonist"
    writer_tier: str | None = None
    seed: int
    scene_count: PositiveInt
    player_retries: NonNegativeInt
    max_tokens_per_call: PositiveInt
    prices: dict[str, Price] = Field(min_length=1)

    def story_choices(self) -> StoryChoices:
        return StoryChoices(tags=self.tags, length_level=self.length_level, pov=self.pov,
                            naming=self.naming)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def load_scenario(path: Path) -> tuple[RunScenario, str]:
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise ConfigError(f"không đọc được đề {path}: {e}") from e
    try:
        return RunScenario.model_validate(yaml.safe_load(raw)), _sha256(raw)
    except (yaml.YAMLError, ValidationError) as e:
        raise ConfigError(f"đề {path.name} sai: {e}") from e


def repo_path(path: Path) -> str:
    """Đường dẫn tương đối gốc repo nếu được: kết quả commit vào repo công khai không mang đường
    dẫn máy chạy."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def config_sha256(config_dir: Path) -> dict[str, str]:
    files = {p.name: _sha256(p.read_bytes()) for p in sorted(config_dir.glob("*.yaml"))}
    combined = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in files.items()).encode())
    return {"combined": combined.hexdigest(), **files}


def models_in_use(config: AppConfig, scenario: RunScenario) -> dict[str, dict[str, Any]]:
    """Model và mức suy luận của từng vai lần chạy dùng (model null = chưa chọn)."""
    out: dict[str, dict[str, Any]] = {
        role: {"model": getattr(config.models.roles, role),
               "reasoning": getattr(config.models.role_reasoning, role)}
        for role in RUN_ROLES if role != "writer"
    }
    try:
        tier = writer_tier(config, scenario.writer_tier)
        out["writer"] = {"tier": tier.id, "model": tier.model, "reasoning": tier.reasoning}
    except (WritoryError, ValueError):
        out["writer"] = {"tier": scenario.writer_tier, "model": None, "reasoning": None}
    return out


def run_problems(config: AppConfig, scenario: RunScenario) -> list[str]:
    """Mọi chỗ config hay đề còn thiếu, báo một lần trước lời gọi đầu. Rỗng là đủ."""
    problems: list[str] = []
    try:
        require_model(config.models.roles, "setup")
    except WritoryError as e:
        problems.append(e.detail)
    tiers = {t.id for t in config.models.writer_tiers}
    tier_id = scenario.writer_tier
    if tier_id is not None and tier_id not in tiers:
        problems.append(f"đề chọn mức model viết {tier_id!r}, config/models.yaml chỉ có "
                        f"{sorted(tiers)}")
        tier_id = None
    problems += [e.detail for e in config_problems(config, tier_id)]
    if scenario.length_level not in config.story_lengths.levels:
        problems.append(f"mức độ dài {scenario.length_level!r} không có trong "
                        "config/story_lengths.yaml")
    allowed = config.story_lengths.scenes_per_chapter
    if not allowed.min <= scenario.scene_count <= allowed.max:
        problems.append(f"scene_count={scenario.scene_count} ngoài khoảng "
                        f"{allowed.min}–{allowed.max} (story_lengths.scenes_per_chapter)")
    for role, info in models_in_use(config, scenario).items():
        if info["model"] is not None and info["model"] not in scenario.prices:
            problems.append(f"đề không có giá (prices) cho model {info['model']} của vai {role}: "
                            "cần để giữ chỗ ngân sách")
    return problems


# --- đo chi phí từng lời gọi ---------------------------------------------------------------------

ROLE_BY_SCHEMA_NAME: dict[str, str] = {
    SettingsOutput.__name__: "setup", PlotsOutput.__name__: "setup",
    CharactersOutput.__name__: "setup", BuildOutput.__name__: "setup",
    SceneOutline.__name__: "outline", ExtractOutput.__name__: "extract",
    ChoicesOutput.__name__: "choices",
}
_SETUP_STEP_BY_SCHEMA = dict(zip(
    (SettingsOutput.__name__, PlotsOutput.__name__, CharactersOutput.__name__,
     BuildOutput.__name__), SETUP_STEPS, strict=True))


def call_role(schema: type[BaseModel] | None) -> str:
    """Vai của một lời gọi, nhận ra qua schema JSON; không schema là bước viết văn."""
    if schema is None:
        return "writer"
    return ROLE_BY_SCHEMA_NAME.get(schema.__name__, f"other:{schema.__name__}")


class StepTracker(CostTracker):
    """CostTracker đếm cảnh. `ChapterRun` gọi `start_scene()` đầu mỗi cảnh và trước bước lựa
    chọn, nên mỗi lời gọi biết mình thuộc cảnh nào: dữ liệu để đặt trần `per_scene`."""

    def __init__(self, limits) -> None:
        super().__init__(limits)
        self.scene_no = 0

    def start_chapter(self) -> None:
        super().start_chapter()
        self.scene_no = 0

    def start_scene(self) -> None:
        super().start_scene()
        self.scene_no += 1


class BudgetedClient(LLMClient):
    """Giữ chỗ ngân sách cả lần chạy trước mỗi lời gọi, gửi kèm `max_tokens`, và ghi mỗi lời gọi một
    dòng (vai, chương, cảnh, chi phí, token). Không ghi chữ của lời gọi hay câu trả lời."""

    def __init__(
        self, inner: LLMClient, *, budget: Budget, prices: Mapping[str, Price], max_tokens: int,
        tracker: StepTracker, record: Callable[[dict[str, Any]], None],
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._inner, self._budget, self._prices = inner, budget, prices
        self._max_tokens, self._tracker, self._record, self._clock = (
            max_tokens, tracker, record, clock)
        self.chapter = 0
        self.attempt = 1
        self.halted: str | None = None
        self._seq = 0

    @property
    def spent_usd(self) -> float:
        return self._budget.spent_usd

    def estimate(self, model: str, messages: Sequence[Message],
                 schema: type[BaseModel] | None) -> float:
        price = self._prices[model]
        chars = sum(len(m.content) for m in messages)
        if schema is not None:
            chars += len(json.dumps(schema.model_json_schema(), ensure_ascii=False))
        tokens_in = math.ceil(chars / EST_CHARS_PER_TOKEN)
        return (tokens_in * price.input + self._max_tokens * price.output) / 1e6

    async def chat(
        self, model: str, messages: list[Message], *,
        response_schema: type[BaseModel] | None = None, extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        if model not in self._prices:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=f"đề không có giá cho {model}")
        role = call_role(response_schema)
        estimate = self.estimate(model, messages, response_schema)
        try:
            held = self._budget.reserve(estimate)
        except BudgetExceeded as e:
            self.halted = str(e)
            raise WritoryError(ErrorCode.COST_LIMIT_STORY,
                               detail=f"trần --budget của lần chạy: {e}") from None
        body_extra = dict(extra or {})  # max_tokens của lần chạy là trần: không để vai nào nâng
        body_extra["max_tokens"] = min(body_extra.get("max_tokens", self._max_tokens),
                                       self._max_tokens)
        self._seq += 1
        row: dict[str, Any] = {
            "seq": self._seq, "chapter": self.chapter, "attempt": self.attempt, "role": role,
            "scene": self._tracker.scene_no if role in ("outline", "writer", "extract") else None,
            "setup_step": _SETUP_STEP_BY_SCHEMA.get(response_schema.__name__)
            if response_schema is not None else None,
            "model": model, "extra": body_extra, "reserved_usd": round(estimate, 6),
        }
        started = self._clock()
        try:
            result = await self._inner.chat(model, messages, response_schema=response_schema,
                                            extra=body_extra)
        except WritoryError as e:
            billed = estimate if _maybe_billed(e) else 0.0
            self._budget.settle(held, billed)
            self._record(row | {"status": e.code.value, "cost_usd": None,
                                "cost_estimated_usd": billed or None,
                                "latency_s": round(self._clock() - started, 3)})
            raise
        except BaseException:
            self._budget.settle(held, estimate)  # có thể đã bị tính tiền: tính theo mức tối đa
            self._record(row | {"status": "INTERRUPTED", "cost_usd": None,
                                "cost_estimated_usd": estimate})
            raise
        cost = result.usage.cost_usd
        self._budget.settle(held, estimate if cost is None else cost)
        self._record(row | {
            "status": "ok", "served_model": result.model, "finish_reason": result.finish_reason,
            "cost_usd": cost, "cost_estimated_usd": estimate if cost is None else None,
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens,
            "latency_s": round(self._clock() - started, 3),
        })
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError("lệnh chạy cả truyện không dùng stream")
        yield  # pragma: no cover


# --- kho truyện ------------------------------------------------------------------------------


class RunStore(ChapterStore, Protocol):
    story_id: str

    def create_story(self, length_level: str) -> None: ...

    def delete_story(self) -> None: ...


class GraphRunStore(GraphStore):
    """`GraphStore` (Neo4j + Postgres) với một story_id mới cho mỗi lần chạy."""

    def __init__(self, conn, driver, story_id: str) -> None:
        super().__init__(conn, driver, story_id)
        self.story_id = story_id

    def create_story(self, length_level: str) -> None:
        from writory.db import create_story

        create_story(self._conn, self.story_id, length_level=length_level)

    def delete_story(self) -> None:
        from writory.db import delete_story_record
        from writory.graph import delete_story

        delete_story_record(self._conn, self.story_id)
        delete_story(self._driver, self.story_id)


# --- lần chạy --------------------------------------------------------------------------------


@dataclass
class RunOptions:
    out: Path
    budget_usd: float | None = None  # bắt buộc khi chạy thật; dry-run không đặt thì vô hạn
    chapters: int | None = None  # None = số chương của kế hoạch
    seed: int | None = None  # None = seed của đề
    dry_run: bool = False
    keep_story: bool = True  # False: xoá truyện khỏi Neo4j + Postgres khi xong
    label: str = ""
    config_dir: Path = REPO_CONFIG_DIR
    scenario_path: Path | None = None


def player_action_text(choice: PlayerChoice) -> str:
    """Hành động dẫn tới chương sau: đúng chữ người chơi thấy trên nút đã bấm."""
    label = choice.kind_label + (f", {choice.tone_label}" if choice.tone_label else "")
    return f"[{label}] {choice.text}"


_REJECT_REASONS = (
    "id không có trong danh mục", "câu trích không có nguyên văn trong chương (G3)",
    "nhân vật chính biết mà không có câu trích (G3)", "hé lộ nút có tên mà thiếu known_as (D-17)",
    "trùng cạnh trong cùng gói", "không phải cạnh đang hiệu lực",
)


def reject_reason(reason: str) -> str:
    """Nhóm lý do bộ trích bỏ cạnh, bỏ id và chữ của model (có thể mang lớp truth)."""
    return next((r for r in _REJECT_REASONS if reason.startswith(r)), "sai schema cạnh")


def _kinds(issues) -> list[str]:
    return [f"{i.source}:{i.kind}" for i in issues]


def _choice_truth(c: Choice) -> dict[str, Any]:
    """Lựa chọn phía máy chủ, kèm id nút (lớp truth): chỉ cho truth_dump."""
    return {"id": c.id, "kind": c.kind, "tone": c.tone, "text": c.text,
            "listeners": list(c.listeners), "about": list(c.about),
            "lie": asdict(c.lie) if c.lie else None, "feeling": c.feeling}


class StoryRun:
    """Một lần chạy cả truyện. `run()` trả mã thoát; mọi file kết quả được ghi kể cả khi dừng giữa
    chừng. `llm` là client thô (OpenRouter hoặc model giả); mọi lời gọi đi qua `BudgetedClient`
    rồi `MeteredClient` (G8)."""

    def __init__(
        self, scenario: RunScenario, scenario_sha: str, config: AppConfig, *, llm: LLMClient,
        store: RunStore, options: RunOptions, style_guide: str | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.scenario, self.scenario_sha, self.config = scenario, scenario_sha, config
        self.store, self.options, self._print = store, options, log
        self.llm = llm
        self.style_guide = style_guide if style_guide is not None else load_style_guide()
        self.seed = options.seed if options.seed is not None else scenario.seed
        self.rng = random.Random(self.seed)
        self.files = Store(options.out)
        self.tracker = StepTracker(config.limits.cost_usd)
        self.calls: list[dict[str, Any]] = []
        self.budgeted: BudgetedClient | None = None
        self.metered: MeteredClient | None = None
        self.plan: StoryPlan | None = None
        self.brief = ""
        self.packages: dict[int, ChangePackage] = {}
        self.setup_record: dict[str, Any] = {}
        self.attempts: list[dict[str, Any]] = []  # chung: số đếm, loại lỗi
        self.truth_chapters: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.errors: list[dict[str, Any]] = []  # chi tiết lỗi, chỉ vào truth_dump
        self.retries_used = {"setup": 0, "chapter": 0, "choices": 0}
        self.stop: dict[str, Any] | None = None
        self.target: int | None = None
        self.clamped = False
        self.started = ""

    # -- điều phối --

    async def run(self) -> int:
        problems = run_problems(self.config, self.scenario)
        if problems:
            raise ConfigError("config hoặc đề chưa đủ để chạy:\n- " + "\n- ".join(problems))
        budget = self.options.budget_usd
        if budget is None and not self.options.dry_run:
            raise ConfigError("lượt chạy thật cần --budget (USD)")
        if (self.options.out / "meta.json").exists():
            raise ConfigError(f"{self.options.out} đã có kết quả; dùng nhãn khác")
        self.budgeted = BudgetedClient(
            self.llm, budget=Budget("run", math.inf if budget is None else budget),
            prices=self.scenario.prices, max_tokens=self.scenario.max_tokens_per_call,
            tracker=self.tracker, record=self._record_call,
        )
        self.metered = MeteredClient(self.budgeted, self.tracker)
        self.started = datetime.now().astimezone().isoformat(timespec="seconds")
        self.files.write_meta(self._meta("running"))
        try:
            if await self._setup():
                await self._chapters()
        except Exception:  # noqa: BLE001 — lỗi của khung chạy: ghi lại, vẫn ghi đủ file
            self._stop("error", "harness", ErrorCode.INTERNAL_ERROR,
                       redact(traceback.format_exc()))
        except BaseException:  # Ctrl+C, huỷ: ghi là dừng, không ghi là xong
            self._stop("error", "interrupted", ErrorCode.INTERNAL_ERROR, "tiến trình bị ngắt")
            raise
        finally:
            self._finish()
        return self.exit_code

    @property
    def exit_code(self) -> int:
        if self.stop is None:
            return EXIT_OK
        return EXIT_BUDGET if self.stop["kind"] == "budget" else EXIT_ABORT

    def _stop(self, kind: str, where: str, code: ErrorCode, detail: str | None) -> None:
        if self.stop is not None:
            return
        self.stop = {"kind": kind, "where": where, "code": code.value}
        self.errors.append({"where": where, "code": code.value, "detail": detail})
        self._event({"type": "run_stopped", **self.stop})
        self._print(f"!! DỪNG ({kind}) ở {where}: {code.value}")

    def _event(self, row: dict[str, Any]) -> None:
        self.files.append("events.jsonl", row)

    def _record_call(self, row: dict[str, Any]) -> None:
        self.calls.append(row)
        self.files.append("calls.jsonl", row)

    def _fail(self, where: str, attempt: int, e: WritoryError) -> None:
        """Ghi một lỗi có mã: câu G12 vào sự kiện chung, chi tiết vào truth_dump."""
        self._event({"where": where, "attempt": attempt, **error_event(e).model_dump(mode="json")})
        self.errors.append({"where": where, "attempt": attempt, "code": e.code.value,
                            "detail": e.detail})

    # -- khởi tạo --

    async def _setup(self) -> bool:
        assert self.budgeted is not None and self.metered is not None
        self.budgeted.chapter = 0
        self.tracker.start_chapter()
        llm, cfg, choices = self.metered, self.config, self.scenario.story_choices()
        settings = await self._setup_step(
            "settings", lambda: propose_settings(choices, llm=llm, config=cfg))
        if settings is None:
            return False
        setting = self._pick_option("settings", settings)
        plots = await self._setup_step(
            "plots", lambda: propose_plots(choices, setting, llm=llm, config=cfg))
        if plots is None:
            return False
        plot = self._pick_option("plots", plots)
        people = await self._setup_step(
            "characters", lambda: propose_characters(choices, setting, plot, llm=llm, config=cfg))
        if people is None:
            return False
        protagonist = self._pick_option("characters", people)
        built = await self._setup_step("build", lambda: build_story(
            choices, setting, plot, protagonist, llm=llm, config=cfg,
            commit_id=f"{self.store.story_id}-ch0"))
        if built is None:
            return False
        self.plan = built.plan
        self.setup_record["build"] = {"done": True, "chapters_planned": built.plan.total_chapters}
        try:
            self.store.create_story(choices.length_level)
            self.store.commit(0, [], built.package)
        except WritoryError as e:
            self._fail("setup:commit", 1, e)
            self._stop("error", "setup:commit", e.code, e.detail)
            return False
        self.packages[0] = built.package
        self.brief = story_brief(choices, setting, plot, protagonist)
        self._event({"type": "chapter_committed", "chapter": 0})
        self._print(f"[khởi tạo] xong; kế hoạch {built.plan.total_chapters} chương, "
                    f"đã tiêu {self.budgeted.spent_usd:.4f} USD")
        return True

    async def _setup_step(self, step: str, op: Callable[[], Any]) -> Any:
        assert self.budgeted is not None
        for attempt in range(1, self.scenario.player_retries + 2):
            self.budgeted.attempt = attempt
            self.tracker.start_scene()  # trần mỗi cảnh áp cho mỗi bước khởi tạo
            try:
                return await op()
            except WritoryError as e:
                self._fail(f"setup:{step}", attempt, e)
                if self.budgeted.halted:
                    self._stop("budget", f"setup:{step}", e.code, e.detail)
                    return None
                if e.code in RETRYABLE and attempt <= self.scenario.player_retries:
                    self.retries_used["setup"] += 1
                    continue
                self._stop("error", f"setup:{step}", e.code, e.detail)
                return None
        return None

    def _pick_option(self, step: str, options: Sequence[BaseModel]) -> Any:
        index = self.rng.randrange(len(options))
        shown = [o.model_dump() for o in options]
        self.setup_record[step] = {"options": shown, "picked": index}
        self._event({"type": "setup_options", "step": step, "options": shown, "picked": index})
        return options[index]

    # -- các chương --

    async def _chapters(self) -> None:
        assert self.plan is not None
        total = self.plan.total_chapters
        wanted = self.options.chapters
        self.target = total if wanted is None else min(wanted, total)
        self.clamped = wanted is not None and wanted > total
        if self.clamped:
            self._print(f"--chapters {wanted} vượt kế hoạch ({total} chương): dừng ở chương {total}")
        present: tuple[str, ...] = ()
        action: str | None = None
        for number in range(1, self.target + 1):
            step = await self._chapter(number, present, action)
            if step is None:
                return
            action, present = step

    async def _chapter(self, number: int, present: tuple[str, ...], action: str | None):
        assert self.budgeted is not None and self.plan is not None
        retries = self.scenario.player_retries
        for attempt in range(1, retries + 2):
            self.budgeted.chapter, self.budgeted.attempt = number, attempt
            request = ChapterRequest(
                present_ids=present, scene_count=self.scenario.scene_count, story_brief=self.brief,
                player_action=action, writer_tier=self.scenario.writer_tier,
            )
            run = ChapterRun(request, llm=self.budgeted, store=self.store, config=self.config,
                             plan=self.plan, tracker=self.tracker, style_guide=self.style_guide)
            shown: list[str] = []
            async for event in run.events():
                self._event({"chapter": number, "attempt": attempt,
                             **event.model_dump(mode="json")})
                if event.type == "scene_ready":
                    shown.append(event.text)
            out = run.outcome
            self._record_attempt(number, attempt, out, action)
            code = out.error or (ErrorCode.SCENE_LEAK_BLOCKED if out.blocked_scene else None)
            if out.committed:
                assert out.package is not None
                self.packages[number] = out.package
                choices = await self._ensure_choices(number, attempt, out, code)
                picked = self._pick_choice(number, choices) if choices else None
                status = None if picked is not None else (
                    f"đã ghi, không có lựa chọn: dừng vì {self.stop['code'] if self.stop else '?'}")
                self._write_chapter(number, shown, action, choices, picked, status=status)
                self._print(f"[chương {number}] đã ghi, {len(out.scenes)} cảnh, đã tiêu "
                            f"{self.budgeted.spent_usd:.4f} USD")
                if picked is None:
                    return None
                return (player_action_text(choices[picked].for_player()),
                        self._carry_present(out))
            if out.error is not None:
                self.errors.append({"where": f"chapter {number}", "attempt": attempt,
                                    "code": out.error.value, "detail": out.error_detail})
            if self.budgeted.halted:
                self._stop("budget", f"chapter {number}", code or ErrorCode.COST_LIMIT_STORY,
                           out.error_detail)
            elif code in RETRYABLE and attempt <= retries:
                self.retries_used["chapter"] += 1
                continue
            else:
                self._stop("error", f"chapter {number}", code or ErrorCode.INTERNAL_ERROR,
                           out.error_detail)
            self._write_chapter(number, shown, action, None, None,
                                status=f"chưa ghi: dừng vì {self.stop['code']}")
            return None
        return None

    async def _ensure_choices(self, number: int, attempt: int, out: ChapterOutcome,
                              code: ErrorCode | None) -> list[Choice]:
        """Chương đã ghi mà chưa có bộ lựa chọn: tạo lại như người chơi bấm thử lại (D-37)."""
        assert self.budgeted is not None
        choices = list(out.choices)
        if not choices and out.error is not None:
            self.errors.append({"where": f"chapter {number}: choices", "attempt": attempt,
                                "code": out.error.value, "detail": out.error_detail})
        regenerated = 0
        while not choices:
            if self.budgeted.halted:
                self._stop("budget", f"chapter {number}", code or ErrorCode.COST_LIMIT_STORY,
                           None)
                return []
            if code not in RETRYABLE or regenerated >= self.scenario.player_retries:
                self._stop("error", f"chapter {number}: choices",
                           code or ErrorCode.INTERNAL_ERROR, None)
                return []
            regenerated += 1
            self.retries_used["choices"] += 1
            try:
                choices = await self._regenerate_choices(number, out)
            except WritoryError as e:
                self._fail(f"chapter {number}: choices", attempt, e)
                code = e.code
                continue
            ready = ChoicesReady(chapter=number, choices=[c.for_player() for c in choices])
            self._event({"chapter": number, "attempt": attempt, **ready.model_dump(mode="json")})
            self.truth_chapters[str(number)][-1]["choices"] = [_choice_truth(c) for c in choices]
        return choices

    async def _regenerate_choices(self, number: int, out: ChapterOutcome) -> list[Choice]:
        assert self.metered is not None and self.plan is not None
        self.tracker.start_scene()  # như bước lựa chọn trong ChapterRun
        state = self.store.state()
        return await make_choices(
            self.metered, require_model(self.config.models.roles, "choices"),
            view=self.store.player_view(number), protagonist_id=state.protagonist_id(),
            last_scene_text=out.scenes[-1].text, truth_names=leak_names(state), plan=self.plan,
            story_brief=self.brief,
            retries=self.config.limits.retries, extra=role_extra(self.config.models, "choices"),
        )

    def _pick_choice(self, number: int, choices: Sequence[Choice]) -> int:
        index = self.rng.randrange(len(choices))
        self._event({"chapter": number, "type": "choice_picked", "index": index,
                     "choice": choices[index].for_player().model_dump(mode="json")})
        return index

    def _carry_present(self, out: ChapterOutcome) -> tuple[str, ...]:
        """Nhân vật có mặt đầu chương sau = có mặt ở cảnh cuối chương này (chỉ id có thật)."""
        if not out.scenes:
            return ()
        characters = {e.id for e in self.store.catalogue() if e.label == "Character"}
        return tuple(p for p in dict.fromkeys(out.scenes[-1].outline.present) if p in characters)

    def _record_attempt(self, number: int, attempt: int, out: ChapterOutcome,
                        action: str | None) -> None:
        reviews = [{
            "scene": r.scene, "attempt": r.attempt, "verdict": r.verdict,
            "issues": _kinds(r.issues), "blocking": _kinds(i for i in r.issues if i.block),
            "rejected": len(r.rejected),
            "rejected_by_reason": dict(Counter(reject_reason(why) for _, why in r.rejected)),
        } for r in out.reviews]
        self.attempts.append({
            "chapter": number, "attempt": attempt, "committed": out.committed,
            "blocked_scene": out.blocked_scene, "error": out.error.value if out.error else None,
            "scenes": [{"scene": s.number, "attempts": s.attempts, "chars": len(s.text),
                        "left_when_shown": _kinds(s.unresolved)} for s in out.scenes],
            "reviews": reviews, "rewrites": sum(r["verdict"] == "rewrite" for r in reviews),
            "choices": len(out.choices), "cost_usd": round(out.cost_usd, 6),
        })
        self.truth_chapters[str(number)].append({
            "attempt": attempt, "commit_id": out.commit_id, "player_action": action,
            "error_detail": out.error_detail,
            "outlines": [{"scene": s.number, **s.outline.model_dump()} for s in out.scenes],
            "reviews": [{
                "scene": r.scene, "attempt": r.attempt, "verdict": r.verdict,
                "issues": [{"source": i.source, "kind": i.kind, "block": i.block,
                            "feedback": i.feedback} for i in r.issues],
                "rejected": [list(x) for x in r.rejected],
            } for r in out.reviews],
            "choices": [_choice_truth(c) for c in out.choices],
        })

    def _write_chapter(self, number: int, scenes: Sequence[str], action: str | None,
                       choices: Sequence[Choice] | None, picked: int | None, *,
                       status: str | None) -> None:
        if not scenes and status is not None:
            return  # chưa hiện cảnh nào: không có gì để đọc
        lines = [f"# Chương {number}", ""]
        if status:
            lines += [f"_Trạng thái: {status}. Chỉ gồm các cảnh đã hiện._", ""]
        if action:
            lines += [f"_Lựa chọn dẫn tới chương này: {action}_", ""]
        lines.append("\n\n* * *\n\n".join(scenes))
        if choices:
            lines += ["", "## Lựa chọn cuối chương", ""]
            for i, c in enumerate(choices):
                shown = c.for_player()
                mark = "  ← đã chọn" if i == picked else ""
                lines.append(f"{i + 1}. {player_action_text(shown)}{mark}")
        path = self.options.out / "chapters" / f"ch{number:02d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # -- kết thúc --

    def _final_graph(self) -> dict[str, Any] | None:
        chapter = self.store.committed_chapter() if self.packages else None
        if chapter is None:
            return None
        state = self.store.state()
        nodes = state.nodes([e.id for e in self.store.catalogue()])
        return {
            "chapter": chapter,
            "nodes": {i: {"label": r.label, "props": r.props} for i, r in sorted(nodes.items())},
            "edges": [asdict(r) for t in EDGE_TYPES for r in state.edges_at(t, chapter)],
        }

    def _finish(self) -> None:
        try:
            final = self._final_graph()
        except Exception:  # noqa: BLE001 — kho hỏng lúc cuối: vẫn ghi phần đã có
            final = {"error": redact(traceback.format_exc())}
        truth = {
            "story_id": self.store.story_id,
            "plan": self.plan.model_dump(mode="json") if self.plan else None,
            "packages": {str(n): p.model_dump(mode="json", by_alias=True)
                         for n, p in sorted(self.packages.items())},
            "final": final, "chapters": self.truth_chapters, "errors": self.errors,
        }
        self._write_json("truth_dump.json", truth)
        self._write_json("setup.json", self.setup_record)
        report = build_report(self)
        self._write_json("report.json", report)
        meta = self._meta(report["status"])
        (self.options.out / "summary.md").write_text(build_summary(meta, report),
                                                     encoding="utf-8", newline="\n")
        if self.options.dry_run and not self.options.keep_story and self.packages:
            try:
                self.store.delete_story()
                meta["story_deleted"] = True
            except Exception:  # noqa: BLE001 — dọn không được thì báo, kết quả vẫn còn
                self._print(f"!! không xoá được truyện {self.store.story_id} khỏi kho")
        self.files.write_meta(meta)
        self._print(f"Xong ({report['status']}). Đã tiêu {report['cost']['total_usd']:.4f} USD. "
                    f"Kết quả: {self.options.out}")

    def _write_json(self, name: str, data: Any) -> None:
        self.options.out.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, ensure_ascii=False, indent=1, default=str)
        (self.options.out / name).write_text(text + "\n", encoding="utf-8", newline="\n")

    def _meta(self, status: str) -> dict[str, Any]:
        path = self.options.scenario_path
        return {
            "bench": "run", "label": self.options.label, "started": self.started,
            "finished": datetime.now().astimezone().isoformat(timespec="seconds"),
            "status": status, "exit_code": self.exit_code if status != "running" else None,
            "stop": self.stop, "dry_run": self.options.dry_run, "git": git_state(),
            "story_id": self.store.story_id, "seed": self.seed,
            "budget_usd": self.options.budget_usd, "chapters_arg": self.options.chapters,
            "scenario": {"path": repo_path(path) if path else None, "sha256": self.scenario_sha,
                         "content": self.scenario.model_dump(mode="json", by_alias=True)},
            "config": {"dir": repo_path(self.options.config_dir),
                       "sha256": config_sha256(self.options.config_dir)},
            "models": models_in_use(self.config, self.scenario),
            "max_tokens_per_call": self.scenario.max_tokens_per_call,
            "prompt_versions": {
                "setup": setup_mod.PROMPT_VERSION, "outline": scene_mod.OUTLINE_PROMPT_VERSION,
                "writer": scene_mod.WRITER_PROMPT_VERSION, "extract": extract_mod.PROMPT_VERSION,
                "choices": choices_mod.PROMPT_VERSION,
            },
            "style_guide_sha256": _sha256(self.style_guide.encode()),
            "cost_limits": self.config.limits.cost_usd.model_dump(),
        }


# --- báo cáo ---------------------------------------------------------------------------------


def _usd(x: float) -> float:
    return round(x, 6)


def build_report(run: StoryRun) -> dict[str, Any]:
    """Số đếm và chi phí: không chữ của truyện, không id nút."""
    by_role: dict[str, float] = defaultdict(float)
    by_chapter: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_attempt: dict[tuple[int, int], float] = defaultdict(float)
    by_scene: dict[tuple[int, int, int], float] = defaultdict(float)
    calls_by_role: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    tokens: dict[str, dict[str, int]] = defaultdict(lambda: {"prompt": 0, "completion": 0})
    estimated = 0.0
    for c in run.calls:
        usd = c.get("cost_usd") or 0.0
        estimated += c.get("cost_estimated_usd") or 0.0
        role, chapter = c["role"], c["chapter"]
        by_role[role] += usd
        by_chapter[str(chapter)][role] += usd
        by_chapter[str(chapter)]["total"] += usd
        if chapter > 0:
            by_attempt[(chapter, c["attempt"])] += usd
        if c.get("scene") is not None and chapter > 0:
            by_scene[(chapter, c["attempt"], c["scene"])] += usd
        calls_by_role[role] += 1
        statuses[c["status"]] += 1
        tokens[role]["prompt"] += c.get("prompt_tokens") or 0
        tokens[role]["completion"] += c.get("completion_tokens") or 0

    found: Counter[str] = Counter()
    blocking: Counter[str] = Counter()
    left: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    for a in run.attempts:
        for r in a["reviews"]:
            found.update(r["issues"])
            blocking.update(r["blocking"])
            rejected.update(r["rejected_by_reason"])
        for s in a["scenes"]:
            left.update(s["left_when_shown"])
    committed = [n for n in run.packages if n > 0]
    status = "done" if run.stop is None else run.stop["kind"]
    return {
        "status": status, "stop": run.stop,
        "chapters_planned": run.plan.total_chapters if run.plan else None,
        "chapters_target": run.target, "chapters_clamped": run.clamped,
        "chapters_committed": len(committed),
        "cost": {
            "total_usd": _usd(sum(by_role.values())),
            "estimated_unbilled_usd": _usd(estimated),
            "by_role": {k: _usd(v) for k, v in sorted(by_role.items())},
            "by_chapter": {k: {r: _usd(x) for r, x in sorted(v.items())}
                           for k, v in sorted(by_chapter.items(), key=lambda kv: int(kv[0]))},
            "max_chapter_attempt_usd": _usd(max(by_attempt.values(), default=0.0)),
            "max_scene_usd": _usd(max(by_scene.values(), default=0.0)),
            "scenes": [{"chapter": ch, "attempt": at, "scene": sc, "usd": _usd(v)}
                       for (ch, at, sc), v in sorted(by_scene.items())],
            "limits": run.config.limits.cost_usd.model_dump(),
        },
        "calls": {"total": len(run.calls), "by_role": dict(sorted(calls_by_role.items())),
                  "by_status": dict(sorted(statuses.items()))},
        "tokens": dict(sorted(tokens.items())),
        "issues": {"found": dict(sorted(found.items())),
                   "blocking_found": dict(sorted(blocking.items())),
                   "left_when_shown": dict(sorted(left.items()))},
        "rewrites": sum(a["rewrites"] for a in run.attempts),
        "scenes_blocked": sum(1 for a in run.attempts if a["blocked_scene"]),
        "rejected_edges": {"total": sum(rejected.values()), "by_reason": dict(sorted(rejected.items()))},
        "player_retries_used": dict(run.retries_used),
        "chapters": run.attempts,
    }


def _fmt_counts(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{k} ×{v}" for k, v in counts.items()) or "—"


def build_summary(meta: dict[str, Any], report: dict[str, Any]) -> str:
    models = meta["models"]

    def model(role: str) -> str:
        info = models[role]
        effort = f", suy luận {info['reasoning']}" if info.get("reasoning") else ""
        return f"{role} `{info['model']}`{effort}"

    stop, cost, limits = report["stop"], report["cost"], report["cost"]["limits"]
    git = meta["git"]
    dirty = " (có sửa chưa commit)" if git.get("dirty") else ""
    scenario = meta["scenario"]
    clamped = "; `--chapters` vượt kế hoạch nên dừng ở chương cuối" if report["chapters_clamped"] \
        else ""
    stopped = f"{stop['kind']} ở {stop['where']} ({stop['code']})" if stop else "không, chạy hết"
    lines = [
        f"# Chạy cả truyện: {meta['label'] or meta['story_id']}",
        "",
        (f"- Commit `{git['commit']}`{dirty}; đề v{scenario['content']['version']} "
         f"(`{scenario['sha256'][:12]}`); config `{meta['config']['sha256']['combined'][:12]}`; "
         f"seed {meta['seed']}; dry-run: {'có' if meta['dry_run'] else 'không'}."),
        "- Model: " + "; ".join(model(r) for r in RUN_ROLES) + ".",
        (f"- Chương đã ghi: {report['chapters_committed']}/{report['chapters_target']} "
         f"(kế hoạch {report['chapters_planned']}){clamped}."),
        f"- Dừng: {stopped}.",
        (f"- Chi phí: {cost['total_usd']:.4f} USD (trần --budget: {meta['budget_usd']}); ước tính "
         f"cho lời gọi không rõ chi phí: {cost['estimated_unbilled_usd']:.4f} USD."),
        (f"- Trần config (USD): cảnh {limits['per_scene']}, chương {limits['per_chapter']}, "
         f"truyện {limits['per_story']}. Cảnh đắt nhất {cost['max_scene_usd']:.4f}, lượt chương "
         f"đắt nhất {cost['max_chapter_attempt_usd']:.4f}."),
        (f"- Viết lại: {report['rewrites']}; cảnh bị chặn: {report['scenes_blocked']}; tự bấm thử "
         f"lại: {_fmt_counts(report['player_retries_used'])}."),
        (f"- Lỗi tìm thấy: {_fmt_counts(report['issues']['found'])}. Còn lại khi hiện: "
         f"{_fmt_counts(report['issues']['left_when_shown'])}."),
        (f"- Cạnh bộ trích bỏ: {report['rejected_edges']['total']} "
         f"({_fmt_counts(report['rejected_edges']['by_reason'])})."),
        "",
        "## Chi phí theo vai",
        "",
        "| Vai | Lời gọi | USD | Token vào | Token ra |",
        "|---|---|---|---|---|",
    ]
    for role, usd in cost["by_role"].items():
        t = report["tokens"].get(role, {"prompt": 0, "completion": 0})
        lines.append(f"| {role} | {report['calls']['by_role'].get(role, 0)} | {usd:.5f} "
                     f"| {t['prompt']} | {t['completion']} |")
    roles = ("setup", "outline", "writer", "extract", "choices")
    lines += ["", "## Chi phí theo chương (USD, mọi lượt)", "",
              "| Chương | " + " | ".join(roles) + " | Tổng |",
              "|---|" + "---|" * (len(roles) + 1)]
    for chapter, parts in cost["by_chapter"].items():
        cells = " | ".join(f"{parts.get(r, 0.0):.5f}" for r in roles)
        lines.append(f"| {chapter} | {cells} | {parts.get('total', 0.0):.5f} |")
    lines += ["", "## Từng lượt chương", "",
              "| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |",
              "|---|---|---|---|---|---|---|---|"]
    for a in report["chapters"]:
        issues = Counter(k for r in a["reviews"] for k in r["issues"])
        lines.append(
            f"| {a['chapter']} | {a['attempt']} | {'có' if a['committed'] else 'không'} "
            f"| {len(a['scenes'])} | {a['rewrites']} | {_fmt_counts(issues)} "
            f"| {sum(r['rejected'] for r in a['reviews'])} | {a['error'] or '—'} |")
    return "\n".join(lines) + "\n"


# --- model giả cho --dry-run ------------------------------------------------------------------

DRY_RUN_COST_USD = 0.0001
DRY_RUN_NPC = "mac_van_ha"
DRY_RUN_NPC_NAME = "Mạc Vân Hà"
DRY_RUN_HIDDEN_NAME = "Hạ Trần"  # nhân vật có thật trong đồ thị, chưa từng hé lộ
DRY_RUN_SECRET_TEXT = "Hạ Trần là nội gián của Huyết Ảnh Các trong tông môn"
_DRY_QUOTE = (f"Đó là {DRY_RUN_NPC_NAME}, người duy nhất trong tông môn chịu chỉ cho tôi vài thế "
              "kiếm cơ bản.")
# Một cảnh tu tiên viết tay, qua được kiểm văn với ngưỡng của config hiện hành, kể cả ngôi kể
# (`quality.narration.person: first`, D-51). Nhân vật chính chỉ xưng "tôi", nên cảnh không phụ thuộc
# tên nhân vật được chọn.
DRY_RUN_SCENE = f"""Sương sớm còn phủ kín bậc đá dẫn lên lưng núi khi tôi ôm bó củi đi qua sân \
luyện kiếm. Tiếng chuông trên đỉnh vừa dứt, đám đệ tử ngoại môn đã đứng thành hàng chờ điểm danh, \
ai nấy cúi đầu tránh ánh nhìn của vị chấp sự mặt lạnh.

Tôi đặt bó củi xuống cạnh giếng, phủi lớp tro bám trên tay áo. Từ hành lang phía đông, một nữ đệ \
tử áo xanh bước tới, tay cầm thanh trúc kiếm còn ướt sương. {_DRY_QUOTE}

- Đêm qua đệ lại lên vách đá phía sau núi phải không? - nàng hỏi, giọng nhỏ nhưng sắc.

- Đệ chỉ đi nhặt củi, sư tỷ.

- Củi không mọc trên vách đá. Lần sau mà để chấp sự bắt gặp, ta cũng không đỡ cho đệ được nữa.

Tôi không đáp. Miếng ngọc bội trong ngực áo vẫn còn hơi ấm, thứ hơi ấm kỳ lạ mà tôi chưa từng kể \
với ai. Mấy đêm nay, mỗi lần tôi ngồi thiền gần vách đá, linh khí quanh người lại tụ về nhanh hơn \
hẳn, như có dòng suối ngầm chảy dưới chân.

Nàng nhìn tôi một lúc lâu rồi thở dài, rút từ tay áo ra một gói giấy dầu, đặt vào tay tôi.

- Đan dược bổ khí, phần của ta tháng này. Đệ cầm lấy mà dùng, đừng để linh lực cạn rồi lại ngất \
giữa buổi tập.

- Sư tỷ không cần à?

- Ta sắp vào nội môn, ở đó không thiếu thứ này. - Nàng quay đi, rồi dừng lại nửa bước. - Còn nữa, \
mấy hôm nay có kẻ lạ mặt dò hỏi về đệ ở chân núi. Đi đâu cũng nhớ mang theo kiếm.

Tôi nắm chặt gói giấy, cảm thấy mép giấy cứa vào lòng bàn tay. Người ngoài tìm tới một đệ tử ngoại \
môn vô danh thì chỉ có một lý do, và lý do ấy đang nằm yên sát ngực tôi.

Khi tiếng điểm danh vang lên lần thứ hai, tôi chạy vội về hàng. Phía trên bậc đá, vị chấp sự mặt \
lạnh đã ghi tên tôi vào sổ phạt, nét bút dài và chậm như cố ý cho cả sân cùng thấy."""

_DRY_SETTINGS = [
    {"title": "Tông môn trên mây",
     "intro": "Một tông môn nhỏ bám vào sườn núi quanh năm mây phủ, sống nhờ một mạch linh khí "
              "đang cạn dần. Các đại tông môn quanh vùng đã gửi thư đòi chia linh mạch. Nhân vật "
              "chính là đệ tử ngoại môn vừa nhặt được một vật lạ dưới vách đá sau núi."},
    {"title": "Thành chợ đêm",
     "intro": "Một tòa thành buôn bán pháp khí chỉ mở cửa khi trăng lên. Mỗi đêm có kẻ giàu lên và "
              "có kẻ biến mất. Nhân vật chính làm thuê cho một tiệm luyện đan và vừa nhận một đơn "
              "hàng không ai dám nhận."},
    {"title": "Đảo lưu đày",
     "intro": "Một hòn đảo giữa biển sương nơi các tông môn đày tội đồ. Linh khí ở đây hỗn loạn, "
              "ai tu luyện sai cách sẽ hoá điên. Nhân vật chính bị đưa tới đảo vì một tội mình "
              "không gây ra."},
]
_DRY_PLOTS = [
    {"title": "Tranh đoạt linh mạch",
     "summary": "Tông môn sắp phải giao một nửa linh mạch cho đại tông môn láng giềng. Nhân vật "
                "chính muốn giữ chỗ đứng của mình trong tông môn. Trở ngại là cảnh giới thấp và "
                "những kẻ muốn đẩy hắn ra làm con tốt."},
    {"title": "Vật lạ dưới vách đá",
     "summary": "Vật nhân vật chính nhặt được khiến linh khí tụ về quanh hắn. Hắn muốn biết nó là "
                "gì trước khi người khác phát hiện. Trở ngại là luật tông môn cấm giấu bảo vật."},
    {"title": "Kỳ khảo hạch nội môn",
     "summary": "Ba tháng nữa là kỳ khảo hạch chọn đệ tử vào nội môn. Nhân vật chính muốn vượt qua "
                "để đổi đời. Trở ngại là đối thủ có chỗ dựa và một vết thương cũ chưa lành."},
]
_DRY_CHARACTERS = [
    {"name": "Lục Trầm", "personality": "Ít nói, nhẫn nại, ghi nhớ từng món nợ.",
     "backstory": "Mồ côi từ nhỏ, được một trưởng lão nhặt về làm tạp dịch rồi thành đệ tử ngoại "
                  "môn. Chưa từng rời núi quá ba ngày."},
    {"name": "Tô Vãn Ngưng", "personality": "Lanh lợi, liều lĩnh, ghét bị coi thường.",
     "backstory": "Con gái một thương nhân sa sút, tự đến xin nhập môn. Mang theo một món nợ "
                  "của gia đình."},
    {"name": "Cố Trường Phong", "personality": "Điềm tĩnh, thích quan sát trước khi ra tay.",
     "backstory": "Từng là thư đồng của một gia tộc tu tiên đã bị diệt. Giấu kín xuất thân khi "
                  "vào tông môn."},
]


def _acts(total: int) -> list[dict[str, Any]]:
    names = ("mở đầu", "phát triển", "cao trào", "kết")
    parts = min(len(names), total)
    bounds = [round(i * total / parts) for i in range(parts + 1)]
    return [{"name": names[i] if parts == len(names) else f"hồi {i + 1}",
             "from_chapter": bounds[i] + 1, "to_chapter": bounds[i + 1]} for i in range(parts)]


def dry_run_world(total: int) -> dict[str, Any]:
    """Bản kế hoạch + thế giới chương 0 hợp lệ cho `total` chương (BuildOutput)."""

    def named(id_, name, aliases, description):
        return {"id": id_, "name": name, "aliases": aliases, "description": description}

    def edge(t, s, d, kind=None, score=None):
        return {"type": t, "source": s, "target": d, "kind": kind, "score": score}

    last = total
    return {
        "acts": _acts(total),
        "characters": [
            {"id": DRY_RUN_NPC, "name": DRY_RUN_NPC_NAME, "aliases": ["Mạc sư tỷ"],
             "personality": "Thẳng thắn, che chở người dưới.",
             "backstory": "Đệ tử ngoại môn giỏi kiếm nhất, sắp được vào nội môn."},
            {"id": "ha_tran", "name": DRY_RUN_HIDDEN_NAME, "aliases": ["Hạ trưởng lão"],
             "personality": "Ôn hoà, kín kẽ.", "backstory": "Trưởng lão coi sổ sách của tông môn."},
        ],
        "locations": [named("thanh_van_tong", "Thanh Vân Tông", [], "Tông môn nhỏ trên núi mây.")],
        "factions": [named("huyet_anh_cac", "Huyết Ảnh Các", [], "Tổ chức sát thủ trong bóng tối.")],
        "items": [named("ngoc_boi", "ngọc bội Huyền Băng", ["miếng ngọc bội"],
                        "Ngọc bội lạnh như băng nhưng ấm khi gần linh mạch.")],
        "facts": [
            {"id": "f_ha_tran_noi_gian", "text": DRY_RUN_SECRET_TEXT,
             "about": ["ha_tran", "huyet_anh_cac"], "known_by": ["ha_tran"]},
            {"id": "f_ngoc_boi_linh_mach", "text": "Ngọc bội Huyền Băng dẫn được tới mạch linh khí "
             "chính của núi", "about": ["ngoc_boi"], "known_by": ["ha_tran"]},
        ],
        "edges": [
            edge("RELATES_TO", "protagonist", DRY_RUN_NPC, "sư tỷ", 60),
            edge("RELATES_TO", DRY_RUN_NPC, "protagonist", "sư đệ", 50),
            edge("HOLDS", "protagonist", "ngoc_boi"),
            edge("LOCATED_AT", "protagonist", "thanh_van_tong"),
            edge("LOCATED_AT", DRY_RUN_NPC, "thanh_van_tong"),
            edge("LOCATED_AT", "ha_tran", "thanh_van_tong"),
            edge("MEMBER_OF", "ha_tran", "huyet_anh_cac"),
        ],
        "threads": [{"id": "t_ngoc_boi", "description": "Bí ẩn của miếng ngọc bội",
                     "due_from_chapter": max(1, last - 1), "due_to_chapter": last,
                     "must_resolve": True}],
        "secrets": [{"fact_id": "f_ha_tran_noi_gian", "reveal_from_chapter": last,
                     "reveal_to_chapter": last,
                     "leak_terms": [[DRY_RUN_HIDDEN_NAME, "nội gián"],
                                    ["Hạ trưởng lão", "Huyết Ảnh Các"]]}],
    }


_EDGE_NULLS = {"kind": None, "score": None, "how": None, "told_by": None, "quote": None,
               "known_as": None, "role": None}


class DryRunLLM(FakeLLM):
    """--dry-run: model giả trả câu ghi sẵn theo vai (nhận ra qua schema JSON), đủ hợp lệ để đi hết
    đường: 3 lựa chọn mỗi bước khởi tạo, thế giới `dry_run_world`, dàn ý, một cảnh viết tay, bộ trích
    hé lộ `DRY_RUN_NPC` ở lần đầu nhân vật này xuất hiện, 3 lựa chọn dùng mã trong sổ tay.
    Không mạng, không key."""

    def __init__(self, total_chapters: int, *, cost_usd: float | None = DRY_RUN_COST_USD) -> None:
        super().__init__([], cost_usd=cost_usd)
        self.total = total_chapters

    def reply(self, schema_name: str | None, text: str) -> str:
        """`text`: nội dung tin nhắn user cuối của lời gọi."""
        if schema_name is None:
            return DRY_RUN_SCENE
        replies: dict[str, Callable[[], Any]] = {
            SettingsOutput.__name__: lambda: {"options": _DRY_SETTINGS},
            PlotsOutput.__name__: lambda: {"options": _DRY_PLOTS},
            CharactersOutput.__name__: lambda: {"options": _DRY_CHARACTERS},
            BuildOutput.__name__: lambda: dry_run_world(self.total),
            SceneOutline.__name__: lambda: {
                "goal": "Sư tỷ nhắc nhở hắn và báo tin có người lạ dò hỏi",
                "present": ["protagonist", DRY_RUN_NPC],
                "beats": ["Hắn về sân sau một đêm ngồi thiền", "Sư tỷ hỏi chuyện vách đá",
                          "Sư tỷ đưa đan dược và dặn mang kiếm"],
                "ends_at": "Hắn bị ghi tên vào sổ phạt",
            },
            ExtractOutput.__name__: lambda: self._extract(text),
            ChoicesOutput.__name__: lambda: self._choices(text),
        }
        return json.dumps(replies[schema_name](), ensure_ascii=False)

    @staticmethod
    def _extract(text: str) -> dict[str, Any]:
        chapter_id = re.search(r"id nút chương: (ch\d+)", text)
        revealed = f"| REVEALED_TO_PLAYER | {DRY_RUN_NPC} →" in text
        edges = [] if revealed or chapter_id is None else [_EDGE_NULLS | {
            "type": "REVEALED_TO_PLAYER", "source": DRY_RUN_NPC, "target": chapter_id.group(1),
            "quote": _DRY_QUOTE, "known_as": DRY_RUN_NPC_NAME,
        }]
        return {"edges": edges, "close": []}

    @staticmethod
    def _choices(text: str) -> dict[str, Any]:
        people = re.findall(r"\[(m\d+)\] Nhân vật: ", text)
        who = people[:1]
        return {"choices": [
            {"kind": "action", "text": "Lén quay lại vách đá sau núi khi trời tối.", "tone": None,
             "lie_content": None, "listeners": [], "about": [], "feeling": None},
            {"kind": "dialogue", "text": "Kể thật với sư tỷ về hơi ấm của miếng ngọc bội.",
             "tone": "truth", "lie_content": None, "listeners": who, "about": who,
             "feeling": None},
            {"kind": "inner", "text": "Thầm hứa sẽ không để sư tỷ bị liên luỵ.", "tone": None,
             "lie_content": None, "listeners": [], "about": who, "feeling": "áy náy"},
        ]}

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        self.calls.append(list(messages))
        self.extras.append(extra)
        if response_schema is not None:
            self.schemas.append(response_schema)
        text = self.reply(response_schema.__name__ if response_schema else None,
                          messages[-1].content)
        chars = sum(len(m.content) for m in messages)
        usage = Usage(prompt_tokens=math.ceil(chars / EST_CHARS_PER_TOKEN),
                      completion_tokens=math.ceil(len(text) / EST_CHARS_PER_TOKEN),
                      cost_usd=self._cost_usd)
        return ChatResult(text=text, usage=usage, model=model, finish_reason="stop")


# --- dòng lệnh --------------------------------------------------------------------------------


class RunServices(BaseSettings):
    """Kết nối Neo4j + Postgres. Chỉ đọc bốn biến này, không đọc key nào."""

    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)  # G7
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr
    postgres_dsn: SecretStr


def openrouter_client(env_file: Path, *, http: httpx.AsyncClient | None = None) -> LLMClient:
    """Client thật, key của chủ dự án: chỉ OPENROUTER_API_KEY (biến môi trường hoặc `env_file`)."""
    from writory.llm.openrouter import OpenRouterClient

    keys = load_keys(env_file, ["openrouter"])
    assert keys.openrouter_api_key is not None
    return OpenRouterClient(keys.openrouter_api_key, http=http)


def resolve_out(args: argparse.Namespace) -> tuple[Path, str]:
    if args.out:
        out = Path(args.out)
        return out, args.label or out.name
    label = args.label
    if not label:
        raise ConfigError("cần --label (thư mục mới) hoặc --out")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", label):
        raise ConfigError(f"--label chỉ gồm a-z, 0-9, '-': {label!r}")
    suffix = "-dryrun" if args.dry_run else ""
    return RESULTS_DIR / f"{date.today().isoformat()}-run-{label}{suffix}", label


def _story_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")[:40] or "run"
    return f"run-{date.today():%Y%m%d}-{slug}-{uuid.uuid4().hex[:8]}"


async def _cli(args: argparse.Namespace) -> int:
    scenario_path = Path(args.scenario)
    scenario, scenario_sha = load_scenario(scenario_path)
    config_dir = Path(args.config_dir)
    config = load_config(config_dir)
    problems = run_problems(config, scenario)
    if problems:  # trước khi kết nối kho hay đọc key
        raise ConfigError("config hoặc đề chưa đủ để chạy:\n- " + "\n- ".join(problems))
    if args.budget is None and not args.dry_run:
        raise ConfigError("lượt chạy thật cần --budget (USD)")
    out, label = resolve_out(args)
    if (out / "meta.json").exists():
        raise ConfigError(f"{out} đã có kết quả; dùng nhãn khác")

    import psycopg
    from neo4j import GraphDatabase
    from neo4j.exceptions import DriverError, Neo4jError

    from writory.db import migrate
    from writory.graph import ensure_schema

    env_file = Path(args.env_file)
    try:
        services = RunServices(_env_file=env_file if env_file.exists() else None)  # type: ignore[call-arg]
    except ValidationError as e:
        missing = sorted({str(err["loc"][0]).upper() for err in e.errors()})
        raise ConfigError(f"thiếu {', '.join(missing)} (biến môi trường hoặc {env_file})") from None
    http: httpx.AsyncClient | None = None
    if args.dry_run:
        total = config.story_lengths.levels[scenario.length_level].chapters.min
        llm: LLMClient = DryRunLLM(total)
    else:
        http = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        llm = openrouter_client(env_file, http=http)
    try:
        conn = psycopg.connect(services.postgres_dsn.get_secret_value(), autocommit=True)
    except psycopg.Error as e:
        raise ConfigError(f"không kết nối được Postgres: {redact(str(e))}") from None
    driver = GraphDatabase.driver(
        services.neo4j_uri,
        auth=(services.neo4j_user, services.neo4j_password.get_secret_value()))
    try:
        try:
            driver.verify_connectivity()
            ensure_schema(driver)
        except (DriverError, Neo4jError) as e:
            raise ConfigError(f"không kết nối được Neo4j: {redact(str(e))}") from None
        migrate(conn)
        store = GraphRunStore(conn, driver, _story_id(label))
        run = StoryRun(
            scenario, scenario_sha, config, llm=llm, store=store,
            options=RunOptions(out=out, budget_usd=args.budget, chapters=args.chapters,
                               seed=args.seed, dry_run=args.dry_run,
                               keep_story=args.keep_story or not args.dry_run, label=label,
                               config_dir=config_dir, scenario_path=scenario_path),
        )
        return await run.run()
    finally:
        driver.close()
        conn.close()
        if http is not None:
            await http.aclose()


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m writory.pipeline.bench_run",
                                description="Chạy cả một truyện (docs/eval.md, D-42).")
    p.add_argument("--scenario", default=str(DEFAULT_SCENARIO), help="file đề YAML")
    p.add_argument("--label", help="tạo evals/results/<ngày>-run-<nhãn>/")
    p.add_argument("--out", help="thư mục kết quả (mới)")
    p.add_argument("--budget", type=float, help="trần USD cho cả lần chạy; bắt buộc khi chạy thật")
    p.add_argument("--chapters", type=int, help="số chương tối đa (mặc định: số chương kế hoạch)")
    p.add_argument("--seed", type=int, help="ghi đè seed của đề")
    p.add_argument("--dry-run", action="store_true", help="model giả, không key, không gọi model")
    p.add_argument("--keep-story", action="store_true",
                   help="dry-run: giữ truyện trong Neo4j + Postgres (chạy thật luôn giữ)")
    p.add_argument("--config-dir", default=str(REPO_CONFIG_DIR))
    p.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.chapters is not None and args.chapters < 1:
        print("Lỗi: --chapters phải >= 1", file=sys.stderr)
        return EXIT_CONFIG
    if args.budget is not None and args.budget <= 0:
        print("Lỗi: --budget phải > 0", file=sys.stderr)
        return EXIT_CONFIG
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    install_log_redaction(root)
    try:
        return asyncio.run(_cli(args))
    except ConfigError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
