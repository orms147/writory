"""Ngữ cảnh lớp truth cho model viết (design §6.2 bước 1), trên truyện mẫu."""

from dataclasses import dataclass

import pytest

from writory.graph.context import render_writer_context, writer_context

pytestmark = pytest.mark.graph


@dataclass(frozen=True)
class _Secret:
    fact_id: str
    reveal_from_chapter: int
    reveal_to_chapter: int


@dataclass(frozen=True)
class _Plan:
    secrets: tuple[_Secret, ...]


PLAN = _Plan((_Secret("f_lan_spy", 4, 5), _Secret("f_lan_killed_gu", 6, 8)))


def _all_ids(ctx) -> set[str]:
    return (
        {c.id for c in ctx.present}
        | {n.id for n in ctx.neighbors}
        | {f.id for f in ctx.known_facts}
        | {lie.id for lie in ctx.open_lies}
    )


def test_chapter_4_minh_and_lan(driver, sample_story_id):
    ctx = writer_context(driver, sample_story_id, 4, ["minh", "lan"], PLAN)
    assert (ctx.as_of_chapter, ctx.writing_chapter) == (4, 5)

    lan = next(c for c in ctx.present if c.id == "lan")
    assert [h.value for h in lan.holds] == ["Thanh Sương"]  # Lan đang giữ kiếm
    minh = next(c for c in ctx.present if c.id == "minh")
    assert [h.value for h in minh.holds] == ["lá thư niêm sáp đỏ"]

    spy = next(f for f in ctx.known_facts if f.id == "f_lan_spy")
    assert {k.id for k in spy.known_by} == {"lan", "gu"}

    lies = {lie.id for lie in ctx.open_lies}
    assert "l_home_night" in lies                  # lời dối của Minh chưa bị phát hiện
    assert "l_lan_cover" in lies                   # lời dối Lan nói với Minh
    assert "l_sword_father" not in lies            # đã bị Lan phát hiện ở chương 4

    rel = {(r.source, r.target): (r.kind, r.score) for r in ctx.relations}
    assert rel[("minh", "lan")] == ("yêu", 80)
    assert rel[("lan", "minh")] == ("con mồi", -20)

    status = {s.fact_id: s.status for s in ctx.secrets}
    assert status == {"f_lan_spy": "in_window", "f_lan_killed_gu": "not_yet"}

    gu = next(n for n in ctx.neighbors if n.id == "gu")
    assert gu.alive is False
    assert "t_gu_warning" in {t.id for t in ctx.open_threads if t.overdue}


def test_hints_do_not_repeat_hard_facts(driver, sample_story_id):
    # Phần gợi ý không lặp lại thứ đã nằm ở phần sự thật (Fact đã biết, lời dối đang treo,
    # đồ vật đang giữ, nơi đang ở), để không phình ngữ cảnh và không tiêu giới hạn nút.
    ctx = writer_context(driver, sample_story_id, 4, ["minh", "lan"], PLAN)
    hints = {n.id for n in ctx.neighbors}
    assert not hints & {f.id for f in ctx.known_facts}
    assert not hints & {lie.id for lie in ctx.open_lies}
    assert not hints & {"sword", "sealed_letter", "quan_tra"}
    assert {"khai", "hac_ky", "ly_that"} <= hints


def test_secret_status_after_reveal(driver, sample_story_id):
    ctx = writer_context(driver, sample_story_id, 5, ["minh"], PLAN)
    spy = next(s for s in ctx.secrets if s.fact_id == "f_lan_spy")
    assert (spy.status, spy.revealed_chapter) == ("revealed", 5)


def test_unrelated_characters_are_left_out(driver, sample_story_id):
    # Chương 1, chỉ cai Khải có mặt: Khải → Minh là 1 bước, mọi thứ của Minh là 2 bước.
    # Lý Thất, Hội Hắc Kỳ và bí mật của Lan cách Khải ≥ 3 bước.
    ctx = writer_context(driver, sample_story_id, 1, ["khai"], None)
    ids = _all_ids(ctx)
    assert {"khai", "minh"} <= ids
    assert not {"ly_that", "hac_ky", "f_lan_spy"} & ids
    assert ctx.known_facts == () and ctx.open_lies == () and ctx.secrets == ()


