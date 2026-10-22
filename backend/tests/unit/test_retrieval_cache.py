"""D-96: (1) truy hồi đoạn kèm đoạn kế sau mỗi đoạn trúng, cấu hình trong limits.yaml, bài A đọc cùng
cấu hình và có phép kiểm tái lập để chọn số; (2) token cache của OpenRouter vào nhật ký lời gọi, nhật
ký chi phí và báo cáo bài A. Không mạng, không model thật."""

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from tests.api_fixtures import MemoryCostLedger
from writory.config import ConfigError, load_config
from writory.graph import read_sample
from writory.llm.base import Message, Usage
from writory.llm.fake import FakeLLM
from writory.llm.ledger import CallCost, RecordingClient
from writory.llm.openrouter import OpenRouterClient
from writory.pipeline import passages
from writory.pipeline.bench_a import (
    CACHE_COLD,
    CACHE_WARM,
    ContextBuilder,
    RunOptions,
    compute_report,
    page_settings,
    run_bench,
)
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_retrieval import recall_table
from writory.quality.bench_d import Store

CFG = load_config()
SAMPLE = read_sample()
STORY = {c.number: c.text for c in SAMPLE.chapters if c.number >= 1}
CHUNK = 500
FACTS = "questions-ky-ao-vua-1-facts.yaml"


def pairs(hits) -> list[tuple[int, int]]:
    return [(c.chapter, c.index) for c in hits]


def pool() -> passages.PagePool:
    return passages.PagePool({ch: STORY[ch] for ch in range(1, 5)}, chunk_chars=CHUNK)


# --- đoạn kế sau mỗi đoạn trúng ---------------------------------------------------------------------

QUESTION = "Lão Gù giao thanh kiếm cho ai?"


def test_neighbors_zero_is_exactly_the_old_behaviour():
    assert pool().top(QUESTION, top_k=3, neighbors=0) == pool().top(QUESTION, top_k=3)


def test_each_hit_brings_the_chunk_right_after_it_in_the_same_chapter():
    plain = pool().top(QUESTION, top_k=1)
    with_next = pool().top(QUESTION, top_k=1, neighbors=1)
    [hit] = plain
    assert pairs(with_next) == [(hit.chapter, hit.index), (hit.chapter, hit.index + 1)]
    assert with_next[1].text != hit.text


def test_neighbor_never_crosses_into_the_next_chapter():
    chunks = passages.chunk_chapter(2, STORY[2], chunk_chars=CHUNK)
    last = chunks[-1]
    hits = pool().top(last.text, top_k=1, neighbors=1)
    assert pairs(hits) == [(2, last.index)]  # đoạn cuối chương 2: không có đoạn kế trong chương
    assert (3, 0) not in pairs(hits)


def test_hits_and_neighbors_come_back_in_story_order_without_duplicates():
    hits = pool().top(QUESTION, top_k=3, neighbors=1)
    assert pairs(hits) == sorted(set(pairs(hits)))


def test_a_neighbor_that_is_also_a_hit_is_not_repeated():
    base = pool().top(QUESTION, top_k=3)
    expanded = pool().top(QUESTION, top_k=3, neighbors=1)
    assert set(pairs(base)) <= set(pairs(expanded))
    assert len(pairs(expanded)) == len(set(pairs(expanded)))


def test_max_chars_drops_neighbors_before_any_hit():
    plain = pool().top(QUESTION, top_k=2)
    cap = sum(len(c.text) for c in plain) + 5  # đủ chỗ cho các đoạn trúng, không cho đoạn kế
    capped = pool().top(QUESTION, top_k=2, max_chars=cap, neighbors=1)
    assert pairs(capped) == pairs(plain)
    assert sum(len(c.text) for c in capped) <= cap


def test_max_chars_keeps_neighbors_that_still_fit_in_hit_rank_order():
    plain = pool().top(QUESTION, top_k=1)
    roomy = pool().top(QUESTION, top_k=1, max_chars=10_000, neighbors=1)
    assert len(roomy) == len(plain) + 1


def test_negative_neighbors_is_a_programming_error():
    with pytest.raises(ValueError, match="neighbors"):
        pool().top(QUESTION, top_k=1, neighbors=-1)


# --- cấu hình --------------------------------------------------------------------------------------


def test_limits_yaml_has_the_page_neighbors_number():
    n = CFG.limits.context.page_quotes_neighbors
    assert isinstance(n, int) and n >= 0
    assert "page_quotes_neighbors" in (Path(__file__).parents[3] / "config" / "limits.yaml").read_text(
        encoding="utf-8")


