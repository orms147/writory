# Nhận xét đọc tay: tu-tien-names-2

Người đọc: Claude, 22/10/2026. Nguồn: `summary.md`, `report.json`.

- Lệnh: `bench_run --label tu-tien-names-2 --scenario evals/scenarios/story_run/tu-tien-ngan.yaml --chapters 3 --budget 0.05`, mã nhánh `feature/forbidden-names` **trước** ngoại lệ "tên thật nằm trọn trong chữ đã hé lộ". Đề có mục "Tên người đọc chưa được biết".
- 3/3 chương, 0,0287 USD, không viết lại, không cảnh bị chặn, không `leak:name`. Thế giới dựng khác `names-1` (setup luôn dựng khác dù cùng seed), nên không so thẳng được.
- Không chứng minh được mục báo trước có tác dụng: thế giới này có thể không có tên cấm nào cần báo.
