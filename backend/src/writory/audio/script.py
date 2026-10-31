"""Bộ viết kịch bản audio: lệnh, điều phối, trần chi phí, ghi file (D-151).

    cd backend
    uv run python -m writory.audio.script propose --tags "thiếu gia bị hoán đổi thân phận, tiểu thư giả, trà xanh" \\
        --count 5 --budget 0.05
    uv run python -m writory.audio.script write --premise-file <ideas.yaml> --pick i2 --minutes 30 --budget 0.50
    uv run python -m writory.audio.script write --premise "<hướng đi ngắn>" --minutes 80 --budget 1.00

CHỈ admin chạy: không endpoint, không nút, không đọc hay ghi Postgres, Neo4j. Kết quả mặc định nằm ở
`exports/` (git bỏ qua): `propose` ghi `ideas.md`, `ideas.yaml`; `write` ghi mỗi hướng đi một thư mục con với
`tts.txt` (chữ đọc liền cho TTS một giọng), `script.md`, `script.json` (người nói, cách đọc, âm thanh) và
`calls.jsonl` (mỗi lời gọi một dòng: vai, model, token, chi phí; không có chữ).

Chế độ: `--dry-run` (model giả, không mạng, không key; có `--budget` thì vẫn áp trần), mặc định là chạy thật:
bắt buộc `--budget` (USD, trần tổng của cả lệnh) và không được vượt `limits.audio_script.max_budget_usd` (G8).
Key: chỉ key nhà cung cấp của các model trong config (`--config-dir`, như bộ xuất video), từ biến môi trường hay
`--env-file`; không in, không ghi (G7). Mỗi đoạn qua kiểm duyệt G9 trước khi vào bản xuất, fail-closed: bị chặn
hay không kiểm được thì đoạn bị giữ lại và kịch bản dừng ở đó. `--no-moderate` tắt và in cảnh báo.

Mã thoát: 0 xong; 1 sai cấu hình hay tham số; 2 dừng vì chạm `--budget`; 3 có đoạn lỗi hay bị giữ lại.
"""

import argparse
import asyncio
import hashlib
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from writory.audio import drama, render
from writory.audio.render import AudioScript, Premise, SegmentOut, Targets
from writory.config import (
    CONFIG_FILE_NAMES,
    REPO_CONFIG_DIR,
    REPO_ROOT,
    AppConfig,
    ConfigError,
    LimitNotSetError,
    config_bytes,
    load_config,
)
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Usage, require_model, role_extra
from writory.llm.capped import CappedClient
from writory.llm.fake import FakeLLM
from writory.llm.provider import llm_identity
from writory.quality.bench_d import EST_CHARS_PER_TOKEN, Budget, git_state
from writory.safety.moderate import Source, Verdict, moderate
from writory.safety.redact import install_log_redaction, redact

DEFAULT_OUT_ROOT = REPO_ROOT / "exports"  # .gitignore: không commit bản xuất
EXIT_OK, EXIT_CONFIG, EXIT_BUDGET, EXIT_ERRORS = 0, 1, 2, 3
DRY_RUN_COST_USD = 0.0001
_ROLES = {"ProposeOutput": drama.ROLE, "PlanOutput": drama.ROLE, "SegmentOutput": drama.ROLE,
          "ModerationOutput": "moderate"}


# --- model giả cho --dry-run và test --------------------------------------------------------------