def test_pending_or_future_data_not_in_context(driver, sample_story_id):
    # Ở chương 3, Lan chưa giữ kiếm và chưa có mạch "Ai đã lấy Thanh Sương".
    ctx = writer_context(driver, sample_story_id, 3, ["minh", "lan"], PLAN)
    lan = next(c for c in ctx.present if c.id == "lan")
    assert lan.holds == ()
    assert "t_sword_missing" not in {t.id for t in ctx.open_threads}


def test_neighbor_limit(driver, sample_story_id):
    full = writer_context(driver, sample_story_id, 4, ["minh", "lan"], PLAN)
    capped = writer_context(driver, sample_story_id, 4, ["minh", "lan"], PLAN, max_neighbors=3)
    assert len(capped.neighbors) == 3 < len(full.neighbors)
    # Giữ những nút gần nhất trước.
    assert max(n.hops for n in capped.neighbors) <= min(
        n.hops for n in full.neighbors if n not in capped.neighbors
    )


def test_unknown_present_id_is_an_error(driver, sample_story_id):
    with pytest.raises(LookupError, match="ghost"):
        writer_context(driver, sample_story_id, 4, ["minh", "ghost"], None)


def test_render_size_is_reported(driver, sample_story_id, capsys):
    # Chỉ in ra để biết kích thước; không khẳng định con số (CLAUDE.md §6).
    ctx = writer_context(driver, sample_story_id, 4, ["minh", "lan"], PLAN)
    text = "\n\n".join(str(p) for p in render_writer_context(ctx))
    with capsys.disabled():
        print(
            f"\n[writer_context ch4 minh+lan] {len(text)} chars, "
            f"{len(text.encode('utf-8'))} UTF-8 bytes, {len(ctx.neighbors)} neighbors"
        )
    assert "Sự thật cần tôn trọng" in text


def test_player_text_from_neo4j_is_wrapped(driver, new_story_id):
    # Hồi quy (security review): cờ user_authored phải đi theo mọi chữ lấy từ Neo4j,
    # kể cả khi nhân vật người chơi viết là người biết, người nghe, hay người nói vắng mặt.
    from writory.graph import ChangePackage, apply_package
    from writory.safety.wrap import UserAuthored

    sid = new_story_id()
    ua = {"user_authored": True}
    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [
            {"id": "hero", "label": "Character",
             "props": {"name": "[P-hero]", "aliases": ["[P-alias]"], "is_protagonist": True, **ua}},
            {"id": "npc", "label": "Character", "props": {"name": "Người hầu"}},
            {"id": "place", "label": "Location", "props": {"name": "[P-place]", **ua}},
            {"id": "item", "label": "Item", "props": {"name": "[P-item]", **ua}},
            {"id": "f1", "label": "Fact", "props": {"text": "Một sự thật"}},
            {"id": "f9", "label": "Fact", "props": {"text": "[P-secret]", **ua}},
            {"id": "l1", "label": "Lie", "props": {"chapter": 0, "content": "[P-lie]", **ua}},
            # Lời dối hệ thống viết, người chơi là người nghe.
            {"id": "l2", "label": "Lie", "props": {"chapter": 0, "content": "Lời dối của người hầu"}},
            {"id": "t1", "label": "Thread", "props": {
                "description": "[P-thread]", "planted_chapter": 0, "due_from_chapter": 1,
                "due_to_chapter": 2, **ua}},
        ],
        "edges": [
            {"type": "LOCATED_AT", "from": "npc", "to": "place", "valid_from_chapter": 0},
            {"type": "HOLDS", "from": "npc", "to": "item", "valid_from_chapter": 0},
            {"type": "KNOWS", "from": "npc", "to": "f1", "valid_from_chapter": 0},
            {"type": "KNOWS", "from": "hero", "to": "f1", "valid_from_chapter": 0},
            {"type": "TOLD", "from": "hero", "to": "l1", "valid_from_chapter": 0},
            {"type": "TOLD_TO", "from": "l1", "to": "npc", "valid_from_chapter": 0},
            {"type": "TOLD", "from": "npc", "to": "l2", "valid_from_chapter": 0},
            {"type": "TOLD_TO", "from": "l2", "to": "hero", "valid_from_chapter": 0},
        ],
    }))

    @dataclass(frozen=True)
    class _P:
        secrets: tuple

    # Chỉ người hầu có mặt: người chơi là người biết, người nói vắng mặt và người nghe.
    ctx = writer_context(driver, sid, 0, ["npc"], _P((_Secret("f9", 3, 4),)))
    assert {lie.id for lie in ctx.open_lies} == {"l1", "l2"}
    parts = render_writer_context(ctx)
    # Từng vị trí riêng: người nghe của l2 là người chơi.
    l2 = next(lie for lie in ctx.open_lies if lie.id == "l2")
    assert [t.user_authored for t in l2.told_to] == [True]
    assert next(lie for lie in ctx.open_lies if lie.id == "l1").speaker.user_authored
    assert next(f for f in ctx.known_facts if f.id == "f1").known_by[0].name.user_authored
    raw = [p for p in parts if isinstance(p, str)]
    for marker in ["[P-hero]", "[P-alias]", "[P-place]", "[P-item]", "[P-secret]",
                   "[P-lie]", "[P-thread]"]:
        assert not any(marker in p for p in raw), f"{marker} đi ra trần"
        assert any(isinstance(p, UserAuthored) and marker in p.text for p in parts), marker