def test_negative_neighbors_in_config_is_rejected(tmp_path: Path):
    import shutil

    import yaml

    from writory.config import REPO_CONFIG_DIR

    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    path = target / "limits.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["context"]["page_quotes_neighbors"] = -1
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="page_quotes_neighbors"):
        load_config(target)


def test_product_writer_stays_off_by_default_whatever_the_neighbors_number():
    assert CFG.limits.context.page_quotes_top_k == 0  # D-85 vẫn mặc định tắt


# --- bài A đọc cùng cấu hình ----------------------------------------------------------------------


DATA = load_data(questions_file=FACTS)


def test_bench_a_reads_neighbors_and_cap_from_the_same_limits():
    got = page_settings(CFG)
    assert got == {"neighbors": CFG.limits.context.page_quotes_neighbors,
                   "max_chars": CFG.limits.context.page_quotes_max_chars}


def test_bench_a_override_flag_wins_and_is_validated():
    assert page_settings(CFG, neighbors=0)["neighbors"] == 0
    assert page_settings(CFG, neighbors=2)["neighbors"] == 2
    with pytest.raises(ConfigError, match="page-neighbors"):
        page_settings(CFG, neighbors=-1)


def _hybrid_hits(neighbors: int, max_chars: int | None):
    builder = ContextBuilder(DATA, DATA.state_at, {}, page_neighbors=neighbors,
                             page_max_chars=max_chars)
    q = DATA.question("item-06")
    return builder.build("graph_quotes", q).detail["retrieved"]


def test_graph_quotes_gets_the_neighbors_and_rag_does_not():
    off, on = _hybrid_hits(0, None), _hybrid_hits(1, None)
    assert len(on) > len(off) and set(off) <= set(on)
    q = DATA.question("item-06")
    rag_off = ContextBuilder(DATA, DATA.state_at, {"x": "y"}).build("rag", q).detail["retrieved"]
    rag_on = ContextBuilder(DATA, DATA.state_at, {"x": "y"}, page_neighbors=1,
                            page_max_chars=2400).build("rag", q).detail["retrieved"]
    assert rag_on == rag_off  # đối chứng: hệ rag giữ nguyên, so được với kết quả cũ


def test_cap_without_neighbors_leaves_the_old_hits_unchanged_on_the_facts_set():
    """Giữ trần 2400 ký tự mà không đoạn kế thì mọi câu của đề ra đúng các đoạn cũ: lần đo mới so
    được với `memory-ky-ao-vua-1-facts-s3` ở phần đoạn trúng."""
    for q in DATA.questions.questions:
        a = ContextBuilder(DATA, DATA.state_at, {}, page_neighbors=0,
                           page_max_chars=None).build("graph_quotes", q).detail["retrieved"]
        b = ContextBuilder(DATA, DATA.state_at, {}, page_neighbors=0,
                           page_max_chars=CFG.limits.context.page_quotes_max_chars
                           ).build("graph_quotes", q).detail["retrieved"]
        assert a == b, q.id


def test_meta_and_fingerprint_record_the_retrieval_settings(tmp_path: Path):
    import asyncio

    out = tmp_path / "o"
    opts = RunOptions(out=out, dry_run=True, samples=1, systems=["graph_quotes"],
                      question_ids=["item-06"], page_neighbors=2)
    assert asyncio.run(run_bench(DATA, opts, config=CFG, log=lambda _: None)) == 0
    meta = Store(out).read_meta()
    assert meta["runs"][-1]["page_quotes"] == {"neighbors": 2, "max_chars": 2400}
    assert meta["fingerprint"]["page_quotes"] == {"neighbors": 2, "max_chars": 2400}
    again = RunOptions(out=out, dry_run=True, samples=1, systems=["graph_quotes"],
                       question_ids=["item-06"], page_neighbors=0)
    with pytest.raises(ConfigError, match="page_quotes"):
        asyncio.run(run_bench(DATA, again, config=CFG, log=lambda _: None))


# --- phép kiểm truy hồi tái lập ---------------------------------------------------------------------


