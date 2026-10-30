# Bộ xuất kịch bản video chạy lại sau D-127 (nhịp thoại): video-export-demo-2

Cùng truyện, chương, ngôn ngữ và trần với `../2026-10-29-video-export-demo/` để so nhịp thoại trước và sau D-127. File xuất có lộ bí mật (dựng từ toàn bộ `truth`), cảnh báo ở đầu mọi file.

- **Lệnh** (trong `backend/`): `uv run python -m writory.export.video --story run-20261021-ky-ao-vua-2-f8a61160 --dialogue-lang zh --chapters 1-3 --budget 0.10 --env-file <.env của chủ dự án> --out <thư mục tạm>`, rồi chép vào đây. Trên Windows cần `PYTHONIOENCODING=utf-8` (lệnh in tiếng Việt ra console cp1252 thì sập, kể cả `--help`).
- **Mã:** main `3c2fe78`, đề `video-2`. Config gộp `acaab6e9a1f6…` (tính bằng `bench_run.config_sha256`). Model vai `video` và `moderate`: `config/models.yaml` (`openai/gpt-6-luna`, suy luận low). 30/10/2026.
- **Chi phí thật:** 0,0164 USD, 16 lời gọi: 1 bảng, 6 cảnh cộng 3 lượt thử lại (model tự chia lại shot dày thoại), 6 kiểm duyệt (cả sáu `allow`). Trần 0,10.

## Số đo bằng code (trên `script.json`)
| | demo cũ (D-125, trước D-127) | demo-2 (sau D-127) |
|---|---|---|
| Shot | 68 | 73 |
| Shot thoại dày hơn nhịp cho phép (đếm như D-127, bỏ dấu câu) | 17 (đếm lại ở `../2026-10-30-video-dialogue-pace/`) | **0** |
| Shot code tách (`split_by_code`) | – | 4, đều ở cảnh 3.2 |
| Shot `pace_over` (một lượt thoại dài hơn mọi shot) | – | 0 |
| Cảnh `ok` | 6/6 | 6/6 |

- Năm cảnh đầu có 11–12 shot, nằm trong trần `max_shots_per_scene`. Cảnh 3.2 có 14 shot sau khi code tách, vượt trần. Hệ quả này đã ghi ở D-127: trần chỉ ràng buộc model, không ràng buộc phép tách của code.
- **Đọc tay 4 shot code tách** (cảnh 3.2 shot 5, 6, 8, 9):
  - Thứ tự lượt thoại và người nói đúng, không mất chữ.
  - **Hạn chế mới thấy:** hai nửa của một shot bị tách dùng **cùng một `action_en`**, nên app video nhận hai shot mô tả hình giống hệt nhau.
  - Muốn khác thì cần model viết lại hành động cho từng nửa. Đó là việc sau, chưa làm.