def test_items_show_current_holder_or_place_even_when_the_holder_is_absent(driver, sample_story_id):
    """D-90: trạng thái đồ vật không phụ thuộc ai có mặt. Chỉ Khải có mặt mà kiếm vẫn ghi do Lan giữ."""
    ctx = writer_context(driver, sample_story_id, 4, ["khai"], None)
    by_id = {i.id: i for i in ctx.items}
    sword = by_id["sword"]
    assert sword.name.value == "Thanh Sương" and sword.holder.value == "Phạm Thị Lan"
    assert sword.place is None and sword.since_chapter == 4
    assert sword.holder_id == "lan" and sword.place_id is None  # D-91: để ghi tên người đọc biết
    for item in ctx.items:  # mỗi đồ vật đúng một chỗ
        assert (item.holder is None) != (item.place is None), item
    assert not {i.id for i in ctx.items} & {n.id for n in ctx.neighbors}
    text = "\n\n".join(str(p) for p in render_writer_context(ctx))
    assert "Thanh Sương — do Phạm Thị Lan giữ (từ chương 4)" in text


def test_items_follow_the_chapter(driver, sample_story_id):
    before = writer_context(driver, sample_story_id, 3, ["minh"], None)
    assert "sword" not in {i.id for i in before.items if i.holder and i.holder.value == "Phạm Thị Lan"}


def test_an_item_with_neither_holder_nor_place_is_not_listed(driver, new_story_id):
    from writory.graph import ChangePackage, apply_package

    sid = new_story_id()
    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [{"id": "hero", "label": "Character",
                   "props": {"name": "Minh", "is_protagonist": True}},
                  {"id": "lost", "label": "Item", "props": {"name": "Chìa khoá mất"}},
                  {"id": "bag", "label": "Item", "props": {"name": "Túi vải"}}],
        "edges": [{"type": "HOLDS", "from": "hero", "to": "bag", "valid_from_chapter": 0}],
    }))
    ctx = writer_context(driver, sid, 0, ["hero"], None)
    assert [i.id for i in ctx.items] == ["bag"]


