# Đo lại khởi tạo `setup-11` (D-135), so với `setup-10`: kết quả

Người đọc: Claude và chủ dự án, 30/10/2026. Đo theo `expectations.md` (khai trước, không sửa). Commit `1cc8eacc1e0abca443fe5abea61ea9dee95d630b` (sạch), config `194e9aa655c67f9d1041f05b3735c87aa7051436e9217a9b5905778067497518`, model `openai/gpt-6-luna` (`reasoning: low`) cho vai `setup`, `prompt_versions.setup` = `setup-11`; cả năm `meta.json` khớp. Lệnh: đúng chuỗi ở `expectations.md` (năm đề, seed của đề, `--setup-only`, trần 0.018 cho ba đề ngắn, 0.023 cho hai đề dài), chạy nối tiếp 10:55–11:02. Năm thư mục `../2026-10-30-run-setup11-*`; số gộp ở `compare.json` (`aggregate.py`), heuristic ở `count_plans_after.txt`.

**Chi phí thật: 0.029883 USD** (không lời gọi nào chỉ có ước tính), dưới trần 0.100 USD.

## Số đo
| | setup-10 (5 lượt) | dự đoán setup-11 | setup-11 (5 lượt) |
|---|---|---|---|
| Mạch phải gỡ | 24 | cùng cỡ | 27 |
| Mạch có `answered_by` | — | — | 13/27 |
| Kế hoạch có liên kết | 4/5 (heuristic) | ≥ 4/5 | 5/5 |
| Lệch thô trước khi dời (`shifted`) | 5 cặp heuristic trong 4/5 kế hoạch | < 5 | 1 (1/5 kế hoạch) |
| Phải dời cả hạn (`shifted_end`) | 3 cặp heuristic nặng | ≤ 2 | 0 |
| Lệch sau khi dời | — | 0 | 0 |
| Lượt cần sửa D-54 | 2/5 | 1–3/5, `answered_by` ở ≤ 1 lượt | 3/5: `edges` ×1 (ab-tu-tien), `answered_by` ×2 ở **2 lượt** (hai đề dài) |
| Khởi tạo hỏng | 0 | 0 | 0 (không lượt nào phải "bấm thử lại") |
| Chi phí `setup` trung bình (USD) | 0.00527 | ≤ 0.0066 | 0.00598 |
| Token vào lần dựng đầu, trung bình | 4318.8 | +150 tới +250 | 4494.6 (+176) |
| Token ra lần dựng đầu, trung bình | 4905 | cùng cỡ | 5021.4 |
| Ngoại hình: "Trông" / mở trùng / trùng tóc (26 nhân vật) | 0 / 3 / 6 | cùng cỡ | 0 / 6 / 6 |

Lần dời duy nhất: ab-ky-ao, mạch "Trống Lễ đang ở đâu?" 1–2 → 2–2 (bí mật "Lê Vĩnh giấu Trống Lễ trong hốc đất bên Lối Lau" lộ 2–3); chỉ dời chương đầu, nhịp không đổi. Hai lượt sửa `answered_by` mỗi lượt tốn thêm một lần dựng (khoảng 9 100 token vào, 4 500 token ra, khoảng 0.003 USD), phần lớn của chênh chi phí so với `setup-10`.

