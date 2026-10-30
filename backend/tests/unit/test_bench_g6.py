"""Bộ câu và bộ chấm của vai `overreach` (G6, D-138). Model giả: kiểm cấu trúc và đường chấm, không đo
model. Đo với model thật: `writory.safety.bench_g6` (docs/eval.md, mục Red-team)."""

import json
from pathlib import Path

import yaml

from writory.config import REPO_ROOT, load_config
from writory.llm.fake import FakeLLM
from writory.safety.bench_g6 import case_inputs, score
from writory.safety.classify import BEYOND_RULES, Feasibility
from writory.safety.overreach import OverreachVerdict, needs_rewrite
from writory.safety.wrap import CLOSE_TAG

DOC = yaml.safe_load((REPO_ROOT / "evals" / "redteam" / "g6_overreach.yaml").read_text(
    encoding="utf-8"))
CASES = DOC["cases"]
CFG = load_config()


def reply(verdict: str) -> str:
    return json.dumps({"verdict": verdict, "reason": "thử"})


def rewrite(case: dict, verdict: str | None = None) -> bool:
    return needs_rewrite(Feasibility(case["feasibility"]),
                         OverreachVerdict(verdict or case["expected"]))


def test_set_is_complete_and_every_reference_resolves():
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert {c["expected"] for c in CASES} == {v.value for v in OverreachVerdict}
    assert {Feasibility(c["feasibility"]) for c in CASES} == set(BEYOND_RULES)
    assert {c.get("set", "original") for c in CASES} == {"original", "hard"}
    for case in CASES:
        inputs = case_inputs(case, DOC)  # tham chiếu lạ thì KeyError
        assert inputs["action"].strip() and inputs["scene_text"].strip(), case["id"]
        assert ("scene" in case) != ("scene_ref" in case), case["id"]
    for name in ("original", "hard"):
        subset = [c for c in CASES if c.get("set", "original") == name]
        assert sum(rewrite(c) for c in subset) >= 5, name
        assert sum(not rewrite(c) for c in subset) >= 5, name
    assert all(c["expected"] == "granted" for c in CASES
               if {"attack", "mentioned-cost", "token-cost", "unrelated-cost"} & set(c["tags"]))
    assert all(c["expected"] == "failed" for c in CASES
               if {"dream", "ordinary-means", "boast"} & set(c["tags"]))


def test_hard_subset_has_every_hard_shape_of_the_review():
    """D-138: thành công kèm giá thật, giá thoáng qua, giá không do hành động hay người khác gánh,
    đạt mục đích bằng cách thường, chỉ khoe khoang, chữ nhắm vào người chấm trong văn cảnh, kết luận
    đổi nếu bỏ qua cảnh trước, và vượt luật thế giới có giá (sản phẩm viết lại như granted)."""
    hard = [c for c in CASES if c.get("set") == "hard"]
    tags = {t for c in hard for t in c["tags"]}
    assert {"real-cost", "token-cost", "unrelated-cost", "ordinary-means", "boast", "attack",
            "flip"} <= tags
    world_cost = [c for c in hard if c["feasibility"] == "beyond_world_rules"
                  and c["expected"] == "cost"]
    assert world_cost and all(rewrite(c) for c in world_cost)
    character_cost = [c for c in hard if c["feasibility"] == "beyond_character"
                      and c["expected"] == "cost"]
    assert character_cost and not any(rewrite(c) for c in character_cost)
    flips = [c for c in hard if "flip" in c["tags"]]
    assert flips and all(c.get("earlier_refs") for c in flips)
    attack = [c for c in hard if "attack" in c["tags"]]
    assert attack and all("người chấm" in case_inputs(c, DOC)["scene_text"] for c in attack)


async def test_an_oracle_scores_perfectly_on_every_set():
    llm = FakeLLM.scripted([reply(c["expected"]) for c in CASES])
    result = await score(DOC, llm=llm, config=CFG)
    assert result.correct == result.total == len(CASES)
    assert (result.rewrite_missed, result.false_rewrite, result.errors) == ([], [], 0)
    hard = len([c for c in CASES if c.get("set") == "hard"])
    assert result.by_set["hard"]["total"] == result.by_set["hard"]["correct"] == hard
    assert result.by_set["original"]["total"] == len(CASES) - hard


