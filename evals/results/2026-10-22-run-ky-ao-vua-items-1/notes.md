# Nhận xét đọc tay: ky-ao-vua-items-1 (chạy hỏng, không dùng làm số đo)

Người đọc: Claude, 22/10/2026. Nguồn: `report.json`, `events.jsonl`, `summary.md`.

- Lệnh: `bench_run --label ky-ao-vua-items-1 --scenario evals/scenarios/story_run/ky-ao-vua.yaml --chapters 10 --seed 20261021 --budget 0.15`, mã nhánh `feature/item-continuity` (D-90, chưa commit lúc chạy).
- Dừng ở chương 1, mã `SCENE_LEAK_BLOCKED`: `leak:name` ×9, hai cảnh bị chặn sau hai lượt, 0/10 chương ghi. Tốn 0,0185 USD.
- Thế giới dựng lần này khác lần 2 (setup luôn dựng khác dù cùng seed). Chương 0 của nó có đồ vật chỉ có người giữ (không đồ vật nào vừa có người giữ vừa ở nơi), nên luật mới không có gì để chặn.
- **Tên bị lộ** (đọc từ `truth_dump.json`, `chapters.1[].reviews[].issues[].feedback`, đoạn trong «»): "Lão đạo sĩ" ×6 ở lượt 1 cảnh 2, và "lão đạo sĩ", "đạo sĩ áo tro" ở lượt 2 cảnh 1. Cả hai là tên và biệt danh của `lao_dao_si` (`Lão Đạo Sĩ`, alias `Đạo sĩ áo tro`), một nhân vật.
- **Chưa kết luận được mục "Đồ vật quan trọng" có gây ra không, nhưng bằng chứng nghiêng về không.** `lao_dao_si` có trong `present` của dàn ý cảnh 1 (cả hai lượt), nên người viết thấy tên "Lão Đạo Sĩ (Đạo sĩ áo tro)" ở mục "Nhân vật có mặt" dù không có mục đồ vật. Tên này thành tên cấm theo D-61 (a): `lao_dao_si` vào player_view với `known_as` khác tên thật nên tên thật (cụm danh từ chung "lão đạo sĩ", so không phân biệt hoa thường) bị cấm. Cơ chế có sẵn, người viết không được báo tên nào đang bị cấm. Mục đồ vật chỉ in thêm "do Lão Đạo Sĩ giữ". Không có lần chạy đối chứng cùng thế giới, nên chưa loại trừ được ảnh hưởng của mục này lên tần suất.
- `leak:name` cùng kiểu từng chặn cảnh ở `tu-tien-1` và `tu-tien-3` trước D-90.
