"""Chấm MÙ các chương hậu quả của cao trào bằng Muse (chỉ số (b) của expectations.md, D-142).

  python judge_aftermath.py pack   --out <thư mục> --spec <spec.json>     (dựng yêu cầu, KHÔNG gọi model)
  python judge_aftermath.py judge  --out <thư mục> --env-file <.env> --budget 3.0
  python judge_aftermath.py count  --out <thư mục>                        (đếm nhãn, mở khoá nhãn)
  python judge_aftermath.py selftest

`spec.json`: danh sách `{"run": <thư mục kết quả>, "arm": "ctrl"|"treat", "climax": <số thứ tự mốc cao trào>,
"chapters": [d+1, d+2, ...]}`; chương d (chương xảy ra) đọc từ `truth_dump.json` của lượt chạy.
`pack` trộn mọi (lượt, chương) thành các mục `C01..` theo thứ tự ngẫu nhiên (seed ghi lại), ghi `key.json`
(khoá giải nhãn, không gửi) và `request.json`. Người chấm chỉ thấy câu mô tả cao trào, chương nào nó xảy ra và
văn của chương: không thấy nhánh, tên lượt hay cờ. `count` đếm nhãn bằng code, không cân nhắc.
Chỉ đọc `META_API_KEY` qua `load_keys` của bộ đo; giá theo `evals/scenarios/bakeoff/judge.yaml`."""

import argparse
import asyncio
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
LABELS = ("HẬU QUẢ", "DIỄN LẠI", "KHÁC")
PRICE = {"input": 4.0, "cached_input": 0.2, "output": 20.0}  # USD / 1 triệu token (judge.yaml)
SEED = 20261030
SYSTEM = (
    "Bạn là biên tập viên đọc bản thảo truyện tương tác tiếng Việt do máy viết. Mỗi mục dưới đây là một chương "
    "ở giữa truyện dài, nguyên văn, kèm một câu mô tả CAO TRÀO của truyện và chương mà cao trào đó đã xảy ra. "
    "Chỉ trả lời đúng định dạng được yêu cầu, không thêm lời."
)
QUESTION = (
    "Với MỖI mục, ghi MỘT dòng dạng `C<số>: <NHÃN> | <một câu giải thích, có trích ít chữ nguyên văn>`, "
    "trong đó NHÃN là đúng một trong ba:\n"
    "- HẬU QUẢ: chương viết hậu quả cụ thể của cao trào (ai phải trả giá, điều gì đổi không đảo được, người khác "
    "phản ứng ra sao) trên trang.\n"
    "- DIỄN LẠI: chương dựng lại hay lặp lại tình huống, quyết định hay xung đột của chính cao trào.\n"
    "- KHÁC: chương đi sang việc khác, không có hậu quả của cao trào trên trang.\n"
    "Nếu chương vừa có hậu quả vừa lặp lại cao trào thì chọn nhãn chiếm phần lớn chương. Chưa chắc thì chọn KHÁC."
)
LINE = re.compile(r"^\s*(C\d+)\s*:\s*(HẬU QUẢ|DIỄN LẠI|KHÁC)\b", re.MULTILINE)


def chapter_text(run: Path, n: int) -> str:
    return (run / "chapters" / f"ch{n:02d}.md").read_text(encoding="utf-8")


def climax_info(run: Path, number: int) -> tuple[str, int]:
    truth = json.loads((run / "truth_dump.json").read_text(encoding="utf-8"))
    goal = truth["plan"]["milestones"][number - 1]["goal"]
    for n, pkg in truth["packages"].items():
        for node in pkg["nodes"]:
            if node["label"] == "Chapter" and number in (node["props"].get("milestones") or []):
                return goal, int(n)
    raise SystemExit(f"{run.name}: mốc {number} chưa có dấu xong")


