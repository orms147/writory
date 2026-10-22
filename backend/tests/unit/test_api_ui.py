"""Endpoint cho giao diện (D-66): tủ truyện, cấu hình công khai, chi phí người chơi. Không Docker:
lớp Postgres thay bằng bản trong bộ nhớ; SQL thật nằm ở `tests/graph/test_ui_api.py`.

G1: phản hồi là danh sách trắng, không id lớp truth, không chữ kế hoạch, không model id hay giá.
G7: `/player/costs` không có gì của key. G10 (TODO đăng nhập): chỉ dữ liệu của người đang dùng.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import (
    FAKE_KEY,
    MemoryCostLedger,
    MemoryKeyStore,
    captured_logs,
    dev_settings,
    offline,
)
from writory.api import create_app, deps
from writory.api import stories as stories_api
from writory.api.schemas import last_sentence
from writory.db import CostEntry, StorySummaryRecord, utc_month

from .test_narrator import CFG, PLAN


async def ok() -> bool:
    return True


def build(*, config=CFG, store: MemoryKeyStore | None = None,
          ledger: MemoryCostLedger | None = None, owner: str = "dev", clock=None):
    app = create_app(dev_settings(), health_checks={"neo4j": ok}, config=config)
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    offline(app)
    app.dependency_overrides[deps.get_owner_id] = lambda: owner
    app.dependency_overrides[deps.get_key_store] = lambda: store or MemoryKeyStore()
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger or MemoryCostLedger()
    if clock is not None:
        app.dependency_overrides[deps.get_clock] = lambda: (lambda: clock)  # đồng hồ giả
    return app


def leaves(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from leaves(v)
    elif isinstance(value, list):
        for v in value:
            yield from leaves(v)
    else:
        yield value


def plan_strings() -> set[str]:
    """Mọi chữ của bản kế hoạch ẩn (id bí mật, cụm từ dò lộ, tên hồi…)."""
    return {s for s in leaves(PLAN.model_dump(mode="json")) if isinstance(s, str)}


# --- câu trích cuối ------------------------------------------------------------------------------


@pytest.mark.parametrize(("scene", "expected"), [
    ("Câu một. Dưới chân nó, tro vẫn còn ấm.", "Dưới chân nó, tro vẫn còn ấm."),
    ("Đoạn đầu.\n\nĐoạn cuối có hai câu! Câu này là cuối?\n\n", "Câu này là cuối?"),
    ("Hắn nói xong.\n- Ta sẽ trở lại.", "Ta sẽ trở lại."),
    ("- Đi thôi. Trời sắp sáng rồi.", "Trời sắp sáng rồi."),
    ("Hắn im lặng… Rồi bỏ đi.", "Rồi bỏ đi."),
    ('Nàng nói: "Về đi." Gió nổi lên.', "Gió nổi lên."),
    ('Nàng chỉ nói: "Về đi."', 'Nàng chỉ nói: "Về đi."'),
    ("Trời tối dần", "Trời tối dần"),
    ("Chờ đã...", "Chờ đã..."),
])
def test_last_sentence_is_the_last_sentence_verbatim(scene, expected):
    got = last_sentence(scene)
    assert got == expected
    assert got in scene  # chữ đúng như đã hiện, không viết lại


@pytest.mark.parametrize("scene", ["", "   \n\n ", "- ", "-"])
def test_last_sentence_of_nothing_is_none(scene):
    assert last_sentence(scene) is None


# --- tủ truyện ----------------------------------------------------------------------------------

STORY_KEYS = {"story_id", "title", "length_level", "length_label", "chapter", "finished",
              "last_excerpt", "updated_at"}
T0 = datetime(2026, 10, 21, 8, 30, tzinfo=UTC)


def record(story_id: str, **kw) -> StorySummaryRecord:
    base = {"id": story_id, "length_level": "short", "committed_chapter": 3, "updated_at": T0,
            "title": "Ngọc bội rạn", "total_chapters": PLAN.total_chapters,
            "last_scene": "Mở đầu.\n\nDưới chân nó, tro vẫn còn ấm."}
    return StorySummaryRecord(**{**base, **kw})


def listed(monkeypatch, records, *, owner="dev", config=CFG):
    seen: list[str] = []

    def fake(conn, owner_id):
        seen.append(owner_id)
        return records

    monkeypatch.setattr(stories_api, "owned_story_summaries", fake)
    with TestClient(build(owner=owner, config=config)) as client:
        resp = client.get("/stories")
    assert resp.status_code == 200
    return resp.json(), seen


def test_story_list_has_only_whitelisted_fields(monkeypatch):
    body, seen = listed(monkeypatch, [record("story-a")], owner="nguoi-choi-1")
    assert seen == ["nguoi-choi-1"]  # chỉ đọc truyện của người đang dùng (G10)
    assert set(body) == {"stories"}
    [story] = body["stories"]
    assert story == {
        "story_id": "story-a", "title": "Ngọc bội rạn", "length_level": "short",
        "length_label": CFG.story_lengths.levels["short"].label, "chapter": 3, "finished": False,
        "last_excerpt": "Dưới chân nó, tro vẫn còn ấm.", "updated_at": "2026-10-21T08:30:00+00:00",
    }


def test_story_list_keeps_the_newest_first_order_of_the_store(monkeypatch):
    recs = [record("story-b", updated_at=T0), record("story-a", updated_at=T0 - timedelta(days=1))]
    body, _ = listed(monkeypatch, recs)
    assert [s["story_id"] for s in body["stories"]] == ["story-b", "story-a"]


def test_story_list_updated_at_is_iso_in_utc(monkeypatch):
    hanoi = timezone(timedelta(hours=7))
    body, _ = listed(monkeypatch, [record("story-a", updated_at=datetime(2026, 10, 21, 15, 30,
                                                                            tzinfo=hanoi))])
    assert body["stories"][0]["updated_at"] == "2026-10-21T08:30:00+00:00"
    assert datetime.fromisoformat(body["stories"][0]["updated_at"]) == T0


@pytest.mark.parametrize(("chapter", "total", "finished"), [
    (3, 6, False), (6, 6, True), (0, 6, False), (None, 6, False), (6, None, False)])
def test_finished_follows_the_hidden_plan_without_showing_it(monkeypatch, chapter, total,
                                                              finished):
    body, _ = listed(monkeypatch, [record("story-a", committed_chapter=chapter,
                                          total_chapters=total)])
    story = body["stories"][0]
    assert (story["chapter"], story["finished"]) == (chapter or 0, finished)
    assert "total_chapters" not in story


def test_story_without_seen_text_has_null_title_and_excerpt(monkeypatch):
    """Truyện không tạo qua /setup (không có phiên khởi tạo) chưa có tên người chơi đã thấy;
    chương 0 chưa có trang nào: không bịa chữ."""
    body, _ = listed(monkeypatch, [record("story-a", title=None, committed_chapter=0,
                                          last_scene=None)])
    story = body["stories"][0]
    assert (story["title"], story["last_excerpt"]) == (None, None)


def test_unknown_length_level_has_null_label(monkeypatch):
    body, _ = listed(monkeypatch, [record("story-a", length_level="da-xoa-khoi-config")])
    assert body["stories"][0]["length_label"] is None


def test_story_list_has_no_plan_text_or_truth_ids(monkeypatch):
    body, _ = listed(monkeypatch, [record("story-a"), record("story-b", committed_chapter=6)])
    values = {x for x in leaves(body) if isinstance(x, str)}
    assert not values & plan_strings()


def test_empty_story_list(monkeypatch):
    body, _ = listed(monkeypatch, [])
    assert body == {"stories": []}


# --- cấu hình công khai -------------------------------------------------------------------------


def expected_public(cfg) -> dict:
    lim = cfg.limits
    return {
        "input": {
            "custom_action_max_chars": lim.input.custom_action_max_chars,
            "character_name_max_chars": lim.input.character_name_max_chars,
            "personality_max_chars": lim.input.personality_max_chars,
            "backstory_max_chars": lim.input.backstory_max_chars,
            "narrator_question_max_chars": lim.input.narrator_question_max_chars,
        },
        "narrator_questions_per_chapter": lim.rate_limit.narrator_questions_per_chapter,
        "rewrite_per_scene": lim.retries.rewrite_per_scene,
        "cost_usd": {"per_scene": lim.cost_usd.per_scene, "per_chapter": lim.cost_usd.per_chapter,
                     "per_story": lim.cost_usd.per_story},
        "story_lengths": [
            {"key": k, "label": v.label, "chapters_min": v.chapters.min,
             "chapters_max": v.chapters.max}
            for k, v in cfg.story_lengths.levels.items()
        ],
        "writer_tier": {"label": cfg.models.writer_tiers[0].label},
        "darkness_levels": [{"key": k, "label": v.label}
                            for k, v in cfg.moderation.darkness_levels.items()],
        "default_darkness_level": cfg.moderation.default_darkness_level,
        "chapter_estimate_default_usd": lim.chapter_estimate.default_usd,
    }


def test_public_config_is_exactly_the_numbers_from_config():
    with TestClient(build()) as client:
        resp = client.get("/config/public")
    assert resp.status_code == 200
    assert resp.json() == expected_public(CFG)
    assert [s["key"] for s in resp.json()["story_lengths"]] == list(CFG.story_lengths.levels)


def test_public_config_has_no_model_ids_prices_ceilings_or_internal_thresholds():
    with TestClient(build()) as client:
        text = client.get("/config/public").text
    models = {m for m in CFG.models.roles.model_dump().values() if m}
    models |= {t.model for t in CFG.models.writer_tiers}
    assert not [m for m in models if m in text]
    for internal in ("model", "eval_result", "reasoning", "ceilings", "darkness_cap", "price",
                     "llm_calls_per_minute", "narrator_notebook", "extract_schema_retry",
                     "max_score_jump", "intensity", "mild", "strong", "extreme"):
        assert internal not in text, internal


def test_public_config_reports_unset_numbers_as_null():
    """Số chưa đặt (null) không bị thay bằng số tự đặt; giao diện tự hiện "chưa có"."""
    from .test_narrator import with_limits

    cfg = with_limits(input__custom_action_max_chars=None, cost_usd__per_story=None)
    with TestClient(build(config=cfg)) as client:
        body = client.get("/config/public").json()
    assert body["input"]["custom_action_max_chars"] is None
    assert body["cost_usd"]["per_story"] is None


def test_public_config_writer_tier_is_the_tier_the_game_uses():
    """Mức viết của đường chơi là mức đầu (`pipeline.chapter.writer_tier(config, None)`)."""
    from writory.pipeline.chapter import writer_tier

    with TestClient(build()) as client:
        body = client.get("/config/public").json()
    assert body["writer_tier"] == {"label": writer_tier(CFG, None).label}


# --- chi phí người chơi -------------------------------------------------------------------------

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(("now", "start", "end"), [
    (datetime(2026, 10, 15, 12, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC),
     datetime(2026, 11, 1, tzinfo=UTC)),
    # 1/11 6:30 giờ Hà Nội vẫn là tháng 10 theo UTC (D-66).
    (datetime(2026, 11, 1, 6, 30, tzinfo=timezone(timedelta(hours=7))),
     datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 11, 1, tzinfo=UTC)),
    (datetime(2026, 12, 31, 23, 59, tzinfo=UTC), datetime(2026, 12, 1, tzinfo=UTC),
     datetime(2027, 1, 1, tzinfo=UTC)),
])
def test_utc_month_bounds(now, start, end):
    assert utc_month(now) == (start, end)


def test_utc_month_needs_a_timezone():
    with pytest.raises(ValueError):
        utc_month(datetime(2026, 10, 15, 12))


def test_player_costs_shape_and_values():
    ledger = MemoryCostLedger()
    ledger.record(CostEntry("writer", "m", 1, 1, 0.01), story_id="story-a", chapter=1)
    ledger.record(CostEntry("narrator", "m", 1, 1, 0.002), story_id="story-a", chapter=1)
    ledger.record(CostEntry("setup", "m", 1, 1, 0.003), setup_id="setup-x")
    ledger.record(CostEntry("writer", "m", 1, 1, None), story_id="story-b", chapter=1)
    with TestClient(build(ledger=ledger, clock=NOW.timestamp())) as client:
        resp = client.get("/player/costs")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"total_usd", "this_month_usd", "stories"}
    assert body["total_usd"] == pytest.approx(0.015)
    assert body["this_month_usd"] == pytest.approx(0.015)
    # Truyện tiêu gần nhất đứng trước; dòng thiếu `cost_usd` không cộng được (D-10).
    assert [(s["story_id"], s["spent_usd"]) for s in body["stories"]] == [
        ("story-b", 0.0), ("story-a", pytest.approx(0.012))]
    assert all(set(s) == {"story_id", "spent_usd"} for s in body["stories"])
    assert ledger.asked_now == [NOW]  # tháng tính theo đồng hồ của app, đổi sang UTC


def test_player_costs_never_show_the_key():
    """G7: có key đã lưu cũng không có gì của key trong phản hồi hay log."""
    app = build()
    store = MemoryKeyStore(app.state.key_cipher.encrypt(SecretStr(FAKE_KEY)))
    app.dependency_overrides[deps.get_key_store] = lambda: store
    with captured_logs() as logs, TestClient(app) as client:
        resp = client.get("/player/costs")
    assert resp.status_code == 200
    for text in (resp.text, logs.text):
        assert FAKE_KEY not in text and FAKE_KEY[9:-4] not in text
    assert FAKE_KEY[-4:] not in resp.text
    assert not {"has_key", "last4", "api_key", "ciphertext"} & set(resp.json())


# --- mount và CORS ------------------------------------------------------------------------------


def test_ui_routes_not_mounted_when_dev_flag_off():
    app = create_app(dev_settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    paths = set(app.openapi()["paths"])
    assert not {"/stories", "/config/public", "/player/costs"} & paths
    with TestClient(app) as client:
        for path in ("/stories", "/config/public", "/player/costs"):
            assert client.get(path).status_code == 404


def test_ui_routes_mounted_when_dev_flag_on():
    app = create_app(dev_settings(), health_checks={"neo4j": ok}, config=CFG)
    assert {"/stories", "/config/public", "/player/costs"} <= set(app.openapi()["paths"])


def test_no_cors_headers_even_for_the_vite_origin():
    """D-66: giao diện dev gọi API qua proxy của Vite (cùng origin), nên máy chủ không bật CORS:
    trang ở origin khác không đọc được phản hồi."""
    with TestClient(build()) as client:
        for origin in ("http://localhost:5173", "https://evil.example"):
            resp = client.get("/config/public", headers={"Origin": origin})
            assert "access-control-allow-origin" not in resp.headers
            pre = client.options("/player/key", headers={
                "Origin": origin, "Access-Control-Request-Method": "PUT"})
            assert "access-control-allow-origin" not in pre.headers
