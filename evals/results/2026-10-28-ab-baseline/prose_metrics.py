"""Số đo bằng code cho phép so đề viết cũ/v3 (nhánh eval/ab-baseline). Không phán đoán văn học: đếm
bề mặt chữ. Ba số đầu theo cách đo của phiên chẩn đoán (`../2026-10-28-prose-diagnosis/stats*.py`),
số thứ tư là chi phí.

  python prose_metrics.py <thư mục chạy> [<thư mục chạy> ...]      (in JSON mỗi lần chạy)

1. static_end_ratio: tỉ lệ chương (trừ chương cuối) mà đoạn cuối của cảnh cuối là "tranh đứng yên"
   (chữ chờ / không ai / vẫn chưa ...; cùng regex `stats.py`).
2. duplicate_openers: số cặp chương (mọi cặp, không chỉ liền kề) có câu mở giống nhau, độ giống
   Jaccard trên tập từ >= 0,5 (cách `stats2.py`).
3. waiting_choice_sets: số bộ lựa chọn cuối chương có ÍT NHẤT HAI trong ba lựa chọn khớp họ từ
   "chờ / đợi / giữ / đứng / ngồi / trông / im lặng ..." (proxy yếu cho "ba cách của cùng một việc
   chờ"). Hiệu chuẩn trên `ky-ao-vua-3` với nhãn tay của phiên chẩn đoán (5/10 bộ là "cùng việc chờ":
   ch01, 05, 06, 07, 10): proxy bắt ch05, ch06, ch10 và không bắt bộ nào ngoài nhãn (độ chính xác
   3/3, độ phủ 3/5). Là chặn dưới, đếm so giữa các lần chạy, không phải số tuyệt đối.
4. usd_per_chapter: report.json: tổng chi phí chia số chương đã ghi (và riêng viết + dàn ý).
"""

import itertools
import json
import re
import sys
from pathlib import Path

CHOICES_HEADING = "## Lựa chọn cuối chương"
TAIL = re.compile(r"\b(Không ai|không ai|vẫn (?:chưa|còn|đứng|nằm|ở)|chưa (?:ai|được|có)|chờ)\b")
WAIT = re.compile(
    r"\b(chờ|đợi|giữ|đứng|ngồi|trông|im lặng|không (?:làm gì|nói gì|động)|nhắc rằng)\b",
    re.IGNORECASE)
CHOICE = re.compile(r"^(\d)\. \[([^\]]*)\] (.*?)(?:  ← đã chọn)?$", re.MULTILINE)


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / max(1, len(ta | tb))


def body_lines(chapter: str) -> list[str]:
    body = chapter.split(CHOICES_HEADING)[0]
    return [ln.strip() for ln in body.split("\n")
            if ln.strip() and not ln.startswith("#") and not ln.strip().startswith("_Lựa chọn dẫn")]


def metrics(run: Path) -> dict:
    files = sorted((run / "chapters").glob("ch*.md"))
    chapters = [f.read_text(encoding="utf-8") for f in files]
    static, openers, waiting, sets = 0, [], 0, 0
    for i, text in enumerate(chapters):
        lines = body_lines(text)
        if i < len(chapters) - 1:  # chương cuối kết truyện, không tính
            last_scene = "\n".join(lines).split("* * *")[-1]
            paragraphs = [p.strip() for p in last_scene.split("\n") if p.strip()]
            static += bool(paragraphs and TAIL.search(paragraphs[-1]))
        first = next((ln for ln in lines if ln != "* * *"), "")
        openers.append(re.split(r"(?<=[.!?])\s", first)[0])
        options = [m.group(3) for m in CHOICE.finditer(text.partition(CHOICES_HEADING)[2])]
        if len(options) == 3:
            sets += 1
            waiting += sum(bool(WAIT.search(o)) for o in options) >= 2
    pairs = list(itertools.combinations(range(len(openers)), 2))
    dup = [(a + 1, b + 1) for a, b in pairs if jaccard(openers[a], openers[b]) >= 0.5]
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    committed = report["chapters_committed"]
    cost = report["cost"]
    by_role = cost["by_role"]
    return {
        "run": run.name, "chapters": len(chapters), "static_end": static,
        "static_end_ratio": round(static / max(1, len(chapters) - 1), 3),
        "duplicate_openers": len(dup), "duplicate_opener_pairs": dup,
        "choice_sets": sets, "waiting_choice_sets": waiting,
        "usd_per_chapter": round(cost["total_usd"] / committed, 6) if committed else None,
        "writer_outline_usd_per_chapter": round(
            (by_role.get("writer", 0) + by_role.get("outline", 0)) / committed, 6) if committed else None,
        "rewrites": report["rewrites"], "chapters_committed": committed,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for d in sys.argv[1:]:
        print(json.dumps(metrics(Path(d)), ensure_ascii=False))
