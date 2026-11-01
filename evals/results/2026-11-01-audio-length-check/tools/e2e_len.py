"""Chạy thật một truyện kiểu kịch bản audio, độ dài ngắn (~40 phút), tự viết đến hết (D-153, D-154). Không in key.

Dùng đúng các route giao diện gọi: /setup (style=audio), /setup/.../finalize, /stories/{id}/chapters/next?auto=true,
/stories/{id}/script.txt. Ghi kịch bản và nhật ký vào thư mục `out`.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = sys.argv[1]
OUT = Path(sys.argv[2])
LEVEL = sys.argv[3]
OUT.mkdir(parents=True, exist_ok=True)
H = {"content-type": "application/json", "origin": BASE}
log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    log_lines.append(msg)


def call(method, path, body=None, timeout=900):
    data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def ok(method, path, body=None):
    status, raw = call(method, path, body)
    if status >= 400:
        log(f"{method} {path} -> {status} {raw[:400]}")
        sys.exit(1)
    return json.loads(raw) if raw[:1] in "{[" else raw


cost0 = ok("GET", "/player/costs")["total_usd"]
t0 = time.time()
s = ok("POST", "/setup", {"tags": {"genre": "đô thị hào môn", "era": "hiện đại",
                                   "voice": "sảng văn, vả mặt, thiếu gia thật giả, trà xanh"},
                          "length_level": LEVEL, "style": "audio"})
sid = s["session_id"]
picked = {}
for step in ("settings", "plots", "characters"):
    opts = ok("POST", f"/setup/{sid}/{step}")[step]
    picked[step] = opts[0].get("title") or opts[0].get("name")
    ok("PUT", f"/setup/{sid}/{step}", {"index": 0})
story = ok("POST", f"/setup/{sid}/finalize")["story_id"]
log(f"story {story} style=audio length={LEVEL}; chọn: {picked}; khởi tạo {time.time() - t0:.0f}s")

for _ in range(14):
    st = ok("GET", f"/stories/{story}")
    if st["finished"]:
        break
    t = time.time()
    status, sse = call("POST", f"/stories/{story}/chapters/next?auto=true")
    kinds = [ln[7:] for ln in sse.splitlines() if ln.startswith("event: ") and ln[7:] != "stage"]
    log(f"ch{st['chapter'] + 1}: HTTP {status} {kinds} {time.time() - t:.0f}s")
    if status != 200 or "chapter_committed" not in kinds:
        log(sse[-800:])
        sys.exit(1)

st = ok("GET", f"/stories/{story}")
script = ok("GET", f"/stories/{story}/script.txt")
(OUT / "tts.txt").write_text(script, encoding="utf-8")
words = len(script.split())
spent = ok("GET", "/player/costs")["total_usd"] - cost0
log(f"finished={st['finished']} chapters={st['chapter']} words={words} (~{words / 150:.1f} phút ở 150 chữ/phút) "
    f"chars={len(script)} spent≈{spent:.4f} USD total {time.time() - t0:.0f}s")
(OUT / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
(OUT / "story.json").write_text(json.dumps({"story_id": story, "picked": picked, "chapters": st["chapter"],
                                            "words": words, "spent_usd": round(spent, 6)}, ensure_ascii=False,
                                           indent=2), encoding="utf-8")