## Luật quyết định
- **C0 hợp lệ: đạt.** Năm lượt thật, commit sạch của nhánh, `setup-11`, model như mốc.
- **C1 đúng code: đạt.** `mismatches` = 0 ở cả năm lượt.
- **C2 không làm hỏng khởi tạo: TRƯỢT.** Năm/năm khởi tạo xong, nhưng lỗi `answered_by` có ở 2/5 lượt (giới hạn khai trước: 1/5). Cả bốn lỗi cùng một kiểu: model ghi id một **fact thường** (không phải bí mật) mà đúng là câu trả lời của mạch:
  - long-tu-tien: "Kẻ giữ ấn vô diện thực sự là ai?" ← "Kỷ Vân Thương chính là kẻ mang danh kẻ giữ ấn vô diện…"; "Nghi thức củng cố phong ấn đòi hỏi cái giá nào?" ← "Nghi thức củng cố phong ấn cần một người tự nguyện từ bỏ linh căn."
  - long-ky-ao-hanh-trinh: "Ai tạo ra những vệt trượt hướng về Giếng Vọng?" ← "Những vệt trượt… được tạo bởi một tấm ván kéo…"; "Bản ghi nào chứng minh khoản nợ của đoàn xe bị ghi sai?" ← "Một bản sao của sổ giếng cũ có thể chứng minh…".

  Lượt sửa nào cũng sửa xong bằng cách để `answered_by` rỗng; không lượt nào đẩy fact đó thành bí mật (long-tu-tien đã có đủ 3 bí mật, mức tối đa). Hai đề dài có 7–9 mạch mà chỉ 3 bí mật, nên model muốn nối nhiều mạch hơn số bí mật.
- **C3 model dùng trường: đạt.** 5/5 kế hoạch có liên kết.
- **C4 liên kết đúng nghĩa (đọc tay): đạt, 12/13 (92%).** Không có dời oan (lần dời duy nhất nằm trên một liên kết đúng). Bảng đọc tay ở dưới. Kết quả nhạy với hai liên kết sát ranh giới (5 và 11): tính cả hai là sai thì còn 10/13 (77%), dưới ngưỡng. Hai cái đó được tính đúng theo luật khai trước ("cả câu hoặc phần quyết định").

**Kết luận theo luật khai trước: C2 trượt, nên chưa giữ `setup-11` như hiện tại; phải sửa trước khi gộp.** `expectations.md` để chủ dự án chọn một trong hai đường:
1. sửa đề (`setup-12`), rồi đo lại;
2. code tự bỏ id không phải bí mật khỏi `answered_by`, không tốn lượt sửa, như D-76.

Đọc được (chưa phải quyết định): fact thường không có khoảng lộ nên bỏ đi không mất gì cho việc dời. Đường 2 giữ được lượt sửa duy nhất (`retries.setup_repair` = 1) cho các lỗi khác; hai lượt sửa ở đây chỉ vì liên kết.

## Đọc tay liên kết (C4)
| # | Lượt | Mạch (khoảng gỡ) | Bí mật (khoảng lộ) | Đánh giá |
|---|---|---|---|---|
| 1 | ab-tu-tien | Yến Tàng còn sống hay đã chết? (3–4) | Yến Tàng còn sống, ẩn dưới mỏ Linh Nham (3–4) | đúng |
| 2 | ab-ky-ao | Trống Lễ đang ở đâu? (1–2 → 2–2) | Lê Vĩnh giấu Trống Lễ trong hốc đất bên Lối Lau (2–3) | đúng; dời chương đầu |
| 3 | ab-ky-ao | Ai đã giấu Trống Lễ? (3–4) | cùng bí mật trên (2–3) | đúng |
| 4 | ab-ky-ao | Vì sao Lê Vĩnh giấu Trống Lễ? (4–5) | Lê Vĩnh giấu trống vì lời thề buộc làng ở lại đầm (4–5) | đúng |
| 5 | ab-trinh-tham | Mai đang ở đâu khi câu chuyện khép lại? (5–6) | Mai rời khu tập thể, ở nhờ nhà người thân tại quê (5–5) | đúng (phần quyết định: nơi Mai ở); sát ranh giới |
| 6 | ab-trinh-tham | Vì sao Mai rời khu tập thể? (5–5) | cùng bí mật trên (5–5) | đúng |
| 7 | ab-trinh-tham | Ai đã sửa các phiếu lĩnh? (4–4) | Trần Quang Hòa đã sửa phiếu lĩnh (4–4) | đúng |
| 8 | long-tu-tien | Đoàn sứ giả có tìm được đường qua Miên Đạo Thạch không? (6–10) | Tào Linh Âm là người duy nhất còn làm được nghi thức mở Miên Đạo Thạch (6–10) | **sai**: bí mật là điều kiện, không trả lời "có qua được không"; không hại (khoảng trùng nhau, không dời) |
| 9 | long-tu-tien | Ai đã ra lệnh phục kích đoàn sứ giả? (14–18) | Kỷ Vân Thương cho người phá cuộc phục kích… (14–18) | đúng |
| 10 | long-tu-tien | Vì sao Dương Khánh Vũ để lộ lộ trình? (18–21) | Dương Khánh Vũ để lộ lộ trình vì tin sẽ ngăn Kỷ thị tấn công phong ấn (18–21) | đúng |
| 11 | long-ky-ao-hanh-trinh | Lan đã đi đâu sau khi rời đoàn xe? (4–6) | Lan rời đoàn xe bằng lối kín dưới Giếng Vọng (4–6) | đúng (phần quyết định: lối đi); sát ranh giới |
| 12 | long-ky-ao-hanh-trinh | Túi khóa kín chứa thứ gì? (9–12) | Túi chứa bản sao sổ giếng cũ (9–11) | đúng |
| 13 | long-ky-ao-hanh-trinh | Ai đã dùng bản ghi nợ giả để kích động tranh chấp? (15–18) | Người thu phí đã dùng bản ghi nợ giả (15–17) | đúng |

