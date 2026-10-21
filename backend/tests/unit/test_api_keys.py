"""Key OpenRouter của người chơi qua API (G7, D-44, D-45) và đường từ key đã lưu tới client model.

G7: key chỉ lưu bản mã hoá; phản hồi chỉ có 4 ký tự cuối; key không có trong log, lỗi hay phản hồi,
kể cả khi thân yêu cầu sai dạng (lỗi 422 không chép lại đầu vào). Key dạng lạ bị từ chối, để bộ lọc
log (`safety.redact`) luôn nhận ra key đã lưu. Không Docker: kho key và nhật ký chi phí trong bộ nhớ.
"""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import (
    FAKE_KEY,
    KeyedFactory,
    MemoryCostLedger,
    MemoryKeyStore,
    captured_logs,
    dev_settings,
    offline,
)
from tests.moderation_fixtures import ALLOW
from writory.api import create_app, deps
from writory.api.errors import HTTP_STATUS
from writory.db import StoryRecord
from writory.errors import ErrorCode, WritoryError
from writory.llm.fake import FakeLLM
from writory.pipeline.narrator import NarratorOutput
from writory.safety.crypto import KeyCipher
from writory.safety.moderate import ModerationOutput

from .test_narrator import CFG, PLAN, MemoryQuota, ref, reply, state, view


async def ok() -> bool:
    return True


def build(*, store: MemoryKeyStore | None = None, ledger: MemoryCostLedger | None = None,
          fake: FakeLLM | None = None, chapter: int = 3):
    app = create_app(dev_settings(), health_checks={"neo4j": ok}, config=CFG)
    store = store if store is not None else MemoryKeyStore()
    ledger = ledger if ledger is not None else MemoryCostLedger()
    factory = KeyedFactory(fake or FakeLLM.scripted([reply(False, None, [])]))
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    offline(app)
    app.dependency_overrides[deps.get_key_store] = lambda: store
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger
    app.dependency_overrides[deps.get_llm_factory] = lambda: factory
    app.dependency_overrides[deps.get_owned_story] = (
        lambda story_id: StoryRecord(story_id, "dev", "short", chapter))
    app.dependency_overrides[deps.get_player_view] = lambda: view(chapter)
    app.dependency_overrides[deps.get_truth_names] = lambda: state(chapter).named_nodes()
    app.dependency_overrides[deps.get_story_brief] = lambda: ""
    app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    quota = MemoryQuota()
    app.dependency_overrides[deps.get_narrator_quota] = lambda: quota
    return app, store, ledger, factory


def cipher_of(app) -> KeyCipher:
    return app.state.key_cipher


def assert_no_key(text: str, key: str = FAKE_KEY) -> None:
    assert key not in text
    assert key[:-4] not in text
    assert key[9:-4] not in text  # phần giữa, sau tiền tố "sk-or-v1-"


# --- lưu, xem, xoá -----------------------------------------------------------------------------


def test_put_key_stores_ciphertext_and_returns_only_last_four():
    app, store, _, _ = build()
    with captured_logs() as logs, TestClient(app) as client:
        resp = client.put("/player/key", json={"api_key": FAKE_KEY})
    assert resp.status_code == 200
    assert resp.json() == {"has_key": True, "last4": FAKE_KEY[-4:]}
    assert_no_key(resp.text)
    assert store.token is not None and FAKE_KEY.encode() not in store.token
    assert cipher_of(app).decrypt(store.token).get_secret_value() == FAKE_KEY
    assert_no_key(logs.text)


def test_key_is_trimmed_before_storing():
    app, store, _, _ = build()
    with TestClient(app) as client:
        resp = client.put("/player/key", json={"api_key": f"  {FAKE_KEY}\n"})
    assert resp.status_code == 200
    assert cipher_of(app).decrypt(store.token).get_secret_value() == FAKE_KEY


