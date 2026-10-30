"""Bài đo A: bộ nhớ, hỏi đáp trên truyện cố định, sáu hệ trả lời cạnh tranh (design §9 A;
docs/eval.md "Bài A"; D-72, D-73, D-81, D-83).

Cùng một bộ câu hỏi khai trước trên một truyện cố định: truyện mẫu 5 chương
(evals/scenarios/memory/questions.yaml), hoặc truyện do pipeline viết mà file đề trỏ tới bằng
`run_dir` (chọn bằng --questions-file; D-83). Mỗi câu hỏi "sau khi đã đọc tới hết chương N"; các hệ
khác nhau ở bộ nhớ đưa cho CÙNG một model trả
lời (vai `narrator` của config/models.yaml): đồ thị WriTory, đồ thị + câu trích, không bộ nhớ, tóm
tắt từng chương, RAG BM25, nhét cả truyện (`pipeline.bench_a_systems`). Chấm bằng code
(`pipeline.bench_a_data`), không giám khảo LLM. Chi phí ghi theo từng hệ, gồm cả chi phí dựng bộ
nhớ (tóm tắt của hệ "tóm tắt"). Hệ tuỳ chọn (`graph_quotes`) bật/tắt trong run.yaml.

Hai hệ đồ thị đọc đồ thị CHỈ qua `GraphState` của lớp graph/ (G10): chạy thật qua `Neo4jState` (nạp
truyện mẫu, hoặc các gói chương của lượt chạy pipeline, vào Neo4j, `story_id` riêng), chạy khô qua
`OverlayState` (cùng nghĩa "ở chương N"; test so hai nền: tests/graph/test_bench_a_graph_parity.py).

Hai hệ người kể (`narrator`, `narrator_pages`; `pipeline.bench_a_narrator`, D-143) chỉ chạy khi nêu
tên ở `--systems`: chúng hỏi đúng đường người kể của sản phẩm (đề narrator-3 và narrator-4), không
dùng model trả lời chung, và chỉ trên truyện do pipeline viết.

Trần: `--budget` (OpenRouter), USD, tính cả các lần chạy trước trong cùng thư mục. Trước mỗi lời gọi
giữ chỗ chi phí tối đa (`bench_run.BudgetedClient`, `bench_d.Budget`). Key: chỉ OPENROUTER_API_KEY
(`bench_d.load_keys`); không in, không ghi (G7). `--dry-run`: model giả, không key, không mạng.
"""

import argparse
import asyncio
import hashlib
import html
import json
import logging
import math
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict

from writory.config import REPO_CONFIG_DIR, REPO_ROOT, AppConfig, ConfigError, LimitNotSetError
from writory.config import load_config as load_app_config
from writory.errors import ErrorCode, WritoryError
from writory.guard.state import GraphState
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
from writory.llm.retry import with_json_retries
from writory.pipeline import bench_a_narrator as narr
from writory.pipeline.bench_a_data import (
    DATA_DIR,
    DISTANCE_BINS,
    GROUP_LABEL,
    GROUPS,
    BenchData,
    Question,
    RunFile,
    context_supports,
    distance_bin,
    load_data,
    null_answer,
    oracle_answer,
    score_answer,
    wrong_answer,
)
from writory.pipeline.bench_a_systems import (
    GRAPH_STYLES,
    SYSTEM_LABELS,
    SYSTEMS,
    Context,
    build_graph_context,
    context_full,
    context_graph_quotes,
    context_none,
    context_rag,
    context_rolling,
)
from writory.pipeline.bench_e import TYPICAL_NARRATOR_OUTPUT_TOKENS
from writory.pipeline.bench_run import BudgetedClient, StepTracker
from writory.pipeline.narrator import BlockReason, NarratorOutput
from writory.pipeline.summary import SummaryOutput, summarize_chapter
from writory.quality.bench_d import (
    EST_CHARS_PER_TOKEN,
    FATAL,
    Budget,
    Store,
    _now,
    git_state,
    load_keys,
)
from writory.safety.redact import install_log_redaction, redact
from writory.safety.wrap import DATA_NOTICE, UserAuthored, system_message, user_message

RESULTS_DIR = REPO_ROOT / "evals" / "results"
STORY_ID = "bench-a-sample"  # story_id trên Neo4j của truyện mẫu
RUN_STORY_ID = "bench-a-run"  # story_id trên Neo4j của truyện do pipeline viết (D-83)
SystemName = Literal["graph", "graph_quotes", "none", "rolling", "rag", "full", "narrator",
                     "narrator_pages"]
# Sáu hệ bộ nhớ cộng hai hệ người kể (chỉ chạy khi nêu tên, D-143).
ALL_SYSTEMS = (*SYSTEMS, *narr.NARRATOR_SYSTEMS)
LABELS = SYSTEM_LABELS | narr.NARRATOR_LABELS

ANSWER_PROMPT_VERSION = "a-answer-1"  # đổi chữ prompt thì tăng số: kết quả cũ không còn so được
EXIT_OK, EXIT_CONFIG, EXIT_BUDGET, EXIT_ABORT = 0, 1, 2, 3
RESULTS, ERRORS, SUMMARIES = "results.jsonl", "errors.jsonl", "summaries.jsonl"
MEMORY_LABEL = "story_memory"
ABSTAIN_REPLY = "Không biết"

DRY_RUN_COST_USD = 0.0001
# Ước tính thô cho lệnh `plan`, chưa đo: token ra mỗi câu trả lời (gồm suy luận mức thấp) và mỗi
# bản tóm tắt. Chi phí thật lấy từ usage.
TYPICAL_ANSWER_OUTPUT_TOKENS = 300
TYPICAL_SUMMARY_OUTPUT_TOKENS = 500


# --- lời gọi trả lời ---------------------------------------------------------------------------------


class AnswerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str


ANSWER_SYSTEM = f"""Bạn trả lời câu hỏi về một truyện đã đọc, CHỈ dựa vào phần tư liệu dưới đây.

Quy tắc:
- Tư liệu có thể là văn bản các chương, bản tóm tắt, các đoạn trích hoặc ghi chú trí nhớ có cấu trúc. Dùng đúng những gì tư liệu nói.
- Không dùng điều không có trong tư liệu. Tư liệu không đủ để trả lời thì trả đúng "{ABSTAIN_REPLY}".
- Trả lời ngắn nhất có thể, đúng dạng câu hỏi yêu cầu, không giải thích.
- "Hiện tại" và "cuối chương N" nghĩa là trạng thái ở cuối chương được hỏi, không phải về sau.

Trả về JSON đúng schema: `answer` là câu trả lời."""

ANSWER_FORMAT = {
    "entities": "Chỉ nêu tên, cách nhau dấu phẩy.",
    "bool": 'Chỉ trả lời "Có" hoặc "Không".',
    "choice": "Chỉ trả lời đúng một lựa chọn.",
    "text": "Trả lời bằng một câu ngắn.",
}


def answer_messages(q: Question, ctx: Context) -> list[Message]:
    return [
        system_message(ANSWER_SYSTEM, DATA_NOTICE),
        user_message(
            f"Bạn đã đọc truyện tới hết chương {q.ask_chapter}. Tư liệu:",
            UserAuthored(ctx.text, MEMORY_LABEL),
            f"Câu hỏi: {q.question}",
            ANSWER_FORMAT[q.answer.type],
        ),
    ]


_FAKE_BLOCK = re.compile(r'<player_data source="' + MEMORY_LABEL + r'">\n(.*)\n</player_data>',
                         re.DOTALL)
