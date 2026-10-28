# Nhánh B: đề viết cũ so với v3 (D-109, D-110) trên 3 thế giới, GPT-6 Luna

Người đọc: Claude (nhánh eval/ab-baseline) và chủ dự án, 29/10/2026. Nguồn: `report.json`, `results.jsonl`, `key.json` của các thư mục dưới đây. Script: `ab_v3_analyze.py` (`python ab_v3_analyze.py <gốc repo>`, đầu ra đã lưu ở `analyze_output.txt`), số đo bằng code: `prose_metrics.jsonl` (từ `../2026-10-28-ab-baseline/prose_metrics.py`). Nhiễu và ngưỡng: `../2026-10-28-ab-baseline/notes.md`. Luật quyết định đã khai và commit trước khi chấm: `docs/eval.md`, mục "Luật quyết định cũ/v3" (a478343).

## Chạy gì
Ba thế giới `evals/scenarios/story_run/ab-*.yaml`, cùng thư mục khởi tạo `evals/results/2026-10-28-run-ab-<thế giới>-setup/` cho cả hai nhánh. Mỗi thế giới hai lượt viết v3 (`--style-guide style_guide_vi_v3.md --prompt-variant v3 --prose-v3`, `--chapters 6`, trần `--budget` 0,15): `evals/results/2026-10-29-run-ab-<thế giới>-v3-{1,2}`. Cặp i ghép `…-28-run-ab-<thế giới>-cu-i` (nhánh baseline) với `…-29-run-ab-<thế giới>-v3-i`. Chạy tuần tự một chuỗi từ 00:09 đến 01:16 ngày 29/10, chấm 01:17 đến 01:30 cùng ngày: không chạy qua nửa đêm, mọi thư mục mang ngày 29. 12 thư mục chấm `evals/results/2026-10-29-ab-<thế giới>-pair{1,2}-{sonnet,muse}/` (Sonnet: solo và compare hai thứ tự; Muse: chỉ solo), mỗi truyện chấm một lần, nhãn mù.

Cả 6 lượt viết v3 ghi đủ 6/6 chương. Tu tiên và trinh thám kết truyện; kỳ ảo dân gian có kế hoạch 7 chương nên chưa kết (như hai lượt cũ).

## Điểm trung bình solo (7 tiêu chí), cũ → v3, theo cặp
| thế giới | cặp | Sonnet cũ | Sonnet v3 | chênh | Muse cũ | Muse v3 | chênh |
|---|---|---|---|---|---|---|---|
| tu tiên | 1 | 2,571 | 3,000 | +0,429 | 2,571 | 3,000 | +0,429 |
| tu tiên | 2 | 3,000 | 2,714 | −0,286 | 2,857 | 2,571 | −0,286 |
| kỳ ảo dân gian | 1 | 3,000 | 3,143 | +0,143 | 3,143 | 3,286 | +0,143 |
| kỳ ảo dân gian | 2 | 3,143 | 3,429 | +0,286 | 3,571 | 3,571 | 0,000 |
| trinh thám | 1 | 2,857 | 2,857 | 0,000 | 2,571 | 3,143 | +0,571 |
| trinh thám | 2 | 2,857 | 2,857 | 0,000 | 3,000 | 3,571 | +0,571 |

Lưu ý: điểm "cũ" ở đây là điểm của truyện cũ trong chính lần chấm cặp (một lần chấm mới), không phải điểm trong lần chấm baseline; hai lần chấm cùng một văn khác nhau cỡ σ_chấm (0,08 Sonnet, 0,12 Muse).

## Theo luật đã khai
| | chênh (trung bình 6 cặp, v3 − cũ) | ngưỡng T | đạt |
|---|---|---|---|
| Sonnet | **+0,095** | +0,50 | không |
| Muse | **+0,238** | +0,71 | không |

Điều kiện (3), tiêu chí tụt quá 1 điểm (trung bình thế giới) ở ≥ 2 thế giới: không có tiêu chí nào, ở cả hai giám khảo (chênh thế giới thấp nhất: Sonnet liền mạch trinh thám −1,0, đúng ở biên chứ không quá). v3 cũng không thua (cần ≤ −0,50 và ≤ −0,71).

**Kết luận theo luật: CHƯA PHÂN BIỆT ĐƯỢC.** Chiều của chênh là dương ở cả hai giám khảo (Sonnet 3 cặp dương, 2 bằng, 1 âm; Muse 4 dương, 1 bằng, 1 âm), nhưng nhỏ hơn nhiều so với ngưỡng. Con số này không nói v3 không hơn; nó nói thiết kế 3 thế giới × 2 cặp với nhiễu đo được không đủ sức nhận ra chênh dưới 0,5 (Sonnet) hay 0,7 (Muse).