class DryRunAudioLLM(FakeLLM):
    """`--dry-run`: câu trả lời ghi sẵn, hợp lệ theo schema và phép kiểm bằng code, đọc số đoạn, số chữ và bí mật
    đến hạn từ chính đề. Không mạng, không key. Test ghi đè `segment_reply`, `moderation_reply`."""

    FILLER = "Tôi nhớ rõ từng lời họ nói trong căn nhà lạnh lẽo ấy."
    REPLY = "Anh nghĩ anh là ai chứ?"

    def __init__(self, *, cost_usd: float | None = DRY_RUN_COST_USD) -> None:
        super().__init__([], cost_usd=cost_usd)

    def ideas_reply(self, count: int) -> dict[str, Any]:
        return {"ideas": [{"title": f"Hướng đi chạy thử {i}",
                           "premise": f"Thiếu gia thật bị tráo lúc sinh, lần thứ {i} trở về vả mặt tiểu thư giả.",
                           "hooks": ["Vạch mặt trà xanh giữa tiệc mừng thọ."]} for i in range(1, count + 1)]}

    def plan_reply(self, segments: int) -> dict[str, Any]:
        return {
            "title": "Thiếu gia trở về", "logline": "Thiếu gia thật bị tráo lúc sinh trở về nhà họ Lâm.",
            "protagonist_id": "toi",
            "cast": [{"id": "toi", "name": "Lâm An", "gender": "nam", "age": 24, "role": "thiếu gia thật",
                      "voice": "trầm, chậm", "romance": False},
                     {"id": "nha", "name": "Tô Nhã", "gender": "nữ", "age": 22, "role": "tiểu thư giả",
                      "voice": "ngọt, giả vờ yếu đuối", "romance": False}],
            "secrets": [{"id": "hoan_doi", "text": "Tô Nhã biết mình bị tráo từ đầu.",
                         "reveal_segment": min(2, segments)}],
            "segments": [{"title": f"Phần {i}", "beats": [f"nhịp chạy thử {i}"]} for i in range(1, segments + 1)],
            "ending": "Tô Nhã bị vạch mặt trước cả họ.",
        }

    def segment_reply(self, index: int, total: int, target: int, due: list[str]) -> dict[str, Any]:
        filler_words, reply_words = len(self.FILLER.split()), len(self.REPLY.split())
        lines = [{"speaker": "narrator", "text": self.FILLER, "cue": "", "sfx": ""}
                 for _ in range(max(1, round((target - reply_words) / filler_words)))]
        lines.insert(1, {"speaker": "nha", "text": self.REPLY, "cue": "khinh khỉnh", "sfx": "tiếng ly vỡ"})
        return {"lines": lines, "reveals": [{"secret_id": s, "quote": self.FILLER} for s in due],
                "summary": f"Đoạn {index} chạy thử: Lâm An đối mặt Tô Nhã."}

    def moderation_reply(self, text: str) -> dict[str, Any]:
        return {"findings": [], "reason": "dry-run"}

    def reply(self, schema: str | None, text: str) -> dict[str, Any]:
        if schema == "ProposeOutput":
            return self.ideas_reply(int(re.search(r"Đề xuất đúng (\d+) hướng đi", text).group(1)))
        if schema == "PlanOutput":
            return self.plan_reply(int(re.search(r"đúng (\d+) đoạn", text).group(1)))
        if schema == "SegmentOutput":
            index, total = map(int, re.search(r"Viết đoạn (\d+)/(\d+)", text).groups())
            target = int(re.search(r"Số chữ mục tiêu: khoảng (\d+) chữ", text).group(1))
            due = re.search(r"Bí mật phải lộ trong đoạn này \(id\): ([^\n]*)\.", text).group(1)
            return self.segment_reply(index, total, target, [] if due == "không có" else due.split(", "))
        if schema == "ModerationOutput":
            return self.moderation_reply(text)
        raise AssertionError(f"DryRunAudioLLM không biết schema {schema!r}")

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        self.calls.append(list(messages))
        self.extras.append(extra)
        if response_schema is not None:
            self.schemas.append(response_schema)
        body = self.reply(response_schema.__name__ if response_schema else None, messages[-1].content)
        text = json.dumps(body, ensure_ascii=False)
        chars = sum(len(m.content) for m in messages)
        usage = Usage(prompt_tokens=math.ceil(chars / EST_CHARS_PER_TOKEN),
                      completion_tokens=math.ceil(len(text) / EST_CHARS_PER_TOKEN), cost_usd=self._cost_usd)
        return ChatResult(text=text, usage=usage, model=model, finish_reason="stop")