_FAKE_QUESTION = re.compile(r"Câu hỏi: (.*)\n", re.MULTILINE)
_FAKE_CHAPTER = re.compile(r"tới hết chương (\d+)")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeAnswerer(LLMClient):
    """Model giả cho `--dry-run` và test. Không đoán: biết câu hỏi nào đang hỏi (qua chữ và chương)
    và ngữ cảnh nào đã được dựng (qua `register`).

    - oracle: đáp án gốc nếu ngữ cảnh ĐỦ chứng cứ (`context_supports`), còn không thì "Không biết".
      Nên 100% ở hệ nhét cả truyện, và ở hai hệ đồ thị trên truyện mẫu (đồ thị dựng tay), chứng tỏ
      các hệ đó dựng đúng ngữ cảnh; các hệ khác, và hệ đồ thị trên truyện do pipeline viết (đồ thị
      do bộ trích dựng, D-83), cho biết trần của chúng nếu model đọc hoàn hảo.
    - null: luôn "Không biết". - wrong: luôn một câu sai (không phải kiêng cữ).
    Tóm tắt (SummaryOutput) trả một câu giả không chứa gì của chương. Người kể (NarratorOutput):
    `bench_a_narrator.fake_reply`, cùng ba chế độ, đủ chứng cứ khi câu trích nằm trong sổ tay hay
    đoạn trên trang nó nhận.
    """

    def __init__(self, data: BenchData, mode: Literal["oracle", "null", "wrong"] = "oracle") -> None:
        self._data, self._mode = data, mode
        self._by_text: dict[str, Context] = {}
        self._names = data.state_at(max(data.chapters)).named_nodes()
        self.calls: list[list[Message]] = []

    def register(self, ctx: Context) -> None:
        self._by_text[_sha(ctx.text)] = ctx

    def _lookup(self, messages: Sequence[Message]) -> tuple[Question, Context | None]:
        user = next(m.content for m in reversed(messages) if m.role == "user")
        chapter = int(_FAKE_CHAPTER.search(user).group(1))  # type: ignore[union-attr]
        text = _FAKE_QUESTION.findall(user)[-1]
        block = html.unescape(_FAKE_BLOCK.search(user).group(1))  # type: ignore[union-attr]
        q = next(x for x in self._data.questions.questions
                 if x.ask_chapter == chapter and x.question == text)
        return q, self._by_text.get(_sha(block))

    async def chat(
        self, model: str, messages: list[Message], *,
        response_schema: type[BaseModel] | None = None, extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        self.calls.append(list(messages))
        if response_schema is SummaryOutput:
            number = re.search(r"Chương (\d+)", messages[-1].content)
            body = {"summary": f"Tóm tắt giả của chương {number.group(1) if number else '?'}."}
        elif response_schema is NarratorOutput:  # hai hệ người kể (D-143)
            body = narr.fake_reply(self._data, messages, self._mode, self._names)
        else:
            q, ctx = self._lookup(messages)
            if self._mode == "null" or (self._mode == "oracle" and (
                    ctx is None or not context_supports(q, ctx, self._data))):
                reply = null_answer(q)
            elif self._mode == "wrong":
                reply = wrong_answer(q, self._names)
            else:
                reply = oracle_answer(q, self._names)
            body = {"answer": reply}
        return ChatResult(text=json.dumps(body, ensure_ascii=False),
                          usage=Usage(prompt_tokens=1, completion_tokens=1,
                                      cost_usd=DRY_RUN_COST_USD),
                          model=model, finish_reason="stop")

    async def stream(self, model: str, messages: list[Message]) -> Any:
        raise NotImplementedError("bài A không dùng stream")
        yield StreamEvent  # pragma: no cover


# --- dựng ngữ cảnh -------------------------------------------------------------------------------------


class ContextBuilder:
    """Ngữ cảnh của mỗi hệ cho mỗi câu hỏi. `graph_state(n)`: nền đồ thị (Neo4j qua graph/ hoặc gói
    trong bộ nhớ). `summaries[k]`: tóm tắt chương k (thiếu thì hệ "rolling" không dựng được)."""

    def __init__(self, data: BenchData, graph_state: Callable[[int], GraphState],
                 summaries: Mapping[int, str], *, page_neighbors: int = 0,
                 page_max_chars: int | None = None, graph_style: str = "base") -> None:
        self.data, self._graph_state, self.summaries = data, graph_state, summaries
        self._page_neighbors, self._page_max_chars = page_neighbors, page_max_chars
        self._graph_style = graph_style
        self._cache: dict[tuple[str, str], Context] = {}

    def rolling_text(self, upto: int) -> dict[int, str]:
        return {k: "\n".join(f"Chương {i}: {self.summaries[i]}" for i in range(1, k + 1))
                for k in range(1, upto + 1)}

    def build(self, system: str, q: Question) -> Context:
        key = (system, q.id)
        if key in self._cache:
            return self._cache[key]
        story, n, run = self.data.story, q.ask_chapter, self.data.run
        if system == "none":
            ctx = context_none(story, n)
        elif system == "full":
            ctx = context_full(story, n)
        elif system == "rolling":
            missing = [k for k in range(1, n) if k not in self.summaries]
            if missing:
                raise KeyError(f"thiếu tóm tắt chương {missing}")
            ctx = context_rolling(story, n, self.rolling_text(n - 1))
        elif system == "rag":
            ctx = context_rag(story, n, q.question, top_k=run.rag.top_k,
                              chunk_chars=run.rag.chunk_chars)
        elif system == "graph":
            ctx = build_graph_context(self._graph_state(n), q.question, n, story=story,
                                      recent=run.graph.recent_chapter, style=self._graph_style)
        elif system == "graph_quotes":
            ctx = context_graph_quotes(self._graph_state(n), q.question, n, story=story,
                                       top_k=run.graph_quotes.top_k,
                                       chunk_chars=run.rag.chunk_chars,
                                       recent=run.graph.recent_chapter,
                                       neighbors=self._page_neighbors,
                                       max_chars=self._page_max_chars,
                                       style=self._graph_style)
        else:
            raise ValueError(f"hệ không biết: {system}")
        self._cache[key] = ctx
        return ctx


def open_graph_backend(kind: str, data: BenchData, *, story_id: str | None = None
                       ) -> tuple[Callable[[int], GraphState], Callable[[], None]]:
    """(hàm chương -> GraphState, hàm đóng). `memory`: gói trong bộ nhớ, không dịch vụ. `neo4j`: nạp
    truyện vào Neo4j rồi đọc qua `Neo4jState`: truyện mẫu bằng `load_sample_story`, truyện do
    pipeline viết bằng cách áp lần lượt các gói chương 0..N của lượt chạy (D-83). Kết nối theo
    NEO4J_URI/USER/PASSWORD (mặc định theo .env.example). `story_id`: test truyền id riêng, vì nạp và
    đóng đều xoá truyện đó; dùng chung id với lượt đo thật thì test xoá đồ thị của lượt đang chạy
    (hồi quy 22/10/2026: 54 lượt mỗi hệ đồ thị lỗi "0 nhân vật chính")."""
    if kind == "memory":
        return data.state_at, lambda: None
    if kind != "neo4j":
        raise ConfigError(f"--graph-backend phải là memory hoặc neo4j: {kind!r}")
    from neo4j import GraphDatabase

    from writory.graph import apply_package, delete_story, ensure_schema, load_sample_story
    from writory.guard.state import Neo4jState

    from_run = data.questions.story == "run"
    story_id = story_id or (RUN_STORY_ID if from_run else STORY_ID)
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"),
              os.environ.get("NEO4J_PASSWORD", "change-me-local")))
    try:
        driver.verify_connectivity()
        ensure_schema(driver)
        delete_story(driver, story_id)  # nạp sạch: không để lại gói của lần chạy trước
        if from_run:
            for _, package in data.packages:
                apply_package(driver, story_id, package)
        else:
            load_sample_story(driver, story_id)
    except Exception as e:  # noqa: BLE001 — chuyển thành lỗi cấu hình nói rõ việc cần làm
        driver.close()
        raise ConfigError("không nạp được truyện vào Neo4j (đã chạy `docker compose up -d` "
                          f"chưa? NEO4J_URI/USER/PASSWORD đúng chưa?): {type(e).__name__}") from None
    state = Neo4jState(driver, story_id)

    def close() -> None:
        delete_story(driver, story_id)
        driver.close()

    return (lambda _n: state), close


