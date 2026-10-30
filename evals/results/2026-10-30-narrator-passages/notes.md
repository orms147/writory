# Kết quả: người kể đọc đoạn trên trang, `narrator-3` so với `narrator-4` (D-143)

Người đọc: Claude (nhánh `feature/narrator-page-passages`), 31/10/2026. Luật và lệnh: `expectations.md`, mục
"Bổ sung trước khi chạy" (khai trong commit `0d91050`, trước mọi lời gọi). Áp luật bằng code: `apply_rules.py`, kết
quả ở `rules_applied_muse.json` và `rules_applied_luna.json`.

## Chạy gì
- Commit chạy: `f431a6f` (nhánh này, đã gộp `main` d1464e3: client Anthropic D-145, G6 vòng hai D-141; không chạm
  code người kể, `config/` hay `evals/config/meta/`), cây sạch (`dirty: false` trong mọi `meta.json`).
- Lượt chính: `meta/muse-wonder-1.0`, suy luận `low`, `--config-dir ../evals/config/meta` (hash config trong
  `meta.json`: models `210914ccaade`, limits `376e09a93349`). Xác nhận: `openai/gpt-6-luna`, suy luận `low`, config
  mặc định (models `1b7c267c3cae`, limits `90c0b92c39bc`). `narrator_pages` như nhau ở cả hai (4 đoạn, 500, 3600, 1).
- Đúng năm lệnh đã khai, đúng thứ tự, không lệnh nào dừng sớm, không lỗi, không thử lại bằng tay:

| Lệnh | Thư mục kết quả | Lời gọi | Chi phí thật | Trần |
|---|---|---|---|---|
| Muse, bài E tu-tien-1 × 1 | `2026-10-30-narrator-passages-muse-tu-tien-1/` | 39 | 0,4231 USD | 2,00 |
| Muse, bài E v2 × 1 | `2026-10-30-narrator-passages-muse-v2/` | 108 | 0,9874 USD | 5,00 |
| Muse, bài A đề chính, hai hệ × 2 | `2026-10-30-memory-narrator-passages-muse/` | 156 | 1,7419 USD | 8,00 |
| **Muse, cộng** | | **303** | **3,1524 USD** | **15,00** |
| Luna, bài E tu-tien-1 × 1 | `2026-10-31-narrator-passages-luna-tu-tien-1/` | 39 | 0,0113 USD | 0,05 |
| Luna, bài A đề chính, hai hệ × 1 | `2026-10-31-memory-narrator-passages-luna/` | 78 | 0,0330 USD | 0,10 |
| **Luna, cộng** | | **117** | **0,0443 USD** | **0,15** |

Chi phí thật bằng khoảng một phần tư ước tính thô (11,8 USD): mỗi lời gọi Muse ở bài E tu-tien-1 tốn trung bình
khoảng 2 860 token vào, 220 token ra, trong đó 180 token suy luận (`results.jsonl`).

## Kết luận theo luật khai trước
**Giữ `narrator-4` bật mặc định.** Lượt chính đạt cả bốn luật, xác nhận Luna đạt.

| Luật (lượt chính, Muse) | Ngưỡng | Kết quả | Đạt |
|---|---|---|---|
| 1. Đúng tổng `narrator_pages` hơn `narrator` | từ 8 lượt (10 điểm trên 78) | 52 so với 30, hơn 22 lượt (67% [56–76] so với 38% [28–50]) | có |
| 2. Sai không kiêng của `narrator_pages` không hơn `narrator` quá | 7 lượt | 7 so với 1, hơn 6 lượt | có, sát ngưỡng |
| 3. Lộ ngoài trang của `narrator_pages` | 0 | 0 | có |
| 4. Bài E, lộ ở câu cuối | 0 trên cả hai đề | 0 (tu-tien-1), 0 (v2); lộ câu thô cũng 0 | có |

| Xác nhận (Luna) | Ngưỡng | Kết quả | Đạt |
|---|---|---|---|
| Đúng tổng `narrator_pages` hơn `narrator` | từ 2 lượt (5 điểm trên 39) | 27 so với 13, hơn 14 lượt (69% so với 33%) | có |
| Lộ ngoài trang của `narrator_pages` | 0 | 0 | có |
| Bài E tu-tien-1, lộ ở câu cuối | 0 | 0 | có |

