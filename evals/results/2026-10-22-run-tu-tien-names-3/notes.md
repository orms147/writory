# Nhận xét đọc tay: tu-tien-names-3

Người đọc: Claude, 22/10/2026. Nguồn: `summary.md`, `report.json`.

- Lệnh: `bench_run --label tu-tien-names-3 --scenario evals/scenarios/story_run/tu-tien-ngan.yaml --chapters 3 --budget 0.045`, mã nhánh `feature/forbidden-names` **sau** ngoại lệ "tên thật nằm trọn trong chữ đã hé lộ" (D-91).
- 3/3 chương, 0,0248 USD, không viết lại, không cảnh bị chặn, không `leak:name`, không cạnh bị bỏ.
- Thế giới khác `names-1` và `names-2`. Cùng cỡ (3 lần chạy), nên đây là một mẫu, không phải so sánh: không biết thế giới này có đồ vật tên chung như ở `names-1` không.

## Chưa kiểm
- Chưa có lần chạy lại đúng thế giới của `names-1` hay `ky-ao-vua-items-1` sau khi sửa (cần `bench_run --setup-from`, chưa vào `main` lúc chạy).
- Tổng ba lần chạy 0,0751 USD (trần 0,10).