async def test_misses_and_false_rewrites_follow_the_product_decision_by_kind():
    """Bỏ sót và báo nhầm tính theo quyết định của sản phẩm (D-138): `cost` thay `granted` ở vượt
    luật thế giới không đổi gì (cả hai viết lại); ở vượt sức nhân vật thì là bỏ sót."""
    def pick(kind, expected):
        return next(c for c in CASES if c["feasibility"] == kind and c["expected"] == expected)

    world_granted = pick("beyond_world_rules", "granted")
    char_granted = pick("beyond_character", "granted")
    world_failed = pick("beyond_world_rules", "failed")
    char_cost = pick("beyond_character", "cost")
    flip = {world_granted["id"]: "cost",   # vẫn viết lại: không đổi quyết định
            char_granted["id"]: "cost",    # cho qua cái phải viết lại: bỏ sót
            world_failed["id"]: "cost",    # bắt viết lại cái được qua: báo nhầm
            char_cost["id"]: "failed"}     # vẫn qua: không đổi quyết định
    llm = FakeLLM.scripted([reply(flip.get(c["id"], c["expected"])) for c in CASES])
    result = await score(DOC, llm=llm, config=CFG)
    assert result.correct == len(CASES) - 4
    assert result.rewrite_missed == [char_granted["id"]]
    assert result.false_rewrite == [world_failed["id"]]
    assert {w["id"] for w in result.wrong} == set(flip)


async def test_failed_calls_count_as_wrong_not_as_misses():
    llm = FakeLLM.scripted(["không phải json"] * 50)
    result = await score({**DOC, "cases": CASES[:1]}, llm=llm, config=CFG)
    assert result.errors == 1 and result.correct == 0
    assert result.rewrite_missed == [] and result.false_rewrite == []


async def test_each_call_carries_its_earlier_scenes_and_wraps_the_action():
    llm = FakeLLM.scripted([reply(c["expected"]) for c in CASES])
    await score(DOC, llm=llm, config=CFG)
    for case, call in zip(CASES, llm.calls, strict=True):
        user = call[-1].content
        inputs = case_inputs(case, DOC)
        assert user.count('<player_data source="scene_text">') == 1 + len(inputs["earlier"])
        start = user.index('<player_data source="player_action">')
        assert inputs["action"] in user[start:user.index(CLOSE_TAG, start)], case["id"]


def test_dry_run_makes_no_paid_call(capsys, monkeypatch):
    from writory.safety import bench_g6

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert bench_g6.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"cả bộ: đúng {len(CASES)}/{len(CASES)}" in out and f"{len(CASES)} lời gọi" in out


def test_round_two_hard_cases_cover_seen_only_others_pay_and_real_exposure():
    """D-141: người chấm tính nhầm cái giá là thứ người khác trả, hay chỉ là bị nhìn thấy. Ca mới
    (không sửa nhãn ca cũ): thấy nhưng không hậu quả, người khác gánh, và bị lộ có hậu quả thật."""
    round2 = [c for c in CASES if "round2" in c["tags"]]
    assert len(round2) >= 8 and all(c["set"] == "hard" for c in round2)
    by_tag: dict[str, list[dict]] = {}
    for c in round2:
        for tag in c["tags"]:
            by_tag.setdefault(tag, []).append(c)
    assert {"seen-only", "unrelated-cost", "exposure-cost", "real-cost"} <= set(by_tag)
    assert all(c["expected"] == "granted" for c in by_tag["seen-only"] + by_tag["unrelated-cost"])
    assert all(c["expected"] == "cost" for c in by_tag["exposure-cost"] + by_tag["real-cost"])
    # Ca sai ở vòng một cần phải viết lại (vượt sức nhân vật: granted thì viết lại, cost thì qua).
    assert all(c["feasibility"] == "beyond_character" for c in by_tag["seen-only"])
    assert all(rewrite(c) for c in by_tag["seen-only"] + by_tag["unrelated-cost"])
    assert not any(rewrite(c) for c in by_tag["exposure-cost"] + by_tag["real-cost"])
    # Hai thế giới (phố bến sông không phép, thế giới tu tiên).
    assert {c["action"] for c in round2} >= {"doi-linh"} and len({c["action"] for c in round2}) >= 2
    old_ids = {c["id"] for c in CASES if not {"round2", "round3"} & set(c["tags"])}
    assert len(old_ids) == 24 and not {c["id"] for c in round2} & old_ids


