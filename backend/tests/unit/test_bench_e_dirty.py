"""Bài E, đề câu "bẩn" (questions-dirty-1.yaml): cùng câu hỏi viết không dấu, sai chính tả hay
teencode, nói trống không. Mỗi biến thể chấm bằng đúng căn cứ của câu gốc, để chênh lệch chỉ do
cách gõ. Không mạng, không model thật."""

import unicodedata
from pathlib import Path

import pytest

pytest.importorskip("anthropic")

from writory.config import load_config
from writory.pipeline import bench_e as be
from writory.pipeline.narrator import NOT_KNOWN

FILE = "questions-dirty-1.yaml"
V2 = {q.id: q for q in be.load_data(questions_file="questions-v2.yaml").questions.questions}
DIRTY = be.load_data(questions_file=FILE)
QUESTIONS = {q.id: q for q in DIRTY.questions.questions}
VARIANTS = ("khongdau", "saichinhta", "trongkhong")


def _split(qid: str) -> tuple[str, str]:
    base, _, variant = qid.partition("--")
    return base, variant


def _groups() -> dict[str, dict[str, be.Question]]:
    groups: dict[str, dict[str, be.Question]] = {}
    for qid, q in QUESTIONS.items():
        base, variant = _split(qid)
        groups.setdefault(base, {})[variant] = q
    return groups


def test_moi_cau_co_hau_to_bien_the():
    allowed = {"goc", "haiy", *VARIANTS}
    assert {_split(qid)[1] for qid in QUESTIONS} <= allowed


def test_cau_goc_giong_het_de_v2():
    goc = {b: g["goc"] for b, g in _groups().items() if "goc" in g}
    assert goc, "đề phải có câu gốc để so trong cùng lượt chạy"
    for base, q in goc.items():
        ref = V2[base]
        assert (q.text, q.chapter, q.type, q.grounds, q.expect_terms) == (
            ref.text, ref.chapter, ref.type, ref.grounds, ref.expect_terms), base


def test_bien_the_loai_a_dung_can_cu_cua_cau_goc_va_du_ba_kieu():
    for base, group in _groups().items():
        if "goc" not in group:
            continue
        goc = group["goc"]
        assert set(group) - {"haiy"} == {"goc", *VARIANTS}, base  # câu hai ý chấm riêng
        for variant in VARIANTS:
            q = group[variant]
            assert (q.chapter, q.type, q.grounds, q.expect_terms) == (
                goc.chapter, goc.type, goc.grounds, goc.expect_terms), q.id
            assert q.text != goc.text, q.id


def test_bien_the_khong_dau_chi_co_ky_tu_ascii():
    for qid, q in QUESTIONS.items():
        if _split(qid)[1] == "khongdau":
            assert q.text.isascii(), qid


def test_bien_the_co_dau_khac_cau_goc_ca_khi_bo_dau():
    """Sai chính tả và trống không phải khác câu gốc ở chữ, không chỉ ở dấu hay hoa thường."""
    def flat(s: str) -> str:
        s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
        return "".join(c for c in s if not unicodedata.combining(c)).lower().strip(" ?.")
    for group in _groups().values():
        if "goc" not in group:
            continue
        for variant in ("saichinhta", "trongkhong"):
            assert flat(group[variant].text) != flat(group["goc"].text), group[variant].id


def test_cau_bi_mat_viet_ban_van_mong_doi_not_known():
    """Câu hỏi bí mật chưa mở, viết bẩn: loại b, không có căn cứ (mong đợi NOT_KNOWN)."""
    secrets = [q for q in QUESTIONS.values() if q.type == "b"]
    assert secrets
    for q in secrets:
        base, variant = _split(q.id)
        assert V2[base].type == "b" and variant in VARIANTS, q.id


def test_cau_hai_y_can_du_cum_cua_ca_hai_y():
    two = [q for q in QUESTIONS.values() if _split(q.id)[1] == "haiy"]
    assert two
    for q in two:
        assert q.type == "a" and len(q.expect_terms) >= 2, q.id


async def test_chay_khung_voi_oracle_khong_lo_va_cau_bi_mat_bi_tu_choi(tmp_path: Path):
    config = load_config()
    opts = be.RunOptions(out=tmp_path / "out", dry_run=True, samples=1, concurrency=4)
    code = await be.run_bench(DIRTY, opts, config=config, log=lambda _line: None)
    assert code == be.EXIT_OK
    rows = be.Store(opts.out).rows(be.RESULTS)
    assert len(rows) == len(QUESTIONS)
    for row in rows:
        if QUESTIONS[row["id"]].type == "b":
            assert row["final"] == NOT_KNOWN, row["id"]