## Liên kết sót
`count_plans.py` (H1/H2) bắt được 15 cặp trên năm kế hoạch `setup-11`. Không cặp nào còn lệch, và 9 trùng với liên kết đã khai. Đọc tay sáu cặp heuristic không có trong `answered_by`: không cặp nào là liên kết sót. Bí mật trong các cặp đó hoặc là tiền đề chứ không phải câu trả lời ("Vì sao Lê Vĩnh giấu trống?" với bí mật "Lê Vĩnh giấu trống ở đâu"), hoặc nói về một chuyện khác (quyết định, kết cục sau đó). Cả sáu mạch đều đã bắt đầu sau khoảng lộ. Có một chỗ đáng ghi về kế hoạch, không phải về liên kết: ở long-tu-tien, danh tính kẻ giữ ấn vô diện là một fact thường, không phải bí mật, nên bộ dò lộ không giữ nó (xem C2).

## Theo dõi (không phải luật)
- **Mở trùng của ngoại hình** 6 so với 3 (26 nhân vật cả hai bên). Phần đề thêm không đụng tới mục ngoại hình. Mẫu nhỏ, chưa phân biệt được với nhiễu; "Trông" vẫn 0, trùng tóc vẫn 6.
- **Chi phí** 0.00598 so với 0.00527 USD/lượt (+13%), dưới ngưỡng "xem lại" 1.5 lần; chênh lệch chủ yếu đến từ hai lượt sửa `answered_by`.
- **Lệch thô** giảm rõ khi đề nêu luật (1 lần dời so với 5 cặp heuristic lệch ở `setup-10`). Hai thước không cùng nhau (heuristic đoán, `shifted` dùng liên kết khai) nên đây chỉ là chiều hướng.

## Chưa kiểm
- Mẫu 5 lượt, một seed mỗi đề. 2/5 lượt có lỗi `answered_by` nằm sát ngưỡng khai trước (1/5); cả hai ở đề dài, nơi số mạch vượt xa số bí mật.
- Chưa đo khoảng gỡ đã dời có làm dàn ý bớt giục gỡ mạch trước khi bí mật lộ không (chỉ có một lần dời ở đây).
- Đánh giá C4 do một người đọc (Claude); hai liên kết sát ranh giới quyết định đạt hay trượt.