# --- chạy ------------------------------------------------------------------------------------------------


@dataclass
class RunOptions:
    out: Path
    dry_run: bool = False
    fake: Literal["oracle", "null", "wrong"] = "oracle"
    systems: Sequence[str] = ()  # rỗng: các hệ đang bật trong run.yaml (`RunFile.systems`)
    budget: float | None = None
    samples: int | None = None  # None: theo run.yaml
    concurrency: int = 4
    question_ids: Sequence[str] = ()
    groups: Sequence[str] = ()
    graph_backend: str | None = None  # None: memory khi --dry-run, neo4j khi chạy thật
    graph_story_id: str | None = None  # None: id mặc định của bộ đo; test truyền id riêng
    page_neighbors: int | None = None  # None: limits.context.page_quotes_neighbors (D-96)
    graph_style: str = "base"  # cách trình bày khối đồ thị của hai hệ đồ thị (D-99)


def page_settings(config: AppConfig, neighbors: int | None = None) -> dict[str, int | None]:
    """Cách lấy đoạn trên trang của hệ `graph_quotes` (D-96): đúng số của sản phẩm trong
    `limits.context` (đoạn kế, trần ký tự); `neighbors` là cờ ghi đè, để đo lại điều kiện cũ."""
    if neighbors is not None and neighbors < 0:
        raise ConfigError(f"--page-neighbors phải >= 0, nhận {neighbors}")
    ctx = config.limits.context
    return {"neighbors": ctx.page_quotes_neighbors if neighbors is None else neighbors,
            "max_chars": ctx.page_quotes_max_chars}


def check_options(opts: RunOptions) -> None:
    """Trước khi đọc key hay tạo thư mục kết quả."""
    if opts.concurrency < 1 or (opts.samples is not None and opts.samples < 1):
        raise ConfigError("--concurrency, --samples phải >= 1")
    if opts.graph_style not in GRAPH_STYLES:
        raise ConfigError(f"--graph-style chọn trong {', '.join(GRAPH_STYLES)}; nhận "
                          f"{opts.graph_style!r}")
    unknown = sorted(set(opts.systems) - set(ALL_SYSTEMS))
    if unknown:
        raise ConfigError(f"--systems chọn trong {', '.join(ALL_SYSTEMS)}; không biết: {unknown}")
    bad = sorted(set(opts.groups) - set(GROUPS))
    if bad:
        raise ConfigError(f"--groups chọn trong {', '.join(GROUPS)}; không biết: {bad}")
    if opts.dry_run:
        return
    if opts.budget is None or opts.budget <= 0:
        raise ConfigError("lượt chạy thật cần --budget (USD, > 0)")


def resolve_systems(run: RunFile, requested: Sequence[str]) -> list[str]:
    """Hệ sẽ chạy: `requested`, hoặc các hệ đang bật trong run.yaml khi bỏ trống. Chọn một hệ tuỳ
    chọn đang tắt là lỗi: run.yaml là tham số khai trước, không bật ngầm (D-81). Hai hệ người kể
    không thuộc bộ mặc định, chỉ chạy khi nêu tên (tham số ở `limits.narrator_pages`, D-143)."""
    unknown = sorted(set(requested) - set(ALL_SYSTEMS))
    if unknown:
        raise ConfigError(f"--systems chọn trong {', '.join(ALL_SYSTEMS)}; không biết: {unknown}")
    if not requested:
        return list(run.systems)
    off = [s for s in requested if s not in run.systems and s not in narr.NARRATOR_SYSTEMS]
    if off:
        flags = ", ".join(f"{s}.enabled" for s in off)
        raise ConfigError(f"hệ {', '.join(off)} đang tắt trong run.yaml ({flags}); bật ở đó "
                          "(tăng `version`) hoặc bỏ khỏi --systems")
    return list(requested)


def select_questions(data: BenchData, opts: RunOptions) -> list[Question]:
    unknown = sorted(set(opts.question_ids) - {q.id for q in data.questions.questions})
    if unknown:
        raise ConfigError(f"câu hỏi không có: {', '.join(unknown)}")
    return [q for q in data.questions.questions
            if (not opts.question_ids or q.id in opts.question_ids)
            and (not opts.groups or q.group in opts.groups)]


def run_problems(config: AppConfig, data: BenchData, systems: Sequence[str] = SYSTEMS) -> list[str]:
    """Mọi chỗ config còn thiếu để chạy, báo một lần trước lời gọi đầu. Rỗng là đủ."""
    problems: list[str] = []
    roles = ["narrator", *(["summary"] if "rolling" in systems else [])]
    for role in roles:
        try:
            model = require_model(config.models.roles, role)
            if model not in data.run.prices:
                problems.append(f"run.yaml không có giá (prices) cho model vai {role} {model}: cần "
                                "để giữ chỗ ngân sách")
        except WritoryError as e:
            problems.append(e.detail)
    needed = [("cost_usd", "per_scene"), ("cost_usd", "per_chapter"), ("cost_usd", "per_story")]
    if "rolling" in systems:
        needed.append(("context", "summary_max_chars"))
    if set(systems) & set(narr.NARRATOR_SYSTEMS):  # đường người kể của sản phẩm (D-40, D-59, D-143)
        needed += [("rate_limit", "narrator_questions_per_chapter"),
                   ("input", "narrator_question_max_chars"),
                   *(("narrator_notebook", n) for n in ("max_entries", "max_chars",
                                                        "recent_entries", "keyword_entries")),
                   ("narrator_pages", "top_k")]
    if "narrator_pages" in systems:
        needed += [("narrator_pages", "chunk_chars"), ("narrator_pages", "max_chars")]
    for section, name in needed:
        try:
            getattr(config.limits, section).require(name)
        except LimitNotSetError as e:
            problems.append(str(e))
    return problems


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def fingerprint(data: BenchData, config_dir: Path, opts: RunOptions,
                config: AppConfig) -> dict[str, Any]:
    """Những gì phải giữ nguyên để chạy tiếp vào cùng thư mục kết quả."""
    from writory.pipeline.summary import PROMPT_VERSION as SUMMARY_PROMPT_VERSION

    models = config.models
    return {
        "dry_run": opts.dry_run,
        "fake": opts.fake if opts.dry_run else None,
        "data_sha256": dict(data.hashes),
        "config_sha256": {n: _sha256((config_dir / n).read_bytes())
                          for n in ("models.yaml", "limits.yaml")},
        "answerer": {"model": models.roles.narrator, "reasoning": models.role_reasoning.narrator},
        "summarizer": {"model": models.roles.summary, "reasoning": models.role_reasoning.summary,
                       "prompt": SUMMARY_PROMPT_VERSION},
        "answer_prompt": ANSWER_PROMPT_VERSION,
        "answer_prompt_sha256": _sha256(f"{ANSWER_SYSTEM}\n{DATA_NOTICE}".encode()),
        "page_quotes": page_settings(config, opts.page_neighbors),
        "graph_style": opts.graph_style,
        # Hai hệ người kể (D-143): đề của từng hệ, chữ hai đề, số đoạn trên trang, file khởi tạo.
        "narrator_prompts": narr.prompt_versions(config),
        "narrator_prompt_sha256": _sha256(narr.prompt_sha_parts().encode()),
        "narrator_pages": config.limits.narrator_pages.model_dump(),
        "narrator_story_sha256": narr.story_hashes(data),
    }


