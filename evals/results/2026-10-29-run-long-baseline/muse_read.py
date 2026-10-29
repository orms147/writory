"""Góc nhìn thứ hai cho đoạn giữa và kết của truyện Dài: nhờ Meta Muse Wonder đọc nguyên văn và nói
chương nào giậm chân, vì sao (đo nền mức Dài, nhánh eval/long-baseline).

  python muse_read.py --env-file <.env> --out <file.json> --budget 1.0 <thư mục chạy> <chương đầu> <chương cuối>

Gửi: đề bài (tag) và văn các chương trong khoảng, kèm lựa chọn cuối chương, cộng chương cuối. KHÔNG gửi
truth_dump, kế hoạch hay key. Chỉ đọc `META_API_KEY` qua `load_keys` của bộ đo; lỗi qua `scrub` (G7).
Trả lời là chữ tự do (không schema). Giá và effort theo `evals/scenarios/bakeoff/judge.yaml` (giám khảo muse),
effort đổi xuống `low` theo yêu cầu của đo nền. Chi phí tính từ `usage`, ghi vào file kết quả.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx
from pydantic import SecretStr

from writory.quality.bench_bakeoff import META_BASE_URL, scrub
from writory.quality.bench_d import load_keys

sys.stdout.reconfigure(encoding="utf-8")
PRICE = {"input": 4.0, "cached_input": 0.2, "output": 20.0}  # USD / 1 triệu token, judge.yaml
SYSTEM = (
    "Bạn là biên tập viên đọc bản thảo truyện tương tác tiếng Việt do máy viết. Dưới đây là một số chương "
    "ở GIỮA truyện dài và chương CUỐI, nguyên văn, mỗi chương kèm ba lựa chọn cuối chương. Trả lời bằng "
    "tiếng Việt, ngắn gọn, đúng sự thật có trong văn (trích câu nếu cần), không bịa. Nếu chưa chắc, nói "
    "'chưa chắc'."
)
QUESTIONS = (
    "Trả lời lần lượt:\n"
    "1. Với MỖI chương đã đọc (trừ chương cuối): một dòng cho biết cuối chương so với đầu chương có gì đổi "
    "cụ thể không (nơi ở, ai biết gì, vật đổi chủ, ai bị thương/chết/bị bắt, mạch gỡ, quan hệ đổi), hay chỉ "
    "là cùng một cảnh nói/làm lại. Ghi 'ĐỔI: <điều gì>' hoặc 'GIẬM CHÂN: <vì sao>'.\n"
    "2. Các chương giữa có lặp một khuôn việc (cùng loại cảnh, cùng thao tác) không? Mô tả khuôn đó.\n"
    "3. Ba lựa chọn cuối chương của các chương này có thật sự dẫn tới ba hướng khác nhau không? Nêu ví dụ.\n"
    "{ENDING}"
    "{LAST}. Theo bạn, ba nguyên nhân hàng đầu khiến đoạn giữa giậm chân (nêu cái nhìn thấy trong văn: thế giới, "
    "nhân vật, nhịp, lựa chọn...), xếp theo mức quan trọng."
)
ENDING_QUESTION = ("4. Chương cuối: có giải quyết mâu thuẫn chính một cách cụ thể (có giá phải trả, có thay đổi) "
                   "hay kết bằng thủ tục/đứng yên?\n")


def questions(no_ending: bool) -> str:
    return QUESTIONS.replace("{ENDING}", "" if no_ending else ENDING_QUESTION).replace(
        "{LAST}", "4" if no_ending else "5")


def chapter_text(run: Path, n: int) -> str:
    return (run / "chapters" / f"ch{n:02d}.md").read_text(encoding="utf-8")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--env-file", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--budget", type=float, required=True)
    p.add_argument("--no-ending", action="store_true",
                   help="lượt dừng giữa chừng: không gửi chương cuối, bỏ câu hỏi về kết truyện")
    p.add_argument("run")
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    args = p.parse_args()
    run = Path(args.run)
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    final = max(int(f.stem[2:]) for f in (run / "chapters").glob("ch*.md"))
    scenario = meta.get("scenario", {}).get("content", {})
    brief = json.dumps(scenario.get("tags", {}), ensure_ascii=False)
    parts = [f"Đề bài người chơi chọn: {brief}", f"Truyện có {final} chương đã viết."]
    for n in range(args.first, args.last + 1):
        parts.append(f"\n===== CHƯƠNG {n} =====\n{chapter_text(run, n)}")
    if not args.no_ending:
        parts.append(f"\n===== CHƯƠNG CUỐI (CHƯƠNG {final}) =====\n{chapter_text(run, final)}")
    else:
        parts.append("\n(Truyện này dừng giữa chừng vì lỗi kỹ thuật, nên KHÔNG có chương cuối.)")
    parts.append("\n" + questions(args.no_ending))
    user = "\n".join(parts)
    # giữ chỗ: ước tính 3 ký tự = 1 token cho đầu vào
    reserve = len(user) / 3 * PRICE["input"] / 1e6 + 20000 * PRICE["output"] / 1e6
    if reserve > args.budget:
        raise SystemExit(f"giữ chỗ {reserve:.3f} USD vượt trần {args.budget}")
    keys = load_keys(Path(args.env_file), ["meta"])
    assert keys.meta_api_key is not None
    secret: SecretStr = keys.meta_api_key
    request = {"model": "muse-wonder-1.0", "max_tokens": 20000, "reasoning_effort": "low",
               "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as http:
        resp = await http.post(f"{META_BASE_URL}/chat/completions", json=request,
                               headers={"Authorization": f"Bearer {secret.get_secret_value()}"})
    if resp.status_code != 200:
        raise SystemExit(scrub(f"HTTP {resp.status_code}: {resp.text[:300]}", secret.get_secret_value()))
    data = resp.json()
    msg = data["choices"][0]["message"]
    usage = data.get("usage") or {}
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    inp = max((usage.get("prompt_tokens") or 0) - cached, 0)
    out = usage.get("completion_tokens") or 0
    cost = (inp * PRICE["input"] + cached * PRICE["cached_input"] + out * PRICE["output"]) / 1e6
    result = {"run": run.name, "chapters_sent": [args.first, args.last, final], "model": data.get("model"),
              "finish_reason": data["choices"][0].get("finish_reason"),
              "usage": {"input": inp, "cached": cached, "output": out,
                        "reasoning": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")},
              "cost_usd": round(cost, 4), "answer": msg.get("content") or ""}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok: {run.name} chi phí {cost:.4f} USD, kết thúc {result['finish_reason']}")


if __name__ == "__main__":
    asyncio.run(main())
