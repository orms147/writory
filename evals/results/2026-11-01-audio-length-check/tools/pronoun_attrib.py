"""Câu dẫn ngay trước lượt thoại chỉ gọi người nói bằng đại từ (cô ta, ông ta...) mà không có tên riêng nào: chỉ số
khách quan cho lời chê "không rõ ai nói" của Muse. Không gọi model."""
import json
import re
import sys
from pathlib import Path

PRONOUNS = re.compile(r"\b(cô ta|anh ta|ông ta|bà ta|cậu ta|chị ta|hắn|người đàn ông|người phụ nữ|cô gái|chàng trai|"
                      r"ông ấy|bà ấy|cô ấy|anh ấy|cậu ấy|chị ấy)\b", re.IGNORECASE)
# Từ viết hoa không đứng đầu câu: gần đúng tên riêng.
NAME = re.compile(r"(?<![.!?…:]\s)(?<!^)\b[A-ZĐÂĂÊÔƠƯÁÀẢÃẠÉÈẺẼẸÍÌỈĨỊÓÒỎÕỌÚÙỦŨỤÝỲỶỸỴ][a-zà-ỹđ]+")


def stats(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    total = pronoun_only = 0
    for prev, cur in zip(lines, lines[1:]):
        if not cur.startswith("“") or prev.startswith("“"):
            continue
        total += 1
        body = prev.lstrip("“").strip()
        if PRONOUNS.search(body) and not NAME.search(body[1:]):
            pronoun_only += 1
    return {"attributed_turns": total, "pronoun_only": pronoun_only,
            "pronoun_only_share": round(pronoun_only / max(total, 1), 3)}


for p in sys.argv[1:]:
    print(Path(p).parent.name, json.dumps(stats(Path(p).read_text(encoding="utf-8")), ensure_ascii=False))
