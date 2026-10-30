# Bản kế hoạch: mạch được gỡ trước khoảng lộ của bí mật cùng nội dung (đếm, không gọi model)

Phát hiện khi dựng đề dàn ý ch8 tu-tiên (`../2026-10-30-outline-next-milestone/expectations.md`, arm C): mạch `thread_lap_truong_su_gia` ("Ninh Tuyết Anh thật sự đại diện cho phe nào?") có hạn gỡ ch7–13, còn bí mật `fact_su_gia_that`, cùng nội dung, chỉ lộ từ ch11. Kế hoạch tự cho phép gỡ mạch trước khi được lộ đáp án.

`count_plans.py` đếm trên mọi kế hoạch đã lưu trong `evals/results/*/truth_dump.json` (mỗi kế hoạch khác nhau đếm một lần); đầu ra `count_plans.txt`. "Gắn nhau" đoán bằng code (H1: chữ của mạch và bí mật trùng nhiều; H2: cùng thực thể), nên là ước lượng thô, có thể đếm thừa hay sót.

- Kế hoạch có mạch phải gỡ kèm khoảng gỡ và bí mật: 34.
- Có ít nhất một cặp mạch–bí mật gắn nhau: 28.
- Có ít nhất một cặp mạch **bắt đầu** được gỡ trước khoảng lộ của bí mật: 22.
- Có ít nhất một cặp mạch phải gỡ **xong** trước khoảng lộ của bí mật (không thể đúng cả hai): 8.

**Đề xuất (chưa làm):** kiểm bằng code ở bước dựng kế hoạch (`pipeline/story_plan.py`): mạch gắn với bí mật (khai bằng id trong kế hoạch, không đoán bằng chữ) không được có hạn gỡ bắt đầu trước khoảng lộ của bí mật; sai thì sửa khoảng gỡ của mạch về sau khoảng lộ (hay trả về lượt sửa của khởi tạo). Muốn làm phải đổi đề khởi tạo để model khai liên kết mạch–bí mật, tức đo lại khởi tạo (D-54). Phép đo dàn ý cùng thư mục cho thấy riêng mạch lệch khoảng không đẩy dàn ý ch8 tới bí mật, nên đây là sửa tính nhất quán của kế hoạch, chưa có bằng chứng nó gây lộ sớm.