Theo tiêu chí (chênh trung bình thế giới, v3 − cũ; chi tiết ở `analyze_output.txt`): cả hai giám khảo chỉ đồng chiều dương ở **nhịp đẩy truyện** (Sonnet +0,5 ở cả 3 thế giới; Muse +0,5, 0, +1,5) và **lựa chọn có ý nghĩa** (Sonnet +0,5, 0, +0,5; Muse +0,5, +1,5, +1,0); tiếng Việt tự nhiên không đổi ở cả hai; **lỗi** nhỉnh âm ở cả hai (Sonnet −0,5 trinh thám; Muse −0,5 tu tiên và kỳ ảo). Nhịp và lựa chọn là hai tiêu chí gần nhất với cái D-110 nhắm tới (chương không mốc kết bằng chờ, câu mở lặp, tính cách NPC), nhưng đây là suy đoán của tôi; 3 thế giới cho từng tiêu chí là quá ít để khẳng định.

## So sánh trực tiếp của Sonnet (chỉ báo cáo, không vào luật)
| thế giới | cặp | thứ tự cũ/v3 → nhất | thứ tự v3/cũ → nhất | đọc |
|---|---|---|---|---|
| tu tiên | 1 | cũ | cũ | cũ nhất (ổn định theo vị trí) |
| tu tiên | 2 | cũ | cũ | cũ nhất |
| kỳ ảo | 1 | cũ | cũ | cũ nhất |
| kỳ ảo | 2 | cũ | cũ | cũ nhất |
| trinh thám | 1 | v3 | v3 | v3 nhất |
| trinh thám | 2 | v3 | cũ | đảo theo vị trí |
Cũ nhất ở 4/6 cặp (cả hai thứ tự), v3 nhất ở 1/6, 1 cặp đảo theo vị trí. Chiều này NGƯỢC với điểm solo (solo: v3 ≥ cũ ở 5/6 cặp). Như baseline đã thấy, solo và compare của cùng giám khảo không nhất quán ở chất lượng ngang nhau; không dùng compare để phán.

## Số đo bằng code (cùng định nghĩa cả hai nhánh)
| lượt | kết đứng yên | cặp mở trùng | bộ "chờ" | USD/chương | viết lại |
|---|---|---|---|---|---|
| tu-tien-cu-1 | 2/5 | 0 | 1/5 | 0,00984 | 4 |
| tu-tien-cu-2 | 5/5 | 0 | 2/5 | 0,01046 | 5 |
| tu-tien-v3-1 | 1/5 | 0 | 0/5 | 0,01045 | 5 |
| tu-tien-v3-2 | 0/5 | 0 | 1/5 | 0,01058 | 5 |
| ky-ao-cu-1 | 0/5 | 0 | 0/6 | 0,00807 | 2 |
| ky-ao-cu-2 | 0/5 | 0 | 0/6 | 0,00789 | 2 |
| ky-ao-v3-1 | 0/5 | 0 | 2/6 | 0,00907 | 3 |
| ky-ao-v3-2 | 0/5 | 0 | 0/6 | 0,00786 | 0 |
| trinh-tham-cu-1 | 2/5 | 0 | 0/5 | 0,00792 | 2 |
| trinh-tham-cu-2 | 3/5 | 0 | 0/5 | 0,00885 | 4 |
| trinh-tham-v3-1 | 2/5 | 0 | 0/5 | 0,00821 | 2 |
| trinh-tham-v3-2 | 1/5 | 0 | 0/5 | 0,00821 | 2 |
Gộp theo nhánh: chương kết đứng yên **12/30 (cũ) → 4/30 (v3)**; bộ lựa chọn "chờ" 3/32 → 3/32 (không đổi; proxy yếu, độ phủ 3/5 khi hiệu chuẩn); cặp mở trùng 0 → 0 (không có chỗ để cải thiện); chi phí mỗi chương 0,00884 → 0,00906 (+2,5%, trong biên dao động của baseline); viết lại 19 → 17. Giảm kết đứng yên là số đo bằng code duy nhất tách rõ giữa hai nhánh, nhưng baseline cho thấy chỉ số này nhiễu mạnh giữa hai lần viết cùng cấu hình (tu tiên 2/5 so với 5/5) nên 12/30 so với 4/30 vẫn cần thêm lần lặp; nó không vào luật.

