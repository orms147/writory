"""Bài F: so nhiều model viết trên cùng một thế giới, giám khảo là Claude (D-101, docs/eval.md).

Các lượt viết chạy bằng `writory.pipeline.bench_run` (`--setup-only` rồi `--setup-from`, đổi model
bằng `--writer-model` và `--outline-model`). Module này lo phần sau:

    pack     ba thư mục kết quả -> truyện gắn nhãn A/B/C ngẫu nhiên + khoá giải nhãn ở file riêng
    judge    chấm mù: mỗi truyện một lượt `solo`, rồi `compare` cả ba hai lần với thứ tự đảo
    value    sau khi điểm mù đã khoá: đưa chi phí thật, hỏi khuyến nghị "đáng tiền"
    summary  giải nhãn, bảng tổng hợp

Giám khảo không thấy tên model ở bất kỳ bước nào. Truyện là dữ liệu: bọc trong khối và escape như
mọi chữ ngoài (G4). Câu trích của giám khảo phải có thật trong truyện (G3), kiểm bằng code.
Dùng lại hạ tầng của bài D (`bench_d`): giá giám khảo, ngân sách giữ chỗ, kiểm câu trích."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, PositiveInt, ValidationError, model_validator
from pydantic import Field as PField
from pydantic.types import SecretStr

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.errors import ErrorCode, WritoryError
from writory.pipeline.bench_run import RunScenario
from writory.pipeline.setup import CharacterOption, PlotOption, SettingOption, story_brief
from writory.quality import (
    check_cliches,
    check_foreign_script,
    check_meta_leak,
    check_repetition,
    normalize_dashes,
)
from writory.quality.bench_d import (
    BACKOFF_BASE_S,
    BACKOFF_CAP_S,
    FATAL,
    HTTP_TIMEOUT_S,
    JUDGE_PRICES,
    MAX_ATTEMPTS,
    NO_QUOTE,
    RETRY_ON,
    Budget,
    BudgetExceeded,
    Store,
    _anthropic_create,
    _maybe_billed,
    git_state,
    judge_cost,
    judge_estimate,
    load_keys,
    mock_judge_client,
    quote_found,
    usage_dict,
)

DATA_DIR = REPO_ROOT / "evals" / "scenarios" / "bakeoff"
JUDGE_FILE = "judge.yaml"
STORY_TAG = "truyen"
LABELS = ("A", "B", "C")
SOLO, COMPARE, VALUE = "solo", "compare", "value"
VERDICTS = ("dang_tien", "chap_nhan_duoc", "khong_dang_tien")
RESULTS_FILE, ERRORS_FILE, LOCK_FILE = "results.jsonl", "errors.jsonl", "value_lock.json"
CHOICES_HEADING = "## Lựa chọn cuối chương"
EXIT_OK, EXIT_CONFIG, EXIT_BUDGET, EXIT_ABORT = 0, 1, 2, 3


# --- thang chấm khai trước ---------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Criterion(_Strict):
    id: str
    label: str
    description: str
    anchors: dict[str, str]


class JudgeSpec(_Strict):
    model: str
    effort: str
    thinking: str
    max_tokens: PositiveInt = PField(le=21000)  # SDK chặn yêu cầu không stream lớn hơn

    @model_validator(mode="after")
    def _known_price(self) -> JudgeSpec:
        if self.model not in JUDGE_PRICES:
            raise ValueError(f"chưa có giá cho giám khảo {self.model} (bench_d.JUDGE_PRICES)")
        return self


class BakeoffData(_Strict):
    version: PositiveInt
    judge: JudgeSpec
    criteria: list[Criterion] = PField(min_length=1)
    solo_instructions: str
    compare_instructions: str
    value_instructions: str

    @model_validator(mode="after")
    def _unique_ids(self) -> BakeoffData:
        ids = [c.id for c in self.criteria]
        if len(set(ids)) != len(ids):
            raise ValueError("id tiêu chí bị trùng")
        return self

    @property
    def ids(self) -> list[str]:
        return [c.id for c in self.criteria]


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def load_data(data_dir: Path = DATA_DIR) -> tuple[BakeoffData, str]:
    path = data_dir / JUDGE_FILE
    try:
        raw = path.read_bytes()
        return BakeoffData.model_validate(yaml.safe_load(raw)), _sha256(raw)
    except OSError as e:
        raise ConfigError(f"không đọc được {path}: {e}") from e
    except (yaml.YAMLError, ValidationError) as e:
        raise ConfigError(f"{path.name} sai: {e}") from e


# --- đóng gói mù --------------------------------------------------------------------------------


@dataclass
class RunInfo:
    dir: Path
    meta: dict[str, Any]
    report: dict[str, Any]
    calls: list[dict[str, Any]]
    chapters: list[str]  # văn từng chương đã ghi, gồm cả phần lựa chọn cuối chương

    @property
    def writer_model(self) -> str:
        return self.meta["models"]["writer"]["model"]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ConfigError(f"không đọc được {path}: {e}") from e


def load_run(run_dir: Path) -> RunInfo:
    chapters = sorted((run_dir / "chapters").glob("ch*.md"))
    if not chapters:
        raise ConfigError(f"{run_dir} chưa có chương nào để chấm")
    calls = [json.loads(line) for line in
             (run_dir / "calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    return RunInfo(run_dir, _read_json(run_dir / "meta.json"), _read_json(run_dir / "report.json"),
                   calls, [p.read_text(encoding="utf-8").strip() for p in chapters])


def _same_world(runs: Sequence[RunInfo]) -> None:
    """Cùng thế giới là điều kiện của phép so: cùng đề, cùng seed, cùng khởi tạo."""
    for field_name, get in (("sha256 của đề", lambda r: r.meta["scenario"]["sha256"]),
                            ("seed", lambda r: r.meta["seed"]),
                            ("--setup-from", lambda r: r.meta.get("setup_from"))):
        values = {json.dumps(get(r)) for r in runs}
        if len(values) != 1 or (field_name == "--setup-from" and values == {"null"}):
            raise ConfigError(f"các lần chạy không cùng thế giới: {field_name} khác nhau hoặc "
                              f"trống ({sorted(values)})")
    models = [r.writer_model for r in runs]
    if len(set(models)) != len(models):
        raise ConfigError(f"hai lần chạy cùng model viết: {models}")


def common_brief(run: RunInfo) -> str:
    """Đề bài chung: đúng đoạn `story_brief` mà model viết nhận, dựng từ khởi tạo dùng chung."""
    source = REPO_ROOT / run.meta["setup_from"]
    record = _read_json(source / "setup.json")
    scenario = run.meta["scenario"]["content"]
    picked = {step: record[step]["options"][record[step]["picked"]]
              for step in ("settings", "plots", "characters")}
    return story_brief(
        RunScenario.model_validate(scenario).story_choices(),
        SettingOption.model_validate(picked["settings"]), PlotOption.model_validate(picked["plots"]),
        CharacterOption.model_validate(picked["characters"]),
        moderation=load_config().moderation)


def story_text(run: RunInfo) -> str:
    return "\n\n".join(run.chapters)


def prose_of(chapter: str) -> str:
    return chapter.split(CHOICES_HEADING, 1)[0]


def code_metrics(run: RunInfo) -> dict[str, Any]:
    """Số đếm khách quan từ bộ kiểm văn của repo (chỉ phần văn, không phần lựa chọn)."""
    quality = load_config().quality
    prose = [normalize_dashes(prose_of(c)) for c in run.chapters]
    counts: dict[str, int] = {}
    for text in prose:
        for issue in (*check_repetition(text, quality), *check_cliches(text, quality),
                      *check_foreign_script(text, quality), *check_meta_leak(text)):
            counts[issue.kind.value] = counts.get(issue.kind.value, 0) + 1
    joined = "\n".join(prose)
    return {"chapters": len(prose), "chars": len(joined), "words": len(joined.split()),
            "issues": dict(sorted(counts.items()))}


def cost_table(run: RunInfo) -> dict[str, Any]:
    """Chi phí thật và độ tin cậy của một lần chạy, từ report.json và calls.jsonl của nó."""
    cost, committed = run.report["cost"], run.report["chapters_committed"]
    by_role = cost["by_role"]
    variable = by_role.get("writer", 0.0) + by_role.get("outline", 0.0)
    bad: dict[str, int] = {}
    for c in run.calls:
        if c.get("status") != "ok":
            bad[c["status"]] = bad.get(c["status"], 0) + 1
    per = (lambda x: round(x / committed, 6)) if committed else (lambda x: None)
    return {
        "chapters_committed": committed, "chapters_target": run.report["chapters_target"],
        "status": run.report["status"], "stop": run.report.get("stop"),
        "total_usd": round(cost["total_usd"], 6), "usd_per_chapter": per(cost["total_usd"]),
        "writer_usd": round(by_role.get("writer", 0.0), 6),
        "outline_usd": round(by_role.get("outline", 0.0), 6),
        "writer_outline_usd_per_chapter": per(variable),
        "rewrites": run.report["rewrites"], "fallbacks": run.report["fallbacks"],
        "scenes_blocked": run.report["scenes_blocked"], "failed_calls": bad,
        "outline_model": run.meta["models"]["outline"]["model"],
        "writer_model": run.writer_model,
    }


def build_pack(run_dirs: Sequence[Path], seed: int, out: Path, data_sha: str) -> dict[str, Any]:
    if len(run_dirs) != len(LABELS):
        raise ConfigError(f"cần đúng {len(LABELS)} thư mục kết quả, nhận {len(run_dirs)}")
    if (out / "pack_meta.json").exists():
        raise ConfigError(f"{out} đã có gói truyện; dùng thư mục mới")
    runs = [load_run(d) for d in run_dirs]
    _same_world(runs)
    order = list(range(len(runs)))
    random.Random(seed).shuffle(order)
    key: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    (out / "stories").mkdir(parents=True, exist_ok=True)
    for label, index in zip(LABELS, order, strict=True):
        run = runs[index]
        text = story_text(run)
        (out / "stories" / f"{label}.md").write_text(text + "\n", encoding="utf-8", newline="\n")
        key[label] = {"model": run.writer_model, "run": _rel(run.dir),
                      "story_sha256": _sha256(text.encode()), "costs": cost_table(run)}
        metrics[label] = code_metrics(run)
    brief = common_brief(runs[0])
    (out / "brief.md").write_text(brief + "\n", encoding="utf-8", newline="\n")
    _write_json(out / "key.json", key)  # KHOÁ GIẢI NHÃN: giám khảo không bao giờ đọc file này
    _write_json(out / "code_metrics.json", metrics)
    meta = {"bench": "F", "seed": seed, "judge_yaml_sha256": data_sha, "git": git_state(),
            "brief_sha256": _sha256(brief.encode()), "runs": [_rel(d) for d in run_dirs]}
    _write_json(out / "pack_meta.json", meta)
    return meta


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                    newline="\n")


# --- yêu cầu, schema và kiểm phản hồi ---------------------------------------------------------


def wrap_story(text: str, label: str | None = None) -> str:
    """Truyện là dữ liệu: escape &, <, > để không đóng khối sớm (như khối player_data, D-12)."""
    attr = f' nhan="{label}"' if label else ""
    return f"<{STORY_TAG}{attr}>\n{html.escape(normalize_dashes(text), quote=False)}\n</{STORY_TAG}>"


def _criterion_text(data: BakeoffData) -> str:
    parts = ["## Tiêu chí (thang 1–5, điểm cao là tốt)"]
    for c in data.criteria:
        block = [f"### {c.id} ({c.label})", c.description.strip()]
        block += [f"Mốc {k}: {v}" for k, v in sorted(c.anchors.items())]
        parts.append("\n".join(block))
    return "\n\n".join(parts)


_OUTPUT = f"""## Đầu ra
Trả về JSON đúng schema. Mọi câu trích là nguyên văn, chép đúng từng chữ từ khối <{STORY_TAG}>
đang nói tới, hoặc "{NO_QUOTE}"."""


def system_text(data: BakeoffData, kind: str) -> str:
    head = {SOLO: data.solo_instructions, COMPARE: data.compare_instructions,
            VALUE: data.value_instructions}[kind].strip()
    return "\n\n".join([head, _criterion_text(data), _OUTPUT])


def _score_prop() -> dict[str, Any]:
    return {"type": "object", "properties": {
        "quote": {"type": "string"}, "reason": {"type": "string"},
        "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]}},
        "required": ["quote", "reason", "score"], "additionalProperties": False}


def _object(props: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": dict(props), "required": list(props),
            "additionalProperties": False}


def solo_schema(data: BakeoffData) -> dict[str, Any]:
    return _object({cid: _score_prop() for cid in data.ids})


def compare_schema(data: BakeoffData) -> dict[str, Any]:
    label = {"type": "string", "enum": list(LABELS)}
    return _object({
        "ranking": {"type": "array", "items": label},
        "reason": {"type": "string"},
        "per_criterion": _object({cid: _object({"best": label, "worst": label,
                                                "reason": {"type": "string"}})
                                  for cid in data.ids}),
        "evidence": {"type": "array", "items": _object({"label": label,
                                                         "quote": {"type": "string"}})},
    })


def value_schema(data: BakeoffData) -> dict[str, Any]:
    story = _object({"verdict": {"type": "string", "enum": list(VERDICTS)},
                     "reason": {"type": "string"}})
    return _object({
        "recommendation": {"type": "string", "enum": list(LABELS)},
        "per_story": _object({label: story for label in LABELS}),
        "reason": {"type": "string"},
        "caveats": {"type": "array", "items": {"type": "string"}},
    })


SCHEMAS: dict[str, Callable[[BakeoffData], dict[str, Any]]] = {
    SOLO: solo_schema, COMPARE: compare_schema, VALUE: value_schema}


def judge_request(data: BakeoffData, kind: str, blocks: Sequence[str]) -> dict[str, Any]:
    """Không có tên model viết; không temperature (Sonnet 5.5 không nhận), không fallbacks (D-25).
    Đề bài chung là khối đầu của tin nhắn và nằm trong cache cùng system."""
    judge = data.judge
    content: list[dict[str, Any]] = [{"type": "text", "text": blocks[0],
                                      "cache_control": {"type": "ephemeral"}}]
    content += [{"type": "text", "text": b} for b in blocks[1:]]
    return {
        "model": judge.model, "max_tokens": judge.max_tokens,
        "thinking": {"type": judge.thinking},
        "output_config": {"effort": judge.effort,
                          "format": {"type": "json_schema", "schema": SCHEMAS[kind](data)}},
        "system": [{"type": "text", "text": system_text(data, kind),
                    "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": content}],
    }


class VerdictError(ValueError):
    """JSON của giám khảo không khớp schema đã khai."""


def _load(text: str) -> dict[str, Any]:
    try:
        out = json.loads(text)
    except json.JSONDecodeError as e:
        raise VerdictError(f"không phải JSON: {e}") from None
    if not isinstance(out, dict):
        raise VerdictError("gốc JSON phải là object")
    return out


def _exact_keys(obj: Any, keys: Sequence[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict) or sorted(obj) != sorted(keys):
        got = sorted(obj) if isinstance(obj, dict) else type(obj).__name__
        raise VerdictError(f"{where}: khoá {got} khác {sorted(keys)}")
    return obj


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise VerdictError(f"{where}: phải là chuỗi")
    return value


def _label(value: Any, where: str) -> str:
    if value not in LABELS:
        raise VerdictError(f"{where}: nhãn {value!r} ngoài {LABELS}")
    return value


def parse_solo(text: str, data: BakeoffData) -> dict[str, dict[str, Any]]:
    obj = _exact_keys(_load(text), data.ids, "solo")
    out = {}
    for cid in data.ids:
        item = _exact_keys(obj[cid], ["quote", "reason", "score"], cid)
        score = item["score"]
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            raise VerdictError(f"{cid}: điểm {score!r} ngoài thang 1–5")
        out[cid] = {"score": score, "quote": _text(item["quote"], cid),
                    "reason": _text(item["reason"], cid)}
    return out


def parse_compare(text: str, data: BakeoffData) -> dict[str, Any]:
    obj = _exact_keys(_load(text), ["ranking", "reason", "per_criterion", "evidence"], "compare")
    ranking = obj["ranking"]
    if not isinstance(ranking, list) or sorted(map(str, ranking)) != sorted(LABELS):
        raise VerdictError(f"ranking phải là hoán vị của {LABELS}, nhận {ranking!r}")
    per = _exact_keys(obj["per_criterion"], data.ids, "per_criterion")
    per_out = {}
    for cid in data.ids:
        item = _exact_keys(per[cid], ["best", "worst", "reason"], cid)
        best, worst = _label(item["best"], f"{cid}.best"), _label(item["worst"], f"{cid}.worst")
        if best == worst:
            raise VerdictError(f"{cid}: tốt nhất và kém nhất cùng là {best}")
        per_out[cid] = {"best": best, "worst": worst, "reason": _text(item["reason"], cid)}
    evidence = obj["evidence"]
    if not isinstance(evidence, list):
        raise VerdictError("evidence phải là mảng")
    ev_out = []
    for i, item in enumerate(evidence):
        item = _exact_keys(item, ["label", "quote"], f"evidence[{i}]")
        ev_out.append({"label": _label(item["label"], f"evidence[{i}]"),
                       "quote": _text(item["quote"], f"evidence[{i}]")})
    return {"ranking": list(ranking), "reason": _text(obj["reason"], "reason"),
            "per_criterion": per_out, "evidence": ev_out}


def parse_value(text: str, data: BakeoffData) -> dict[str, Any]:
    obj = _exact_keys(_load(text), ["recommendation", "per_story", "reason", "caveats"], "value")
    stories = _exact_keys(obj["per_story"], LABELS, "per_story")
    per = {}
    for label in LABELS:
        item = _exact_keys(stories[label], ["verdict", "reason"], label)
        if item["verdict"] not in VERDICTS:
            raise VerdictError(f"{label}.verdict {item['verdict']!r} ngoài {VERDICTS}")
        per[label] = {"verdict": item["verdict"], "reason": _text(item["reason"], label)}
    caveats = obj["caveats"]
    if not isinstance(caveats, list) or not all(isinstance(c, str) for c in caveats):
        raise VerdictError("caveats phải là mảng chuỗi")
    return {"recommendation": _label(obj["recommendation"], "recommendation"), "per_story": per,
            "reason": _text(obj["reason"], "reason"), "caveats": list(caveats)}


PARSERS: dict[str, Callable[[str, BakeoffData], Any]] = {
    SOLO: parse_solo, COMPARE: parse_compare, VALUE: parse_value}


def check_quotes(kind: str, parsed: Any, texts: Mapping[str, str]) -> dict[str, Any]:
    """Câu trích có thật trong truyện được nhắc không (G3). True/False; None là "không có".
    Chỉ đếm là sai cho truyện đúng nhãn, không tin trích ở truyện khác."""
    if kind == SOLO:
        return {cid: quote_found(v["quote"], normalize_dashes(texts["story"]))
                for cid, v in parsed.items()}
    if kind == COMPARE:
        return {"evidence": [quote_found(e["quote"], normalize_dashes(texts[e["label"]]))
                             for e in parsed["evidence"]]}
    return {}


# --- gọi giám khảo ----------------------------------------------------------------------------


def _now() -> str:
    from datetime import datetime

    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class Unit:
    """Một lượt gọi giám khảo. `key` định danh ổn định để chạy tiếp không chấm lại."""

    kind: str
    key: str
    labels: tuple[str, ...]  # nhãn truyện đưa vào, theo thứ tự trình bày


def plan_units() -> list[Unit]:
    solo = [Unit(SOLO, f"{SOLO}:{label}", (label,)) for label in LABELS]
    forward, backward = LABELS, tuple(reversed(LABELS))
    compare = [Unit(COMPARE, f"{COMPARE}:{''.join(order)}", order) for order in (forward, backward)]
    return [*solo, *compare]


class Bakeoff:
    def __init__(
        self, data: BakeoffData, pack: Path, store: Store, client: Any, *, budget: Budget,
        workspace_id: SecretStr | None = None, log: Callable[[str], None] = print,
        sleep: Callable[[float], Any] = asyncio.sleep, clock: Callable[[], float] = time.perf_counter,
        rng: random.Random | None = None,
    ) -> None:
        self.data, self.pack, self.store, self.client = data, pack, store, client
        self.budget, self.workspace_id, self._log = budget, workspace_id, log
        self._sleep, self._clock, self._rng = sleep, clock, rng or random.Random()
        self.brief = (pack / "brief.md").read_text(encoding="utf-8").strip()
        self.texts = {label: (pack / "stories" / f"{label}.md").read_text(encoding="utf-8").strip()
                      for label in LABELS}
        self.stop: tuple[str, str] | None = None

    # -- đơn vị --

    def done(self) -> set[str]:
        return {r["unit"] for r in self.store.rows(RESULTS_FILE) if r["status"] != "error"}

    def request_for(self, unit: Unit, extra: str = "") -> dict[str, Any]:
        blocks = [f"# Đề bài chung\n\n{self.brief}"]
        if unit.kind == SOLO:
            blocks.append(f"# Truyện\n\n{wrap_story(self.texts[unit.labels[0]])}")
        else:
            blocks.append("# Ba truyện\n\n" + "\n\n".join(
                wrap_story(self.texts[label], label) for label in unit.labels))
        if extra:
            blocks.append(extra)
        return judge_request(self.data, unit.kind, blocks)

    async def run_units(self) -> int:
        finished = self.done()
        for unit in plan_units():
            if unit.key in finished:
                continue
            if not await self._run(unit, self.request_for(unit), self._texts_for(unit)):
                break
        return self._exit()

    def _texts_for(self, unit: Unit) -> dict[str, str]:
        return {"story": self.texts[unit.labels[0]]} if unit.kind == SOLO else dict(self.texts)

    async def run_value(self, extra: str) -> int:
        unit = Unit(VALUE, VALUE, LABELS)
        if unit.key not in self.done():
            await self._run(unit, self.request_for(unit, extra), {})
        return self._exit()

    def _exit(self) -> int:
        if self.stop is None:
            return EXIT_OK
        return EXIT_BUDGET if self.stop[0] == "budget" else EXIT_ABORT

    # -- một lượt có thử lại --

    async def _run(self, unit: Unit, request: dict[str, Any], texts: Mapping[str, str]) -> bool:
        estimate = judge_estimate(request)
        unknown = 0.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                held = self.budget.reserve(estimate)
            except BudgetExceeded as e:
                return self._halt("budget", str(e))
            started = self._clock()
            workspace = self.workspace_id.get_secret_value() if self.workspace_id else None
            try:
                msg = await _anthropic_create(self.client, request, workspace)
            except WritoryError as e:
                billed = estimate if _maybe_billed(e) else 0.0
                self.budget.settle(held, billed)
                unknown += billed
                if e.code in RETRY_ON and attempt < MAX_ATTEMPTS:
                    cap = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2 ** (attempt - 1))
                    await self._sleep(self._rng.uniform(0, cap))
                    continue
                self._error(unit, e.code.value, e.detail, attempt, unknown)
                # Yêu cầu giống nhau ở mọi lần: lỗi 4xx (trừ 429) hay khoá sai sẽ lặp lại.
                if e.code in FATAL or e.code == ErrorCode.LLM_REQUEST_INVALID:
                    return self._halt("abort", f"{unit.key}: {e.code.value} {e.detail}")
                return True
            except BaseException:
                self.budget.settle(held, estimate)
                raise
            usage = usage_dict(msg.usage)
            cost = judge_cost(self.data.judge.model, usage)
            self.budget.settle(held, cost)
            return self._record(unit, request, msg, usage, cost, attempt, started, unknown, texts)
        raise AssertionError("không tới đây")

    def _record(self, unit: Unit, request: dict[str, Any], msg: Any, usage: dict[str, int],
                cost: float, attempts: int, started: float, unknown: float,
                texts: Mapping[str, str]) -> bool:
        latency = round(self._clock() - started, 3)
        trace = self.store.trace(f"{unit.key.replace(':', '-')}.json", {
            "request": request, "response": msg.to_dict(), "attempts": attempts,
            "latency_s": latency})
        base = {"unit": unit.key, "kind": unit.kind, "labels": list(unit.labels),
                "judge_model": msg.model, "usage": usage, "cost_usd": round(cost, 6),
                "cost_estimated_usd": unknown or None, "attempts": attempts,
                "latency_s": latency, "trace": trace, "stop_reason": msg.stop_reason,
                "time": _now()}
        if msg.model != self.data.judge.model:
            self.store.append(RESULTS_FILE, base | {"status": "error",
                              "error": f"phản hồi mang model {msg.model}"})
            return self._halt("abort", "giám khảo phải cố định nhưng phản hồi mang model khác")
        if msg.stop_reason == "refusal":
            self.store.append(RESULTS_FILE, base | {"status": "judge_refusal"})
            self._log(f"[{unit.key}] giám khảo từ chối")
            return True
        if msg.stop_reason == "max_tokens":
            self._error(unit, "JUDGE_TRUNCATED", f"chạm max_tokens={self.data.judge.max_tokens}",
                        attempts, unknown, cost=cost)
            return True
        body = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            parsed = PARSERS[unit.kind](body, self.data)
        except VerdictError as e:
            self._error(unit, "JUDGE_BAD_JSON", str(e)[:300], attempts, unknown, cost=cost)
            return True
        self.store.append(RESULTS_FILE, base | {
            "status": "ok", "result": parsed, "quote_found": check_quotes(unit.kind, parsed, texts)})
        self._log(f"[{unit.key}] xong, {cost:.4f} USD, {latency:.1f}s")
        return True

    def _error(self, unit: Unit, code: str, detail: str, attempts: int, unknown: float,
               cost: float | None = None) -> None:
        self.store.append(ERRORS_FILE, {"unit": unit.key, "error_type": code, "detail": detail,
                                        "attempts": attempts, "cost_usd": cost,
                                        "cost_estimated_usd": unknown or None, "time": _now()})
        self._log(f"[lỗi {unit.key}] {code} {detail}")

    def _halt(self, kind: str, message: str) -> bool:
        self.stop = (kind, message)
        self._log(f"!! DỪNG ({kind}): {message}")
        return False


# --- khoá điểm mù, bảng chi phí và tổng hợp -----------------------------------------------------


def blind_rows(store: Store) -> list[dict[str, Any]]:
    return [r for r in store.rows(RESULTS_FILE) if r["kind"] in (SOLO, COMPARE)]


def blind_sha256(store: Store) -> str:
    """Băm điểm bước 1 (không gồm giờ, chi phí hay trace), để biết có bị đổi sau khi thấy chi phí."""
    core = [{k: r.get(k) for k in ("unit", "status", "result")} for r in blind_rows(store)]
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def lock_blind_scores(store: Store) -> str:
    """Ghi dấu bước 1 trước khi đưa chi phí. Có dấu rồi mà điểm đã đổi thì từ chối."""
    done = {r["unit"] for r in blind_rows(store) if r["status"] == "ok"}
    missing = [u.key for u in plan_units() if u.key not in done]
    if missing:
        raise ConfigError(f"chấm mù chưa đủ, còn thiếu {missing}: chạy `judge` cho xong trước")
    sha = blind_sha256(store)
    lock = store.root / LOCK_FILE
    if lock.exists():
        old = json.loads(lock.read_text(encoding="utf-8"))["blind_sha256"]
        if old != sha:
            raise ConfigError("điểm chấm mù đã đổi sau khi khoá (value_lock.json): bước 2 từ chối")
        return sha
    _write_json(lock, {"blind_sha256": sha, "time": _now()})
    return sha


def ensure_unlocked(store: Store) -> None:
    if (store.root / LOCK_FILE).exists():
        raise ConfigError("điểm chấm mù đã khoá (value_lock.json): không chấm thêm; dùng "
                          "thư mục kết quả mới")


def ok_results(store: Store, kind: str) -> list[dict[str, Any]]:
    return [r for r in store.rows(RESULTS_FILE) if r["kind"] == kind and r["status"] == "ok"]


def value_context(data: BakeoffData, pack: Path, store: Store) -> str:
    """Điểm đã khoá và chi phí thật, theo nhãn (vẫn mù tên model)."""
    key = _read_json(pack / "key.json")
    metrics = _read_json(pack / "code_metrics.json")
    summary = blind_summary(data, store)
    lines = ["# Kết quả đã khoá", "", "Điểm trung bình theo tiêu chí (chấm riêng từng truyện):"]
    for label in LABELS:
        scores = ", ".join(f"{cid}={summary['solo_mean'][label][cid]:.1f}" for cid in data.ids)
        lines.append(f"- {label}: {scores}")
    lines.append(f"Xếp hạng so sánh (hạng trung bình, 1 là tốt nhất): {summary['mean_rank']}")
    lines += ["", "# Chi phí thật và độ tin cậy (USD)", ""]
    for label in LABELS:
        c = key[label]["costs"]
        lines += [(f"- {label}: {c['chapters_committed']}/{c['chapters_target']} chương, trạng thái "
                  f"{c['status']}; tổng {c['total_usd']} USD, {c['usd_per_chapter']} USD/chương; "
                  f"riêng model viết + dàn ý {c['writer_outline_usd_per_chapter']} USD/chương; "
                  f"viết lại {c['rewrites']}, dự phòng {c['fallbacks']}, cảnh bị chặn "
                  f"{c['scenes_blocked']}; lời gọi lỗi {c['failed_calls'] or 'không'}; "
                  f"lỗi do bộ kiểm văn của repo: {metrics[label]['issues'] or 'không'}")]
    return "\n".join(lines)


def blind_summary(data: BakeoffData, store: Store) -> dict[str, Any]:
    solo = {r["labels"][0]: r["result"] for r in ok_results(store, SOLO)}
    solo_mean = {label: {cid: float(solo[label][cid]["score"]) for cid in data.ids}
                 for label in solo}
    ranks: dict[str, list[int]] = {label: [] for label in LABELS}
    rankings = []
    for r in ok_results(store, COMPARE):
        order = r["result"]["ranking"]
        rankings.append({"presented": r["labels"], "ranking": order})
        for position, label in enumerate(order, start=1):
            ranks[label].append(position)
    mean_rank = {label: round(sum(v) / len(v), 2) for label, v in ranks.items() if v}
    return {"solo_mean": solo_mean, "mean_rank": mean_rank, "rankings": rankings,
            "order_agrees": len({tuple(r["ranking"]) for r in rankings}) == 1 if rankings else None}


def build_summary(data: BakeoffData, pack: Path, store: Store) -> str:
    """Giải nhãn và dựng bảng: model | điểm từng mục | xếp hạng | USD/chương | lỗi."""
    key = _read_json(pack / "key.json")
    metrics = _read_json(pack / "code_metrics.json")
    blind = blind_summary(data, store)
    value = ok_results(store, VALUE)
    head = ["Model", *[c.label for c in data.criteria], "Trung bình", "Hạng so sánh", "USD/chương",
            "Lỗi (code)", "Lỗi lời gọi"]
    rows = []
    for label in sorted(LABELS, key=lambda x: blind["mean_rank"].get(x, 9)):
        scores = blind["solo_mean"].get(label, {})
        mean = sum(scores.values()) / len(scores) if scores else None
        c = key[label]["costs"]
        rows.append([
            f"{key[label]['model']} ({label})",
            *[f"{scores[cid]:.0f}" if cid in scores else "-" for cid in data.ids],
            f"{mean:.2f}" if mean is not None else "-",
            str(blind["mean_rank"].get(label, "-")),
            f"{c['usd_per_chapter']}",
            f"{sum(metrics[label]['issues'].values())}",
            f"{sum(c['failed_calls'].values())}"])
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    lines = ["# Bài F: so 3 model viết trên cùng một thế giới", "", *out, "",
             (f"Hạng so sánh: trung bình của hai lượt thứ tự đảo; hai lượt "
             f"{'đồng ý' if blind['order_agrees'] else 'KHÔNG đồng ý (nghi thiên lệch vị trí)'}.")]
    for r in blind["rankings"]:
        lines.append(f"- trình bày {''.join(r['presented'])}: hạng {' > '.join(r['ranking'])}")
    bad = _bad_quotes(store)
    lines += ["", f"Câu trích giám khảo không có thật trong truyện (G3): {bad}."]
    if value:
        v = value[0]["result"]
        lines += ["", "## Khuyến nghị đáng tiền (bước 2, điểm bước 1 đã khoá)", "",
                  (f"Khuyến nghị: {key[v['recommendation']]['model']} ({v['recommendation']}). "
                  f"{v['reason']}"), ""]
        lines += [f"- {key[lb]['model']}: {s['verdict']}. {s['reason']}"
                  for lb, s in v["per_story"].items()]
        lines += ["", "Điều chưa chắc: " + "; ".join(v["caveats"])]
    lock = store.root / LOCK_FILE
    if lock.exists() and json.loads(lock.read_text(encoding="utf-8"))["blind_sha256"] != (
            blind_sha256(store)):
        lines += ["", "!! Điểm bước 1 đã đổi sau khi khoá."]
    spent = sum(r.get("cost_usd") or 0 for r in store.rows(RESULTS_FILE))
    lines += ["", f"Chi phí giám khảo: {spent:.4f} USD."]
    return "\n".join(lines) + "\n"


def _bad_quotes(store: Store) -> int:
    bad = 0
    for r in store.rows(RESULTS_FILE):
        found = r.get("quote_found") or {}
        values = found.get("evidence", []) if "evidence" in found else list(found.values())
        bad += sum(1 for v in values if v is False)
    return bad


# --- giám khảo giả cho --dry-run ---------------------------------------------------------------


def fake_judge_reply(body: dict[str, Any]) -> dict[str, Any]:
    """Phản hồi Messages API giả theo schema của yêu cầu: điểm giữa thang, xếp hạng theo nhãn."""
    props = body["output_config"]["format"]["schema"]["properties"]
    if "ranking" in props:
        crit = list(props["per_criterion"]["properties"])
        verdict: dict[str, Any] = {
            "ranking": list(LABELS), "reason": "dry-run", "evidence": [],
            "per_criterion": {cid: {"best": LABELS[0], "worst": LABELS[-1], "reason": "dry-run"}
                              for cid in crit}}
    elif "recommendation" in props:
        verdict = {"recommendation": LABELS[0], "reason": "dry-run", "caveats": ["dry-run"],
                   "per_story": {label: {"verdict": VERDICTS[1], "reason": "dry-run"}
                                 for label in LABELS}}
    else:
        verdict = {cid: {"quote": NO_QUOTE, "reason": "dry-run", "score": 3} for cid in props}
    return {
        "id": "msg_dry_run", "type": "message", "role": "assistant", "model": body["model"],
        "content": [{"type": "text", "text": json.dumps(verdict, ensure_ascii=False)}],
        "stop_reason": "end_turn", "stop_sequence": None, "stop_details": None,
        "usage": {"input_tokens": 1000, "output_tokens": 500,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}


# --- dòng lệnh ---------------------------------------------------------------------------------


def _client(args: argparse.Namespace) -> tuple[Any, SecretStr | None]:
    if args.dry_run:
        return mock_judge_client(fake_judge_reply), None
    keys = load_keys(Path(args.env_file), ["anthropic"])
    try:
        import anthropic
    except ImportError:
        raise ConfigError("thiếu gói anthropic: chạy `uv sync --group eval`") from None
    assert keys.anthropic_api_key is not None
    client = anthropic.AsyncAnthropic(api_key=keys.anthropic_api_key.get_secret_value(),
                                      max_retries=0, timeout=HTTP_TIMEOUT_S)
    return client, keys.anthropic_workspace_id


def _budget(store: Store, args: argparse.Namespace) -> Budget:
    if args.budget is None and not args.dry_run:
        raise ConfigError("lượt chấm thật cần --budget (USD)")
    spent = sum(r.get("cost_usd") or 0.0 for r in store.rows(RESULTS_FILE))
    spent += sum((r.get("cost_usd") or 0.0) + (r.get("cost_estimated_usd") or 0.0)
                 for r in store.rows(ERRORS_FILE))
    return Budget("anthropic", float("inf") if args.budget is None else args.budget, spent_usd=spent)


def _store(args: argparse.Namespace) -> Store:
    pack = Path(args.dir)
    if not (pack / "pack_meta.json").exists():
        raise ConfigError(f"{pack} chưa có gói truyện: chạy `pack` trước")
    return Store(pack)


async def _judge(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    store = _store(args)
    ensure_unlocked(store)
    budget = _budget(store, args)
    client, workspace = _client(args)
    try:
        bake = Bakeoff(data, store.root, store, client, budget=budget, workspace_id=workspace)
        return await bake.run_units()
    finally:
        await client.close()


async def _value(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    store = _store(args)
    lock_blind_scores(store)
    budget = _budget(store, args)
    client, workspace = _client(args)
    try:
        bake = Bakeoff(data, store.root, store, client, budget=budget, workspace_id=workspace)
        return await bake.run_value(value_context(data, store.root, store))
    finally:
        await client.close()


def _cmd_pack(args: argparse.Namespace) -> int:
    _, sha = load_data(Path(args.data_dir))
    out = Path(args.out)
    meta = build_pack([Path(d) for d in args.run], args.seed, out, sha)
    print(f"Đã đóng gói 3 truyện vào {out} (nhãn xáo theo seed {meta['seed']}); khoá: key.json")
    return EXIT_OK


def _cmd_summary(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    store = _store(args)
    text = build_summary(data, store.root, store)
    (store.root / "summary.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m writory.quality.bench_bakeoff",
                                description="Bài F: so nhiều model viết (D-101).")
    sub = p.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", help="đóng gói mù ba lần chạy")
    pack.add_argument("--run", action="append", required=True, metavar="DIR",
                      help="thư mục kết quả của bench_run (lặp lại đúng ba lần)")
    pack.add_argument("--seed", type=int, required=True, help="seed xáo nhãn A/B/C")
    pack.add_argument("--out", required=True, help="thư mục kết quả mới của bài F")
    for name, helptext in (("judge", "chấm mù: solo ×3 + compare ×2"),
                           ("value", "khuyến nghị đáng tiền, sau khi khoá điểm mù"),
                           ("summary", "giải nhãn và dựng bảng")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--dir", required=True, help="thư mục kết quả của bài F (đã `pack`)")
        if name != "summary":
            sp.add_argument("--budget", type=float, help="trần USD Anthropic (bắt buộc khi chạy thật)")
            sp.add_argument("--dry-run", action="store_true", help="giám khảo giả, không key")
            sp.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    for sp in sub.choices.values():
        sp.add_argument("--data-dir", default=str(DATA_DIR))
    return p


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if getattr(args, "budget", None) is not None and args.budget <= 0:
        print("Lỗi: --budget phải > 0", file=sys.stderr)
        return EXIT_CONFIG
    try:
        if args.command == "pack":
            return _cmd_pack(args)
        if args.command == "summary":
            return _cmd_summary(args)
        return asyncio.run({"judge": _judge, "value": _value}[args.command](args))
    except ConfigError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