def test_get_key_shows_last_four_or_nothing():
    app, store, _, _ = build()
    with TestClient(app) as client:
        assert client.get("/player/key").json() == {"has_key": False, "last4": None}
        store.save(cipher_of(app).encrypt(SecretStr(FAKE_KEY)))
        resp = client.get("/player/key")
    assert resp.json() == {"has_key": True, "last4": FAKE_KEY[-4:]}
    assert_no_key(resp.text)


def test_replace_then_delete_key():
    other = "sk-or-v1-" + "feedface" * 8
    app, store, _, _ = build()
    with TestClient(app) as client:
        client.put("/player/key", json={"api_key": FAKE_KEY})
        assert client.put("/player/key", json={"api_key": other}).json()["last4"] == other[-4:]
        assert cipher_of(app).decrypt(store.token).get_secret_value() == other
        assert client.delete("/player/key").json() == {"has_key": False, "last4": None}
        assert store.token is None
        assert client.delete("/player/key").status_code == 200
        assert client.get("/player/key").json() == {"has_key": False, "last4": None}


def test_unreadable_stored_key_is_g12_error_without_detail():
    other = KeyCipher(SecretStr(Fernet.generate_key().decode()))
    app, _, _, _ = build(store=MemoryKeyStore(other.encrypt(SecretStr(FAKE_KEY))))
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/player/key")
    assert resp.status_code == 400 == HTTP_STATUS[ErrorCode.PLAYER_KEY_UNREADABLE]
    assert resp.json() == WritoryError(ErrorCode.PLAYER_KEY_UNREADABLE).player_payload()


# --- key sai dạng, thân yêu cầu sai dạng ---------------------------------------------------------


@pytest.mark.parametrize("bad", [
    "",
    "abc",
    "sk-or-",
    "sk-or-v1-abc",  # quá ngắn để bộ lọc log nhận ra
    "sk-or-v1-" + "ab cd ef gh" * 3,
    "sk-or-v1-" + "a" * 400,
    "sk-ant-api03-" + "b" * 40,  # key của nhà cung cấp khác
    "Bearer sk-or-v1-" + "c" * 40,
    "sk-or-v1-" + "d" * 40 + "é",
])
def test_malformed_key_is_refused_and_never_echoed(bad):
    app, store, _, _ = build()
    with captured_logs() as logs, TestClient(app, raise_server_exceptions=False) as client:
        resp = client.put("/player/key", json={"api_key": bad})
    assert resp.status_code == 422
    # G12: nói trường nào sai để người chơi sửa; G7: không chép lại chữ đã dán.
    assert resp.json() == WritoryError(ErrorCode.PLAYER_KEY_INVALID,
                                       fields=["api_key"]).player_payload()
    assert resp.json()["fields"] == ["api_key"]
    assert store.token is None
    if len(bad) >= 8:
        assert bad not in resp.text and bad not in logs.text


@pytest.mark.parametrize(("body", "fields"), [
    ({"api_key": FAKE_KEY, "note": "thêm trường lạ"}, {"note"}),
    ({"key": FAKE_KEY}, {"api_key", "key"}),
    ({"api_key": [FAKE_KEY]}, {"api_key"}),
    ({"api_key": {"value": FAKE_KEY}}, {"api_key"}),
    # Tên trường do người gửi đặt (ở đây chính là key) không được chép lại: thành "?".
    ({FAKE_KEY: "x"}, {"api_key", "?"}),
])
def test_bad_request_body_is_g12_error_that_never_echoes_input(body, fields):
    """Lỗi 422 mặc định của FastAPI chép lại đầu vào (`input`), tức chép lại key. Phản hồi chỉ có
    mã, câu tiếng Việt, và đường dẫn các trường sai."""
    app, store, _, _ = build()
    with captured_logs() as logs, TestClient(app, raise_server_exceptions=False) as client:
        resp = client.put("/player/key", json=body)
    assert resp.status_code == 422 == HTTP_STATUS[ErrorCode.REQUEST_INVALID]
    payload = resp.json()
    assert set(payload) == {"code", "message", "fields"}
    expected = WritoryError(ErrorCode.REQUEST_INVALID).player_payload()
    assert (payload["code"], payload["message"]) == (expected["code"], expected["message"])
    assert set(payload["fields"]) == fields
    assert_no_key(resp.text)
    assert_no_key(logs.text)
    assert store.token is None