def test_recall_table_is_reproducible_and_matches_the_numbers_used_to_pick_the_setting():
    table = recall_table(DATA, top_ks=(2, 3, 4), neighbors=(0, 1), max_chars=None)
    assert table.total == 27  # câu có bằng chứng ở chương cũ
    cell = {(r.top_k, r.neighbors): r.hit for r in table.rows}
    assert cell == {(2, 0): 16, (2, 1): 19, (3, 0): 18, (3, 1): 21, (4, 0): 18, (4, 1): 21}
    assert recall_table(DATA, top_ks=(2,), neighbors=(0, 1), max_chars=None).rows == [
        r for r in table.rows if r.top_k == 2]


def test_recall_table_counts_characters_and_respects_the_cap():
    free = recall_table(DATA, top_ks=(2,), neighbors=(1,), max_chars=None)
    capped = recall_table(DATA, top_ks=(2,), neighbors=(1,), max_chars=1200)
    assert capped.rows[0].mean_chars <= free.rows[0].mean_chars
    assert capped.rows[0].hit <= free.rows[0].hit
    assert free.rows[0].mean_chars > recall_table(DATA, top_ks=(2,), neighbors=(0,),
                                                  max_chars=None).rows[0].mean_chars


def test_recall_counts_a_question_only_if_a_quote_is_in_the_retrieved_text():
    table = recall_table(DATA, top_ks=(1,), neighbors=(0,), max_chars=None)
    assert 0 <= table.rows[0].hit < table.total


# --- token cache trong usage ------------------------------------------------------------------------


def completion(usage: dict) -> dict:
    return {"id": "gen-1", "model": "x/y", "choices": [
        {"message": {"role": "assistant", "content": "Xin chào"}, "finish_reason": "stop"}],
        "usage": usage}


async def usage_of(usage: dict) -> Usage:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=completion(usage)))
    http = httpx.AsyncClient(transport=transport)
    client = OpenRouterClient(SecretStr("sk-or-v1-" + "ab" * 16), http=http)
    try:
        return (await client.chat("x/y", [Message(role="user", content="a")])).usage
    finally:
        await http.aclose()


async def test_openrouter_reads_cached_tokens_from_prompt_tokens_details():
    u = await usage_of({"prompt_tokens": 4000, "completion_tokens": 30, "cost": 0.00005,
                        "prompt_tokens_details": {"cached_tokens": 3968, "cache_write_tokens": 0}})
    assert u.cached_tokens == 3968 and u.prompt_tokens == 4000


async def test_openrouter_zero_cached_tokens_is_zero_not_unknown():
    u = await usage_of({"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001,
                        "prompt_tokens_details": {"cached_tokens": 0}})
    assert u.cached_tokens == 0