def _apply_people(driver, sid):
    from writory.graph import ChangePackage, apply_package

    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [
            {"id": "hero", "label": "Character",
             "props": {"name": "Minh", "is_protagonist": True, "user_authored": True,
                       "personality": "Điềm tĩnh, hay ghi nhớ.", "backstory": "BÍ MẬT-HERO"}},
            {"id": "npc", "label": "Character",
             "props": {"name": "Lan", "personality": "Kín đáo, nói ít, hay hỏi ngược lại.",
                       "backstory": "BÍ MẬT-NPC giết Lão Gù"}},
            {"id": "far", "label": "Character",
             "props": {"name": "Khải", "personality": "Nóng nảy, thẳng ruột ngựa."}},
            {"id": "club", "label": "Faction", "props": {"name": "Hội", "personality": "X"}}],
        "edges": [{"type": "RELATES_TO", "from": "hero", "to": "npc", "valid_from_chapter": 0,
                   "props": {"kind": "bạn", "score": 50}},
                  {"type": "MEMBER_OF", "from": "far", "to": "club", "valid_from_chapter": 0},
                  {"type": "RELATES_TO", "from": "npc", "to": "far", "valid_from_chapter": 0,
                   "props": {"kind": "bạn", "score": 50}}],
    }))


def test_personality_is_off_by_default(driver, new_story_id):
    sid = new_story_id()
    _apply_people(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "npc"], None)
    assert all(c.personality is None for c in ctx.present)
    assert all(n.personality is None for n in ctx.neighbors)


def test_personality_of_present_and_neighbor_characters_is_read_clipped_and_never_the_backstory(
        driver, new_story_id):
    sid = new_story_id()
    _apply_people(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "npc"], None, personality_max_chars=200)
    by_id = {c.id: c for c in ctx.present}
    assert by_id["npc"].personality == "Kín đáo, nói ít, hay hỏi ngược lại."
    assert by_id["hero"].personality == "Điềm tĩnh, hay ghi nhớ." and by_id["hero"].user_authored
    far = next(n for n in ctx.neighbors if n.id == "far")
    assert far.personality == "Nóng nảy, thẳng ruột ngựa."
    club = next(n for n in ctx.neighbors if n.id == "club")
    assert club.personality is None  # không phải nhân vật
    text = " ".join(str(p) for p in render_writer_context(ctx))
    assert "BÍ MẬT" not in text  # backstory không bao giờ vào ngữ cảnh viết
    short = writer_context(driver, sid, 0, ["npc"], None, personality_max_chars=12)
    assert len(short.present[0].personality) <= 12 and short.present[0].personality.endswith("…")


def _shared_neighbor_story(driver, sid):
    from writory.graph import ChangePackage, apply_package

    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [
            {"id": "hero", "label": "Character", "props": {"name": "Minh", "is_protagonist": True}},
            {"id": "ally", "label": "Character", "props": {"name": "Lan"}},
            {"id": "third", "label": "Character", "props": {"name": "Khải"}},
            {"id": "club", "label": "Faction", "props": {"name": "Hội"}},
            {"id": "guild", "label": "Faction", "props": {"name": "Bang"}}],
        "edges": [
            {"type": "MEMBER_OF", "from": "hero", "to": "club", "valid_from_chapter": 0},
            {"type": "MEMBER_OF", "from": "ally", "to": "club", "valid_from_chapter": 0},
            {"type": "MEMBER_OF", "from": "hero", "to": "guild", "valid_from_chapter": 0},
            {"type": "MEMBER_OF", "from": "ally", "to": "guild", "valid_from_chapter": 0},
            {"type": "MEMBER_OF", "from": "third", "to": "club", "valid_from_chapter": 0}]}))


def test_a_neighbor_reached_from_two_present_characters_is_listed_once(driver, new_story_id, caplog):
    """Hồi quy session 1 (D-117): truy vấn hàng xóm trả node trùng khi ≥ 2 nhân vật có mặt cùng tới
    một node và `$shown` rỗng (kế hoạch Neo4j bỏ bước gom theo node)."""
    sid = new_story_id()
    _shared_neighbor_story(driver, sid)
    with caplog.at_level("WARNING"):
        ctx = writer_context(driver, sid, 0, ["hero", "ally"], None)
    ids = [n.id for n in ctx.neighbors]
    assert sorted(ids) == ["club", "guild", "third"] and len(ids) == len(set(ids))
    assert "node trùng" not in caplog.text  # chính truy vấn đã đúng, chặn ở Python không phải gánh
    hops = {n.id: n.hops for n in ctx.neighbors}
    assert hops == {"club": 1, "guild": 1, "third": 2}  # hops nhỏ nhất của mỗi node


