# Nhận xét đọc tay: ky-ao-vua-1

Người đọc: Claude (điều phối), 21/10/2026. Đề `ky-ao-vua` (Truyện vừa, kỳ ảo phương Đông, tên Hán Việt), `--chapters 10`, kế hoạch 12 chương. Chi phí 0,0972 USD, khoảng 0,01 USD mỗi chương.

## Mốc tuần 2
**Chạy liền 10 chương từ dòng lệnh: đạt** (design §12).
- 10/10 chương ghi được, không cảnh nào bị chặn.
- Khởi tạo qua ngay lượt đầu, không cần lượt sửa (D-54, D-76 có tác dụng).
- Tóm tắt chương tạo 10/10, không lỗi.
- Mọi chương kể ngôi thứ nhất "tôi", không lẫn chữ Hán.

## Kế hoạch so với kết quả (tính tới chương 10/12)
- **Bí mật lộ đúng khoảng 2/2** (chương 6 và 8).
- **Mạch gỡ đúng hạn chỉ 1/5.**
  - mạch 3 gỡ trễ (hạn 4–8, gỡ ở 10);
  - mạch 1 (hạn 2–6) và mạch 4 (hạn 6–10) chưa gỡ, đã quá hạn;
  - mạch 5 chưa tới hạn.
- Người canh báo `overdue_thread` 17 lần, 8 lần còn lại khi hiện, vì lượt viết lại không sửa được. Còn 5 lần `teller_does_not_know` khi hiện.
- Chưa kiểm: văn có gỡ mạch mà bộ trích không ghi `RESOLVED_IN`, hay văn thật sự không gỡ. Cần đọc chương 6–10 so với `truth_dump.json`.

## Việc tiếp
- Gỡ mạch là điểm yếu ở truyện dài. Có hai hướng:
  - khi mạch đến hạn, dàn ý bắt buộc có một nhịp gỡ mạch đó, kiểm bằng code;
  - bộ trích được nhắc riêng về `RESOLVED_IN` của các mạch đang đến hạn.
- Truyện này là truyện dài đầu tiên. Dùng nó để đo bài A trên truyện do pipeline viết.