# --- điều phối ------------------------------------------------------------------------------------


@dataclass
class WriteOptions:
    moderate: bool = True
    dry_run: bool = False
    budget_usd: float | None = None
    git: dict[str, Any] | None = None  # commit đang chạy và có sửa chưa commit không (`bench_d.git_state`)
    config_sha256: str | None = None  # hash config đã gộp của `--config-dir`


def config_sha256(config_dir: Path) -> str:
    """Hash config ĐÃ GỘP (nền `config/` và phần đè của `--config-dir`), như lệnh đo (D-140)."""
    digest = hashlib.sha256()
    for name in sorted(CONFIG_FILE_NAMES):
        digest.update(name.encode() + b"\0" + config_bytes(config_dir, name) + b"\0")
    return digest.hexdigest()


def _meta(premise: Premise, targets: Targets, *, config: AppConfig, model: str, options: WriteOptions,
          today: date | None) -> dict[str, Any]:
    models = [model, *filter(None, [config.models.roles.moderate if options.moderate else None])]
    return {
        "premise_id": premise.id, "premise": premise.text, "minutes": targets.minutes,
        "words_per_minute": targets.words_per_minute, "target_words": targets.total_words,
        "segments_planned": targets.segments, "words_per_segment": targets.words_per_segment,
        "words": 0, "est_minutes": 0.0, "model": model, "provider": llm_identity(config, models)["provider"],
        "prompt_version": drama.PROMPT_VERSION, "moderation": options.moderate, "dry_run": options.dry_run,
        "budget_usd": options.budget_usd, "generated": (today or date.today()).isoformat(),
        "git": options.git, "config_sha256": options.config_sha256, "calls": 0, "cost_usd": 0.0,
    }


async def _moderate_segment(seg: SegmentOut, *, llm: LLMClient, config: AppConfig) -> None:
    """G9 fail-closed như bộ xuất video: bị chặn hay không kiểm được vì bất kỳ lỗi nào thì đoạn bị giữ lại, không
    còn chữ nào của nó trong bản xuất. Quá mức u tối thì giữ đoạn và ghi lại để admin quyết."""
    text = "\n".join(line["text"] for line in seg.lines)
    try:
        result = await moderate(text, source=Source.SCENE, llm=llm, config=config)
    except WritoryError as e:
        seg.moderation = {"verdict": "not_checked", "error": e.code.value, "categories": []}
        seg.status = "skipped_budget" if e.code is ErrorCode.COST_LIMIT_STORY else "withheld_unmoderated"
    else:
        seg.moderation = {"verdict": result.verdict.value, "categories": [c.value for c in result.categories]}
        if result.verdict in (Verdict.HARD_BLOCKED, Verdict.BLOCKED):
            seg.status = "withheld_moderation"
    if seg.status != "ok":
        seg.lines, seg.reveals, seg.summary = [], [], ""


