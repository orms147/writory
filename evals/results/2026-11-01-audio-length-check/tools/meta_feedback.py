"""Nhờ Meta Muse (config bộ đo D-140) đọc một kịch bản audio và nhận xét. Một lời gọi, trần 0,50 USD. Không in key.

    uv --directory backend run python meta_feedback.py <tts.txt> <out.md>
"""
import asyncio
import json
import sys
from pathlib import Path

from writory.config import REPO_ROOT, load_config
from writory.llm.base import Message
from writory.llm.capped import CappedClient
from writory.llm.openrouter import call_deadline
from writory.llm.provider import bench_llm
from writory.quality.bench_d import Budget
from writory.safety.wrap import DATA_NOTICE, UserAuthored, system_message, user_message

MODEL = "meta/muse-wonder-1.0"
SYSTEM = """Bạn là biên tập viên truyện audio tiếng Việt, quen thể loại truyện mạng sảng văn ("chết não": hào môn, \
thiếu gia thật giả, tiểu thư giả, trà xanh, vả mặt) đọc trên kênh truyện audio bằng một giọng đọc máy (TTS). Kịch bản \
trong khối dữ liệu do một hệ thống viết truyện có trí nhớ đồ thị sinh ra, tự đi tới hết (không có người chơi chọn), mục \
tiêu khoảng {minutes} phút đọc. Đọc hết rồi nhận xét thẳng thắn, cụ thể, bằng tiếng Việt, dạng markdown, không quá 900 chữ:

1. Chấm điểm 1–10 kèm một câu lý do cho từng mục: móc mở đầu; nhịp và độ cuốn; độ sảng khoái của các màn vả mặt; nhân \
vật (rõ, nhất quán, phản diện có đáng ghét không); lời thoại và câu dẫn ai nói (TTS một giọng có nghe ra không); tiếng \
Việt tự nhiên; cái kết. Cuối cùng một điểm chung.
2. Tối đa 8 vấn đề cụ thể, mỗi vấn đề kèm một câu trích ngắn nguyên văn từ kịch bản.
3. Những chỗ giọng đọc máy dễ vấp hay người nghe dễ lạc (số, tên, câu dài, đoạn thoại không rõ ai nói).
4. Tối đa 6 đề xuất sửa cho hướng dẫn văn phong của hệ thống, mỗi đề xuất một câu ra lệnh cụ thể dùng được ngay.
Không viết lại truyện."""


async def main(src: Path, out: Path, minutes: int) -> None:
    config = load_config(REPO_ROOT / "evals" / "config" / "meta")
    script = src.read_text(encoding="utf-8")
    calls: list[dict] = []
    inner = bench_llm(config, REPO_ROOT / ".env", deadline_s=call_deadline(config), models=[MODEL])
    llm = CappedClient(inner, budget=Budget("meta-feedback", 0.50), prices=config.models.prices,
                       max_tokens=12000, record=calls.append, roles={})
    messages: list[Message] = [
        system_message(SYSTEM.format(minutes=minutes), DATA_NOTICE),
        user_message(f"Kịch bản ({len(script.split())} chữ):", UserAuthored(script, "audio_script"),
                     "Nhận xét theo đúng bốn mục."),
    ]
    result = await llm.chat(MODEL, messages, extra={"reasoning": {"effort": "low"}, "max_tokens": 12000})
    out.write_text(result.text.strip() + "\n", encoding="utf-8")
    print(json.dumps({"model": result.model, "cost_usd": result.usage.cost_usd,
                      "prompt_tokens": result.usage.prompt_tokens,
                      "completion_tokens": result.usage.completion_tokens}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40))
