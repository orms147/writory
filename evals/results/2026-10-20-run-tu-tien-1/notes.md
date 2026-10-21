# Nhận xét đọc tay: tu-tien-1

Người đọc: Claude (điều phối), 20/10/2026. Số liệu lấy từ `summary.md` và `truth_dump.json` của chính thư mục này.

## Chạy được
- Khởi tạo và 6/6 chương đều ghi xong. Không cảnh nào bị chặn; có 5 lượt viết lại, lượt nào cũng sửa được lỗi.
- Bộ trích, người canh và bộ dò lộ đều bắt được lỗi thật: `teller_does_not_know` ở chương 1, `at_most_one` ở chương 4. Bản viết lại hết lỗi.
- Văn là tiếng Việt tự nhiên, thoại đúng "- ", không lẫn chữ Hán. Lựa chọn bám sát cảnh.
- Chi phí 0,0512 USD, trung bình khoảng 0,0085 USD một chương. Bộ trích tốn nhiều nhất (0,0176), rồi tới model viết (0,0161).

## Lỗi và khoảng trống
1. **Cốt truyện không đi theo kế hoạch.**
   - Hai bí mật chính (`f_doan_khac_tao_phu_gia`, khoảng lộ 3–6; `f_doan_khac_muon_mac_ca`, khoảng lộ 4–6) chưa hé lộ khi truyện hết.
   - Có 4 mạch phải gỡ, mới gỡ được 1 (`t_cuu_dong_mon`).
   - Chương 6 là chương cuối nhưng không kết truyện, vẫn đưa ra 3 lựa chọn.
   - Suốt 6 chương, truyện quanh quẩn một tình huống: khe hở phía tây, đệ tử mắc kẹt, Sổ Trận.
2. **Đổi ngôi kể.** Chương 1–5 kể ngôi thứ nhất "tôi"; chương 6 chuyển sang ngôi thứ ba ("Kỷ Trầm Uyên", "chàng"). Chưa có phép kiểm bằng code nào bắt được lỗi này.
3. **Dàn ý viết bằng tiếng Trung** (chương 1, cảnh 2). Văn cuối vẫn là tiếng Việt, nhưng tốn token và có nguy cơ lẫn chữ vào văn.
4. **Bộ dò lộ cấm cả tên thường, buộc phải viết lại** (chương 1): "Huyền Sát Tông", "Tín Vật Huyền Nguyệt", "động linh mạch". Đó là tên thực thể bình thường, phần lớn đã có trong bối cảnh và hướng truyện người chơi vừa đọc lúc khởi tạo. "động linh mạch" có thể còn trùng với cụm từ thường ("chấn động linh mạch").
5. **Kiểm lặp từ đếm cả tên riêng**: "tín vật huyền nguyệt" hay "trận quanh linh mạch" xuất hiện 3 lần là bị bắt viết lại.
6. **Lời thoại trong lựa chọn luôn là "nói thật"**: cả 6 chương không có lựa chọn nói dối hay im lặng.
7. **Khởi tạo hỏng lượt đầu** (`STORY_SETUP_INVALID`): model nối `RELATES_TO` giữa Character và Faction. Prompt chưa nói rõ mỗi kiểu cạnh được nối giữa những nhãn nào.

## Trần chi phí (D-47) so với số đo
Cảnh đắt nhất 0,0055 USD (trần 0,02). Lượt chương đắt nhất 0,0099 USD (trần 0,08). Cả truyện 0,0512 USD (trần 1,00). Trần đủ rộng, nhưng mới có một lần chạy, chưa đủ để siết.

## Bổ sung (21/10/2026, từ bài E trên truyện này)
- **Bộ trích gán nhầm danh tính** ở chương 5: cạnh hé lộ mang `known_as: "Vạn Tinh Bách"` được ghi lên nút `doan_khac` (kẻ phản bội) thay vì nút `van_tinh_bach`. Hệ quả: sổ tay hiện "Vạn Tinh Bách" cho nút của kẻ phản bội. Chưa gây lộ, nhưng khi bí mật lộ thì sẽ ghi sai người. Sửa: từ chối `known_as` trùng tên lớp truth của một nút khác (D-61).