CACHE_COLD = "lạnh"  # lời gọi báo cached_tokens = 0
CACHE_WARM = "có cache"  # lời gọi báo cached_tokens > 0


def cache_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Chi phí tách theo cache prompt (D-96): lượt lạnh (nhà cung cấp báo 0 token cache), lượt có
    cache (báo > 0), và lượt không rõ (phản hồi không có trường, nhật ký cũ). Giá của lượt có cache
    thấp hơn nhiều, nên USD mỗi lời gọi giữa các lần chạy chỉ so được khi cùng tỉ lệ cache."""
    calls = [c for r in rows for c in r.get("calls", []) if c.get("status", "ok") == "ok"]
    cold = [c for c in calls if c.get("cached_tokens") == 0]
    warm = [c for c in calls if (c.get("cached_tokens") or 0) > 0]
    known = len(cold) + len(warm)

    def usd(group: Sequence[Mapping[str, Any]]) -> float:
        return sum(c.get("cost_usd") or 0.0 for c in group)

    return {
        "calls": len(calls), "cold_calls": len(cold), "warm_calls": len(warm),
        "unknown_calls": len(calls) - known,
        "cold_usd": usd(cold), "warm_usd": usd(warm),
        "cold_usd_per_call": usd(cold) / len(cold) if cold else None,
        "warm_usd_per_call": usd(warm) / len(warm) if warm else None,
        "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
        "cached_tokens": sum(c.get("cached_tokens") or 0 for c in calls),
    }


def _calls_usd(rows: Sequence[Mapping[str, Any]]) -> float:
    return sum((c.get("cost_usd") or 0.0) + (c.get("cost_estimated_usd") or 0.0)
               for r in rows for c in r.get("calls", []))


def spent_from_store(store: Store) -> float:
    """Chi phí đã tiêu trong thư mục này (kể cả lời gọi lỗi), để trần tính cả các lần chạy trước."""
    return (_calls_usd(store.rows(RESULTS)) + _calls_usd(store.rows(SUMMARIES))
            + _calls_usd(store.rows(ERRORS)))


class Runner:
    def __init__(self, data: BenchData, store: Store, opts: RunOptions, *, config: AppConfig,
                 answerer: LLMClient, budget: Budget, graph_state: Callable[[int], GraphState],
                 log: Callable[[str], None] = print,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        self.data, self.store, self.opts, self.config = data, store, opts, config
        self.answerer, self.budget, self._log, self._clock = answerer, budget, log, clock
        self.samples = opts.samples or data.run.samples
        self.done = {(r["id"], r["system"], r["sample"]) for r in store.rows(RESULTS)}
        self.summaries = {r["chapter"]: r["summary"] for r in store.rows(SUMMARIES)}
        page = page_settings(config, opts.page_neighbors)
        self.builder = ContextBuilder(data, graph_state, self.summaries,
                                      page_neighbors=page["neighbors"] or 0,
                                      page_max_chars=page["max_chars"],
                                      graph_style=opts.graph_style)
        self.narrator = (narr.NarratorSide.load(data)
                         if set(opts.systems) & set(narr.NARRATOR_SYSTEMS) else None)
        self.stop: tuple[str, str] | None = None

    def _halt(self, kind: str, message: str) -> None:
        if self.stop is None:
            self.stop = (kind, message)
            self._log(f"!! DỪNG ({kind}): {message}")

    def _gate(self, calls: list[dict[str, Any]], chapter: int, attempt: int = 1) -> BudgetedClient:
        gate = BudgetedClient(self.answerer, budget=self.budget, prices=self.data.run.prices,
                              max_tokens=self.data.run.max_tokens_per_call,
                              tracker=StepTracker(self.config.limits.cost_usd),
                              record=calls.append, clock=self._clock)
        gate.chapter, gate.attempt = chapter, attempt
        return gate

    def _error(self, stage: str, what: str, system: str | None, sample: int, code: str,
               detail: str, **fields: Any) -> None:
        self.store.append(ERRORS, {"stage": stage, "id": what, "system": system, "sample": sample,
                                   "code": code, "detail": redact(detail)[:400], **fields,
                                   "time": _now()})
        self._log(f"[lỗi {stage}] {what} · {system} · lần {sample}: {code}")

    # tóm tắt của hệ "rolling": mỗi chương một lần, dùng chung cho mọi câu hỏi
    async def prepare_summaries(self, questions: Sequence[Question]) -> None:
        if "rolling" not in self.opts.systems:
            return
        upto = max((q.ask_chapter for q in questions), default=1) - 1
        cfg = self.config
        model = require_model(cfg.models.roles, "summary")
        for k in range(1, upto + 1):
            if k in self.summaries or self.stop:
                continue
            calls: list[dict[str, Any]] = []
            gate = self._gate(calls, k)
            started = self._clock()
            try:
                text = await summarize_chapter(
                    gate, model, chapter=k, scenes=[self.data.story[k]],
                    max_chars=cfg.limits.context.require("summary_max_chars"),
                    retries=cfg.limits.retries, extra=role_extra(cfg.models, "summary"))
            except WritoryError as e:
                self._error("summary", f"chương {k}", "rolling", 0, e.code.value, e.detail,
                            calls=calls)
                if gate.halted:
                    self._halt("budget", gate.halted)
                elif e.code in FATAL or e.code is ErrorCode.LLM_REQUEST_INVALID:
                    self._halt("abort", f"tóm tắt chương {k}: {e.code.value}")
                continue
            row = {"chapter": k, "summary": text, "calls": calls,
                   "cost_usd": sum(c.get("cost_usd") or 0.0 for c in calls),
                   "latency_s": round(self._clock() - started, 3), "time": _now()}
            self.store.append(SUMMARIES, row)
            self.summaries[k] = text
            self._log(f"[tóm tắt] chương {k}: {len(text)} ký tự")

    async def run(self, questions: Sequence[Question]) -> None:
        await self.prepare_summaries(questions)
        gate = asyncio.Semaphore(self.opts.concurrency)

        async def guarded(q: Question, system: str, s: int) -> None:
            async with gate:
                await self._unit(q, system, s)

        async with asyncio.TaskGroup() as tg:
            for q in questions:
                for system in self.opts.systems:
                    for s in range(self.samples):
                        tg.create_task(guarded(q, system, s))

    async def _unit(self, q: Question, system: str, s: int) -> None:
        if self.stop or (q.id, system, s) in self.done:
            return
        try:
            await self._ask(q, system, s)
        except Exception as e:  # noqa: BLE001 — lỗi của khung chạy: ghi lại, câu khác chạy tiếp
            self._error("harness", q.id, system, s, "HARNESS_ERROR", f"{type(e).__name__}: {e}")

    async def _ask(self, q: Question, system: str, s: int) -> None:
        if system in narr.NARRATOR_SYSTEMS:
            await self._ask_narrator(q, system, s)
            return
        try:
            ctx = self.builder.build(system, q)
        except KeyError as e:  # hệ rolling thiếu tóm tắt (tóm tắt lỗi hoặc hết ngân sách)
            self._error("context", q.id, system, s, "CONTEXT_MISSING", str(e))
            return
        if isinstance(self.answerer, FakeAnswerer):
            self.answerer.register(ctx)
        cfg = self.config
        messages = answer_messages(q, ctx)
        calls: list[dict[str, Any]] = []
        gate = self._gate(calls, q.ask_chapter, s + 1)
        model = require_model(cfg.models.roles, "narrator")
        extra = role_extra(cfg.models, "narrator")
        started = self._clock()

        async def call() -> AnswerOutput:
            output, _ = await gate.chat_json(model, messages, AnswerOutput, extra=extra)
            return output

        try:
            output = await with_json_retries(
                call, schema_retries=cfg.limits.retries.extract_schema_retry,
                transient_retries=cfg.limits.retries.llm_transient,
                backoff=cfg.limits.retries.transient_backoff_seconds)
        except WritoryError as e:
            if gate.halted:
                self._halt("budget", gate.halted)
                if not calls:
                    return  # chưa gọi gì: để lần chạy tiếp hỏi lại
            self._error("answer", q.id, system, s, e.code.value, e.detail, calls=calls)
            if e.code in FATAL or e.code is ErrorCode.LLM_REQUEST_INVALID:
                self._halt("abort", f"{q.id} · {system}: {e.code.value}")
            return
        names = self.data.state_at(q.ask_chapter).named_nodes()
        verdict = score_answer(q, output.answer, names)
        row = {"id": q.id, "group": q.group, "system": system, "sample": s,
               "ask_chapter": q.ask_chapter, "fact_chapter": q.fact_chapter,
               "distance": q.distance, "type": q.answer.type, "question": q.question,
               "answer": output.answer, **verdict, "context_chars": len(ctx.text),
               "calls": calls, "cost_usd": sum(c.get("cost_usd") or 0.0 for c in calls),
               "latency_s": round(self._clock() - started, 3), "time": _now()}
        self.store.append(RESULTS, row)
        self.done.add((q.id, system, s))
        mark = "đúng" if verdict["correct"] else ("kiêng" if verdict["abstained"] else "sai")
        self._log(f"[hỏi] {q.id} · {system} · lần {s}: {mark}")


    async def _ask_narrator(self, q: Question, system: str, s: int) -> None:
        """Hai hệ người kể (D-143): đúng `ask_narrator_reply` của sản phẩm, mỗi câu hỏi một bộ đếm
        trần như mỗi yêu cầu của người chơi, qua cùng cổng ngân sách."""
        assert self.narrator is not None
        calls: list[dict[str, Any]] = []
        gate = self._gate(calls, q.ask_chapter, s + 1)
        llm = MeteredClient(gate, CostTracker(self.config.limits.cost_usd))
        started = self._clock()
        try:
            reply = await narr.ask(q, system, data=self.data, side=self.narrator, llm=llm,
                                   config=self.config)
        except WritoryError as e:
            if gate.halted:
                self._halt("budget", gate.halted)
                if not calls:
                    return  # chưa gọi gì: để lần chạy tiếp hỏi lại
            self._error("answer", q.id, system, s, e.code.value, e.detail, calls=calls)
            if e.code in FATAL or e.code is ErrorCode.LLM_REQUEST_INVALID:
                self._halt("abort", f"{q.id} · {system}: {e.code.value}")
            return
        fields = narr.row_fields(q, system, reply, data=self.data, side=self.narrator,
                                 config=self.config)
        row = {"id": q.id, "group": q.group, "system": system, "sample": s,
               "ask_chapter": q.ask_chapter, "fact_chapter": q.fact_chapter,
               "distance": q.distance, "type": q.answer.type, "question": q.question, **fields,
               "calls": calls, "cost_usd": sum(c.get("cost_usd") or 0.0 for c in calls),
               "latency_s": round(self._clock() - started, 3), "time": _now()}
        self.store.append(RESULTS, row)
        self.done.add((q.id, system, s))
        mark = "đúng" if row["correct"] else ("kiêng" if row["abstained"] else "sai")
        self._log(f"[hỏi] {q.id} · {system} · lần {s}: {mark}"
                  + (f" · chặn {row['blocked']}" if row["blocked"] else ""))


def _open_results(store: Store, fp: dict[str, Any], meta_extra: dict[str, Any],
                  run_info: dict[str, Any]) -> None:
    meta = store.read_meta()
    if meta is None:
        meta = {"bench": "A", "created": _now(), **meta_extra, "fingerprint": fp, "runs": []}
    elif meta.get("fingerprint") != fp:
        changed = sorted(k for k in fp if meta.get("fingerprint", {}).get(k) != fp[k])
        raise ConfigError(f"{store.root} đã có kết quả với đề hoặc cấu hình khác "
                          f"({', '.join(changed)}). Không chạy tiếp lên kết quả cũ; dùng nhãn mới.")
    meta["runs"].append(run_info)
    store.write_meta(meta)


async def run_bench(
    data: BenchData, opts: RunOptions, *, config: AppConfig, answerer: LLMClient | None = None,
    config_dir: Path = REPO_CONFIG_DIR, argv: Sequence[str] = (),
    log: Callable[[str], None] = print,
    graph_state: Callable[[int], GraphState] | None = None,
) -> int:
    """Chạy (hoặc chạy tiếp) bài A vào `opts.out`. Chạy thật: nơi gọi đưa client thật."""
    check_options(opts)
    opts = replace(opts, systems=resolve_systems(data.run, opts.systems))
    problems = run_problems(config, data, opts.systems)
    if problems:
        raise ConfigError("config chưa đủ để chạy bài A:\n- " + "\n- ".join(problems))
    questions = select_questions(data, opts)
    if answerer is None:
        if not opts.dry_run:
            raise ConfigError("chạy thật cần client trả lời")
        answerer = FakeAnswerer(data, opts.fake)

    close: Callable[[], None] = lambda: None
    # Hệ người kể đọc player_view từ gói trong bộ nhớ như bài E: không có hệ đồ thị thì không cần Neo4j.
    needs_graph = bool(set(opts.systems) & {"graph", "graph_quotes"})
    backend = opts.graph_backend or ("neo4j" if needs_graph and not opts.dry_run else "memory")
    if graph_state is None:
        graph_state, close = open_graph_backend(backend, data, story_id=opts.graph_story_id)
    try:
        store = Store(opts.out)
        samples = opts.samples or data.run.samples
        run_info = {"started": _now(), **git_state(), "argv": list(argv), "samples": samples,
                    "concurrency": opts.concurrency, "systems": list(opts.systems),
                    "graph_backend": backend,
                    "questions": [q.id for q in questions]
                    if (opts.question_ids or opts.groups) else "all",
                    "budget": opts.budget,
                    "page_quotes": page_settings(config, opts.page_neighbors),
                    "graph_style": opts.graph_style}
        meta_extra = {"versions": {"questions": data.questions.version, "run": data.run.version},
                      "status": data.questions.status, "story": data.source}
        _open_results(store, fingerprint(data, config_dir, opts, config), meta_extra, run_info)
        budget = Budget("openrouter", math.inf if opts.dry_run or opts.budget is None
                        else opts.budget, spent_usd=spent_from_store(store))
        runner = Runner(data, store, opts, config=config, answerer=answerer, budget=budget,
                        graph_state=graph_state, log=log)
        started = time.monotonic()
        await runner.run(questions)
        meta = store.read_meta() or {"runs": [{}]}
        meta["runs"][-1] |= {
            "finished": _now(), "wall_s": round(time.monotonic() - started, 1),
            "stopped": f"{runner.stop[0]}: {runner.stop[1]}" if runner.stop else None,
            "spent_usd": round(budget.spent_usd, 6)}
        store.write_meta(meta)
    finally:
        close()
    report = compute_report(data, store, opts.systems, questions, samples)
    (store.root / "summary.md").write_text(build_summary(data, store, report), encoding="utf-8",
                                           newline="\n")
    log(f"Xong. Đã tiêu {budget.spent_usd:.4f} USD. Kết quả: {store.root}")
    if runner.stop:
        return EXIT_BUDGET if runner.stop[0] == "budget" else EXIT_ABORT
    return EXIT_OK


# --- tổng hợp -----------------------------------------------------------------------------------------


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Khoảng tin cậy 95% Wilson cho tỉ lệ k/n."""
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def compute_report(data: BenchData, store: Store, systems: Sequence[str],
                   questions: Sequence[Question], samples: int) -> dict[str, Any]:
    """Độ chính xác chia cho số lượt ĐÃ KHAI (câu × lần hỏi): lượt lỗi hoặc chưa chạy tính là chưa
    đúng, để hệ lỗi nhiều không trông tốt hơn."""
    rows = store.rows(RESULTS)
    summaries = store.rows(SUMMARIES)
    errors = store.rows(ERRORS)
    qs = {q.id: q for q in questions}
    expected_per_system = len(qs) * samples
    out: dict[str, Any] = {"expected_per_system": expected_per_system, "systems": {}}
    for system in systems:
        mine = [r for r in rows if r["system"] == system and r["id"] in qs
                and r["sample"] < samples]
        cost_answer = sum(r["cost_usd"] for r in mine)
        cost_build = sum(r["cost_usd"] for r in summaries) if system == "rolling" else 0.0
        correct = sum(r["correct"] for r in mine)

        def cell(sub: list[dict[str, Any]], total: int) -> dict[str, Any]:
            k = sum(r["correct"] for r in sub)
            return {"k": k, "n": total, "answered": len(sub), "ci": wilson(k, total),
                    "abstained": sum(r["abstained"] for r in sub)}

        by_group = {g: cell([r for r in mine if r["group"] == g],
                            sum(1 for q in qs.values() if q.group == g) * samples)
                    for g in GROUPS}
        by_bin = {b: cell([r for r in mine if distance_bin(r["distance"]) == b],
                          sum(1 for q in qs.values() if distance_bin(q.distance) == b) * samples)
                  for b in DISTANCE_BINS}
        by_kind = {kind: cell([r for r in mine if qs[r["id"]].inference is flag],
                              sum(1 for q in qs.values() if q.inference is flag) * samples)
                   for kind, flag in (("memory", False), ("inference", True))}
        by_graph = {kind: cell([r for r in mine if qs[r["id"]].graph_agrees is flag],
                               sum(1 for q in qs.values() if q.graph_agrees is flag) * samples)
                    for kind, flag in (("agrees", True), ("disagrees", False))}
        out["systems"][system] = {
            "overall": cell(mine, expected_per_system), "by_group": by_group, "by_bin": by_bin,
            "by_kind": by_kind, "by_graph": by_graph,
            "cost_answer_usd": cost_answer, "cost_build_usd": cost_build,
            "cost_usd": cost_answer + cost_build,
            "cost_per_answer_usd": (cost_answer + cost_build) / len(mine) if mine else None,
            "mean_context_chars": (sum(r["context_chars"] for r in mine) / len(mine)
                                   if mine else None),
            "errors": Counter(e["code"] for e in errors if e["system"] == system),
            "correct": correct,
            "cache": cache_stats(mine),
        }
        if system in narr.NARRATOR_SYSTEMS:
            called = [r for r in mine if r.get("raw") is not None]
            leaked = [r for r in mine if r.get("final_leaks")]
            out.setdefault("narrator", {})[system] = {
                "rows": len(mine),
                "blocked": dict(Counter(r["blocked"] for r in mine if r.get("blocked"))),
                "final_leaks": len(leaked),
                "final_leaks_off_page": sum(any(not h["on_page"] for h in r["final_leaks"])
                                            for r in leaked),
                "mean_passages": (sum(len(r.get("passages") or []) for r in called) / len(called)
                                  if called else 0.0),
                "wrong": sum(not r["correct"] and not r["abstained"] for r in mine),
            }
    return out