## Hai đoạn mẫu (cùng thế giới, cùng chương 3, lượt 1 mỗi nhánh)
Cùng khởi tạo nên cùng thế giới và nhân vật, nhưng truyện rẽ nhánh từ chương 1 (câu mở khác hẳn), nên đây không phải cùng một cảnh viết hai lần; chỉ cùng vị trí trong truyện. Đoạn cuối chương 3, tu tiên:
- Cũ (`2026-10-28-run-ab-tu-tien-cu-1/chapters/ch03.md`): "Thanh Nghi vẫn giữ cánh cửa. Mảnh phù văn nằm trong khe đá, những nét khắc nối với mạch luyện còn âm ấm. Hai sứ giả đứng ngoài gian lò, đã thấy cùng một chứng cứ; không ai chịu rời khỏi ngưỡng cửa."
- v3 (`2026-10-29-run-ab-tu-tien-v3-1/chapters/ch03.md`): "Mảnh phù văn nằm giữa hai người. Một bên đòi kiểm chứng, bên kia đòi quyền tiếp cận. Thanh Nghi khép tay quanh chiếc chìa khóa, còn hai sứ giả cùng tiến gần chiếc bàn."

Đoạn cuối chương 3, trinh thám:
- Cũ (`2026-10-28-run-ab-trinh-tham-cu-1/chapters/ch03.md`): "Anh Bình quay người xuống cầu thang để báo lại với công an khu vực."
- v3 (`2026-10-29-run-ab-trinh-tham-v3-1/chapters/ch03.md`): "Anh Bình gật một cái. Lâm vẫn đứng trên bậc chiếu nghỉ, nhưng lúc anh Bình gọi công an khu vực, anh ta đã không còn đường lảng sang chuyện khác."

Đọc tay (suy luận của tôi, không phải số đo): ở tu tiên, bản cũ kết bằng "không ai chịu rời khỏi ngưỡng cửa", đúng kiểu tranh đứng yên mà số đo bắt; bản v3 kết bằng một chuyển động ("cùng tiến gần chiếc bàn"). Ở trinh thám, cả hai đều kết bằng việc gọi công an; bản v3 có thêm một hệ quả cho nhân vật (Lâm hết đường lảng), bản cũ chỉ là một động tác. Hai đoạn chọn theo quy tắc cố định (đoạn cuối ch03 của lượt 1, tu tiên và trinh thám), không chọn đoạn đẹp nhất của v3; không đại diện cho cả 6 lượt. Hai bản cũng khác nhau ở nội dung vì truyện đã rẽ nhánh, nên so hai đoạn này chỉ để thấy kiểu kết, không so chất lượng văn.

## Chi phí
OpenRouter nhánh B: 6 lượt viết v3 tổng 0,3263 USD (0,0472 đến 0,0635 mỗi lượt, trần 0,15 mỗi lượt, tổng 1,0); cộng nhánh A (0,3302) là 0,6565 USD. Anthropic (Sonnet): 2,0154 USD cho 6 thư mục `judge` (solo và compare hai thứ tự), trần 3 của nhánh B; cộng nhánh A (1,0388) là 3,0542 USD, tức tổng hai nhánh vượt 3 nhưng mỗi nhánh nằm trong trần được giao riêng. Meta (Muse): 1,1595 USD cho 6 thư mục solo, trần 3; cộng nhánh A (1,6386) là 2,7981 USD. Không có đơn vị chấm nào hỏng ở nhánh B.

## Chưa kiểm
- σ lấy từ 3 bậc tự do nên ngưỡng 0,50 và 0,71 rất rộng cả hai chiều; "chưa phân biệt được" có thể là v3 thật sự hơn một ít.
- Mỗi cặp ghép cu-i với v3-i, và cu-2 cao hơn cu-1 ở baseline: nếu đó là hiệu ứng thật thì cặp 1 có lợi cho v3 và cặp 2 bất lợi, nhưng trung bình 6 cặp triệt phần này.
- Điểm "cũ" trong lần chấm cặp khác điểm của cùng truyện ở baseline (chấm lại; ví dụ tu tiên cu-1 Sonnet 2,714 so với 2,571, Muse 2,429 so với 2,571), phù hợp với nhiễu chấm.
- Một mô hình viết (Luna), ba thể loại, tên Việt và Hán Việt chưa tách riêng; v3 thay cả hướng dẫn văn, biến thể prompt và `--prose-v3`, nên không biết phần nào mang chênh.
- Chưa đọc tay toàn bộ 12 truyện; hai đoạn mẫu ở trên là toàn bộ đọc tay.
