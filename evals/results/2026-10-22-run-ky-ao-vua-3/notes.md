# Nhận xét đọc tay: ky-ao-vua-3

Người đọc: Claude, 22/10/2026. Nguồn: `report.json`, `truth_dump.json`, `chapters/`.

- Lệnh: `bench_run --label ky-ao-vua-3 --scenario evals/scenarios/story_run/ky-ao-vua.yaml --chapters 10 --seed 20261021 --budget 0.20`, đề `ky-ao-vua` v1 (cùng sha256 với lần 1 và 2), hash config trùng.
- Code ở commit `0418465` (D-84: `extract-4`, `setup-7`, `outline-6`, `writer-6`, mục "Bí mật đã lộ").
- Chi phí lần chạy này 0,0778 USD. Một lần chạy trước cùng lệnh chết giữa chừng ở chương 8 (tiến trình thoát mã 1, không có traceback, `meta.json` còn `running`): đã tốn khoảng 0,065 USD, không dùng kết quả, không đưa vào repo. Không rõ nguyên nhân; trên máy lúc đó có lần chạy của một nhánh khác (chưa kiểm xem có liên quan). Tổng chi cho hai lần: khoảng 0,143 USD.

**Không so thẳng được với lần 1 và 2.** Model khởi tạo dựng thế giới khác dù cùng seed (lần này: nhân vật Ninh Tố Hành, 5 mạch phải gỡ, 1 bí mật). Chỉ là chiều hướng, một lần chạy.

## Số đo (từ `report.json`, `truth_dump.json`)
| | ky-ao-vua-2 | ky-ao-vua-3 |
|---|---|---|
| Chương ghi được | 10/10 | 10/10 |
| Mạch phải gỡ gỡ đúng khoảng (`plan_vs_result`) | 3/4 (1 sớm) | 4/4, mạch còn lại chưa tới hạn (10–12) |
| Đọc tay: mạch gỡ thật và đúng khoảng | 2/4 | 4/4 |
| Gỡ giả hay gỡ sớm | 2 (1 chưa tới khoảng, 1 một phần) | 0 |
| `RESOLVED_IN` ghi được | 5, đều có câu trích | 4, đều có câu trích nguyên văn |
| Cạnh bị bỏ vì luật D-84 (gỡ chưa tới khoảng) | — | 0 |
| `overdue_thread` còn khi hiện | 0 | 0 |
| Viết lại | 4 | 3 |
| Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử | 0 | 0 |

- **Luật bỏ gỡ chưa tới khoảng (D-84) không bị kích hoạt lần này**, nên chưa có số đo thực tế về nó: bộ trích không ghi gỡ sớm. Nó chỉ được kiểm bằng test (`tests/unit/test_pipeline_extract.py`).
- Cạnh bộ trích bỏ (5): thiếu `known_as` ×3, sai schema ×2; không liên quan gỡ mạch.

## Đọc từng `RESOLVED_IN` (câu trích kiểm với `chapters/`)
1. **ch01 `tim_loi_qua_thap`** (hạn 1–3, "có tìm được lối qua các tháp nghiêng tới trạm canh kế tiếp không?"). Câu trích ch01:71 "Tôi đã tìm được đường tới trạm." Gỡ thật, đúng khoảng; câu liền sau nói việc qua trạm bằng lệnh nào còn bỏ ngỏ, đó là mạch khác.
2. **ch04 `giu_vat_khoi_tram`** (hạn 4–6). "Mảnh Thiên Khuyết còn nguyên bên trong, và tôi đã đưa nó qua khỏi Trạm Canh Sương mà không giao cho lính canh." Gỡ thật: cảnh qua rào chắn, kiểm niêm hộp.
3. **ch06 `lenh_nao_that`** (hạn 6–8). "Trong hai lệnh, đây là lệnh duy nhất đã được xác nhận hợp lệ." Gỡ thật: chấp sự xác nhận Lệnh Thứ Nhất, nói rõ chưa xác nhận lệnh kia. Chi tiết lệnh kia giả là ai làm thì ở bí mật (lộ ch07), không phải vế của mạch.
4. **ch08 `buoc_vao_dai_dien`** (hạn 8–10). "Khi qua ngưỡng, tôi nghe sau lưng vang lên tiếng cửa nặng nề khép dần." Gỡ thật (ch08:17 "Tôi bước vào"). Câu trích yếu hơn câu trả lời, nhưng nguyên văn và nằm đúng chỗ.

Không thấy gỡ một phần hay gỡ khi chưa tới khoảng. Cả 5 mô tả mạch lần này là một câu hỏi có/không, không ghép hai việc (lần 2 có "tìm... và xác định...", "ngăn... và tìm ra..."): có vẻ `setup-7` có tác dụng, nhưng một lần chạy chưa đủ kết luận. Chưa kiểm xem dạng câu hỏi có/không làm mạch dễ gỡ hơn hay lệch kiểu mạch.

## Lặp nhịp
- Bí mật đã lộ: Lý Vân Thư thú nhận làm giả Lệnh Gọi Thứ Hai ở ch07:35 (đúng khoảng 7–8). Các chương sau chỉ **phản ứng với điều đã biết**: ch08:17 "Lệnh Gọi Thứ Hai đã được ghi nhận là giả", ch08:27 "Ông không nhắc lại chuyện ai làm giả lệnh", ch08:59 hội nghị xét trách nhiệm người làm giả. Không có cảnh nào dựng lại lời thú nhận như lần 2 (Bạch Kinh Luân ch07, rồi ch08–10). Đây là cải thiện rõ so với lần 2, nhưng không tách được tác dụng của mục "Bí mật đã lộ" khỏi khác biệt do thế giới mới.
- Chương 7–10 cùng xoay quanh ngưỡng và Đại Điện Hàn Phong, một hội nghị (theo các dòng đã đọc). Chưa đọc kỹ ch09–ch10 để kết luận có giậm chân hay không. Mạch cuối (hạn 10–12) chưa gỡ ở chương 10.

## Chưa kiểm
- Chạy lại cùng thế giới với lần 1 hay 2 (setup luôn dựng thế giới khác), nhiều lần chạy.
- Chương 11–12 (kết truyện) và việc mạch cuối có gỡ đúng hạn không.
- Gỡ một phần mà câu trích có thật và đúng khoảng vẫn có thể lọt (code không đọc được nghĩa).
- Lỗi liền mạch trạng thái nơi chốn (cửa khoá hay mở) giữa các chương: không đọc kỹ lần này.