async def build_script(premise: Premise, targets: Targets, *, config: AppConfig, llm: LLMClient,
                       options: WriteOptions, today: date | None = None) -> AudioScript:
    """Lập kế hoạch rồi viết từng đoạn. `llm` nên là `CappedClient` (trần G8). Dừng ở đoạn đầu tiên lỗi, bị giữ
    lại hay chạm trần: các đoạn sau dựa vào nó."""
    limits, retries = config.limits.audio_script, config.limits.retries
    model = require_model(config.models.roles, drama.ROLE)
    extra = role_extra(config.models, drama.ROLE)
    script = AudioScript(_meta(premise, targets, config=config, model=model, options=options, today=today))
    try:
        plan = await drama.make_plan(llm, model, premise, targets, retries=retries, extra=extra)
    except WritoryError as e:
        script.stop = "budget" if e.code is ErrorCode.COST_LIMIT_STORY else f"plan: {e.code.value}"
        return script
    script.plan = plan.model_dump()
    summaries: list[str] = []
    recent: list[dict[str, Any]] = []
    keep = limits.require("recent_lines")
    for k, seg_plan in enumerate(plan.segments, 1):
        try:
            result = await drama.write_segment(
                llm, model, plan, premise=premise, targets=targets, index=k, summaries=summaries,
                recent_lines=recent, limits=limits, quality=config.quality, retries=retries, extra=extra)
        except WritoryError as e:
            budget = e.code is ErrorCode.COST_LIMIT_STORY
            script.segments.append(SegmentOut(k, seg_plan.title, "skipped_budget" if budget else "error",
                                              target_words=targets.words_per_segment,
                                              error=None if budget else e.code.value))
            script.stop = "budget" if budget else f"segment {k}: {e.code.value}"
            break
        out = result.output
        seg = SegmentOut(k, seg_plan.title, "ok", lines=[line.model_dump() for line in out.lines],
                         words=result.words, target_words=targets.words_per_segment, length_off=result.length_off,
                         reveals=[r.model_dump() for r in out.reveals], summary=out.summary)
        if options.moderate:
            await _moderate_segment(seg, llm=llm, config=config)
        script.segments.append(seg)
        if seg.status != "ok":
            script.stop = "budget" if seg.status == "skipped_budget" else f"moderation: segment {k} {seg.status}"
            break
        summaries.append(f"Đoạn {k}: {seg.summary}")
        recent = seg.lines[-keep:]
    words = sum(s.words for s in script.segments if s.status == "ok")
    script.meta["words"] = words
    script.meta["est_minutes"] = round(words / targets.words_per_minute, 1)
    return script


def write_script(script: AudioScript, out: Path, calls: Sequence[Mapping[str, Any]]) -> list[Path]:
    files = {"tts.txt": render.render_tts(script), "script.md": render.render_markdown(script),
             "script.json": render.dumps(render.script_json(script))}
    if calls:
        files["calls.jsonl"] = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in calls)
    return render.write_dir(out, files, render.OUTPUT_FILES)


# --- lệnh -----------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m writory.audio.script",
                                description="Viết kịch bản audio từ hướng đi ngắn (chỉ admin; D-151).")
    sub = p.add_subparsers(dest="command", required=True)

    def common(q: argparse.ArgumentParser) -> None:
        q.add_argument("--out", help="thư mục kết quả (mặc định exports/audio-..., git bỏ qua)")
        q.add_argument("--budget", type=float, help="trần chi phí USD của cả lệnh (bắt buộc khi chạy thật)")
        q.add_argument("--dry-run", action="store_true", help="model giả, không mạng, không key")
        q.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
        q.add_argument("--config-dir", default=str(REPO_CONFIG_DIR))

    q = sub.add_parser("propose", help="đề xuất vài hướng đi ngắn từ tag")
    q.add_argument("--tags", required=True, help='ví dụ "thiếu gia bị hoán đổi thân phận, tiểu thư giả, trà xanh"')
    q.add_argument("--count", type=int, help="số hướng đi (mặc định limits.audio_script.propose_count)")
    common(q)

    w = sub.add_parser("write", help="viết kịch bản audio từ một hay nhiều hướng đi")
    w.add_argument("--premise", action="append", default=[], help="một hướng đi ngắn (lặp được)")
    w.add_argument("--premise-file", help="ideas.yaml của propose, YAML danh sách, hay file chữ (khối cách dòng trống)")
    w.add_argument("--pick", help="chỉ các id này, cách nhau dấu phẩy")
    w.add_argument("--minutes", type=int, help="thời lượng nói mong muốn (hướng đi có minutes riêng thì dùng của nó)")
    w.add_argument("--wpm", type=int, help="tốc độ đọc của TTS, chữ mỗi phút (mặc định limits.audio_script)")
    w.add_argument("--no-moderate", action="store_true", help="tắt kiểm duyệt G9 trên lời đọc")
    common(w)
    return p


