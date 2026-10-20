"""Bài đo C v1: trích thay đổi chương, chấm bằng code so với đồ thị dựng tay (docs/eval.md, D-34).

Mỗi (model, chương 1..5 của truyện mẫu): đưa bộ trích (`pipeline/extract.py`) văn bản chương, danh
mục thực thể có tới hết chương đó và các cạnh đang hiệu lực trước chương; so gói trích ra với gói
dựng tay của chương. Không giám khảo LLM.

Chạy: cd backend && uv run python -m writory.pipeline.bench_c --label <nhãn> [--dry-run]
Dữ liệu khai trước: evals/scenarios/extract/config.yaml.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from writory.config import REPO_ROOT
from writory.errors import WritoryError
from writory.graph.package import ChangePackage
from writory.graph.sample import SampleStory, read_sample
from writory.llm.base import LLMClient
from writory.llm.retry import RETRY_SCHEMA, RETRY_TRANSIENT, with_retries
from writory.pipeline.extract import PROMPT_VERSION, Entity, OpenEdge, extract_changes

DATA_DIR = REPO_ROOT / "evals" / "scenarios" / "extract"
RESULTS_DIR = REPO_ROOT / "evals" / "results"
LIE_LIKE = ("Fact",)  # bí mật/sự thật: hé lộ sai thì lộ bí mật (G1)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelEntry(_Strict):
    id: str
    label: str
    reasoning: Literal["none", "mandatory-minimal"] = "none"


class BenchConfig(_Strict):
    version: int
    chapters: list[PositiveInt] = Field(min_length=1)
    samples: PositiveInt
    schema_retries: int = Field(ge=0)
    transient_retries: int = Field(ge=0)
    max_tokens: PositiveInt
    models: list[ModelEntry] = Field(min_length=1)


# --- trạng thái vàng của truyện mẫu --------------------------------------------------------------


def _entity(node, user_authored: bool = False) -> Entity:
    p = node.props
    text = p.get("name") or p.get("text") or p.get("description") or p.get("content") or p.get(
        "title") or node.id
    aliases = tuple(p.get("aliases") or ()) if "name" in p else ()
    return Entity(id=node.id, label=node.label, text=str(text), aliases=aliases,
                  user_authored=bool(p.get("user_authored", user_authored)))


def gold_state(sample: SampleStory, chapter: int) -> tuple[list[Entity], list[OpenEdge]]:
    """Danh mục thực thể có tới hết chương `chapter`, và cạnh đang hiệu lực ở cuối chương trước."""
    entities: dict[str, Entity] = {}
    open_edges: dict[str, OpenEdge] = {}
    for ch in sample.chapters:
        if ch.number > chapter:
            break
        for n in ch.package.nodes:
            entities[n.id] = _entity(n)
        if ch.number == chapter:
            break
        for e in ch.package.edges:
            open_edges[e.id] = OpenEdge(e.id, e.type, e.source, e.target)
        for c in ch.package.close:
            open_edges.pop(c.id, None)
    return list(entities.values()), list(open_edges.values())


def gold_package(sample: SampleStory, chapter: int) -> ChangePackage:
    return next(ch.package for ch in sample.chapters if ch.number == chapter)


def revealed_by(sample: SampleStory, chapter: int) -> set[str]:
    """Id các nút người chơi đã được biết (hé lộ hoặc nhân vật chính KNOWS) tính tới hết `chapter`."""
    out: set[str] = set()
    for ch in sample.chapters:
        if ch.number > chapter:
            break
        for e in ch.package.edges:
            if e.type == "REVEALED_TO_PLAYER":
                out.add(e.source)
            elif e.type == "KNOWS" and e.source == sample.protagonist:
                out.add(e.target)
    return out


# --- chấm ---------------------------------------------------------------------------------------


def _key(e) -> tuple[str, str, str]:
    return (e.type, e.source, e.target)


def _pv(e, protagonist: str) -> bool:
    """Cạnh thuộc lớp người chơi biết: hé lộ, hoặc nhân vật chính biết. Luôn có bằng chứng trên trang."""
    return e.type == "REVEALED_TO_PLAYER" or (e.type == "KNOWS" and e.source == protagonist)


def score_chapter(
    pred: ChangePackage, gold: ChangePackage, *, protagonist: str, labels: dict[str, str],
    revealed_so_far: set[str],
) -> dict[str, Any]:
    """So gói trích với gói vàng của cùng chương. Khoá cạnh = (kiểu, từ, tới)."""
    p_all = {_key(e): e for e in pred.edges}
    g_all = {_key(e): e for e in gold.edges}
    p_pv = {k for k, e in p_all.items() if _pv(e, protagonist)}
    g_pv = {k for k, e in g_all.items() if _pv(e, protagonist)}
    knows_how_ok = sum(
        1 for k in set(p_all) & set(g_all)
        if k[0] == "KNOWS" and p_all[k].props.get("how") == g_all[k].props.get("how")
        and p_all[k].props.get("told_by") == g_all[k].props.get("told_by")
    )
    knows_matched = sum(1 for k in set(p_all) & set(g_all) if k[0] == "KNOWS")
    # Hé lộ (hoặc cho nhân vật chính biết) một Fact mà dữ liệu vàng chưa hé lộ tới hết chương: rủi ro lộ bí mật.
    false_reveal = sorted(
        k[1] if k[0] == "REVEALED_TO_PLAYER" else k[2]
        for k in p_pv - g_pv
        if labels.get(k[1] if k[0] == "REVEALED_TO_PLAYER" else k[2]) in LIE_LIKE
        and (k[1] if k[0] == "REVEALED_TO_PLAYER" else k[2]) not in revealed_so_far
    )
    p_close, g_close = {c.id for c in pred.close}, {c.id for c in gold.close}
    return {
        "all": {"tp": len(set(p_all) & set(g_all)), "fp": len(set(p_all) - set(g_all)),
                "fn": len(set(g_all) - set(p_all))},
        "player_view": {"tp": len(p_pv & g_pv), "fp": len(p_pv - g_pv), "fn": len(g_pv - p_pv)},
        "close": {"tp": len(p_close & g_close), "fp": len(p_close - g_close),
                  "fn": len(g_close - p_close)},
        "knows_how": {"ok": knows_how_ok, "n": knows_matched},
        "false_reveal_facts": false_reveal,
        "missed_player_view": sorted("|".join(k) for k in g_pv - p_pv),
        "extra_player_view": sorted("|".join(k) for k in p_pv - g_pv),
    }


def prf(c: dict[str, int]) -> tuple[float | None, float | None, float | None]:
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return p, r, f


# --- chạy ---------------------------------------------------------------------------------------


@dataclass
class Store:
    root: Path

    def append(self, name: str, row: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / name).open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def rows(self, name: str) -> list[dict[str, Any]]:
        path = self.root / name
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def load_config(path: Path = DATA_DIR / "config.yaml") -> BenchConfig:
    return BenchConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


async def run_one(
    llm: LLMClient, model: ModelEntry, sample: SampleStory, chapter: int, sample_no: int,
    cfg: BenchConfig,
) -> dict[str, Any]:
    entities, open_edges = gold_state(sample, chapter)
    gold = gold_package(sample, chapter)
    text = next(ch.text for ch in sample.chapters if ch.number == chapter)
    chapter_node = next(n.id for n in gold.nodes if n.label == "Chapter")

    async def call():
        return await extract_changes(
            llm, model.id, chapter=chapter, chapter_id=chapter_node,
            commit_id=f"bench-c-{chapter}", protagonist_id=sample.protagonist, chapter_text=text,
            entities=entities, open_edges=open_edges, extra=_extra_for(model, cfg),
        )

    async def with_schema_retry():
        return await with_retries(call, max_retries=cfg.schema_retries, retry_on=RETRY_SCHEMA)

    started = time.monotonic()
    result = await with_retries(with_schema_retry, max_retries=cfg.transient_retries,
                                retry_on=RETRY_TRANSIENT)
    labels = {e.id: e.label for e in entities}
    score = score_chapter(result.package, gold, protagonist=sample.protagonist, labels=labels,
                          revealed_so_far=revealed_by(sample, chapter))
    usage = result.chat.usage if result.chat else None
    return {
        "model": model.id, "chapter": chapter, "sample": sample_no, "status": "ok",
        "score": score, "rejected": [{"edge": d, "reason": r} for d, r in result.rejected],
        "n_edges": len(result.package.edges), "n_close": len(result.package.close),
        "cost_usd": usage.cost_usd if usage else None,
        "usage": usage.model_dump() if usage else None,
        "latency_s": round(time.monotonic() - started, 2),
        "package": result.package.model_dump(mode="json", by_alias=True),
    }


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.2f}"


def summarize(rows: list[dict[str, Any]], errors: list[dict[str, Any]], cfg: BenchConfig,
              meta: dict[str, Any]) -> str:
    lines = [f"# Bài đo C v1 — {meta['label']}", "",
             (f"- Commit: `{meta['commit']}`; prompt: {PROMPT_VERSION}; config v{cfg.version} "
             f"(`{meta['config_sha']}`); truyện mẫu graph.yaml `{meta['graph_sha']}`."),
             f"- Chương {cfg.chapters}, {cfg.samples} mẫu mỗi (model, chương). Chấm bằng code, không giám khảo.",
             ("- **PV** = lớp người chơi biết (REVEALED_TO_PLAYER + KNOWS của nhân vật chính). "
             "**Hé lộ sai** = hé lộ một Fact mà dữ liệu vàng chưa hé lộ tới hết chương (rủi ro lộ bí mật)."),
             "- Toàn bộ cạnh gồm cả sự thật tác giả biết mà trang không viết ra, nên recall phần này có trần thấp.",
             "",
             ("| Model | n | PV P | PV R | PV F1 | Hé lộ sai | Toàn bộ P | Toàn bộ R | close P | close R "
             "| KNOWS how đúng | Cạnh bị bỏ | Lỗi gọi | USD/chương | Trễ s |"),
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in cfg.models:
        rs = [r for r in rows if r["model"] == m.id]
        errs = [e for e in errors if e["model"] == m.id]
        if not rs:
            lines.append(f"| {m.label} | 0 | — | — | — | — | — | — | — | — | — | — | {len(errs)} | — | — |")
            continue
        agg = {k: {"tp": 0, "fp": 0, "fn": 0} for k in ("all", "player_view", "close")}
        how_ok = how_n = 0
        false_rev = rejected = 0
        for r in rs:
            for k, counts in agg.items():
                for f in ("tp", "fp", "fn"):
                    counts[f] += r["score"][k][f]
            how_ok += r["score"]["knows_how"]["ok"]
            how_n += r["score"]["knows_how"]["n"]
            false_rev += len(r["score"]["false_reveal_facts"])
            rejected += len(r["rejected"])
        pv, al, cl = prf(agg["player_view"]), prf(agg["all"]), prf(agg["close"])
        costs = [r["cost_usd"] for r in rs if r["cost_usd"] is not None]
        lat = sorted(r["latency_s"] for r in rs)
        lines.append(
            f"| {m.label} | {len(rs)} | {_fmt(pv[0])} | {_fmt(pv[1])} | {_fmt(pv[2])} | {false_rev} "
            f"| {_fmt(al[0])} | {_fmt(al[1])} | {_fmt(cl[0])} | {_fmt(cl[1])} "
            f"| {how_ok}/{how_n} | {rejected} | {len(errs)} "
            f"| {(sum(costs) / len(costs)) if costs else float('nan'):.5f} | {lat[len(lat) // 2]:.1f} |")
    total = sum(r["cost_usd"] or 0 for r in rows) + sum(e.get("cost_usd") or 0 for e in errors)
    lines += ["", f"- Tổng chi phí OpenRouter: {total:.4f} USD.", ""]
    return "\n".join(lines)


def _make_llm(dry_run: bool, sample: SampleStory) -> LLMClient:
    if dry_run:
        # Model giả trả đúng gói vàng của chương được hỏi: kiểm dây nối, kỳ vọng PV F1 = 1.
        return _GoldFake(sample)
    from writory.llm.openrouter import OpenRouterClient
    from writory.quality.bench_d import load_keys  # chỉ đọc đúng key cần, không in key (G7)

    keys = load_keys(REPO_ROOT / ".env", ["openrouter"])
    return OpenRouterClient(keys.openrouter_api_key)


class _GoldFake(LLMClient):
    """--dry-run: trả JSON đúng bằng gói vàng của chương, để kiểm luồng chạy và cách chấm."""

    def __init__(self, sample: SampleStory) -> None:
        self.sample = sample

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        from writory.llm.base import ChatResult, Usage

        text = messages[-1].content
        chapter = int(text.split("Chương: ", 1)[1].split(" ", 1)[0])
        gold = gold_package(self.sample, chapter)
        edges = [{"type": e.type, "source": e.source, "target": e.target,
                  "kind": e.props.get("kind"), "score": e.props.get("score"),
                  "how": e.props.get("how"), "told_by": e.props.get("told_by"),
                  "quote": e.props.get("quote"), "known_as": e.props.get("known_as"),
                  "role": e.props.get("role")} for e in gold.edges]
        out = {"edges": edges, "close": [c.id for c in gold.close]}
        return ChatResult(text=json.dumps(out, ensure_ascii=False), usage=Usage(cost_usd=0.0))

    async def stream(self, model, messages):  # pragma: no cover - không dùng
        raise NotImplementedError
        yield


def _extra_for(model: ModelEntry, cfg: BenchConfig) -> dict[str, Any]:
    extra: dict[str, Any] = {"max_tokens": cfg.max_tokens}
    extra["reasoning"] = {"effort": "none"} if model.reasoning == "none" else {"effort": "minimal"}
    return extra


async def run(args: argparse.Namespace) -> int:
    cfg = load_config(Path(args.config))
    sample = read_sample()
    llm = _make_llm(args.dry_run, sample)
    label = args.label + ("-dry" if args.dry_run else "")
    store = Store(RESULTS_DIR / f"{datetime.now():%Y-%m-%d}-extract-{label}")
    if (store.root / "results.jsonl").exists():
        raise SystemExit(f"{store.root} đã có kết quả; dùng nhãn khác.")
    meta = {"label": label, "commit": _git_sha(), "config_sha": _sha(Path(args.config)),
            "graph_sha": _sha(REPO_ROOT / "data" / "sample-story" / "graph.yaml"),
            "prompt_version": PROMPT_VERSION, "created": datetime.now().isoformat(timespec="seconds"),
            "dry_run": args.dry_run}
    spent = 0.0
    wanted = {m for m in args.models.split(",") if m}
    for model in cfg.models:
        if wanted and model.id not in wanted:
            continue
        for chapter in cfg.chapters:
            for s in range(cfg.samples):
                if spent >= args.budget:
                    print(f"Chạm trần {args.budget} USD, dừng.", file=sys.stderr)
                    return 2
                try:
                    row = await run_one(llm, model, sample, chapter, s, cfg)
                except WritoryError as e:
                    store.append("errors.jsonl", {"model": model.id, "chapter": chapter, "sample": s,
                                                  "error": e.code.value, "detail": e.detail})
                    print(f"[lỗi] {model.label} ch{chapter} s{s}: {e.code.value}")
                    continue
                spent += row["cost_usd"] or 0
                if args.pause:
                    await asyncio.sleep(args.pause)
                store.append("results.jsonl", row)
                pv = prf(row["score"]["player_view"])
                print(f"[ok] {model.label} ch{chapter} s{s}: PV F1 {_fmt(pv[2])}, "
                      f"hé lộ sai {len(row['score']['false_reveal_facts'])}, "
                      f"bỏ {len(row['rejected'])}, {row['cost_usd']} USD, {row['latency_s']}s")
    (store.root / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                          encoding="utf-8", newline="\n")
    summary = summarize(store.rows("results.jsonl"), store.rows("errors.jsonl"), cfg, meta)
    (store.root / "summary.md").write_text(summary, encoding="utf-8", newline="\n")
    print(f"Xong. Đã tiêu {spent:.4f} USD. Kết quả: {store.root}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m writory.pipeline.bench_c")
    parser.add_argument("--label", required=True)
    parser.add_argument("--config", default=str(DATA_DIR / "config.yaml"))
    parser.add_argument("--budget", type=float, default=0.5, help="trần OpenRouter, USD")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--models", default="", help="lọc model theo id, cách nhau dấu phẩy")
    parser.add_argument("--pause", type=float, default=0.0,
                        help="nghỉ giữa các lời gọi, giây (nhà cung cấp giới hạn tần suất)")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