def test_the_neighbor_limit_counts_distinct_nodes(driver, new_story_id):
    sid = new_story_id()
    _shared_neighbor_story(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "ally"], None, max_neighbors=3)
    assert [n.id for n in ctx.neighbors] == ["club", "guild", "third"]  # gần trước, rồi theo id
    ctx = writer_context(driver, sid, 0, ["hero", "ally"], None, max_neighbors=2)
    assert [n.id for n in ctx.neighbors] == ["club", "guild"]


# --- ngoại hình nhân vật (D-118): thuộc tính tuỳ chọn của lớp truth ---------------------------------


def _apply_looks(driver, sid):
    from writory.graph import ChangePackage, apply_package

    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [
            {"id": "hero", "label": "Character",
             "props": {"name": "Minh", "is_protagonist": True, "user_authored": True,
                       "appearance": "Cao gầy, tóc đen buộc gọn."}},
            {"id": "npc", "label": "Character",
             "props": {"name": "Lan", "appearance": "Nhỏ nhắn, cài trâm bạc hình cánh én."}},
            {"id": "far", "label": "Character", "props": {"name": "Khải"}},
            {"id": "club", "label": "Faction",
             "props": {"name": "Hội", "appearance": "KHÔNG-ĐƯỢC-ĐỌC"}},
            {"id": "inn", "label": "Location",
             "props": {"name": "Quán trà", "visual": "Đèn dầu vàng đục, gỗ ẩm mục."}}],
        "edges": [{"type": "RELATES_TO", "from": "hero", "to": "npc", "valid_from_chapter": 0,
                   "props": {"kind": "bạn", "score": 50}},
                  {"type": "MEMBER_OF", "from": "far", "to": "club", "valid_from_chapter": 0},
                  {"type": "RELATES_TO", "from": "npc", "to": "far", "valid_from_chapter": 0,
                   "props": {"kind": "bạn", "score": 50}}],
    }))


def test_appearance_is_off_by_default_even_when_the_graph_has_it(driver, new_story_id):
    sid = new_story_id()
    _apply_looks(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "npc"], None)
    assert all(c.appearance is None for c in ctx.present)
    assert all(n.appearance is None for n in ctx.neighbors)
    assert "ngoại hình" not in " ".join(str(p) for p in render_writer_context(ctx))


def test_appearance_of_present_and_neighbor_characters_is_read_clipped_and_nothing_else(
        driver, new_story_id):
    sid = new_story_id()
    _apply_looks(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "npc"], None, appearance_max_chars=200)
    by_id = {c.id: c for c in ctx.present}
    assert by_id["npc"].appearance == "Nhỏ nhắn, cài trâm bạc hình cánh én."
    assert by_id["hero"].appearance == "Cao gầy, tóc đen buộc gọn." and by_id["hero"].user_authored
    far = next(n for n in ctx.neighbors if n.id == "far")
    assert far.appearance is None  # nút không có thuộc tính: không lỗi, không chữ
    club = next(n for n in ctx.neighbors if n.id == "club")
    assert club.appearance is None  # không phải nhân vật
    text = " ".join(str(p) for p in render_writer_context(ctx))
    assert "KHÔNG-ĐƯỢC-ĐỌC" not in text and "Đèn dầu" not in text  # `visual` chưa vào đề viết
    short = writer_context(driver, sid, 0, ["npc"], None, appearance_max_chars=12)
    assert len(short.present[0].appearance) <= 12 and short.present[0].appearance.endswith("…")