## Sau quyết định chủ dự án (30/10/2026): bỏ id fact thường bằng code, đánh giá bằng phát lại
Phần trên giữ nguyên: **C2 trượt trên `setup-11` như đã chạy.** Chủ dự án chọn đường 2. Ở bước dựng, code bỏ khỏi `answered_by` của mạch phải gỡ những id là fact đã khai mà không phải bí mật, trước mọi phép kiểm, không tốn lượt sửa (`setup.drop_plain_fact_answers`, như D-76). Id không phải fact nào vẫn đi lượt sửa (lý do ở D-135). Report có thêm `thread_answers.dropped`; các cặp (mạch, fact) có id ở `truth_dump.json` (`answers_dropped`). Đề vẫn là `setup-11`, chữ không đổi.

Cách sửa này **chỉ được kiểm bằng phát lại, không gọi model** (`replay_drop.py`, đầu ra `replay_drop.txt`: code `24f62cf` trước khi sửa, `a248b42` sau khi sửa). Câu trả lời thô của lần dựng đầu **không được lưu**: `calls.jsonl` không có thân, không có `rejected.jsonl`, đề lượt sửa không lưu. Vì vậy script dựng lại:
- **Câu trả lời đã nhận:** kế hoạch + gói chương 0 đổi ngược về dạng đầu ra model, lấy lại khoảng gỡ trước khi dời. Đi qua code thì ra **đúng** kế hoạch và gói đã lưu ở cả năm lượt, nên phép dựng lại là trung thực.
- **Lần dựng đầu:** câu trả lời đã nhận cộng các id `answered_by` mà danh sách lỗi của lượt sửa nêu tên. Danh sách đó là đủ: lỗi `answered_by` chỉ được kiểm khi kế hoạch và gói đã qua pydantic, nên mọi lỗi quy tắc khác của lần dựng đầu cũng có trong danh sách. Trên code trước khi sửa, lần dựng đầu dựng lại ra **đúng từng chữ** danh sách lỗi đã ghi ở hai lượt.

| Lượt | Lượt sửa đã chạy | Code mới |
|---|---|---|
| ab-tu-tien | 1 (`edges`) | không đổi: lỗi không dính `answered_by`, vẫn cần lượt sửa |
| ab-ky-ao | 0 | không đổi |
| ab-trinh-tham | 0 | không đổi |
| long-tu-tien | 1 (`answered_by` ×2) | **tránh được**: bỏ 2 id fact thường, không còn lỗi |
| long-ky-ao-hanh-trinh | 1 (`answered_by` ×2) | **tránh được**: bỏ 2 id fact thường, không còn lỗi |

Ở cả hai lượt tránh được, kế hoạch và gói mà code mới nhận từ lần dựng đầu dựng lại giống hệt bản đã lưu (cùng liên kết bí mật, cùng khoảng, không lần dời nào).

Đọc được, có giới hạn:
- Lượt cần sửa vì `answered_by` từ 2/5 xuống 0/5; lượt cần sửa nói chung từ 3/5 xuống 1/5 (còn lỗi `edges` của ab-tu-tien). Chi phí tránh được khoảng 0.003 USD mỗi lượt sửa (lần dựng thứ hai: khoảng 9 100 token vào, 4 500 token ra).
- "Kế hoạch cuối không đổi" chỉ đúng **với lần dựng đầu dựng lại**. Lần dựng đầu thật có thể khác câu trả lời đã nhận ở chỗ khác, vì lượt sửa viết lại cả câu trả lời: token ra của lần dựng đầu là 5880 và 6016, của lượt sửa là 4550 và 4502. Điều chắc chắn là lần dựng đầu thật không có lỗi quy tắc nào khác, nên code mới nhận nó ngay mà không cần lượt sửa. Nó có giống hệt bản đã lưu không thì không biết.
- Chưa đo lại bằng model thật. Muốn có số thật thì phải chạy lại năm lượt (khoảng 0.03 USD) với luật khai trước mới.