def _pct(k: int, n: int) -> str:
    return "—" if n == 0 else f"{100 * k / n:.0f}% ({k}/{n})"


def _cell(c: Mapping[str, Any]) -> str:
    ci = c["ci"]
    span = "" if ci is None else f" [{100 * ci[0]:.0f}–{100 * ci[1]:.0f}]"
    return f"{_pct(c['k'], c['n'])}{span}"


def _usd(x: float | None) -> str:
    return "—" if x is None else f"{x:.4f}"


def build_summary(data: BenchData, store: Store, report: dict[str, Any] | None = None) -> str:
    meta = store.read_meta() or {}
    last = (meta.get("runs") or [{}])[-1]
    systems = list(report["systems"]) if report else []
    if report is None:
        qs = list(data.questions.questions)
        systems = [s for s in ALL_SYSTEMS if any(r["system"] == s for r in store.rows(RESULTS))]
        report = compute_report(data, store, systems, qs, meta.get("runs", [{}])[0].get(
            "samples", data.run.samples))
    fp = meta.get("fingerprint", {})
    lines = [
        "# Bài A: bộ nhớ, kết quả",
        "",
        (f"- Đề: {meta.get('status', '?')}; truyện `{meta.get('story', '?')}`; "
        f"questions v{meta.get('versions', {}).get('questions')}, "
        f"run v{meta.get('versions', {}).get('run')}."),
        (f"- Commit `{str(last.get('commit', '?'))[:12]}`"
        f"{' (có sửa chưa commit)' if last.get('dirty') else ''}; model trả lời "
        f"`{fp.get('answerer', {}).get('model')}` (suy luận {fp.get('answerer', {}).get('reasoning')}); "
        f"tóm tắt `{fp.get('summarizer', {}).get('model')}`."),
        (f"- Chạy khô (model giả): {fp.get('dry_run')}"
        f"{' / ' + str(fp.get('fake')) if fp.get('dry_run') else ''}. Nền đồ thị: "
        f"{last.get('graph_backend')}."),
        (f"- Lượt khai mỗi hệ: {report['expected_per_system']} (câu × lần hỏi). Đúng = đúng đáp án gốc; "
        "kiêng = trả \"Không biết\" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng."),
        f"- Đã tiêu: {_usd(last.get('spent_usd'))} USD. Dừng sớm: {last.get('stopped') or 'không'}.",
        "",
        "## Độ chính xác chung",
        "",
        ("| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | "
        "USD / câu |"),
        "|---|---|---|---|---|---|---|",
    ]
    for s in systems:
        r = report["systems"][s]
        lines.append(
            f"| {LABELS[s]} | {_cell(r['overall'])} | {r['overall']['abstained']} | "
            f"{'—' if r['mean_context_chars'] is None else round(r['mean_context_chars'])} | "
            f"{_usd(r['cost_answer_usd'])} | {_usd(r['cost_build_usd'])} | "
            f"{_usd(r['cost_per_answer_usd'])} |")
    lines += ["", "## Theo nhóm câu hỏi", "",
              "| Hệ | " + " | ".join(GROUP_LABEL[g] for g in GROUPS) + " |",
              "|---|" + "---|" * len(GROUPS)]
    for s in systems:
        lines.append(f"| {LABELS[s]} | " + " | ".join(
            _pct(report["systems"][s]["by_group"][g]["k"], report["systems"][s]["by_group"][g]["n"])
            for g in GROUPS) + " |")
    lines += ["", "## Câu nhớ và câu suy luận (`inference`, tách riêng)", "",
              "| Hệ | Câu nhớ | Câu suy luận |", "|---|---|---|"]
    for s in systems:
        k = report["systems"][s]["by_kind"]
        lines.append(f"| {LABELS[s]} | {_pct(k['memory']['k'], k['memory']['n'])} | "
                     f"{_pct(k['inference']['k'], k['inference']['n'])} |")
    if any(not q.graph_agrees for q in data.questions.questions):
        lines += ["", "## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)", "",
                  ("Đáp án gốc lấy từ trang. \"Có đáp án\": đồ thị bộ trích đã dựng cho đúng đáp án ở "
                   "chương được hỏi (code kiểm). \"Thiếu hoặc sai\": đồ thị không có hoặc nói khác."),
                  "", "| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |", "|---|---|---|"]
        for s in systems:
            g = report["systems"][s]["by_graph"]
            lines.append(f"| {LABELS[s]} | {_pct(g['agrees']['k'], g['agrees']['n'])} | "
                         f"{_pct(g['disagrees']['k'], g['disagrees']['n'])} |")
    lines += ["", "## Theo khoảng cách (chương hỏi trừ chương của sự thật)", "",
              "| Hệ | " + " | ".join(f"cách {b} chương" for b in DISTANCE_BINS) + " |",
              "|---|" + "---|" * len(DISTANCE_BINS)]
    for s in systems:
        lines.append(f"| {LABELS[s]} | " + " | ".join(
            _pct(report["systems"][s]["by_bin"][b]["k"], report["systems"][s]["by_bin"][b]["n"])
            for b in DISTANCE_BINS) + " |")
    lines += ["", "## Cache prompt (D-96)", "",
              (f"Lượt {CACHE_COLD}: nhà cung cấp báo 0 token đọc từ cache; lượt {CACHE_WARM}: báo > 0. "
               "Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn "
               "nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. "
               "Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh."),
              "",
              (f"| Hệ | Lời gọi {CACHE_COLD} | USD / lời gọi {CACHE_COLD} | Lời gọi {CACHE_WARM} | "
              f"USD / lời gọi {CACHE_WARM} | Không rõ | Token vào được cache |"),
              "|---|---|---|---|---|---|---|"]
    for s in systems:
        c = report["systems"][s]["cache"]
        share = "—" if not c["prompt_tokens"] else f"{100 * c['cached_tokens'] / c['prompt_tokens']:.0f}%"
        per_cold = "—" if c["cold_usd_per_call"] is None else f"{c['cold_usd_per_call']:.6f}"
        per_warm = "—" if c["warm_usd_per_call"] is None else f"{c['warm_usd_per_call']:.6f}"
        lines.append(f"| {LABELS[s]} | {c['cold_calls']} | {per_cold} | {c['warm_calls']} | "
                     f"{per_warm} | {c['unknown_calls']} | {share} |")
    if report.get("narrator"):
        reasons = ", ".join(f"`{r.value}`" for r in BlockReason)
        lines += ["", "## Người kể: lý do chặn và lộ", "",
                  ("Câu \"Bạn chưa biết điều này.\" tính là kiêng. Lý do: " + reasons + ". Lộ: bộ "
                   "chấm chặt của bài E trên câu cuối; \"ngoài trang\" = chuỗi trúng không có trong "
                   "văn chương 1..N người chơi đã đọc."),
                  "", ("| Hệ | Lý do chặn | Lộ ở câu cuối | Lộ ngoài trang | Sai (không kiêng) | "
                  "Đoạn TB mỗi lời gọi |"), "|---|---|---|---|---|---|"]
        for s, n in report["narrator"].items():
            blocked = ", ".join(f"{k} ×{v}" for k, v in sorted(n["blocked"].items())) or "—"
            lines.append(f"| {LABELS[s]} | {blocked} | {n['final_leaks']} | "
                         f"{n['final_leaks_off_page']} | {n['wrong']} | {n['mean_passages']:.1f} |")
    err_lines = [f"- {LABELS[s]}: " + ", ".join(
        f"{c} ×{n}" for c, n in sorted(report["systems"][s]["errors"].items()))
        for s in systems if report["systems"][s]["errors"]]
    if err_lines:
        lines += ["", "## Lỗi", "", *err_lines]
    lines += ["", ("Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); "
              "lỗi: `errors.jsonl`; tóm tắt của hệ \"tóm tắt\": `summaries.jsonl`."), ""]
    return "\n".join(lines)