def test_looks_never_reach_the_player_view_after_being_revealed(driver, new_story_id):
    """G1: nút được hé lộ cho người chơi vẫn chỉ hiện tên và câu trích, không hiện ngoại hình."""
    from writory.graph import ChangePackage, apply_package
    from writory.graph.player_view import player_view

    sid = new_story_id()
    _apply_looks(driver, sid)
    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c1",
        "nodes": [{"id": "ch1", "label": "Chapter", "props": {"number": 1}}],
        "edges": [
            {"type": "REVEALED_TO_PLAYER", "from": "npc", "to": "ch1", "valid_from_chapter": 1,
             "quote": "Lan cài trâm bạc bước vào.", "known_as": "Lan"},
            {"type": "REVEALED_TO_PLAYER", "from": "inn", "to": "ch1", "valid_from_chapter": 1,
             "quote": "Họ vào Quán trà đầu bến.", "known_as": "Quán trà"}],
    }))
    blob = repr(player_view(driver, sid, 1))
    assert "Lan" in blob  # nút đã hé lộ
    for secret in ("Nhỏ nhắn", "Cao gầy", "Đèn dầu"):
        assert secret not in blob


# --- cạnh sai đầu mút đã nằm trong đồ thị (D-128, ca psab-b1) -----------------------------------


def _apply_misplaced_edges(driver, sid):
    """Đồ thị của psab-b1 sau chương 11: HOLDS tới một Fact do bộ trích tạo ở chương 10."""
    from writory.graph import ChangePackage, apply_package

    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [
            {"id": "hero", "label": "Character", "props": {"name": "Thảo", "is_protagonist": True,
                                                            "user_authored": True}},
            {"id": "yen", "label": "Character", "props": {"name": "Phụng Yên"}},
            {"id": "paper", "label": "Item", "props": {"name": "Tờ giấy"}},
            {"id": "pier", "label": "Location", "props": {"name": "Bến cảng"}},
            {"id": "fact_c10s1_1", "label": "Fact", "props": {"text": "Phụng Yên giấu tờ giấy"}}],
        "edges": [
            {"type": "HOLDS", "from": "yen", "to": "fact_c10s1_1", "valid_from_chapter": 0},
            {"type": "LOCATED_AT", "from": "yen", "to": "hero", "valid_from_chapter": 0},
            {"type": "HOLDS", "from": "yen", "to": "paper", "valid_from_chapter": 0},
            {"type": "LOCATED_AT", "from": "paper", "to": "fact_c10s1_1", "valid_from_chapter": 0},
            {"type": "LOCATED_AT", "from": "hero", "to": "pier", "valid_from_chapter": 0}],
    }))


def test_misplaced_edges_in_the_graph_are_ignored_by_the_writer_context(driver, new_story_id):
    sid = new_story_id()
    _apply_misplaced_edges(driver, sid)
    ctx = writer_context(driver, sid, 0, ["hero", "yen"], None)
    by_id = {c.id: c for c in ctx.present}
    assert [t.value for t in by_id["yen"].holds] == ["Tờ giấy"]  # chỉ cạnh HOLDS tới một Item
    assert by_id["yen"].location is None  # LOCATED_AT tới nhân vật không phải nơi chốn
    assert by_id["hero"].location is not None and by_id["hero"].location.value == "Bến cảng"
    text = " ".join(str(p) for p in render_writer_context(ctx))  # không sập vì None
    assert "Tờ giấy" in text and "giấu tờ giấy" not in text.split("Nhân vật có mặt")[1].split("##")[0]
    assert all(i.holder is None or i.holder.value for i in ctx.items)


def test_edge_endpoint_violations_counts_only_the_bad_combinations(driver, new_story_id):
    from writory.graph import edge_endpoint_violations

    sid = new_story_id()
    _apply_misplaced_edges(driver, sid)
    assert sorted((v.type, v.source_label, v.target_label, v.count)
                  for v in edge_endpoint_violations(driver, sid)) == [
        ("HOLDS", "Character", "Fact", 1), ("LOCATED_AT", "Character", "Character", 1),
        ("LOCATED_AT", "Item", "Fact", 1)]


def test_the_sample_story_has_no_edge_with_a_wrong_endpoint(driver, sample_story_id):
    from writory.graph import edge_endpoint_violations

    assert edge_endpoint_violations(driver, sample_story_id) == []
