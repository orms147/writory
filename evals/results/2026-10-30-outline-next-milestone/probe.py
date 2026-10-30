"""Đo: đề dàn ý ch8 tu-tiên có/không dòng mốc "kế tiếp" m4 (khai trước ở `expectations.md`).

Chạy từ `backend/`, một mình (không song song với lượt khác dùng cùng key), Neo4j đang chạy:
    uv run python ../evals/results/2026-10-30-outline-next-milestone/probe.py --dry-run
    uv run python ../evals/results/2026-10-30-outline-next-milestone/probe.py --budget 0.10

Nạp gói chương 0..7 của lượt gốc vào một truyện Neo4j tạm (id riêng, xoá khi xong), dựng đề dàn ý
cảnh 2 của ch8 bằng `outline_messages`, gọi vai dàn ý n lần mỗi bên, chấm bằng nhóm `leak_terms` của
bí mật `fact_su_gia_that`. Ghi `results.jsonl`, `calls.jsonl`, `meta.json` (không ghi key, G7).
`--dry-run`: model giả, vẫn nạp Neo4j tạm, không gọi model thật.
"""

import argparse
import asyncio
import dataclasses
import json
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from writory.config import REPO_ROOT, load_config
from writory.graph import ChangePackage, apply_package, delete_story, ensure_schema
from writory.graph.schema import EDGE_TYPES
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, role_extra
from writory.llm.cost import CostEstimator
from writory.llm.fake import FakeLLM
from writory.pipeline.bench_run import RunServices, load_scenario
from writory.pipeline.chapter import _candidates
from writory.pipeline.pacing import chapter_goals
from writory.pipeline.passages import opening_of
from writory.pipeline.scene import EarlierScene, Named, SceneBrief, SceneOutline, outline_messages
from writory.pipeline.setup import CharacterOption, PlotOption, SettingOption, story_brief
from writory.pipeline.store import entities_from_rows
from writory.pipeline.story_plan import StoryPlan
from writory.quality.bench_d import load_keys
from writory.safety.leak import _SENTENCE, _pattern, forbidden_for_prompt, strip_diacritics

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")

RUN = "2026-10-29-run-long-after-tu-tien"
CHAPTER, SCENE, SECRET = 8, 2, "fact_su_gia_that"
CONFOUND_THREAD = "thread_lap_truong_su_gia"  # mạch "Ninh Tuyết Anh đại diện cho phe nào?", hạn gỡ ch7-13
SUMMARY_CHAPTERS = 2


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"),
            "dirty": bool(run("status", "--porcelain", "--", "backend", "config"))}


def scene_texts(number: int) -> list[str]:
    raw = (RESULTS / RUN / "chapters" / f"ch{number:02d}.md").read_text(encoding="utf-8")
    body = raw.split("## Lựa chọn cuối chương")[0]
    kept = [ln for ln in body.splitlines()
            if not ln.startswith("# Chương ") and not ln.startswith("_Lựa chọn dẫn tới")]
    return [part.strip() + "\n" for part in "\n".join(kept).split("* * *")]


class CappedLLM(LLMClient):
    """Chi tiêu thật; dừng trước lời gọi mà chi + 1,5 × lời gọi đắt nhất đã thấy vượt trần."""

    def __init__(self, inner: LLMClient, estimator: CostEstimator, budget: float, record) -> None:
        self._inner, self._est, self._budget, self._record = inner, estimator, budget, record
        self.spent = self.max_call = 0.0
        self.calls = 0
        self.halted: str | None = None

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        bound = self._est.bound(extra)
        reserve = 1.5 * self.max_call if self.max_call else self._est.max_cost(
            model, messages, response_schema)
        if self.spent + reserve > self._budget:
            self.halted = f"chi {self.spent:.4f} + giữ chỗ {reserve:.4f} > trần {self._budget:.2f}"
            raise RuntimeError(self.halted)
        result = await self._inner.chat(model, messages, response_schema=response_schema, extra=bound)
        cost = result.usage.cost_usd or 0.0
        self.spent += cost
        self.max_call = max(self.max_call, cost)
        self.calls += 1
        self._record({"seq": self.calls, "cost_usd": cost, "spent_usd": round(self.spent, 6),
                      "prompt_tokens": result.usage.prompt_tokens,
                      "completion_tokens": result.usage.completion_tokens,
                      "finish_reason": result.finish_reason})
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


def outline_text(o: SceneOutline) -> str:
    return "\n".join([o.goal, *o.beats, o.ends_at])


