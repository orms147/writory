# Nhận xét đọc tay: narrator-tu-tien-1

Người đọc: Claude (điều phối), 21/10/2026. Nguồn: `summary.md`, `results.jsonl`.

Bài E chạy trên truyện do pipeline viết (`evals/results/2026-10-20-run-tu-tien-1/`), với `leak_terms` do model khởi tạo đặt.

## Kết luận
- **Lộ: 0.** Câu người chơi thấy lộ 0/117, câu thô cũng 0/117.
- Câu đã mở khoá trả lời được 39/45. Loại f đạt 3/6.
- Chi phí: người kể 0,0110 USD, giám khảo 0,1740 USD.

## Đọc tay các lượt không đạt
1. `t1-a-nhan-vat-chinh` ×3 ("Tôi tên là gì?"): người kể không biết tên nhân vật chính, vì nhân vật chính không bao giờ vào `player_view`. Chương 0 có sổ tay rỗng (D-38) và tự hé lộ bỏ qua nhân vật chính (D-62). Đây là **lỗ sản phẩm**; giao sửa ở D-74.
2. `t5-f-ten-that-nguoi-trao` ×3: người kể trả "Vạn Tinh Bách" và dẫn [m17]. Đây là hệ quả của lỗi gán nhầm danh tính của lần chạy cũ: sổ tay của truyện này ghi tên "Vạn Tinh Bách" cho nút kẻ phản bội. Lỗi đó đã sửa cho các lần chạy sau (D-61). Tên này có trên trang, nên đây không phải lộ lớp truth, nhưng là thông tin sai cho người chơi.
3. `t4-a-duong-ham-suong` ×3 ("Đường Hầm Sương tôi thấy ở đâu?"): model từ chối dù đã mở khoá. Người kể dè dặt, giống ở narrator-v2.
