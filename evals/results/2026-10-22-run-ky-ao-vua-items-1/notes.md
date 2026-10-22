# Nhận xét đọc tay: ky-ao-vua-items-1 (chạy hỏng, không dùng làm số đo)

Người đọc: Claude, 22/10/2026. Nguồn: `report.json`, `events.jsonl`, `summary.md`.

- Lệnh: `bench_run --label ky-ao-vua-items-1 --scenario evals/scenarios/story_run/ky-ao-vua.yaml --chapters 10 --seed 20261021 --budget 0.15`, mã nhánh `feature/item-continuity` (D-90, chưa commit lúc chạy).
- Dừng ở chương 1, mã `SCENE_LEAK_BLOCKED`: `leak:name` ×9, hai cảnh bị chặn sau hai lượt, 0/10 chương ghi. Tốn 0,0185 USD.
- Thế giới dựng lần này khác lần 2 (setup luôn dựng khác dù cùng seed). Chương 0 của nó có đồ vật chỉ có người giữ (không đồ vật nào vừa có người giữ vừa ở nơi), nên luật mới không có gì để chặn.
- **Chưa biết nguyên nhân.** Báo cáo chỉ ghi loại lỗi, không ghi tên bị lộ, và văn cảnh bị chặn không được lưu. `leak:name` cũng từng chặn cảnh ở `tu-tien-1` và `tu-tien-3` trước D-90, nên không thể quy cho mục "Đồ vật quan trọng" từ một lần chạy. Mục này cho người viết thấy tên của mọi đồ vật (tối đa 12), kể cả đồ vật của nhân vật vắng mặt; trước đây tên đồ vật chỉ vào ngữ cảnh khi gần nhân vật có mặt. Đó là khả năng chưa loại trừ.