def check_budget(config: AppConfig, budget: float | None, *, real: bool) -> float | None:
    cap = config.limits.audio_script.require("max_budget_usd")
    if budget is not None and (budget <= 0 or budget > cap):
        raise ConfigError(f"--budget {budget} phải trong (0, {cap}] (limits.audio_script.max_budget_usd)")
    if real and budget is None:
        raise ConfigError("chạy thật cần --budget (USD)")
    return budget


def _premises(args: argparse.Namespace, config: AppConfig) -> list[Premise]:
    max_chars = config.limits.audio_script.require("premise_max_chars")
    if args.premise and args.premise_file:
        raise ConfigError("dùng --premise hoặc --premise-file, không cả hai")
    found = (render.load_premises(Path(args.premise_file), max_chars=max_chars) if args.premise_file
             else render.parse_premises(list(args.premise), max_chars=max_chars))
    if args.pick:
        wanted = [p.strip() for p in args.pick.split(",") if p.strip()]
        missing = sorted(set(wanted) - {p.id for p in found})
        if missing:
            raise ConfigError(f"--pick: không có hướng đi {', '.join(missing)}")
        found = [p for p in found if p.id in wanted]
    return found


def _inner_llm(config: AppConfig, args: argparse.Namespace, models: list[str]) -> LLMClient:
    if args.dry_run:
        return DryRunAudioLLM()
    from writory.llm.openrouter import call_deadline
    from writory.llm.provider import bench_llm

    return bench_llm(config, Path(args.env_file), deadline_s=call_deadline(config), models=models)


async def run(argv: Sequence[str] | argparse.Namespace, *, llm: LLMClient | None = None,
              today: date | None = None) -> int:
    """`llm` và `today` chỉ để test truyền vào; lệnh thật tự dựng."""
    install_log_redaction()
    args = argv if isinstance(argv, argparse.Namespace) else build_parser().parse_args(list(argv))
    try:
        config = load_config(Path(args.config_dir))
        budget = check_budget(config, args.budget, real=not args.dry_run)
        model = require_model(config.models.roles, drama.ROLE)
        stamp = (today or date.today()).strftime("%Y%m%d")
        if args.command == "propose":
            return await _propose(args, config=config, model=model, budget=budget, llm=llm, stamp=stamp)
        return await _write(args, config=config, model=model, budget=budget, llm=llm, today=today, stamp=stamp)
    except (ConfigError, LimitNotSetError, ValueError, WritoryError) as e:
        print(f"lỗi: {redact(str(e))}", file=sys.stderr)
        return EXIT_CONFIG


def _client(inner: LLMClient, config: AppConfig, budget: Budget, calls: list[dict[str, Any]]) -> CappedClient:
    return CappedClient(inner, budget=budget, prices=config.models.prices,
                        max_tokens=config.limits.audio_script.require("max_output_tokens"),
                        record=calls.append, roles=_ROLES)


async def _propose(args: argparse.Namespace, *, config: AppConfig, model: str, budget: float | None,
                   llm: LLMClient | None, stamp: str) -> int:
    limits = config.limits.audio_script
    count = args.count or limits.require("propose_count")
    if not 1 <= count <= limits.require("propose_max"):
        raise ConfigError(f"--count {count} phải trong [1, {limits.propose_max}] (limits.audio_script.propose_max)")
    out = Path(args.out) if args.out else DEFAULT_OUT_ROOT / f"audio-ideas-{stamp}"
    render.check_fresh(out, render.IDEA_FILES)
    calls: list[dict[str, Any]] = []
    spend = Budget("audio", math.inf if budget is None else budget)
    client = _client(llm or _inner_llm(config, args, [model]), config, spend, calls)
    try:
        ideas = await drama.make_ideas(client, model, args.tags, count=count, retries=config.limits.retries,
                                       extra=role_extra(config.models, drama.ROLE))
    except WritoryError as e:
        print(f"lỗi {e.code.value}: không đề xuất được hướng đi ({redact(e.detail or '')}). Chạy lại, hay nâng "
              "--budget nếu vừa chạm trần.", file=sys.stderr)
        return EXIT_BUDGET if e.code is ErrorCode.COST_LIMIT_STORY else EXIT_ERRORS
    rows = [{"id": f"i{n}", "title": i.title.strip(), "premise": i.premise.strip(),
             "hooks": [h.strip() for h in i.hooks if h.strip()]} for n, i in enumerate(ideas, 1)]
    meta = {"model": model, "calls": len(calls), "cost_usd": round(spend.spent_usd, 6)}
    files = {"ideas.md": render.render_ideas_md(rows, tags=args.tags, meta=meta), "ideas.yaml": render.ideas_yaml(rows)}
    if calls:
        files["calls.jsonl"] = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in calls)
    render.write_dir(out, files, render.IDEA_FILES)
    print(f"đã ghi {len(rows)} hướng đi vào {out}; {meta['calls']} lời gọi, {meta['cost_usd']:.4f} USD",
          file=sys.stderr)
    return EXIT_OK


