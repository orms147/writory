"""Viết tiếp một truyện bằng tự viết đến hết (D-154); chương bị chặn (vd. SCENE_LEAK_BLOCKED) thì thử lại như người
chơi bấm "thử lại", tối đa `RETRIES` lần mỗi chương. Ghi tts.txt, run.log, story.json vào `out`. Không in key."""
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE, SID, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
RETRIES = 2
OUT.mkdir(parents=True, exist_ok=True)
H = {"content-type": "application/json", "origin": BASE}
log_lines: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    log_lines.append(msg)


def call(method, path, timeout=900):
    req = urllib.request.Request(BASE + path, data=b"" if method == "POST" else None, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def story_cost() -> float:
    costs = json.loads(call("GET", "/player/costs")[1])
    return next((s["spent_usd"] for s in costs["stories"] if s["story_id"] == SID), 0.0)


t0 = time.time()
retries_used = 0
for _ in range(16):
    st = json.loads(call("GET", f"/stories/{SID}")[1])
    if st["finished"]:
        break
    chapter = st["chapter"] + 1
    for attempt in range(1, RETRIES + 2):
        t = time.time()
        status, sse = call("POST", f"/stories/{SID}/chapters/next?auto=true")
        kinds = [ln[7:] for ln in sse.splitlines() if ln.startswith("event: ") and ln[7:] != "stage"]
        log(f"ch{chapter} lượt {attempt}: HTTP {status} {kinds} {time.time() - t:.0f}s")
        if status == 200 and "chapter_committed" in kinds:
            break
        retries_used += 1
    else:
        log("dừng: hết lượt thử lại")
        break

st = json.loads(call("GET", f"/stories/{SID}")[1])
script = call("GET", f"/stories/{SID}/script.txt")[1]
(OUT / "tts.txt").write_text(script, encoding="utf-8")
words = len(script.split())
spent = story_cost()
log(f"finished={st['finished']} chapters={st['chapter']} words={words} (~{words / 150:.1f} phút ở 150 chữ/phút) "
    f"thử lại {retries_used} lần; chi phí truyện (gồm khởi tạo? không: theo truyện) {spent:.4f} USD; {time.time() - t0:.0f}s")
(OUT / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
(OUT / "story.json").write_text(json.dumps({"story_id": SID, "chapters": st["chapter"], "words": words,
                                            "retries": retries_used, "story_spent_usd": round(spent, 6)},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