@pytest.mark.parametrize("usage", [
    {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
    {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001, "prompt_tokens_details": None},
    {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001, "prompt_tokens_details": {}},
    {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001,
     "prompt_tokens_details": {"cached_tokens": "nhiều"}},
])
async def test_missing_or_malformed_cache_field_is_unknown(usage):
    assert (await usage_of(usage)).cached_tokens is None


def test_fake_llm_usage_has_no_cache_number():
    assert Usage(cost_usd=0.0).cached_tokens is None


async def test_recording_client_passes_cached_tokens_to_the_cost_sink():
    class Cached(FakeLLM):
        def _usage(self) -> Usage:
            return Usage(prompt_tokens=100, completion_tokens=5, cost_usd=0.01, cached_tokens=64)

    seen: list[CallCost] = []
    client = RecordingClient(Cached.scripted(["{}"]), seen.append, role_of=lambda _s: "writer")
    await client.chat("m", [Message(role="user", content="x")])
    assert seen[0].cached_tokens == 64


def test_memory_ledger_keeps_cached_tokens():
    from writory.db import CostEntry

    ledger = MemoryCostLedger()
    ledger.record(CostEntry("writer", "m", 10, 1, 0.1, cached_tokens=7), story_id="s", chapter=1)
    assert ledger.rows[0][0].cached_tokens == 7


# --- báo cáo bài A tách lượt lạnh và lượt có cache ------------------------------------------------


def row(system: str, sample: int, cached: int | None, cost: float, prompt=1000, qid="item-01"):
    q = DATA.question(qid)
    call = {"status": "ok", "prompt_tokens": prompt, "completion_tokens": 10, "cost_usd": cost,
            "cached_tokens": cached}
    return {"id": qid, "group": q.group, "system": system, "sample": sample,
            "ask_chapter": q.ask_chapter, "fact_chapter": q.fact_chapter, "distance": q.distance,
            "type": q.answer.type, "question": q.question, "answer": "x", "correct": True,
            "abstained": False, "parsed": None, "context_chars": 10, "calls": [call],
            "cost_usd": cost}


def report_for(tmp_path: Path, rows: list[dict]):
    store = Store(tmp_path)
    for r in rows:
        store.append("results.jsonl", r)
    return compute_report(DATA, store, ["graph"], DATA.questions.questions[:1], 3)["systems"]["graph"]


def test_report_splits_cold_and_cached_calls(tmp_path: Path):
    got = report_for(tmp_path, [row("graph", 0, 0, 0.0004), row("graph", 1, 900, 0.00005),
                               row("graph", 2, 900, 0.00005)])["cache"]
    assert got["cold_calls"] == 1 and got["warm_calls"] == 2 and got["unknown_calls"] == 0
    assert got["cold_usd"] == pytest.approx(0.0004) and got["warm_usd"] == pytest.approx(0.0001)
    assert got["cached_tokens"] == 1800 and got["prompt_tokens"] == 3000
    assert got["cold_usd_per_call"] == pytest.approx(0.0004)
    assert got["warm_usd_per_call"] == pytest.approx(0.00005)


def test_report_marks_calls_without_cache_numbers_as_unknown_not_cold(tmp_path: Path):
    got = report_for(tmp_path, [row("graph", 0, None, 0.0004)])["cache"]
    assert (got["cold_calls"], got["warm_calls"], got["unknown_calls"]) == (0, 0, 1)
    assert got["cold_usd_per_call"] is None


def test_summary_md_has_a_cache_section(tmp_path: Path):
    from writory.pipeline.bench_a import build_summary

    store = Store(tmp_path)
    for r in (row("graph", 0, 0, 0.0004), row("graph", 1, 900, 0.00005)):
        store.append("results.jsonl", r)
    store.write_meta({"runs": [{"samples": 3}], "fingerprint": {}, "versions": {}})
    text = build_summary(DATA, store, compute_report(DATA, store, ["graph"],
                                                     DATA.questions.questions[:1], 3))
    assert "Cache prompt" in text and CACHE_COLD in text and CACHE_WARM in text


def test_budgetedclient_rows_carry_cached_tokens():
    from writory.pipeline.bench_run import BudgetedClient, Price, StepTracker
    from writory.quality.bench_d import Budget

    class Cached(FakeLLM):
        def _usage(self) -> Usage:
            return Usage(prompt_tokens=100, completion_tokens=5, cost_usd=0.01, cached_tokens=64)

    rows: list[dict] = []
    gate = BudgetedClient(Cached.scripted(["{}"]), budget=Budget("b", 1.0),
                          prices={"m": Price.model_validate({"in": 0.1, "out": 0.5})},
                          max_tokens=100, tracker=StepTracker(CFG.limits.cost_usd),
                          record=rows.append)
    import asyncio

    asyncio.run(gate.chat("m", [Message(role="user", content="x")]))
    assert rows[0]["cached_tokens"] == 64
    assert json.dumps(rows[0])  # ghi được ra calls.jsonl


async def test_player_llm_writes_cached_tokens_into_the_cost_ledger():
    """Đường sản phẩm: lời gọi bằng key người chơi → `RecordingClient` → nhật ký chi phí (D-96)."""
    from tests.api_fixtures import FAKE_KEY, MASTER_KEY, AllowAllQuota, MemoryKeyStore
    from writory.api import deps
    from writory.llm.cost import CostEstimator
    from writory.safety.crypto import KeyCipher

    class Cached(FakeLLM):
        def _usage(self) -> Usage:
            return Usage(prompt_tokens=100, completion_tokens=5, cost_usd=0.01, cached_tokens=64)

    cipher = KeyCipher(SecretStr(MASTER_KEY))
    ledger = MemoryCostLedger()
    llm = deps.PlayerLLM(
        keys=MemoryKeyStore(cipher.encrypt(SecretStr(FAKE_KEY))), cipher=cipher,
        factory=lambda _key: Cached.scripted(["{}"]), ledger=ledger, limits=CFG.limits.cost_usd,
        quota=AllowAllQuota(), estimator=CostEstimator.from_config(CFG))
    client, _tracker = llm.open(story_id="s1", chapter=2)
    await client.chat(CFG.models.roles.narrator, [Message(role="user", content="x")])
    [(entry, story_id, _setup, chapter)] = ledger.rows
    assert (entry.cached_tokens, story_id, chapter) == (64, "s1", 2)