# --- kế hoạch (ước chi phí, không gọi model) -------------------------------------------------------


def plan_text(data: BenchData, config: AppConfig, *, samples: int,
              systems: Sequence[str] = ()) -> str:
    """Ước chi phí từng hệ từ ngữ cảnh thật (nền bộ nhớ) và giá trong run.yaml. Ước tính thô: token
    vào = ký tự / EST_CHARS_PER_TOKEN, token ra = hằng số chưa đo. Chi phí thật lấy từ usage.
    `systems` rỗng: các hệ đang bật trong run.yaml."""
    systems = resolve_systems(data.run, systems)
    model = require_model(config.models.roles, "narrator")
    price = data.run.prices[model]
    cap = config.limits.context.summary_max_chars or 1000
    fake_summaries = {k: "x" * cap for k in range(1, max(data.chapters))}
    builder = ContextBuilder(data, data.state_at, fake_summaries)
    side = (narr.NarratorSide.load(data) if set(systems) & set(narr.NARRATOR_SYSTEMS) else None)
    questions = list(data.questions.questions)
    lines = [
        (f"Bài A: {len(questions)} câu × {samples} lần × {len(systems)} hệ; model trả lời {model} "
        f"(giá vào {price.input}, ra {price.output} USD / 1 triệu token)."),
        "ƯỚC TÍNH THÔ (token ra chưa đo); chi phí thật ghi trong kết quả.", "",
        "| Hệ | Lời gọi | Ngữ cảnh TB (ký tự) | Token vào / ra (ước) | Ước USD |",
        "|---|---|---|---|---|"]
    total = 0.0
    for s in systems:
        chars = []
        for q in questions:
            if s in narr.NARRATOR_SYSTEMS:
                assert side is not None
                chars.append(sum(len(m.content) for m in narr.messages_for(
                    q, s, data=data, side=side, config=config)))
                continue
            ctx = builder.build(s, q)
            chars.append(len(ANSWER_SYSTEM) + len(DATA_NOTICE) + len(ctx.text) + len(q.question))
        tokens_in = sum(math.ceil(c / EST_CHARS_PER_TOKEN) for c in chars) * samples
        out_each = (TYPICAL_NARRATOR_OUTPUT_TOKENS if s in narr.NARRATOR_SYSTEMS
                    else TYPICAL_ANSWER_OUTPUT_TOKENS)
        tokens_out = out_each * len(questions) * samples
        usd = (tokens_in * price.input + tokens_out * price.output) / 1e6
        total += usd
        lines.append(f"| {LABELS[s]} | {len(questions) * samples} | "
                     f"{round(sum(chars) / len(chars))} | {tokens_in} / {tokens_out} | {usd:.4f} |")
    if "rolling" in systems:
        sprice = data.run.prices.get(require_model(config.models.roles, "summary"), price)
        sums = sum(math.ceil(len(data.story[k]) / EST_CHARS_PER_TOKEN) for k in fake_summaries)
        usd = (sums * sprice.input + TYPICAL_SUMMARY_OUTPUT_TOKENS * len(fake_summaries)
               * sprice.output) / 1e6
        total += usd
        lines.append(f"| (dựng tóm tắt, tính cho hệ tóm tắt) | {len(fake_summaries)} | — | — | "
                     f"{usd:.4f} |")
    lines += ["", f"Tổng ước tính: {total:.4f} USD. Trần `--budget` nên đặt cao hơn vài lần."]
    return "\n".join(lines)