def test_malformed_json_body_reports_the_body():
    app, _, _, _ = build()
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.put("/player/key", content=b'{"api_key": "' + FAKE_KEY.encode(),
                          headers={"content-type": "application/json"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "REQUEST_INVALID" and resp.json()["fields"] == ["body"]
    assert_no_key(resp.text)


def test_invalid_master_key_fails_at_startup_without_echoing_it():
    with pytest.raises(ValueError) as exc:
        create_app(dev_settings(master_key="not-a-fernet-key-123"), health_checks={}, config=CFG)
    assert "not-a-fernet-key-123" not in str(exc.value)


def test_key_routes_not_mounted_when_dev_flag_off():
    app = create_app(dev_settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    assert not any(p.startswith("/player") for p in app.openapi()["paths"])
    with TestClient(app) as client:
        assert client.get("/player/key").status_code == 404
        assert client.put("/player/key", json={"api_key": FAKE_KEY}).status_code == 404


# --- key đã lưu → client model (G7, G8) ----------------------------------------------------------


def test_narrator_uses_stored_player_key_and_records_cost():
    v = view(3)
    # Hai lời gọi, cùng key người chơi, cùng ghi nhật ký: kiểm duyệt đầu vào (G9, D-57), rồi người kể.
    fake = FakeLLM.scripted(
        [ALLOW, reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])], cost_usd=0.0012)
    app, store, ledger, factory = build(fake=fake)
    store.save(cipher_of(app).encrypt(SecretStr(FAKE_KEY)))
    with TestClient(app) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.json() == {"answer": "Lão Gù chết sau miếu Bà."}
    assert factory.keys == [FAKE_KEY]  # key giải mã chỉ đi tới client model
    [(moderated, *where), (answered, *_)] = ledger.rows
    assert (moderated.role, moderated.model, moderated.cost_usd) == (
        "moderate", CFG.models.roles.moderate, 0.0012)
    assert (answered.role, answered.model, answered.cost_usd) == (
        "narrator", CFG.models.roles.narrator, 0.0012)
    assert tuple(where) == ("s1", None, 3)  # story_id, setup_id, chapter
    assert fake.schemas == [ModerationOutput, NarratorOutput]


def test_narrator_without_stored_key_fails_closed():
    fake = FakeLLM.scripted([])
    app, _, ledger, factory = build(fake=fake)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 400
    assert resp.json() == WritoryError(ErrorCode.PLAYER_KEY_MISSING).player_payload()
    assert factory.keys == [] and fake.calls == [] and ledger.rows == []


def test_story_spent_from_ledger_counts_toward_story_cap():
    """Trần mỗi truyện tính cả chi phí đã ghi (G8): đã chạm trần thì không gọi model."""
    fake = FakeLLM.scripted([])
    cap = CFG.limits.cost_usd.per_story
    app, store, _, _ = build(fake=fake, ledger=MemoryCostLedger(story_spent=cap))
    store.save(cipher_of(app).encrypt(SecretStr(FAKE_KEY)))
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 402
    assert resp.json()["code"] == "COST_LIMIT_STORY"
    assert fake.calls == []


def test_model_error_echoing_the_key_leaks_nothing():
    """OpenRouter có thể chép key vào thông báo lỗi: phản hồi và log vẫn không có key."""
    fake = FakeLLM.scripted([WritoryError(ErrorCode.LLM_AUTH_FAILED,
                                          detail=f"401 invalid key {FAKE_KEY}")])
    app, store, ledger, _ = build(fake=fake)
    store.save(cipher_of(app).encrypt(SecretStr(FAKE_KEY)))
    with captured_logs() as logs, TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 400
    assert resp.json() == WritoryError(ErrorCode.LLM_AUTH_FAILED).player_payload()
    assert_no_key(resp.text)
    assert_no_key(logs.text)
    assert ledger.rows == []  # lời gọi lỗi không có usage để ghi