def secret_hit(text: str, groups: list[list[str]]) -> list[str]:
    """Nhóm `leak_terms` có mọi cụm trong một câu của `text` (luật của `safety/leak.check_leaks`)."""
    flat = strip_diacritics(text)
    hits = []
    for sentence in _SENTENCE.finditer(flat):
        for group in groups:
            if all(_pattern(p).search(sentence.group()) for p in group):
                hits.append(" + ".join(group))
    return hits


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.10)
    ap.add_argument("--n", type=int, default=10, help="số lời gọi mỗi bên")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--env-file", default="C:/Work/AI/WriTory/.env")
    args = ap.parse_args()
    out = Path(args.out)
    if not args.dry_run and (out / "results.jsonl").exists():
        print("results.jsonl đã có: không ghi đè; chọn --out khác")
        return 1
    out.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    dump = json.loads((RESULTS / RUN / "truth_dump.json").read_text(encoding="utf-8"))
    plan = StoryPlan.model_validate(dump["plan"])
    packs = {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()}
    meta = json.loads((RESULTS / RUN / "meta.json").read_text(encoding="utf-8"))
    setup = json.loads((RESULTS / RUN / "setup.json").read_text(encoding="utf-8"))
    scenario, _ = load_scenario(REPO_ROOT / meta["scenario"]["path"])
    picked = [cls.model_validate(setup[step]["options"][setup[step]["picked"]])
              for step, cls in (("settings", SettingOption), ("plots", PlotOption),
                                ("characters", CharacterOption))]
    brief_text = story_brief(scenario.story_choices(), *picked, moderation=cfg.moderation)
    secret = next(s for s in plan.secrets if s.fact_id == SECRET)
    groups = [list(g) for g in secret.leak_terms]

    services = RunServices(_env_file=Path(args.env_file))  # type: ignore[call-arg]
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(services.neo4j_uri, auth=(
        services.neo4j_user, services.neo4j_password.get_secret_value()))
    story_id = f"probe-{uuid.uuid4().hex[:10]}"
    try:
        driver.verify_connectivity()
        ensure_schema(driver)
        for n in sorted(packs):
            if n <= CHAPTER - 1:
                apply_package(driver, story_id, packs[n])
        from writory.graph.context import writer_context

        before = OverlayState(EmptyState(), [packs[n] for n in sorted(packs) if n <= CHAPTER - 1])
        protagonist = before.protagonist_id()
        ctxl = cfg.limits.context
        outline_one = dump["chapters"][str(CHAPTER)][0]["outlines"][0]
        present = list(dict.fromkeys([protagonist, *outline_one["present"]]))
        ctx = writer_context(
            driver, story_id, CHAPTER - 1, present, plan, max_neighbors=ctxl.writer_max_neighbors,
            personality_max_chars=ctxl.character_personality_max_chars,
            appearance_max_chars=ctxl.character_appearance_max_chars)
        keep = cfg.limits.facts.writer_max_page_facts
        if keep:
            from writory.graph.context import cap_page_facts
            ctx = dataclasses.replace(ctx, known_facts=cap_page_facts(ctx.known_facts, keep))

        ids = [n.id for k, p in packs.items() if k <= CHAPTER - 1 for n in p.nodes]
        catalogue = entities_from_rows(before.nodes(ids))
        names = {e.id: Named(e.text, e.user_authored) for e in catalogue}
        edge_ends = {r.id: (r.type, r.source, r.target)
                     for t in EDGE_TYPES for r in before.edges_at(t, CHAPTER)}
        goals = chapter_goals(
            plan, CHAPTER, before, standstill_chapters=ctxl.standstill_chapters,
            unplanned_goal=ctxl.unplanned_chapter_goal, idle_chapters=ctxl.idle_chapters,
            milestone_lookahead=ctxl.milestone_lookahead)
        goals_b = dataclasses.replace(goals, milestones=())
        goals_c = dataclasses.replace(goals_b, threads=tuple(
            t for t in goals.threads if t.thread_id != CONFOUND_THREAD))
        view = player_view_of(before, CHAPTER)
        forbidden = forbidden_for_prompt(before, view=view, plan=plan, story_brief=brief_text,
                                         scope="scene")
        lengths = cfg.story_lengths.chapter_chars
        count = scenario.scene_count
        act = next((a.name for a in plan.acts if a.from_chapter <= CHAPTER <= a.to_chapter), None)
        wanted = [c for c in range(CHAPTER - SUMMARY_CHAPTERS, CHAPTER) if c >= 1]
        summaries = tuple((c, dump["chapters"][str(c)][-1]["summary"]) for c in wanted
                          if dump["chapters"][str(c)][-1].get("summary"))
        openings = tuple(
            (c, o) for c in range(max(1, CHAPTER - ctxl.previous_openings), CHAPTER)
            if (o := opening_of("\n\n".join(scene_texts(c)), ctxl.previous_opening_max_chars)))
        first_text = scene_texts(CHAPTER)[0]
        base_brief = SceneBrief(
            chapter=CHAPTER, scene=SCENE, scene_count=count, min_chars=lengths.min // count,
            max_chars=lengths.max // count, act=act, story_brief=brief_text,
            player_action=dump["chapters"][str(CHAPTER)][0]["player_action"],
            earlier=(EarlierScene(1, first_text, ChangePackage(commit_id="earlier")),),
            goals=goals, summaries=summaries, forbidden=tuple(forbidden),
            forbidden_max=ctxl.forbidden_names_max, openings=openings)
        candidates = _candidates(ctx, protagonist)
        arms = {
            "A-co-m4": outline_messages(base_brief, ctx, candidates, names, edge_ends, []),
            "B-khong-m4": outline_messages(dataclasses.replace(base_brief, goals=goals_b), ctx,
                                           candidates, names, edge_ends, []),
            # Thăm dò (khai ở expectations.md): bỏ cả mạch trùng nội dung với bí mật.
            "C-khong-m4-khong-mach": outline_messages(
                dataclasses.replace(base_brief, goals=goals_c), ctx, candidates, names, edge_ends, []),
        }
    finally:
        delete_story(driver, story_id)
        driver.close()

    a, b = arms["A-co-m4"][1].content, arms["B-khong-m4"][1].content
    assert arms["A-co-m4"][0].content == arms["B-khong-m4"][0].content
    assert "Danh nghĩa của Ninh Tuyết Anh" in a and "Danh nghĩa của Ninh Tuyết Anh" not in b
    assert "### Mốc cốt truyện" in a and "### Mốc cốt truyện" not in b
    # Hai bên chỉ khác mục "### Mốc cốt truyện" (kiểm bằng cách bỏ mục đó ở bên A)
    section = a[a.index("### Mốc cốt truyện"):]
    section = section[:section.index("\n###", 5) + 1] if "\n###" in section[5:] else section
    assert a.replace(section, "") == b, "hai đề khác nhau ở chỗ ngoài mục mốc"

    if args.dry_run:
        print(f"độ dài đề A/B: {len(a)}/{len(b)} ký tự; phần cuối đề A:")
        print(a[-1600:])
    model = cfg.models.roles.require("outline")
    extra = role_extra(cfg.models, "outline")
    estimator = CostEstimator.from_config(cfg)
    calls_log = None if args.dry_run else (out / "calls.jsonl").open("w", encoding="utf-8")
    current: dict = {}

    def record(row: dict) -> None:
        if calls_log:
            calls_log.write(json.dumps(current | row, ensure_ascii=False) + "\n")
            calls_log.flush()

    if args.dry_run:
        fake = json.dumps({"goal": "g", "present": [protagonist], "beats": ["b1", "b2", "b3"],
                           "ends_at": "e", "resolves": []})
        inner: LLMClient = FakeLLM.scripted([fake] * 200, cost_usd=0.003)
    else:
        from writory.llm.openrouter import OpenRouterClient
        keys = load_keys(Path(args.env_file), ["openrouter"])
        assert keys.openrouter_api_key is not None
        inner = OpenRouterClient(keys.openrouter_api_key, deadline_s=300)
    llm = CappedLLM(inner, estimator, args.budget, record)

    rows, skipped = [], []
    for i in range(args.n):  # xen kẽ hai bên để lệch theo thời gian không dồn vào một bên
        for arm, messages in arms.items():
            current.clear()
            current.update({"arm": arm, "i": i})
            try:
                outline, chat = await llm.chat_json(model, messages, SceneOutline, extra=extra)
            except RuntimeError:
                skipped.append({"arm": arm, "i": i})
                continue
            text = outline_text(outline)
            hits = secret_hit(text, groups)
            rows.append({"arm": arm, "i": i, "hit": bool(hits), "groups": hits,
                         "mentions_minh_uoc": "minh uoc" in strip_diacritics(text).lower(),
                         "resolves": outline.resolves, "cost_usd": round(chat.usage.cost_usd or 0.0, 6),
                         "outline": {"goal": outline.goal, "beats": outline.beats,
                                     "ends_at": outline.ends_at}})
    n = {arm: sum(r["hit"] for r in rows if r["arm"] == arm) for arm in arms}
    done = {arm: sum(r["arm"] == arm for r in rows) for arm in arms}
    print("; ".join(f"{arm}: trúng {n[arm]}/{done[arm]}" for arm in arms)
          + f"; chi {llm.spent:.4f} USD" + (f"; dừng: {llm.halted}" if llm.halted else ""))
    if not args.dry_run:
        with (out / "results.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        (out / "meta.json").write_text(json.dumps({
            "bench": "outline-next-milestone-probe", "git": git_info(), "model": model,
            "extra": extra, "run": RUN, "chapter": CHAPTER, "scene": SCENE, "secret": SECRET,
            "n_per_arm": args.n, "budget_usd": args.budget, "spent_usd": round(llm.spent, 6),
            "calls": llm.calls, "halted": llm.halted, "skipped": skipped,
            "hits": n, "completed": done,
            "prompt_versions": meta["prompt_versions"],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
