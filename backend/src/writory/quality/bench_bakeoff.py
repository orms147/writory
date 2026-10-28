"""Bài F: so nhiều model viết trên cùng một thế giới, giám khảo là Claude hoặc Meta Muse Wonder
(D-101, D-108, docs/eval.md).

Các lượt viết chạy bằng `writory.pipeline.bench_run` (`--setup-only` rồi `--setup-from`, đổi model
bằng `--writer-model` và `--outline-model`). Module này lo phần sau:

    pack     hai hay ba thư mục kết quả -> truyện gắn nhãn A/B(/C) ngẫu nhiên + khoá giải nhãn;
             mỗi thư mục kết quả của bài F dành cho đúng một giám khảo (`--judge`, D-108)
    judge    chấm mù: mỗi truyện một lượt `solo`, rồi `compare` tất cả hai lần với thứ tự đảo
    value    sau khi điểm mù đã khoá: đưa chi phí thật, hỏi khuyến nghị "đáng tiền"
    summary  giải nhãn, bảng tổng hợp; `--with` thêm giám khảo khác trên cùng truyện: bảng điểm
             từng giám khảo, độ đồng thuận, điểm gộp

Giám khảo không thấy tên model ở bất kỳ bước nào. Truyện là dữ liệu: bọc trong khối và escape như
mọi chữ ngoài (G4). Câu trích của giám khảo phải có thật trong truyện (G3), kiểm bằng code.
Dùng lại hạ tầng của bài D (`bench_d`): giá giám khảo, ngân sách giữ chỗ, kiểm câu trích."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import itertools
import json
import math
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveFloat,
    PositiveInt,
    ValidationError,
    model_validator,
)
from pydantic import Field as PField
from pydantic.types import SecretStr

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.cost import EST_CHARS_PER_TOKEN
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
LABELS = ("A", "B", "C")  # nhãn tối đa; gói hai truyện dùng A, B (`labels_for`, ghi ở pack_meta)
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


ANTHROPIC_EFFORTS = ("low", "medium", "high", "xhigh", "max")
META_EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")  # Meta từ chối `none` (HTTP 400)
ANTHROPIC_MAX_TOKENS = 21000  # SDK chặn yêu cầu không stream lớn hơn


class JudgePrice(_Strict):
    """USD / 1 triệu token của giám khảo tính theo token (Meta); token suy luận nằm trong `output`."""

    input: PositiveFloat
    cached_input: PositiveFloat
    output: PositiveFloat


class JudgeSpec(_Strict):
    id: str
    provider: Literal["anthropic", "meta"]
    model: str
    effort: str
    thinking: str | None = None
    max_tokens: PositiveInt
    price: JudgePrice | None = None  # bắt buộc với Meta; giá Claude ở bench_d.JUDGE_PRICES

    @model_validator(mode="after")
    def _provider_rules(self) -> JudgeSpec:
        if self.provider == "anthropic":
            if self.model not in JUDGE_PRICES:
                raise ValueError(f"chưa có giá cho giám khảo {self.model} (bench_d.JUDGE_PRICES)")
            if self.thinking is None:
                raise ValueError("giám khảo Anthropic cần `thinking`")
            if self.effort not in ANTHROPIC_EFFORTS:
                raise ValueError(f"effort {self.effort!r} ngoài {ANTHROPIC_EFFORTS}")
            if self.max_tokens > ANTHROPIC_MAX_TOKENS:
                raise ValueError(f"max_tokens vượt {ANTHROPIC_MAX_TOKENS} (SDK chặn không stream)")
        else:
            if self.price is None:
                raise ValueError("giám khảo Meta cần `price` (USD / 1 triệu token)")
            if self.effort not in META_EFFORTS:
                raise ValueError(f"effort {self.effort!r} ngoài {META_EFFORTS} (Meta từ chối `none`)")
            if "contributor" in self.model:
                raise ValueError("không dùng bản -contributor: Meta huấn luyện bằng dữ liệu của bản đó")
        return self


class BakeoffData(_Strict):
    version: PositiveInt
    judge: JudgeSpec  # giám khảo chính (id mặc định của `pack`)
    extra_judges: list[JudgeSpec] = PField(default_factory=list)
    criteria: list[Criterion] = PField(min_length=1)
    solo_instructions: str
    compare_instructions: str
    value_instructions: str

    @model_validator(mode="after")
    def _unique_ids(self) -> BakeoffData:
        ids = [c.id for c in self.criteria]
        if len(set(ids)) != len(ids):
            raise ValueError("id tiêu chí bị trùng")
        judge_ids = [j.id for j in self.judges]
        if len(set(judge_ids)) != len(judge_ids):
            raise ValueError("id giám khảo bị trùng")
        return self

    @property
    def ids(self) -> list[str]:
        return [c.id for c in self.criteria]

    @property
    def judges(self) -> list[JudgeSpec]:
        return [self.judge, *self.extra_judges]

    def judge_by_id(self, judge_id: str) -> JudgeSpec:
        for j in self.judges:
            if j.id == judge_id:
                return j
        raise ConfigError(f"không có giám khảo {judge_id!r}; có: {', '.join(j.id for j in self.judges)}")


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

    @property
    def identity(self) -> tuple[Any, ...]:
        """Cái làm hai lần chạy khác nhau (D-109): model viết và dàn ý, hướng dẫn văn phong, các file
        của biến thể đề. Hash, không phải tên: hai tên cùng nội dung là một lần chạy. Meta cũ chưa
        ghi hai trường sau thì coi như đề mặc định."""
        variant = self.meta.get("prompt_variant") or {}
        return (self.writer_model, self.meta["models"]["outline"]["model"],
                self.meta.get("style_guide_sha256"), tuple(sorted((variant.get("files") or {}).items())))


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


def _same_world(runs: Sequence[RunInfo], *, replicates: bool = False) -> None:
    """Cùng thế giới là điều kiện của phép so: cùng đề, cùng seed, cùng khởi tạo. `replicates`: cho
    phép hai lần chạy cùng cấu hình (cùng model, đề viết) khác thư mục, để đo nhiễu giữa các lần
    viết; cùng thế giới vẫn bắt buộc, và mỗi lần chạy phải là một thư mục riêng."""
    for field_name, get in (("sha256 của đề", lambda r: r.meta["scenario"]["sha256"]),
                            ("seed", lambda r: r.meta["seed"]),
                            ("--setup-from", lambda r: r.meta.get("setup_from"))):
        values = {json.dumps(get(r)) for r in runs}
        if len(values) != 1 or (field_name == "--setup-from" and values == {"null"}):
            raise ConfigError(f"các lần chạy không cùng thế giới: {field_name} khác nhau hoặc "
                              f"trống ({sorted(values)})")
    if replicates:
        if len({r.dir.resolve() for r in runs}) != len(runs):
            raise ConfigError("--replicates cần mỗi lần chạy một thư mục riêng, nhận cùng một thư mục "
                              "hai lần")
    elif len({r.identity for r in runs}) != len(runs):
        raise ConfigError("hai lần chạy cùng model viết và cùng đề (hướng dẫn văn phong, biến thể "
                          f"đề): {[r.writer_model for r in runs]}; đo nhiễu giữa các lần viết thì "
                          "thêm --replicates (cùng cấu hình, khác thư mục)")


def display_names(runs: Sequence[RunInfo]) -> list[str]:
    """Tên hiện ở `key.json` và bảng tổng hợp. Model nào chỉ có một lần chạy thì giữ tên model; nhiều
    lần chạy cùng model (khác đề viết, D-109) thì thêm hướng dẫn văn phong và biến thể để phân biệt."""
    names = []
    for r in runs:
        if sum(o.writer_model == r.writer_model for o in runs) == 1:
            names.append(r.writer_model)
            continue
        parts = []
        if r.meta.get("style_guide_sha256"):
            parts.append(f"style:{r.meta['style_guide_sha256'][:8]}")
        variant = r.meta.get("prompt_variant") or {}
        if variant.get("name"):
            parts.append(f"variant:{variant['name']}")
        if sum(o.identity == r.identity for o in runs) > 1:  # cùng cấu hình: phân biệt bằng thư mục
            parts.append(f"run:{r.dir.name}")
        names.append(f"{r.writer_model} [{'; '.join(parts) or 'đề mặc định'}]")
    return names


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


def build_pack(run_dirs: Sequence[Path], seed: int, out: Path, data_sha: str,
               judge_id: str | None = None, data: BakeoffData | None = None, *,
               replicates: bool = False) -> dict[str, Any]:
    """Gói truyện mù cho MỘT giám khảo (`judge_id`, mặc định giám khảo chính của judge.yaml).
    `replicates`: các lần chạy là cùng một cấu hình lặp lại (đo nhiễu giữa các lần viết)."""
    judge = (data or load_data()[0]).judge_by_id(judge_id) if judge_id else (
        data or load_data()[0]).judge
    if not 2 <= len(run_dirs) <= len(LABELS):
        raise ConfigError(f"cần 2 hoặc {len(LABELS)} thư mục kết quả, nhận {len(run_dirs)}")
    labels = labels_for(len(run_dirs))
    if (out / "pack_meta.json").exists():
        raise ConfigError(f"{out} đã có gói truyện; dùng thư mục mới")
    runs = [load_run(d) for d in run_dirs]
    _same_world(runs, replicates=replicates)
    order = list(range(len(runs)))
    random.Random(seed).shuffle(order)
    key: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    (out / "stories").mkdir(parents=True, exist_ok=True)
    shown = display_names(runs)
    for label, index in zip(labels, order, strict=True):
        run = runs[index]
        text = story_text(run)
        (out / "stories" / f"{label}.md").write_text(text + "\n", encoding="utf-8", newline="\n")
        key[label] = {"model": shown[index], "writer_model": run.writer_model, "run": _rel(run.dir),
                      "story_sha256": _sha256(text.encode()), "costs": cost_table(run)}
        metrics[label] = code_metrics(run)
    brief = common_brief(runs[0])
    (out / "brief.md").write_text(brief + "\n", encoding="utf-8", newline="\n")
    _write_json(out / "key.json", key)  # KHOÁ GIẢI NHÃN: giám khảo không bao giờ đọc file này
    _write_json(out / "code_metrics.json", metrics)
    meta = {"bench": "F", "seed": seed, "judge_yaml_sha256": data_sha, "git": git_state(),
            "brief_sha256": _sha256(brief.encode()), "runs": [_rel(d) for d in run_dirs],
            "labels": list(labels), "judge": judge.id, "replicates": replicates}
    _write_json(out / "pack_meta.json", meta)
    return meta


def labels_for(count: int) -> tuple[str, ...]:
    return LABELS[:count]


def pack_labels(pack: Path) -> tuple[str, ...]:
    """Nhãn của một gói (`pack_meta.json`); gói cũ không ghi thì A, B, C."""
    meta = pack / "pack_meta.json"
    if not meta.exists():
        return LABELS
    return tuple(json.loads(meta.read_text(encoding="utf-8")).get("labels", LABELS))


LEGACY_JUDGE_ID = "sonnet"  # gói tạo trước D-108 không ghi giám khảo


def pack_judge_id(pack: Path) -> str:
    """Giám khảo mà gói này dành cho (`pack_meta.json`)."""
    meta = pack / "pack_meta.json"
    if not meta.exists():
        return LEGACY_JUDGE_ID
    return json.loads(meta.read_text(encoding="utf-8")).get("judge", LEGACY_JUDGE_ID)


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


def solo_schema(data: BakeoffData, labels: Sequence[str] = LABELS) -> dict[str, Any]:
    return _object({cid: _score_prop() for cid in data.ids})


def compare_schema(data: BakeoffData, labels: Sequence[str] = LABELS) -> dict[str, Any]:
    label = {"type": "string", "enum": list(labels)}
    return _object({
        "ranking": {"type": "array", "items": label},
        "reason": {"type": "string"},
        "per_criterion": _object({cid: _object({"best": label, "worst": label,
                                                "reason": {"type": "string"}})
                                  for cid in data.ids}),
        "evidence": {"type": "array", "items": _object({"label": label,
                                                         "quote": {"type": "string"}})},
    })


def value_schema(data: BakeoffData, labels: Sequence[str] = LABELS) -> dict[str, Any]:
    story = _object({"verdict": {"type": "string", "enum": list(VERDICTS)},
                     "reason": {"type": "string"}})
    return _object({
        "recommendation": {"type": "string", "enum": list(labels)},
        "per_story": _object({label: story for label in labels}),
        "reason": {"type": "string"},
        "caveats": {"type": "array", "items": {"type": "string"}},
    })


SCHEMAS: dict[str, Callable[[BakeoffData, Sequence[str]], dict[str, Any]]] = {
    SOLO: solo_schema, COMPARE: compare_schema, VALUE: value_schema}


def judge_request(data: BakeoffData, kind: str, blocks: Sequence[str],
                  labels: Sequence[str] = LABELS, spec: JudgeSpec | None = None) -> dict[str, Any]:
    """Yêu cầu cho giám khảo Anthropic. Không có tên model viết; không temperature (Sonnet 5.5
    không nhận), không fallbacks (D-25). Đề bài chung là khối đầu của tin nhắn và nằm trong cache
    cùng system."""
    judge = spec or data.judge
    content: list[dict[str, Any]] = [{"type": "text", "text": blocks[0],
                                      "cache_control": {"type": "ephemeral"}}]
    content += [{"type": "text", "text": b} for b in blocks[1:]]
    return {
        "model": judge.model, "max_tokens": judge.max_tokens,
        "thinking": {"type": judge.thinking},
        "output_config": {"effort": judge.effort,
                          "format": {"type": "json_schema", "schema": SCHEMAS[kind](data, labels)}},
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


def _label(value: Any, where: str, labels: Sequence[str] = LABELS) -> str:
    if value not in labels:
        raise VerdictError(f"{where}: nhãn {value!r} ngoài {tuple(labels)}")
    return value


def parse_solo(text: str, data: BakeoffData,
               labels: Sequence[str] = LABELS) -> dict[str, dict[str, Any]]:
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


def parse_compare(text: str, data: BakeoffData, labels: Sequence[str] = LABELS) -> dict[str, Any]:
    obj = _exact_keys(_load(text), ["ranking", "reason", "per_criterion", "evidence"], "compare")
    ranking = obj["ranking"]
    if not isinstance(ranking, list) or sorted(map(str, ranking)) != sorted(labels):
        raise VerdictError(f"ranking phải là hoán vị của {tuple(labels)}, nhận {ranking!r}")
    per = _exact_keys(obj["per_criterion"], data.ids, "per_criterion")
    per_out = {}
    for cid in data.ids:
        item = _exact_keys(per[cid], ["best", "worst", "reason"], cid)
        best = _label(item["best"], f"{cid}.best", labels)
        worst = _label(item["worst"], f"{cid}.worst", labels)
        if best == worst:
            raise VerdictError(f"{cid}: tốt nhất và kém nhất cùng là {best}")
        per_out[cid] = {"best": best, "worst": worst, "reason": _text(item["reason"], cid)}
    evidence = obj["evidence"]
    if not isinstance(evidence, list):
        raise VerdictError("evidence phải là mảng")
    ev_out = []
    for i, item in enumerate(evidence):
        item = _exact_keys(item, ["label", "quote"], f"evidence[{i}]")
        ev_out.append({"label": _label(item["label"], f"evidence[{i}]", labels),
                       "quote": _text(item["quote"], f"evidence[{i}]")})
    return {"ranking": list(ranking), "reason": _text(obj["reason"], "reason"),
            "per_criterion": per_out, "evidence": ev_out}


def parse_value(text: str, data: BakeoffData, labels: Sequence[str] = LABELS) -> dict[str, Any]:
    obj = _exact_keys(_load(text), ["recommendation", "per_story", "reason", "caveats"], "value")
    stories = _exact_keys(obj["per_story"], labels, "per_story")
    per = {}
    for label in labels:
        item = _exact_keys(stories[label], ["verdict", "reason"], label)
        if item["verdict"] not in VERDICTS:
            raise VerdictError(f"{label}.verdict {item['verdict']!r} ngoài {VERDICTS}")
        per[label] = {"verdict": item["verdict"], "reason": _text(item["reason"], label)}
    caveats = obj["caveats"]
    if not isinstance(caveats, list) or not all(isinstance(c, str) for c in caveats):
        raise VerdictError("caveats phải là mảng chuỗi")
    return {"recommendation": _label(obj["recommendation"], "recommendation", labels),
            "per_story": per,
            "reason": _text(obj["reason"], "reason"), "caveats": list(caveats)}


PARSERS: dict[str, Callable[[str, BakeoffData, Sequence[str]], Any]] = {
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


# --- nhà cung cấp giám khảo -----------------------------------------------------------------------


@dataclass(frozen=True)
class JudgeReply:
    """Phản hồi của giám khảo, chuẩn hoá giữa các nhà cung cấp. `stop_reason`: end_turn,
    max_tokens hay refusal. `usage` dùng khoá của Anthropic (input_tokens không gồm phần cache,
    cache_read_input_tokens, output_tokens) cộng `reasoning_tokens` nếu nhà cung cấp báo."""

    text: str
    model: str
    stop_reason: str | None
    usage: dict[str, int]
    raw: dict[str, Any]


def scrub(text: str, secret: str) -> str:
    """Bỏ khoá khỏi chữ sắp ghi hay in (G7): lỗi của nhà cung cấp có thể lặp lại khoá."""
    return text.replace(secret, "[key]") if secret else text


def _tokens_est(chars: int) -> int:
    return math.ceil(chars / EST_CHARS_PER_TOKEN)


class AnthropicProvider:
    """Giám khảo Claude qua Messages API (D-101): hạ tầng của bài D."""

    def __init__(self, client: Any, spec: JudgeSpec, workspace_id: SecretStr | None = None) -> None:
        self.client, self.spec, self.workspace_id = client, spec, workspace_id

    @staticmethod
    def build_request(data: BakeoffData, spec: JudgeSpec, kind: str, blocks: Sequence[str],
                      labels: Sequence[str]) -> dict[str, Any]:
        return judge_request(data, kind, blocks, labels, spec)

    async def create(self, request: dict[str, Any]) -> JudgeReply:
        workspace = self.workspace_id.get_secret_value() if self.workspace_id else None
        msg = await _anthropic_create(self.client, request, workspace)
        text = next((b.text for b in msg.content if b.type == "text"), "")
        return JudgeReply(text, msg.model, msg.stop_reason, usage_dict(msg.usage), msg.to_dict())

    def cost(self, usage: Mapping[str, int]) -> float:
        return judge_cost(self.spec.model, dict(usage))

    def estimate(self, request: dict[str, Any]) -> float:
        return judge_estimate(request)


META_BASE_URL = "https://api.meta.ai/v1"
_META_STOP = {"stop": "end_turn", "length": "max_tokens", "content_filter": "refusal"}


class MetaProvider:
    """Giám khảo Meta Muse Wonder qua API tương thích OpenAI (D-108): `POST /chat/completions`,
    bearer. Structured output bằng `response_format` json_schema strict (chế độ `json_object` bỏ
    qua schema). Khoá chỉ nằm trong header; chữ lỗi luôn qua `scrub`."""

    def __init__(self, http: httpx.AsyncClient, key: SecretStr, spec: JudgeSpec, *,
                 base_url: str = META_BASE_URL) -> None:
        self.http, self.key, self.spec, self.base_url = http, key, spec, base_url

    @staticmethod
    def build_request(data: BakeoffData, spec: JudgeSpec, kind: str, blocks: Sequence[str],
                      labels: Sequence[str]) -> dict[str, Any]:
        return {
            "model": spec.model, "max_tokens": spec.max_tokens, "reasoning_effort": spec.effort,
            "messages": [{"role": "system", "content": system_text(data, kind)},
                         {"role": "user", "content": "\n\n".join(blocks)}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": f"bakeoff_{kind}", "strict": True, "schema": SCHEMAS[kind](data, labels)}},
        }

    async def create(self, request: dict[str, Any]) -> JudgeReply:
        secret = self.key.get_secret_value()
        try:
            resp = await self.http.post(f"{self.base_url}/chat/completions", json=request,
                                        headers={"Authorization": f"Bearer {secret}"})
        except httpx.HTTPError as e:  # không có phản hồi: yêu cầu có thể đã chạy (xem _maybe_billed)
            raise WritoryError(ErrorCode.LLM_UNAVAILABLE, detail=type(e).__name__) from None
        if resp.status_code != 200:
            raise self._error(resp, secret)
        try:
            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
            text = message.get("content") or ""
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail="phản hồi Meta không đúng dạng chat completion") from None
        usage = data.get("usage") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        normalised = {
            "input_tokens": max((usage.get("prompt_tokens") or 0) - cached, 0),
            "output_tokens": usage.get("completion_tokens") or 0,
            "cache_creation_input_tokens": 0, "cache_read_input_tokens": cached,
            "reasoning_tokens": reasoning,
        }
        finish = choice.get("finish_reason")
        stop = "refusal" if message.get("refusal") else _META_STOP.get(finish, finish)
        return JudgeReply(text, data.get("model") or "", stop, normalised, data)

    @staticmethod
    def _error(resp: httpx.Response, secret: str) -> WritoryError:
        try:
            body = resp.json()
            message = body["error"]["message"] if isinstance(body.get("error"), dict) else resp.text
        except (ValueError, KeyError, AttributeError):
            message = resp.text
        status = resp.status_code
        code = {401: ErrorCode.LLM_AUTH_FAILED, 403: ErrorCode.LLM_AUTH_FAILED,
                429: ErrorCode.LLM_RATE_LIMITED}.get(status)
        code = code or (ErrorCode.LLM_UNAVAILABLE if status >= 500 else ErrorCode.LLM_REQUEST_INVALID)
        return WritoryError(code, detail=scrub(f"HTTP {status}: {message}", secret)[:400])

    def cost(self, usage: Mapping[str, int]) -> float:
        price = self.spec.price
        assert price is not None  # JudgeSpec đã kiểm
        return (usage["input_tokens"] * price.input
                + usage["cache_read_input_tokens"] * price.cached_input
                + usage["output_tokens"] * price.output) / 1e6

    def estimate(self, request: dict[str, Any]) -> float:
        """Tối đa: mọi token vào tính giá đầy đủ, token ra (cả suy luận) chạm max_tokens."""
        price = self.spec.price
        assert price is not None
        chars = len(json.dumps(request["messages"], ensure_ascii=False)) + len(
            json.dumps(request["response_format"], ensure_ascii=False))
        return (_tokens_est(chars) * price.input + request["max_tokens"] * price.output) / 1e6


JudgeProvider = AnthropicProvider | MetaProvider


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


def plan_units(labels: Sequence[str] = LABELS) -> list[Unit]:
    labels = tuple(labels)
    solo = [Unit(SOLO, f"{SOLO}:{label}", (label,)) for label in labels]
    forward, backward = labels, tuple(reversed(labels))
    compare = [Unit(COMPARE, f"{COMPARE}:{''.join(order)}", order) for order in (forward, backward)]
    return [*solo, *compare]


class Bakeoff:
    def __init__(
        self, data: BakeoffData, pack: Path, store: Store, client: Any = None, *, budget: Budget,
        provider: JudgeProvider | None = None, spec: JudgeSpec | None = None,
        workspace_id: SecretStr | None = None, log: Callable[[str], None] = print,
        sleep: Callable[[float], Any] = asyncio.sleep, clock: Callable[[], float] = time.perf_counter,
        rng: random.Random | None = None,
    ) -> None:
        """`client`: AsyncAnthropic (giám khảo chính, tương thích trước D-108); giám khảo khác đi
        qua `provider` và `spec`. Một thư mục kết quả dành cho đúng một giám khảo."""
        self.data, self.pack, self.store = data, pack, store
        self.spec = spec or (provider.spec if provider is not None else data.judge)
        self.provider = provider or AnthropicProvider(client, self.spec, workspace_id)
        expected = pack_judge_id(pack)
        if expected != self.spec.id:
            raise ConfigError(f"{pack} dành cho giám khảo {expected!r}, không phải {self.spec.id!r}")
        self.budget, self._log = budget, log
        self._sleep, self._clock, self._rng = sleep, clock, rng or random.Random()
        self.brief = (pack / "brief.md").read_text(encoding="utf-8").strip()
        self.labels = pack_labels(pack)
        self.texts = {label: (pack / "stories" / f"{label}.md").read_text(encoding="utf-8").strip()
                      for label in self.labels}
        self.stop: tuple[str, str] | None = None

    # -- đơn vị --

    def done(self) -> set[str]:
        return {r["unit"] for r in self.store.rows(RESULTS_FILE) if r["status"] != "error"}

    def request_for(self, unit: Unit, extra: str = "") -> dict[str, Any]:
        blocks = [f"# Đề bài chung\n\n{self.brief}"]
        if unit.kind == SOLO:
            blocks.append(f"# Truyện\n\n{wrap_story(self.texts[unit.labels[0]])}")
        else:
            blocks.append("# Các truyện\n\n" + "\n\n".join(
                wrap_story(self.texts[label], label) for label in unit.labels))
        if extra:
            blocks.append(extra)
        return self.provider.build_request(self.data, self.spec, unit.kind, blocks, self.labels)

    async def run_units(self, kinds: Sequence[str] = (SOLO, COMPARE)) -> int:
        """Chấm các lượt `kinds` (mặc định solo và compare) chưa có kết quả. Chỉ `solo` để giữ chi
        phí trong trần khi không cần hạng so sánh; chạy tiếp sau đó chỉ thêm phần còn thiếu."""
        finished = self.done()
        for unit in plan_units(self.labels):
            if unit.key in finished or unit.kind not in kinds:
                continue
            if not await self._run(unit, self.request_for(unit), self._texts_for(unit)):
                break
        return self._exit()

    def _texts_for(self, unit: Unit) -> dict[str, str]:
        return {"story": self.texts[unit.labels[0]]} if unit.kind == SOLO else dict(self.texts)

    async def run_value(self, extra: str) -> int:
        unit = Unit(VALUE, VALUE, self.labels)
        if unit.key not in self.done():
            await self._run(unit, self.request_for(unit, extra), {})
        return self._exit()

    def _exit(self) -> int:
        if self.stop is None:
            return EXIT_OK
        return EXIT_BUDGET if self.stop[0] == "budget" else EXIT_ABORT

    # -- một lượt có thử lại --

    async def _run(self, unit: Unit, request: dict[str, Any], texts: Mapping[str, str]) -> bool:
        estimate = self.provider.estimate(request)
        unknown = 0.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                held = self.budget.reserve(estimate)
            except BudgetExceeded as e:
                return self._halt("budget", str(e))
            started = self._clock()
            try:
                reply = await self.provider.create(request)
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
            cost = self.provider.cost(reply.usage)
            self.budget.settle(held, cost)
            return self._record(unit, request, reply, cost, attempt, started, unknown, texts)
        raise AssertionError("không tới đây")

    def _record(self, unit: Unit, request: dict[str, Any], reply: JudgeReply, cost: float,
                attempts: int, started: float, unknown: float, texts: Mapping[str, str]) -> bool:
        latency = round(self._clock() - started, 3)
        trace = self.store.trace(f"{unit.key.replace(':', '-')}.json", {
            "request": request, "response": reply.raw, "attempts": attempts,
            "latency_s": latency})
        base = {"unit": unit.key, "kind": unit.kind, "labels": list(unit.labels),
                "judge": self.spec.id, "judge_model": reply.model, "usage": reply.usage,
                "cost_usd": round(cost, 6), "cost_estimated_usd": unknown or None,
                "attempts": attempts, "latency_s": latency, "trace": trace,
                "stop_reason": reply.stop_reason, "time": _now()}
        if reply.model != self.spec.model:
            self.store.append(RESULTS_FILE, base | {"status": "error",
                              "error": f"phản hồi mang model {reply.model}"})
            return self._halt("abort", "giám khảo phải cố định nhưng phản hồi mang model khác")
        if reply.stop_reason == "refusal":
            self.store.append(RESULTS_FILE, base | {"status": "judge_refusal"})
            self._log(f"[{unit.key}] giám khảo từ chối")
            return True
        if reply.stop_reason == "max_tokens":
            self._error(unit, "JUDGE_TRUNCATED", f"chạm max_tokens={self.spec.max_tokens}",
                        attempts, unknown, cost=cost)
            return True
        try:
            parsed = PARSERS[unit.kind](reply.text, self.data, self.labels)
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
    missing = [u.key for u in plan_units(pack_labels(store.root)) if u.key not in done]
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
    labels = pack_labels(pack)
    summary = blind_summary(data, store, labels)
    lines = ["# Kết quả đã khoá", "", "Điểm trung bình theo tiêu chí (chấm riêng từng truyện):"]
    for label in labels:
        scores = ", ".join(f"{cid}={summary['solo_mean'][label][cid]:.1f}" for cid in data.ids)
        lines.append(f"- {label}: {scores}")
    lines.append(f"Xếp hạng so sánh (hạng trung bình, 1 là tốt nhất): {summary['mean_rank']}")
    lines += ["", "# Chi phí thật và độ tin cậy (USD)", ""]
    for label in labels:
        c = key[label]["costs"]
        lines += [(f"- {label}: {c['chapters_committed']}/{c['chapters_target']} chương, trạng thái "
                  f"{c['status']}; tổng {c['total_usd']} USD, {c['usd_per_chapter']} USD/chương; "
                  f"riêng model viết + dàn ý {c['writer_outline_usd_per_chapter']} USD/chương; "
                  f"viết lại {c['rewrites']}, dự phòng {c['fallbacks']}, cảnh bị chặn "
                  f"{c['scenes_blocked']}; lời gọi lỗi {c['failed_calls'] or 'không'}; "
                  f"lỗi do bộ kiểm văn của repo: {metrics[label]['issues'] or 'không'}")]
    return "\n".join(lines)


def blind_summary(data: BakeoffData, store: Store,
                  labels: Sequence[str] = LABELS) -> dict[str, Any]:
    solo = {r["labels"][0]: r["result"] for r in ok_results(store, SOLO)}
    solo_mean = {label: {cid: float(solo[label][cid]["score"]) for cid in data.ids}
                 for label in solo}
    ranks: dict[str, list[int]] = {label: [] for label in labels}
    rankings = []
    for r in ok_results(store, COMPARE):
        order = r["result"]["ranking"]
        rankings.append({"presented": r["labels"], "ranking": order})
        for position, label in enumerate(order, start=1):
            ranks[label].append(position)
    mean_rank = {label: round(sum(v) / len(v), 2) for label, v in ranks.items() if v}
    return {"solo_mean": solo_mean, "mean_rank": mean_rank, "rankings": rankings,
            "order_agrees": len({tuple(r["ranking"]) for r in rankings}) == 1 if rankings else None}


def build_summary(data: BakeoffData, pack: Path, store: Store,
                  others: Sequence[Path] = ()) -> str:
    """Giải nhãn và dựng bảng: model | điểm từng mục | xếp hạng | USD/chương | lỗi. `others`: thư
    mục kết quả của giám khảo khác trên CÙNG truyện, để thêm phần đồng thuận và điểm gộp (D-108)."""
    key = _read_json(pack / "key.json")
    metrics = _read_json(pack / "code_metrics.json")
    labels = pack_labels(pack)
    blind = blind_summary(data, store, labels)
    value = ok_results(store, VALUE)
    head = ["Model", *[c.label for c in data.criteria], "Trung bình", "Hạng so sánh", "USD/chương",
            "Lỗi (code)", "Lỗi lời gọi"]
    rows = []
    for label in sorted(labels, key=lambda x: blind["mean_rank"].get(x, 9)):
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
    ranking_note = (
        f"Hạng so sánh: trung bình của hai lượt thứ tự đảo; hai lượt "
        f"{'đồng ý' if blind['order_agrees'] else 'KHÔNG đồng ý (nghi thiên lệch vị trí)'}."
        if blind["rankings"] else "Hạng so sánh: chưa chạy so sánh trực tiếp (chỉ chấm solo).")
    lines = [f"# Bài F: so {len(labels)} model viết trên cùng một thế giới", "", *out, "",
             ranking_note]
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
    models = sorted({r["judge_model"] for r in store.rows(RESULTS_FILE) if r.get("judge_model")})
    lines += ["", (f"Giám khảo: {pack_judge_id(pack)} ({', '.join(models) or 'chưa chấm'}). "
              f"Chi phí giám khảo: {spent:.4f} USD.")]
    if others:
        lines += ["", build_agreement_text(data, agreement(data, [pack, *others]))]
    return "\n".join(lines) + "\n"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _order(values: Mapping[str, float], *, descending: bool) -> tuple[tuple[str, ...], ...]:
    """Thứ tự các model theo giá trị, gom cả nhóm hoà (hai giám khảo cùng thứ tự khi chữ ký trùng)."""
    groups: dict[float, list[str]] = {}
    for model, value in values.items():
        groups.setdefault(round(value, 6), []).append(model)
    return tuple(tuple(sorted(groups[v])) for v in sorted(groups, reverse=descending))


def agreement(data: BakeoffData, packs: Sequence[Path]) -> dict[str, Any]:
    """So các giám khảo trên CÙNG truyện (mỗi thư mục một giám khảo, đã chấm xong solo và compare).
    Mọi số theo model, không theo nhãn (nhãn A/B có thể khác giữa các thư mục).
    - `solo_mean`, `criterion_means`, `mean_rank`: của từng giám khảo.
    - `criterion_gap[tiêu chí]`: chênh tuyệt đối trung bình và lớn nhất giữa các cặp giám khảo, và
      `concordance`: tỉ lệ cặp (giám khảo, cặp model) mà hai giám khảo nói cùng bên hơn; hoà tính 0,5.
    - Điểm gộp: trung bình cộng điểm trung bình solo, trọng số bằng nhau; hạng gộp: trung bình
      cộng hạng so sánh. Không chuẩn hoá thang riêng của từng giám khảo."""
    if len(packs) < 2:
        raise ConfigError("so giám khảo cần ít nhất hai thư mục kết quả đã chấm")
    judges: list[str] = []
    criterion_means: dict[str, dict[str, dict[str, float]]] = {}
    solo_mean: dict[str, dict[str, float]] = {}
    mean_rank: dict[str, dict[str, float]] = {}
    value_pick: dict[str, str | None] = {}
    judge_models: dict[str, str] = {}
    stories: dict[str, str] | None = None
    for pack in packs:
        judge = pack_judge_id(pack)
        if judge in criterion_means:
            raise ConfigError(f"hai thư mục cùng giám khảo {judge!r}")
        key = _read_json(pack / "key.json")
        labels = pack_labels(pack)
        store = Store(pack)
        shas = {row["model"]: row["story_sha256"] for row in key.values()}
        if stories is None:
            stories = shas
        elif shas != stories:
            raise ConfigError(f"{pack} không chấm cùng truyện với thư mục đầu "
                              "(model hay story_sha256 khác)")
        blind = blind_summary(data, store, labels)
        if set(blind["solo_mean"]) != set(labels) or set(blind["mean_rank"]) != set(labels):
            raise ConfigError(f"{pack} chưa chấm xong solo và compare")
        to_model = {label: key[label]["model"] for label in labels}
        criterion_means[judge] = {to_model[lb]: dict(sc) for lb, sc in blind["solo_mean"].items()}
        solo_mean[judge] = {m: _mean(list(sc.values())) for m, sc in criterion_means[judge].items()}
        mean_rank[judge] = {to_model[lb]: r for lb, r in blind["mean_rank"].items()}
        picked = ok_results(store, VALUE)
        value_pick[judge] = (key[picked[0]["result"]["recommendation"]]["model"]
                             if picked else None)
        rows_ = [r for r in store.rows(RESULTS_FILE) if r.get("judge_model")]
        judge_models[judge] = rows_[0]["judge_model"] if rows_ else ""
        judges.append(judge)
    models = list(stories or {})
    gap: dict[str, dict[str, float]] = {}
    for cid in data.ids:
        diffs, agree = [], []
        for j1, j2 in itertools.combinations(judges, 2):
            for m in models:
                diffs.append(abs(criterion_means[j1][m][cid] - criterion_means[j2][m][cid]))
            for m1, m2 in itertools.combinations(models, 2):
                d1 = criterion_means[j1][m1][cid] - criterion_means[j1][m2][cid]
                d2 = criterion_means[j2][m1][cid] - criterion_means[j2][m2][cid]
                agree.append(0.5 if d1 == 0 or d2 == 0 else float((d1 > 0) == (d2 > 0)))
        gap[cid] = {"mean_abs": _mean(diffs), "max_abs": max(diffs), "concordance": _mean(agree)}
    return {
        "judges": judges, "judge_models": judge_models, "models": models,
        "solo_mean": solo_mean, "criterion_means": criterion_means, "mean_rank": mean_rank,
        "criterion_gap": gap,
        "same_order_solo": len({_order(solo_mean[j], descending=True) for j in judges}) == 1,
        "same_order_compare": len({_order(mean_rank[j], descending=False) for j in judges}) == 1,
        "merged_mean": {m: _mean([solo_mean[j][m] for j in judges]) for m in models},
        "merged_rank": {m: _mean([mean_rank[j][m] for j in judges]) for m in models},
        "value_pick": value_pick,
    }


def build_agreement_text(data: BakeoffData, report: dict[str, Any]) -> str:
    judges, models = report["judges"], report["models"]
    count = {2: "Hai"}.get(len(judges), str(len(judges)))
    yes = lambda ok: "có" if ok else "KHÔNG"
    head = ["Giám khảo", "Model", *[c.label for c in data.criteria], "Trung bình", "Hạng so sánh"]
    table = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for judge in judges:
        for m in sorted(models, key=lambda x: report["solo_mean"][judge][x], reverse=True):
            cells = [f"{report['criterion_means'][judge][m][cid]:.1f}" for cid in data.ids]
            table.append("| " + " | ".join([
                f"{judge} ({report['judge_models'][judge]})", m, *cells,
                f"{report['solo_mean'][judge][m]:.2f}", f"{report['mean_rank'][judge][m]:.2f}"]) + " |")
    gaps = ["| Tiêu chí | Chênh TB | Chênh lớn nhất | Cùng chiều |", "|---|---|---|---|"]
    for c in data.criteria:
        g = report["criterion_gap"][c.id]
        gaps.append(f"| {c.label} | {g['mean_abs']:.2f} | {g['max_abs']:.1f} | "
                    f"{g['concordance']:.2f} |")
    merged = ["| Model | Điểm gộp | Hạng gộp |", "|---|---|---|"]
    for m in sorted(models, key=lambda x: report["merged_mean"][x], reverse=True):
        merged.append(f"| {m} | {report['merged_mean'][m]:.2f} | {report['merged_rank'][m]:.2f} |")
    picks = [f"- {j}: {report['value_pick'][j] or 'chưa hỏi'}" for j in judges]
    return "\n".join([
        f"## {count} giám khảo: điểm từng giám khảo, độ đồng thuận, điểm gộp", "",
        "### Điểm từng giám khảo (trung bình solo 1–5; hạng so sánh 1 là tốt nhất)", "", *table, "",
        "### Độ đồng thuận", "",
        (f"- Các giám khảo xếp các model cùng thứ tự theo điểm trung bình solo: "
        f"{yes(report['same_order_solo'])}."),
        (f"- Các giám khảo xếp các model cùng thứ tự theo hạng so sánh: "
        f"{yes(report['same_order_compare'])}."),
        ("- Chênh điểm từng mục: chênh tuyệt đối trung bình và lớn nhất giữa các giám khảo, trên "
        "các model; \"cùng chiều\" là tỉ lệ cặp model mà các giám khảo nói cùng bên hơn "
        "(hoà tính nửa)."), "", *gaps, "",
        "### Điểm gộp", "",
        ("Cách gộp: điểm gộp của một model là trung bình cộng điểm trung bình solo của các giám "
        "khảo, trọng số bằng nhau; hạng gộp là trung bình cộng hạng so sánh. Không chuẩn hoá thang "
        "riêng của từng giám khảo, nên giám khảo khắt khe hơn kéo điểm gộp xuống. Hai giám khảo "
        "không có đa số: chênh lớn giữa họ cần đọc tay, không dựa vào điểm gộp."), "", *merged, "",
        "### Khuyến nghị đáng tiền theo từng giám khảo (bước 2)", "", *picks])


def _bad_quotes(store: Store) -> int:
    bad = 0
    for r in store.rows(RESULTS_FILE):
        found = r.get("quote_found") or {}
        values = found.get("evidence", []) if "evidence" in found else list(found.values())
        bad += sum(1 for v in values if v is False)
    return bad


# --- giám khảo giả cho --dry-run ---------------------------------------------------------------


def _fake_verdict(props: Mapping[str, Any]) -> dict[str, Any]:
    """Kết luận giả theo schema: điểm giữa thang, xếp hạng theo nhãn."""
    if "ranking" in props:
        labels = props["ranking"]["items"]["enum"]
        crit = list(props["per_criterion"]["properties"])
        verdict: dict[str, Any] = {
            "ranking": list(labels), "reason": "dry-run", "evidence": [],
            "per_criterion": {cid: {"best": labels[0], "worst": labels[-1], "reason": "dry-run"}
                              for cid in crit}}
    elif "recommendation" in props:
        labels = props["recommendation"]["enum"]
        verdict = {"recommendation": labels[0], "reason": "dry-run", "caveats": ["dry-run"],
                   "per_story": {label: {"verdict": VERDICTS[1], "reason": "dry-run"}
                                 for label in labels}}
    else:
        verdict = {cid: {"quote": NO_QUOTE, "reason": "dry-run", "score": 3} for cid in props}
    return verdict


def fake_judge_reply(body: dict[str, Any]) -> dict[str, Any]:
    """Phản hồi Messages API giả (Anthropic) theo schema của yêu cầu."""
    verdict = _fake_verdict(body["output_config"]["format"]["schema"]["properties"])
    return {
        "id": "msg_dry_run", "type": "message", "role": "assistant", "model": body["model"],
        "content": [{"type": "text", "text": json.dumps(verdict, ensure_ascii=False)}],
        "stop_reason": "end_turn", "stop_sequence": None, "stop_details": None,
        "usage": {"input_tokens": 1000, "output_tokens": 500,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}


def fake_meta_reply(body: dict[str, Any]) -> dict[str, Any]:
    """Phản hồi chat completion giả (Meta) theo schema của yêu cầu."""
    schema = body["response_format"]["json_schema"]["schema"]["properties"]
    verdict = _fake_verdict(schema)
    return {
        "id": "chatcmpl-dry-run", "object": "chat.completion", "created": 0, "model": body["model"],
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": json.dumps(verdict, ensure_ascii=False),
            "refusal": None}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500,
                  "completion_tokens_details": {"reasoning_tokens": 300},
                  "prompt_tokens_details": {"cached_tokens": 0}}}


def mock_meta_http() -> httpx.AsyncClient:
    """AsyncClient mà HTTP đi vào `fake_meta_reply` thay vì mạng (cho --dry-run)."""
    def transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fake_meta_reply(json.loads(request.content)))

    return httpx.AsyncClient(transport=httpx.MockTransport(transport))


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


def _budget(store: Store, args: argparse.Namespace, spec: JudgeSpec | None = None) -> Budget:
    """Trần riêng của nhà cung cấp: `--budget` cho Anthropic, `--budget-meta` cho Meta."""
    provider = spec.provider if spec else "anthropic"
    flag, cap = (("--budget", args.budget) if provider == "anthropic"
                 else ("--budget-meta", getattr(args, "budget_meta", None)))
    if cap is None and not args.dry_run:
        raise ConfigError(f"lượt chấm thật cần {flag} (USD)")
    spent = sum(r.get("cost_usd") or 0.0 for r in store.rows(RESULTS_FILE))
    spent += sum((r.get("cost_usd") or 0.0) + (r.get("cost_estimated_usd") or 0.0)
                 for r in store.rows(ERRORS_FILE))
    return Budget(provider, float("inf") if cap is None else cap, spent_usd=spent)


def resolve_judge(data: BakeoffData, pack: Path, requested: str | None) -> JudgeSpec:
    """Giám khảo của thư mục: đúng cái `pack` đã ghi; `--judge` khác thì từ chối."""
    own = pack_judge_id(pack)
    if requested is not None and requested != own:
        raise ConfigError(f"{pack} dành cho giám khảo {own!r}, không phải {requested!r}; "
                          "dùng thư mục kết quả mới (`pack --judge`)")
    return data.judge_by_id(own)


def _make_provider(spec: JudgeSpec, args: argparse.Namespace
                   ) -> tuple[JudgeProvider, Callable[[], Any]]:
    if spec.provider == "anthropic":
        client, workspace = _client(args)
        return AnthropicProvider(client, spec, workspace), client.close
    if args.dry_run:
        http, key = mock_meta_http(), SecretStr("dry-run-not-a-key")
    else:
        keys = load_keys(Path(args.env_file), ["meta"])
        assert keys.meta_api_key is not None
        key = keys.meta_api_key
        http = httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT_S, connect=10.0))
    return MetaProvider(http, key, spec), http.aclose


def _store(args: argparse.Namespace) -> Store:
    pack = Path(args.dir)
    if not (pack / "pack_meta.json").exists():
        raise ConfigError(f"{pack} chưa có gói truyện: chạy `pack` trước")
    return Store(pack)


def parse_kinds(raw: str) -> tuple[str, ...]:
    kinds = tuple(k.strip() for k in raw.split(",") if k.strip())
    if not kinds or not set(kinds) <= {SOLO, COMPARE}:
        raise ConfigError(f"--kinds chọn trong {SOLO}, {COMPARE} (cách nhau bằng dấu phẩy); "
                          f"nhận {raw!r}")
    return kinds


async def _judge(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    kinds = parse_kinds(args.kinds)
    store = _store(args)
    ensure_unlocked(store)
    spec = resolve_judge(data, store.root, args.judge)
    budget = _budget(store, args, spec)
    provider, close = _make_provider(spec, args)
    try:
        bake = Bakeoff(data, store.root, store, provider=provider, spec=spec, budget=budget)
        return await bake.run_units(kinds)
    finally:
        await close()


async def _value(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    store = _store(args)
    spec = resolve_judge(data, store.root, args.judge)
    lock_blind_scores(store)
    budget = _budget(store, args, spec)
    provider, close = _make_provider(spec, args)
    try:
        bake = Bakeoff(data, store.root, store, provider=provider, spec=spec, budget=budget)
        return await bake.run_value(value_context(data, store.root, store))
    finally:
        await close()


def _cmd_pack(args: argparse.Namespace) -> int:
    data, sha = load_data(Path(args.data_dir))
    out = Path(args.out)
    meta = build_pack([Path(d) for d in args.run], args.seed, out, sha, args.judge, data,
                      replicates=args.replicates)
    print(f"Đã đóng gói {len(meta['labels'])} truyện vào {out} cho giám khảo {meta['judge']} "
          f"(nhãn xáo theo seed {meta['seed']}); khoá: key.json")
    return EXIT_OK


def _cmd_summary(args: argparse.Namespace) -> int:
    data, _ = load_data(Path(args.data_dir))
    store = _store(args)
    text = build_summary(data, store.root, store, [Path(d) for d in args.with_dirs])
    (store.root / "summary.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m writory.quality.bench_bakeoff",
                                description="Bài F: so nhiều model viết (D-101).")
    sub = p.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", help="đóng gói mù hai hoặc ba lần chạy")
    pack.add_argument("--run", action="append", required=True, metavar="DIR",
                      help="thư mục kết quả của bench_run (lặp lại hai hoặc ba lần)")
    pack.add_argument("--seed", type=int, required=True, help="seed xáo nhãn A/B/C")
    pack.add_argument("--out", required=True, help="thư mục kết quả mới của bài F")
    pack.add_argument("--judge", help="id giám khảo của thư mục này (judge.yaml); mặc định giám "
                                      "khảo chính")
    pack.add_argument("--replicates", action="store_true",
                      help="các lần chạy là cùng một cấu hình lặp lại ở thư mục khác (đo nhiễu "
                           "giữa các lần viết); vẫn đòi cùng thế giới")
    for name, helptext in (("judge", "chấm mù: solo ×3 + compare ×2"),
                           ("value", "khuyến nghị đáng tiền, sau khi khoá điểm mù"),
                           ("summary", "giải nhãn và dựng bảng")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--dir", required=True, help="thư mục kết quả của bài F (đã `pack`)")
        if name == "summary":
            sp.add_argument("--with", dest="with_dirs", action="append", default=[], metavar="DIR",
                            help="thư mục kết quả của giám khảo khác trên cùng truyện (lặp lại "
                                 "được): thêm bảng điểm từng giám khảo, độ đồng thuận, điểm gộp")
        else:
            if name == "judge":
                sp.add_argument("--kinds", default=f"{SOLO},{COMPARE}",
                                help="các lượt chấm: solo, compare hoặc cả hai (mặc định). Chỉ solo "
                                     "thì rẻ hơn nhiều; value đòi đủ cả hai")
            sp.add_argument("--judge", help="phải là giám khảo của thư mục (`pack_meta.json`)")
            sp.add_argument("--budget", type=float,
                            help="trần USD Anthropic (bắt buộc khi giám khảo là Anthropic)")
            sp.add_argument("--budget-meta", type=float,
                            help="trần USD Meta (bắt buộc khi giám khảo là Meta)")
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
    for flag in ("budget", "budget_meta"):
        if getattr(args, flag, None) is not None and getattr(args, flag) <= 0:
            print(f"Lỗi: --{flag.replace('_', '-')} phải > 0", file=sys.stderr)
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