# --- dòng lệnh ------------------------------------------------------------------------------------------


def _load(args: argparse.Namespace) -> BenchData:
    return load_data(Path(args.data), questions_file=args.questions_file)


def _split(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


def resolve_out(args: argparse.Namespace) -> Path:
    if args.out:
        return Path(args.out)
    if not args.label:
        raise ConfigError("cần --label (thư mục mới) hoặc --out (thư mục có sẵn để chạy tiếp)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.label):
        raise ConfigError(f"--label chỉ gồm a-z, 0-9, '-': {args.label!r}")
    suffix = "-dryrun" if args.dry_run else ""
    return RESULTS_DIR / f"{date.today().isoformat()}-memory-{args.label}{suffix}"


def _options(args: argparse.Namespace) -> RunOptions:
    return RunOptions(
        out=resolve_out(args), dry_run=args.dry_run, fake=args.fake,
        systems=_split(args.systems), budget=args.budget, samples=args.samples,
        concurrency=args.concurrency, question_ids=_split(args.questions),
        groups=_split(args.groups), graph_backend=args.graph_backend,
        page_neighbors=args.page_neighbors, graph_style=args.graph_style)


async def _cmd_run(args: argparse.Namespace, argv: Sequence[str]) -> int:
    opts = _options(args)
    check_options(opts)  # trước khi đọc key
    data = _load(args)
    config_dir = Path(args.config_dir)
    config = load_app_config(config_dir)
    if opts.dry_run:
        return await run_bench(data, opts, config=config, config_dir=config_dir, argv=argv)

    from writory.llm.openrouter import OpenRouterClient, call_deadline

    keys = load_keys(Path(args.env_file), ["openrouter"])
    assert keys.openrouter_api_key is not None
    http = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    try:
        return await run_bench(data, opts, config=config,
                               answerer=OpenRouterClient(keys.openrouter_api_key, http=http,
                                                         deadline_s=call_deadline(config)),
                               config_dir=config_dir, argv=argv)
    finally:
        await http.aclose()


def _cmd_summary(args: argparse.Namespace) -> int:
    data = _load(args)
    store = Store(Path(args.out))
    if store.read_meta() is None:
        raise ConfigError(f"{store.root} không có meta.json")
    text = build_summary(data, store)
    (store.root / "summary.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return EXIT_OK


def _cmd_plan(args: argparse.Namespace) -> int:
    data = _load(args)
    config = load_app_config(Path(args.config_dir))
    systems = resolve_systems(data.run, _split(args.systems))
    problems = run_problems(config, data, systems)
    if problems:
        raise ConfigError("config chưa đủ để chạy bài A:\n- " + "\n- ".join(problems))
    print(plan_text(data, config, samples=args.samples or data.run.samples, systems=systems))
    return EXIT_OK


def _ints(value: str, name: str) -> list[int]:
    try:
        out = [int(v) for v in _split(value)]
    except ValueError:
        raise ConfigError(f"{name} phải là số nguyên cách nhau dấu phẩy: {value!r}") from None
    if not out or any(v < 0 for v in out):
        raise ConfigError(f"{name} cần ít nhất một số >= 0: {value!r}")
    return out


def _cmd_retrieval(args: argparse.Namespace) -> int:
    """Phép kiểm truy hồi không tốn tiền (D-96): in bảng trúng theo (top_k, đoạn kế)."""
    from writory.pipeline.bench_a_retrieval import recall_table, table_text

    data = _load(args)
    cap = (load_app_config(Path(args.config_dir)).limits.context.page_quotes_max_chars
           if args.max_chars is None else (args.max_chars or None))
    table = recall_table(data, top_ks=_ints(args.top_k, "--top-k"),
                         neighbors=_ints(args.neighbors, "--neighbors"), max_chars=cap)
    print(table_text(table, max_chars=cap))
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m writory.pipeline.bench_a",
                                description="Bài đo A: bộ nhớ, sáu hệ trả lời (docs/eval.md).")
    sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="hỏi mọi câu của đề trên các hệ, chấm, ghi kết quả")
    run.add_argument("--label", help="tạo evals/results/<ngày>-memory-<nhãn>/")
    run.add_argument("--out", help="thư mục kết quả (có sẵn thì chạy tiếp)")
    run.add_argument("--dry-run", action="store_true", help="model giả, không key, không mạng")
    run.add_argument("--fake", choices=("oracle", "null", "wrong"), default="oracle",
                     help="model giả khi --dry-run: oracle (đúng nếu ngữ cảnh đủ), null (không "
                          "biết), wrong (luôn sai)")
    run.add_argument("--budget", type=float, help="trần OpenRouter, USD; bắt buộc khi chạy thật")
    run.add_argument("--graph-style", default="base",
                     help="cách trình bày khối đồ thị của graph và graph_quotes (D-99): "
                          + ", ".join(GRAPH_STYLES))
    run.add_argument("--page-neighbors", type=int,
                     help="ghi đè limits.context.page_quotes_neighbors cho hệ graph_quotes "
                          "(0 = như trước D-96); có ghi vào meta.json")
    run.add_argument("--samples", type=int, help="số lần hỏi mỗi câu (mặc định: run.yaml)")
    run.add_argument("--concurrency", type=int, default=4)
    run.add_argument("--systems", help=f"chỉ các hệ này, cách nhau dấu phẩy ({', '.join(ALL_SYSTEMS)}); "
                                       "mặc định: các hệ đang bật trong run.yaml (hai hệ người kể chỉ "
                                       "chạy khi nêu tên, D-143)")
    run.add_argument("--questions", help="chỉ các id này, cách nhau dấu phẩy")
    run.add_argument("--groups", help=f"chỉ các nhóm này ({', '.join(GROUPS)})")
    run.add_argument("--graph-backend", choices=("memory", "neo4j"),
                     help="nền đồ thị của hệ đồ thị (mặc định: memory khi --dry-run, neo4j khi "
                          "chạy thật)")
    run.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    summary = sub.add_parser("summary", help="dựng lại summary.md từ thư mục kết quả")
    summary.add_argument("--out", required=True)
    retrieval = sub.add_parser("retrieval", help="phép kiểm truy hồi đoạn, không gọi model (D-96)")
    retrieval.add_argument("--top-k", default="2,3,4", help="các top_k, cách nhau dấu phẩy")
    retrieval.add_argument("--neighbors", default="0,1", help="các số đoạn kế, cách nhau dấu phẩy")
    retrieval.add_argument("--max-chars", type=int,
                           help="trần ký tự (mặc định: limits.context.page_quotes_max_chars; 0 = không trần)")
    retrieval.add_argument("--config-dir", default=str(REPO_CONFIG_DIR))
    plan = sub.add_parser("plan", help="ước tính chi phí, không gọi model")
    plan.add_argument("--samples", type=int, help="mặc định: run.yaml")
    plan.add_argument("--systems", help="chỉ các hệ này")
    for sp in (run, summary, plan, retrieval):
        sp.add_argument("--data", default=str(DATA_DIR), help="thư mục đề")
        sp.add_argument("--questions-file", default="questions.yaml")
    for sp in (run, plan):
        sp.add_argument("--config-dir", default=str(REPO_CONFIG_DIR))
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(argv)
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    install_log_redaction(root)
    try:
        if args.command == "run":
            return asyncio.run(_cmd_run(args, argv))
        if args.command == "summary":
            return _cmd_summary(args)
        if args.command == "retrieval":
            return _cmd_retrieval(args)
        return _cmd_plan(args)
    except ConfigError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
