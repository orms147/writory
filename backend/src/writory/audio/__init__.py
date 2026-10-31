"""Bộ viết kịch bản audio (D-151): công cụ CHỈ của admin, chạy bằng lệnh `python -m writory.audio.script`.

Admin đưa vài hướng đi ngắn (hay nhờ model đề xuất từ vài tag), model lên kế hoạch (nhân vật, bí mật, lịch
lộ, các đoạn) rồi viết từng đoạn có nhớ các đoạn trước, cho một kịch bản nói dài cỡ `--minutes` phút. Đầu ra
là chữ cho TTS: `tts.txt` (một giọng), `script.md` và `script.json` (có người nói, cách đọc, âm thanh).

Không có endpoint, không có nút trên giao diện, không đọc hay ghi Postgres, Neo4j: không có đường nào từ
người chơi tới đây. Key là OPENROUTER_API_KEY của chủ dự án (hay key bộ đo khi `--config-dir`), không in,
không ghi (G7). Mỗi đoạn qua kiểm duyệt G9 fail-closed trước khi vào bản xuất. App không tạo âm thanh:
TTS và dựng video do admin làm ở công cụ khác.
"""