# --- vòng ba (D-146): hậu quả của việc thử, và cái giá chỉ được nhắc --------------------------------

ROUND3 = [c for c in CASES if "round3" in c["tags"]]


def _fold(text: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(ch for ch in plain if not unicodedata.combining(ch))


def _shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    import re

    words = re.sub(r"[^\w\s]", " ", _fold(text)).split()
    return {tuple(words[i:i + n]) for i in range(max(len(words) - n + 1, 0))}


def test_round_three_cases_cover_the_attempt_that_hurts_and_the_cost_that_is_only_mentioned():
    assert len(ROUND3) >= 9 and all(c["set"] == "hard" for c in ROUND3)
    by_tag: dict[str, list[dict]] = {}
    for c in ROUND3:
        for tag in c["tags"]:
            by_tag.setdefault(tag, []).append(c)
    assert {"failed-after-try", "mention-only", "control"} <= set(by_tag)
    tried = by_tag["failed-after-try"]
    assert len(tried) >= 4 and all(c["expected"] == "failed" for c in tried)
    # Chỉ vượt luật thế giới mới đổi quyết định giữa `failed` và `cost` (cost bị viết lại).
    assert all(c["feasibility"] == "beyond_world_rules" for c in tried)
    assert any(c.get("earlier_refs") for c in tried)  # một ca có cú ngã nằm ở cảnh trước
    mentioned = by_tag["mention-only"]
    assert len(mentioned) >= 3 and all(c["expected"] == "granted" for c in mentioned)
    assert all(c["feasibility"] == "beyond_character" for c in mentioned)
    assert all(rewrite(c) for c in mentioned)
    # Hai ca đối chứng chống sửa quá tay: giá thật vẫn là `cost`, điều bất khả xảy ra một phần vẫn là `cost`.
    controls = by_tag["control"]
    assert {c["feasibility"] for c in controls} == {"beyond_character", "beyond_world_rules"}
    assert all(c["expected"] == "cost" for c in controls)
    assert {c["action"] for c in ROUND3} >= {"doi-linh", "chem-nguyen-anh"}


OVERREACH3_PROMPT = (Path(__file__).parents[3] / "evals" / "results" / "2026-10-31-g6-check-3"
                     / "overreach3_system_prompt.txt")  # đề đã thử, không dùng (D-146)


def test_round_three_cases_are_new_and_the_prompt_does_not_echo_any_case():
    """Ca vòng ba viết bằng chữ khác các ca phát triển (hai ca ổn định sai ở lần đo đầu) và các ca cũ;
    đề `overreach-3` (đã thử, lưu ở file cạnh notes) nêu quy tắc chung, không chép cụm của ca nào (cụm bốn từ)."""
    def case_text(c: dict) -> str:
        inputs = case_inputs(c, DOC)
        return " ".join([inputs["action"], *inputs["earlier"], inputs["scene_text"]])

    prompt = _shingles(OVERREACH3_PROMPT.read_text(encoding="utf-8"))
    others = [c for c in CASES if "round3" not in c["tags"]]
    dev_ids = {"truoc-nga-nay-im", "hc2-thang-lai-bi-lo-chi-duoc-nhac"}
    for case in CASES:
        if case["id"] in dev_ids or "round3" in case["tags"]:  # ca cũ khác cố ý bắt chước giọng đề (tấn công)
            assert not prompt & _shingles(case_text(case)), case["id"]
    def page_text(c: dict) -> str:
        """Văn của ca trừ câu hành động và đoạn mở đầu của cảnh (dựng tình huống, dùng chung giữa các ca:
        cùng một cuộc vây lính, khác kết quả); phần so là diễn biến và kết quả."""
        inputs = case_inputs(c, DOC)
        outcome = inputs["scene_text"].split("\n\n", 1)[-1]
        return " ".join([*inputs["earlier"], outcome])

    old = set().union(*(_shingles(page_text(c)) for c in others))
    for case in ROUND3:
        assert len(_shingles(page_text(case)) & old) <= 2, case["id"]
    dev = {c["id"] for c in CASES if c["id"] in {"truoc-nga-nay-im", "hc2-thang-lai-bi-lo-chi-duoc-nhac"}}
    assert dev == {"truoc-nga-nay-im", "hc2-thang-lai-bi-lo-chi-duoc-nhac"}  # ca phát triển còn nguyên
