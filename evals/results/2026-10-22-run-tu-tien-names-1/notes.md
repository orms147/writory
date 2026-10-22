# Nhận xét đọc tay: tu-tien-names-1 (dừng ở chương 1)

Người đọc: Claude, 22/10/2026. Nguồn: `report.json`, `truth_dump.json`.

- Lệnh: `bench_run --label tu-tien-names-1 --scenario evals/scenarios/story_run/tu-tien-ngan.yaml --chapters 3 --budget 0.05`, mã nhánh `feature/forbidden-names` (D-91) **trước** khi thêm ngoại lệ "tên thật nằm trọn trong chữ đã hé lộ". Đề có mục "Tên người đọc chưa được biết".
- Dừng ở chương 1, `SCENE_LEAK_BLOCKED`: `leak:name` ×12, hai cảnh bị chặn, 0/3 chương. Tốn 0,0216 USD.
- **Nguyên nhân (đọc từ `truth_dump.json`, phản hồi viết lại):** hai đồ vật tên chung, `thuyen_nho` ("Thuyền Nhỏ") và `tui_luong_kho` ("Túi Lương Khô"). Trang gọi chúng "chiếc thuyền nhỏ", "chiếc túi lương khô" (`known_as`). Luật D-61 (a) chỉ miễn tên thật CHỨA chữ đã hé lộ, không miễn tên thật NẰM TRỌN trong chữ đã hé lộ, nên "thuyền nhỏ" bị cấm. Phản hồi viết lại bảo "dùng «chiếc thuyền nhỏ» thay vào", mà chính chữ đó chứa "thuyền nhỏ", nên model làm đúng vẫn trúng: "thuyền nhỏ" trúng 8 lần qua hai lượt chương.
- Đây là báo nhầm của luật có sẵn, không phải model thiếu lời nhắc. Cùng kiểu có thể là nguyên nhân `leak:name` ở `ky-ao-vua-items-1` ("Lão đạo sĩ"), nhưng tên người đọc biết ở đó không được lưu nên chưa kiểm.
- Sửa ở D-91: tên thật nằm trọn trong chữ đã hé lộ thì không bị cấm. Không có lần chạy lại cùng thế giới (`--setup-from` chưa có ở `main`).
