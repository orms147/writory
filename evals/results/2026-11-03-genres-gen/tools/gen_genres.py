"""Soạn danh mục thể loại bằng Meta Muse Wonder, chấm bằng Claude Sonnet 5.5 (D-161; thang chấm: ../rubric.md).

Chạy từ backend/ (key đọc từ biến môi trường, không in):
    uv run --env-file ../.env python ../evals/results/2026-11-03-genres-gen/tools/gen_genres.py

Ghi vào thư mục cha: candidates_round1.yaml, verdicts_round1.jsonl, candidates_round2.yaml, verdicts_round2.jsonl,
final_genres.yaml, cost.json, calls.jsonl, run.log. Không tự sửa config/genres.yaml: bản cuối qua bộ kiểm của app
(`load_config` trên một bản sao config/) rồi mới chép tay. Không đặt trần chi phí (chủ dự án quyết, chỉ lượt này); số
lời gọi cố định theo quy trình.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel, SecretStr, ValidationError

from writory.config import REPO_CONFIG_DIR, Genre, ModelPrice, load_config
from writory.llm.anthropic_client import AnthropicClient
from writory.llm.base import Message
from writory.llm.meta import MetaClient

OUT = Path(__file__).resolve().parent.parent
META = "meta/muse-wonder-1.0"
SONNET = "anthropic-api/claude-sonnet-5-5"
META_EFFORT = "xhigh"
SONNET_EFFORT = "high"
# Giá USD / 1 triệu token: Meta theo danh sách chủ dự án (evals/config/meta/models.yaml); Sonnet 5.5 theo skill
# claude-api (tra 3/11/2026): 2 vào, 10 ra, 0,20 đọc cache, ghi cache 5 phút 1,25 x giá vào.
PRICES_META = {META: ModelPrice.model_validate({"in": 4.0, "out": 20.0, "cached_in": 0.2})}
PRICES_SONNET = {SONNET: ModelPrice.model_validate({"in": 2.0, "out": 10.0, "cached_in": 0.2, "cache_write_in": 2.5})}
NEW_PER_CALL = 8
NEW_CALLS = 2
DIRECTIONS = [
    "ngôn tình hiện đại", "kinh dị, linh dị dân gian", "hài hước đời thường", "xuyên không", "trọng sinh, làm lại cuộc đời",
    "hệ thống, thế giới như trò chơi", "mạt thế sinh tồn", "võ hiệp giang hồ", "cung đấu, hậu cung", "học đường thanh xuân",
    "điền văn, làm giàu ở quê", "khoa huyễn không gian", "quân sự, chiến tranh hư cấu", "thể thao, thi đấu",
    "nghề nghiệp, ẩm thực, thủ công", "truyền kỳ dân gian Việt", "tâm lý tội phạm", "gia đấu, tranh gia sản",
    "phiêu lưu khám phá", "giả tưởng phương Tây",
]

LOG: list[str] = []
CALLS: list[dict] = []


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    LOG.append(line)


class NamingDraft(BaseModel):
    names: Literal["han_viet", "viet"]
    places: Literal["hu_cau", "that"]


class GenreDraft(BaseModel):
    key: str
    label: str
    hint: str
    styles: list[Literal["prose", "audio"]]
    naming: NamingDraft
    setup_brief: str
    outline_brief: str
    voice_brief: str


class Drafts(BaseModel):
    genres: list[GenreDraft]


class Verdict(BaseModel):
    verdict: Literal["pass", "fix", "reject"]
    reasons: list[str]
    fix: str


def header_text(genres_yaml: str) -> str:
    """Chú thích yêu cầu đầu file genres.yaml, bỏ dấu '#'."""
    lines = []
    for line in genres_yaml.splitlines():
        if not line.startswith("#"):
            break
        lines.append(line[1:].removeprefix(" "))
    return "\n".join(lines)


def draft_yaml(d: GenreDraft | dict) -> str:
    data = d.model_dump() if isinstance(d, BaseModel) else d
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)


def code_problems(d: GenreDraft, limits) -> list[str]:
    problems: list[str] = []
    try:
        Genre.model_validate(d.model_dump())
    except ValidationError as e:
        problems += [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
    for field in ("label", "hint", "setup_brief", "outline_brief", "voice_brief"):
        text = getattr(d, field).strip()
        cap = getattr(limits, field)
        if len(text) > cap:
            problems.append(f"{field}: {len(text)} ký tự, quá trần {cap}; phải rút ngắn")
    return problems


async def call(client, model: str, messages: list[Message], schema: type[BaseModel], *, role: str, item: str,
               extra: dict) -> BaseModel:
    last: Exception | None = None
    for attempt in (1, 2):
        started = time.time()
        try:
            res = await client.chat(model, messages, response_schema=schema, extra=extra)
            CALLS.append({"role": role, "item": item, "model": model, "attempt": attempt,
                          "prompt_tokens": res.usage.prompt_tokens, "completion_tokens": res.usage.completion_tokens,
                          "cost_usd": res.usage.cost_usd, "finish": res.finish_reason,
                          "seconds": round(time.time() - started, 1)})
            text = res.text.strip()
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            return schema.model_validate(json.loads(text))
        except Exception as e:  # noqa: BLE001 — một lần thử lại cho mọi lỗi (mạng, JSON sai schema)
            last = e
            CALLS.append({"role": role, "item": item, "model": model, "attempt": attempt,
                          "error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": round(time.time() - started, 1)})
            log(f"{role} {item}: lỗi lượt {attempt}: {type(e).__name__}: {str(e)[:200]}")
    raise RuntimeError(f"{role} {item}: hỏng sau 2 lượt") from last


def gen_system(header: str, example: str) -> str:
    return (
        "Bạn là biên tập viên thể loại cho WriTory, trò chơi truyện tương tác tiếng Việt: người chơi sống đời nhân vật "
        "chính, chọn hướng đi mỗi chương; một hệ thống AI dựng thế giới, bí mật, và viết truyện theo đề của thể loại "
        "người chơi chọn. Việc của bạn là soạn các mục thể loại cho danh mục.\n\n"
        f"YÊU CẦU CỦA DANH MỤC (nguyên văn đầu file cấu hình):\n{header}\n\n"
        f"MẪU MỘT MỤC (định dạng tham khảo, nội dung là của thể loại sảng văn):\n{example}\n"
        "Viết đề bằng gạch đầu dòng ngắn ('- ...'), xuống dòng giữa các gạch. Mỗi mục phải có cả outline_brief và "
        "voice_brief (không để trống). Trả lời CHỈ bằng JSON đúng schema được giao."
    )


async def main() -> None:
    for name in ("META_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.environ.get(name):
            sys.exit(f"thiếu biến môi trường {name} (chạy với --env-file ../.env)")
    cfg = load_config()
    genres_path = REPO_CONFIG_DIR / "genres.yaml"
    genres_yaml = genres_path.read_text(encoding="utf-8")
    header = header_text(genres_yaml)
    limits = cfg.genres.limits
    sang_van = cfg.genres.get("sang_van")
    existing = [g for g in cfg.genres.genres if g.key != "sang_van"]
    example = draft_yaml(sang_van.model_dump(exclude_none=True))

    meta = MetaClient(SecretStr(os.environ["META_API_KEY"]), PRICES_META,
                      http=httpx.AsyncClient(timeout=httpx.Timeout(900.0, connect=10.0)))
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    sonnet = AnthropicClient(SecretStr(os.environ["ANTHROPIC_API_KEY"]), PRICES_SONNET,
                             workspace_id=SecretStr(ws) if ws else None)
    meta_extra = {"reasoning": {"effort": META_EFFORT}, "max_tokens": 64000}
    sonnet_extra = {"reasoning": {"effort": SONNET_EFFORT}, "max_tokens": 16000}
    system = gen_system(header, example)
    limits_text = (f"Trần ký tự: label {limits.label}, hint {limits.hint}, setup_brief {limits.setup_brief}, "
                   f"outline_brief {limits.outline_brief}, voice_brief {limits.voice_brief}. Viết gọn dưới trần.")

    # --- vòng 1: soạn --------------------------------------------------------------------------------------------
    fixed = {g.key: g for g in existing}
    existing_list = "\n".join(f"- key {g.key}, label \"{g.label}\", naming {g.naming.names}/{g.naming.places}"
                              for g in existing)
    log("Wonder: soạn lại 7 thể loại đang có")
    redo = await call(meta, META, [Message(role="system", content=system), Message(role="user", content=(
        f"Việc: soạn lại đề cho {len(existing)} thể loại đang có dưới đây. GIỮ NGUYÊN key, label, naming; viết mới hint, "
        f"styles, setup_brief, outline_brief, voice_brief cho sâu và cụ thể hơn. {limits_text}\n{existing_list}"))],
        Drafts, role="generate", item="existing", extra=meta_extra)
    drafts: list[GenreDraft] = []
    for d in redo.genres:
        if d.key in fixed:  # khoá, nhãn, quy ước tên của thể loại đang có không đổi (truyện đã lưu khoá)
            g = fixed[d.key]
            d = d.model_copy(update={"label": g.label, "naming": NamingDraft(**g.naming.model_dump())})
            drafts.append(d)
    taken = [g.label for g in cfg.genres.genres]
    for i in range(NEW_CALLS):
        log(f"Wonder: soạn {NEW_PER_CALL} thể loại mới (lượt {i + 1}/{NEW_CALLS})")
        new = await call(meta, META, [Message(role="system", content=system), Message(role="user", content=(
            f"Việc: soạn {NEW_PER_CALL} thể loại MỚI, khác hẳn nhau và khác các thể loại đã có: {', '.join(taken)}. "
            f"Gợi ý hướng (chọn hay kết hợp, không bắt buộc): {', '.join(DIRECTIONS)}. key mới chữ thường không dấu "
            f"a-z0-9_, không trùng key đã có. {limits_text}"))],
            Drafts, role="generate", item=f"new{i + 1}", extra=meta_extra)
        known_keys = {d.key for d in drafts} | {g.key for g in cfg.genres.genres}
        for d in new.genres:
            if d.key in known_keys or d.label in taken:
                log(f"bỏ {d.key}: trùng khoá hay nhãn")
                continue
            drafts.append(d)
            known_keys.add(d.key)
            taken.append(d.label)
    (OUT / "candidates_round1.yaml").write_text(
        yaml.safe_dump([d.model_dump() for d in drafts], allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    log(f"vòng 1: {len(drafts)} ứng viên")

    # --- chấm ----------------------------------------------------------------------------------------------------
    rubric = (OUT / "rubric.md").read_text(encoding="utf-8")
    judge_system = (
        "Bạn là giám khảo danh mục thể loại cho WriTory (trò chơi truyện tương tác tiếng Việt). Chấm MỘT mục thể loại "
        "theo thang dưới đây và yêu cầu của danh mục. Khắt khe với tiêu chí an toàn và tuân yêu cầu; công bằng với văn. "
        "`fix` phải kèm việc sửa cụ thể trong trường `fix`; `pass` thì `fix` là chuỗi rỗng.\n\n"
        f"THANG CHẤM:\n{rubric}\n\nYÊU CẦU CỦA DANH MỤC:\n{header}\n\nTrả lời CHỈ bằng JSON đúng schema."
    )
    sem = asyncio.Semaphore(4)

    async def judge(d: GenreDraft, catalog: str, round_no: int) -> dict:
        problems = code_problems(d, limits)
        async with sem:
            try:
                v = await call(sonnet, SONNET, [Message(role="system", content=judge_system), Message(role="user", content=(
                    f"Danh mục hiện có (nhãn: gợi ý), để kiểm trùng:\n{catalog}\n\nMỤC CẦN CHẤM:\n{draft_yaml(d)}\n"
                    + ("\nLỗi code đã tìm thấy (bắt buộc ít nhất `fix`):\n- " + "\n- ".join(problems) if problems else "")))],
                    Verdict, role=f"judge{round_no}", item=d.key, extra=sonnet_extra)
                out = v.model_dump()
            except RuntimeError as e:
                out = {"verdict": "reject", "reasons": [f"giám khảo không trả lời được: {e}"], "fix": ""}
        if problems and out["verdict"] == "pass":
            out = {"verdict": "fix", "reasons": out["reasons"] + problems, "fix": "Sửa các lỗi code: " + "; ".join(problems)}
        return {"key": d.key, "label": d.label, "code_problems": problems, **out}

    def catalog_of(items: list[GenreDraft]) -> str:
        rows = [f"- {d.label}: {d.hint}" for d in items] + [f"- {sang_van.label}: {sang_van.hint}"]
        return "\n".join(rows)

    log("Sonnet: chấm vòng 1")
    v1 = await asyncio.gather(*(judge(d, catalog_of(drafts), 1) for d in drafts))
    (OUT / "verdicts_round1.jsonl").write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in v1) + "\n",
                                               encoding="utf-8")
    log("vòng 1: " + ", ".join(f"{v['key']}={v['verdict']}" for v in v1))

    # --- vòng 2: sửa mục fix ----------------------------------------------------------------------------------------
    by_key = {d.key: d for d in drafts}
    to_fix = [v for v in v1 if v["verdict"] == "fix"]
    msem = asyncio.Semaphore(3)

    async def revise(v: dict) -> GenreDraft | None:
        d = by_key[v["key"]]
        async with msem:
            try:
                out = await call(meta, META, [Message(role="system", content=system), Message(role="user", content=(
                    "Việc: sửa mục thể loại dưới đây theo nhận xét của giám khảo. GIỮ NGUYÊN key"
                    + (", label, naming" if d.key in fixed else "") + f". {limits_text} Trả về danh sách genres có "
                    f"đúng một mục.\n\nMỤC HIỆN TẠI:\n{draft_yaml(d)}\nNHẬN XÉT:\n- " + "\n- ".join(v["reasons"])
                    + f"\nVIỆC PHẢI SỬA: {v['fix']}"))], Drafts, role="revise", item=d.key, extra=meta_extra)
            except RuntimeError as e:
                log(f"sửa {d.key} hỏng: {e}")
                return None
        if not out.genres:
            return None
        r = out.genres[0].model_copy(update={"key": d.key})
        if d.key in fixed:
            g = fixed[d.key]
            r = r.model_copy(update={"label": g.label, "naming": NamingDraft(**g.naming.model_dump())})
        return r

    log(f"Wonder: sửa {len(to_fix)} mục fix")
    revised = [r for r in await asyncio.gather(*(revise(v) for v in to_fix)) if r is not None]
    (OUT / "candidates_round2.yaml").write_text(
        yaml.safe_dump([d.model_dump() for d in revised], allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    current = [by_key[k] for k in by_key]
    for r in revised:
        current = [r if c.key == r.key else c for c in current]
    log("Sonnet: chấm vòng 2")
    v2 = await asyncio.gather(*(judge(r, catalog_of(current), 2) for r in revised))
    (OUT / "verdicts_round2.jsonl").write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in v2) + "\n",
                                               encoding="utf-8")
    log("vòng 2: " + ", ".join(f"{v['key']}={v['verdict']}" for v in v2))

    # --- ghép danh mục cuối -------------------------------------------------------------------------------------------
    passed: dict[str, GenreDraft] = {v["key"]: by_key[v["key"]] for v in v1 if v["verdict"] == "pass"}
    rev_by_key = {r.key: r for r in revised}
    passed |= {v["key"]: rev_by_key[v["key"]] for v in v2 if v["verdict"] == "pass"}
    final: list[dict] = []
    kept_old: list[str] = []
    for g in existing:
        if g.key in passed:
            final.append(passed[g.key].model_dump())
        else:
            final.append(g.model_dump(exclude_none=True))
            kept_old.append(g.key)
    final.append(sang_van.model_dump(exclude_none=True))
    final += [d.model_dump() for k, d in passed.items() if k not in fixed]
    for item in final:
        item["styles"] = list(item["styles"])
    head = genres_yaml[: genres_yaml.index("genres:\n")]
    body = yaml.dump({"genres": final}, Dumper=_BlockDumper, allow_unicode=True, sort_keys=False, width=110)
    text = head + body
    (OUT / "final_genres.yaml").write_text(text, encoding="utf-8", newline="\n")
    with tempfile.TemporaryDirectory() as tmp:  # bộ kiểm của app trên bản sao config/
        copy = Path(tmp) / "config"
        shutil.copytree(REPO_CONFIG_DIR, copy)
        (copy / "genres.yaml").write_text(text, encoding="utf-8")
        ok = load_config(copy).genres
    cost = {"meta_usd": round(sum(c.get("cost_usd", 0) for c in CALLS if c["model"] == META), 6),
            "anthropic_usd": round(sum(c.get("cost_usd", 0) for c in CALLS if c["model"] == SONNET), 6),
            "calls": len(CALLS), "final_genres": len(ok.genres), "kept_old": kept_old,
            "new_genres": [d["key"] for d in final if d["key"] not in fixed and d["key"] != "sang_van"]}
    (OUT / "cost.json").write_text(json.dumps(cost, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"xong: {len(ok.genres)} thể loại hợp lệ; Meta {cost['meta_usd']} USD, Anthropic {cost['anthropic_usd']} USD")


class _BlockDumper(yaml.SafeDumper):
    pass


def _str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value.strip() else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value.strip() + ("\n" if style else ""), style=style)


_BlockDumper.add_representer(str, _str)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows: stdout chuyển hướng là cp1252
    try:
        asyncio.run(main())
    finally:
        (OUT / "calls.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in CALLS) + "\n",
                                         encoding="utf-8")
        (OUT / "run.log").write_text("\n".join(LOG) + "\n", encoding="utf-8")