def pack(out: Path, spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    items = []
    for s in spec:
        run = Path(s["run"])
        goal, done = climax_info(run, s["climax"])
        for ch in s["chapters"]:
            items.append({"run": run.name, "arm": s["arm"], "chapter": ch, "goal": goal, "done_chapter": done,
                          "text": chapter_text(run, ch)})
    random.Random(SEED).shuffle(items)
    out.mkdir(parents=True, exist_ok=True)
    key, blocks = {}, []
    for i, it in enumerate(items, 1):
        cid = f"C{i:02d}"
        key[cid] = {k: it[k] for k in ("run", "arm", "chapter", "done_chapter")}
        blocks.append(f"===== MỤC {cid} =====\nCao trào của truyện: {it['goal']} (đã xảy ra ở chương "
                      f"{it['done_chapter']}).\n\n{it['text']}")
    user = "\n\n".join(blocks) + "\n\n" + QUESTION
    (out / "key.json").write_bytes(json.dumps(key, ensure_ascii=False, indent=1).encode("utf-8"))
    (out / "request.json").write_bytes(json.dumps(
        {"system": SYSTEM, "user": user, "seed": SEED, "items": len(items)}, ensure_ascii=False,
        indent=1).encode("utf-8"))
    reserve = len(user) / 3 * PRICE["input"] / 1e6 + 20000 * PRICE["output"] / 1e6
    print(f"ok: {len(items)} mục, giữ chỗ ước tính {reserve:.3f} USD, khoá ở key.json (không gửi)")


async def judge(out: Path, env_file: Path, budget: float) -> None:
    import httpx
    from pydantic import SecretStr

    from writory.quality.bench_bakeoff import META_BASE_URL, scrub
    from writory.quality.bench_d import load_keys

    req = json.loads((out / "request.json").read_text(encoding="utf-8"))
    reserve = len(req["user"]) / 3 * PRICE["input"] / 1e6 + 20000 * PRICE["output"] / 1e6
    if reserve > budget:
        raise SystemExit(f"giữ chỗ {reserve:.3f} USD vượt trần {budget}")
    keys = load_keys(env_file, ["meta"])
    assert keys.meta_api_key is not None
    secret: SecretStr = keys.meta_api_key
    body = {"model": "muse-wonder-1.0", "max_tokens": 20000, "reasoning_effort": "low",
            "messages": [{"role": "system", "content": req["system"]},
                         {"role": "user", "content": req["user"]}]}
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as http:
        resp = await http.post(f"{META_BASE_URL}/chat/completions", json=body,
                               headers={"Authorization": f"Bearer {secret.get_secret_value()}"})
    if resp.status_code != 200:
        raise SystemExit(scrub(f"HTTP {resp.status_code}: {resp.text[:300]}", secret.get_secret_value()))
    data = resp.json()
    usage = data.get("usage") or {}
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    inp = max((usage.get("prompt_tokens") or 0) - cached, 0)
    outp = usage.get("completion_tokens") or 0
    cost = (inp * PRICE["input"] + cached * PRICE["cached_input"] + outp * PRICE["output"]) / 1e6
    (out / "answer.json").write_bytes(json.dumps(
        {"model": data.get("model"), "finish_reason": data["choices"][0].get("finish_reason"),
         "usage": {"input": inp, "cached": cached, "output": outp}, "cost_usd": round(cost, 4),
         "answer": data["choices"][0]["message"].get("content") or ""}, ensure_ascii=False,
        indent=1).encode("utf-8"))
    print(f"ok: chi phí {cost:.4f} USD")


def parse(answer: str) -> dict[str, str]:
    return {cid: label for cid, label in LINE.findall(answer)}


def count(out: Path) -> None:
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    answer = json.loads((out / "answer.json").read_text(encoding="utf-8"))["answer"]
    labels = parse(answer)
    missing = sorted(set(key) - set(labels))
    table: dict[str, Counter] = {}
    for cid, info in key.items():
        if cid in labels:
            table.setdefault(f"{info['arm']}:{info['run']}", Counter())[labels[cid]] += 1
    result = {"labels_parsed": len(labels), "missing": missing,
              "by_run": {k: {lab: c.get(lab, 0) for lab in LABELS} for k, c in sorted(table.items())}}
    (out / "counts.json").write_bytes(json.dumps(result, ensure_ascii=False, indent=1).encode("utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=1))


def selftest() -> None:
    got = parse("C01: HẬU QUẢ | x\nC02 : DIỄN LẠI | y\nrác\n  C03: KHÁC | z\nC04: GIỮ | sai")
    assert got == {"C01": "HẬU QUẢ", "C02": "DIỄN LẠI", "C03": "KHÁC"}, got
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "judge", "count", "selftest"])
    ap.add_argument("--out")
    ap.add_argument("--spec")
    ap.add_argument("--env-file")
    ap.add_argument("--budget", type=float, default=3.0)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "pack":
        pack(Path(a.out), Path(a.spec))
    elif a.cmd == "judge":
        asyncio.run(judge(Path(a.out), Path(a.env_file), a.budget))
    else:
        count(Path(a.out))