Luật 2 không thuộc luật xác nhận; `rules_applied_luna.json` chạy nó với ngưỡng 999 nên luôn "đạt" (Luna: 0 so với 0).

## Đọc thêm (không phải cổng)
- **Chênh nằm ở câu đồ thị thiếu, như mong đợi.** Muse, câu đồ thị bộ trích thiếu hoặc sai: 82% (23/28) so với 25%
  (7/28); câu đồ thị có đáp án: 58% (29/50) so với 46% (23/50). Luna cùng chiều: 86% (12/14) so với 21% (3/14).
  Theo khoảng cách, câu cách từ 3 chương trở lên: Muse 82% (36/44) so với 36% (16/44). Theo nhóm, `narrator_pages`
  hơn ở cả bốn nhóm (đồ vật 11/22 so với 6/22, sống–chết 8/10 so với 4/10, ai biết gì 24/32 so với 14/32, quan hệ
  9/14 so với 6/14; nhóm nhỏ, chỉ mô tả).
- **Kiêng giảm mạnh:** Muse 19 so với 47 lượt "Bạn chưa biết điều này."; mọi lượt kiêng là model tự trả
  `known = false`. Không lượt nào bị bộ dò lộ, mã mục hay lưới úp mở chặn, ở cả hai hệ và cả năm lệnh.
- **Đọc tay 7 lượt sai của `narrator_pages` (Muse):**
  - 3 lượt là cách chấm văn xuôi, nội dung đúng: `item-10` × 2 (câu trả lời đúng người giữ thẻ, nhưng có nhắc
    "không giao thẻ cho Trần Mặc", bộ chấm thực thể đếm thêm Trần Mặc; `narrator` cũng sai câu này 1 lần vì cùng lý
    do) và `rel-07` lần 1 (đúng người đi cùng, nhắc thêm "Huyền Kính").
  - 4 lượt sai thật: `item-06` × 2 ("Không", đáp án Có; chính câu mà hệ lai đồ thị + đoạn của bài A cũng sai 3/3 ở
    `2026-10-22-memory-ky-ao-vua-1-facts-s3`, đoạn kéo về có hai đoạn chương 10) và `rel-06` × 2 ("Không", đáp án Có;
    câu cần nối "Nàng không cản" với "Chúng tôi trở về nền chợ").
  - Không lượt câu có/không nào chấm `parsed: null`: Muse và Luna đều mở câu có/không bằng "Có"/"Không".
- **Lộ theo bộ chấm chặt, đều có trên trang đã đọc:** 6 lượt bài A Muse (5 `narrator_pages`, 1 `narrator`) và 1 lượt
  Luna trúng "Vùng Đá Trôi" hay "Đèn Lưu Quang": tên nơi và vật trang đã nói, bộ trích chưa ghi vào `player_view`; 4
  lượt Muse là nhắc lại chữ của câu hỏi. Mọi lượt đó chấm đúng. Không lượt nào trúng chuỗi ngoài trang.
- **Bài E:** loại a Muse 14/15 (tu-tien-1) và 33/35 (v2), Luna 15/15; loại b–e đúng "Bạn chưa biết điều này." mọi
  lượt. Loại f của tu-tien-1 (hỏi tên thật người trao tín vật): Muse trả lời 2/2, Luna 1/2, đều bằng tên "Vạn Tinh
  Bách" mà chương 5 viết thẳng ("Vạn Tinh Bách đã trao nó cho tôi") và sổ tay đã có (mục `m17`); bộ chấm không thấy
  lộ, vì tên thật bị giấu là của nút khác (ghi chú đầu `plan-tu-tien-1.yaml`). Không phải cổng.
- **Cỡ context:** đoạn trung bình mỗi lời gọi 5,9 (bài A) và 5,3–5,5 (bài E), tính cả đoạn kế.

## Chưa kiểm
- Một truyện dài, một lần phát lại bộ trích, 39 câu; các lần hỏi cùng câu không độc lập nên khoảng Wilson trên lượt
  hẹp hơn thật. Luật 2 đạt sát ngưỡng (hơn 6 trên 7 cho phép); 3 trong 7 lượt sai là cách chấm.
- Không đo kiểm duyệt câu trả lời và trần số câu (bài đo không qua hai lớp đó), không có giám khảo cho `narrator-4`.
- Số `narrator_pages` vẫn là số tạm chờ chủ dự án duyệt; chưa thử số khác bằng model thật.