async def _write(args: argparse.Namespace, *, config: AppConfig, model: str, budget: float | None,
                 llm: LLMClient | None, today: date | None, stamp: str) -> int:
    limits = config.limits.audio_script
    premises = _premises(args, config)
    plans: list[tuple[Premise, Targets]] = []
    for p in premises:
        minutes = p.minutes or args.minutes
        if minutes is None:
            raise ConfigError(f"hướng đi {p.id}: cần --minutes (hay minutes trong file)")
        plans.append((p, render.targets(minutes, limits, words_per_minute=args.wpm)))
    root = Path(args.out) if args.out else DEFAULT_OUT_ROOT / f"audio-{stamp}"
    for p, _ in plans:  # trước mọi lời gọi tốn tiền: không đè kịch bản cũ
        render.check_fresh(root / p.id, render.OUTPUT_FILES)
    if args.no_moderate:
        print("CẢNH BÁO: --no-moderate: lời đọc KHÔNG qua kiểm duyệt G9 (D-151); admin chịu trách nhiệm trước khi "
              "đưa sang TTS.", file=sys.stderr)
    options = WriteOptions(moderate=not args.no_moderate, dry_run=args.dry_run, budget_usd=budget,
                           git=git_state(), config_sha256=config_sha256(Path(args.config_dir)))
    moderator = config.models.roles.moderate if options.moderate else None
    if options.moderate:
        require_model(config.models.roles, "moderate")
    inner = llm or _inner_llm(config, args, [model, *filter(None, [moderator])])
    spend = Budget("audio", math.inf if budget is None else budget)
    codes: list[int] = []
    for p, t in plans:
        out = root / p.id
        if spend.spent_usd >= spend.cap_usd:
            print(f"{p.id}: bỏ qua, đã chạm --budget", file=sys.stderr)
            codes.append(EXIT_BUDGET)
            continue
        calls: list[dict[str, Any]] = []
        before = spend.spent_usd
        script = await build_script(p, t, config=config, llm=_client(inner, config, spend, calls), options=options,
                                    today=today)
        script.meta["calls"] = len(calls)
        script.meta["cost_usd"] = round(spend.spent_usd - before, 6)
        write_script(script, out, calls)
        print(f"{p.id}: {out} · {script.meta['words']} chữ (~{script.meta['est_minutes']} phút) · "
              f"{script.meta['calls']} lời gọi · {script.meta['cost_usd']:.4f} USD"
              + (f" · DỪNG: {script.stop}" if script.stop else ""), file=sys.stderr)
        codes.append(EXIT_BUDGET if script.stop == "budget" else EXIT_ERRORS if script.stop else EXIT_OK)
    return max(codes, default=EXIT_OK) if EXIT_BUDGET not in codes else EXIT_BUDGET


def main(argv: Sequence[str] | None = None) -> int:
    # Console Windows mặc định cp1252: chữ Việt của --help và của lỗi làm lệnh sập (như bench_run).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return asyncio.run(run(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
