# Nhiễu của giám khảo bài F: chấm lại 3 lần cùng hai truyện bằng Sonnet và bằng Muse

Người đọc: Claude (nhánh eval/judge-noise), 28/10/2026. Nguồn: `results.jsonl` của 6 thư mục: lần 1 (đã có) `../2026-10-22-model-bakeoff-1/` (Sonnet) và `../2026-10-28-model-bakeoff-muse-1/` (Muse); lần 2 và 3 là `2026-10-28-judge-noise-{sonnet,muse}-{2,3}`. Notes này là của cả bốn thư mục mới; ba thư mục kia chỉ trỏ về đây. Phân tích: `noise_analyze.py` (cùng thư mục này): `python noise_analyze.py <gốc repo> 2026-10-28`.

Phép đo: cùng hai truyện (DeepSeek V4 Flash và GPT-6 Luna, `run-bakeoff-*`), cùng seed `20261022` và cùng thứ tự `--run` nên cùng nhãn và cùng `story_sha256`; mỗi giám khảo chấm lại 2 lần, chỉ bước `judge` (4 lượt: solo ×2, compare ×2 thứ tự đảo), không `value`. Cấu hình y hệt lần 1 (`judge.yaml` version 3, Sonnet `effort: high`, Muse `effort: high`, `max_tokens` 20000). Không lỗi, không thử lại, không `errors.jsonl`. Chi phí lần 2 và 3: Sonnet 0,3771 và 0,3511 USD (tổng 0,7282, trần 1,5); Muse 0,5022 và 0,2893 USD (tổng 0,7915, trần 2). **Đo nhiễu của giám khảo (chấm lại cùng văn), KHÔNG đo nhiễu của lần viết** (hai lần viết khác nhau của cùng cấu hình): xem "Chưa kiểm".

## Điểm trung bình solo (7 tiêu chí) qua 3 lần chấm
| giám khảo · truyện | lần 1 | lần 2 | lần 3 | trung bình | độ lệch chuẩn | biên độ |
|---|---|---|---|---|---|---|
| Sonnet · DeepSeek | 2,714 | 2,714 | 2,571 | 2,667 | 0,082 | 0,143 |
| Sonnet · Luna | 3,000 | 2,857 | 3,000 | 2,952 | 0,082 | 0,143 |
| Muse · DeepSeek | 2,571 | 2,571 | 2,571 | 2,571 | 0,000 | 0,000 |
| Muse · Luna | 2,429 | 2,714 | 2,429 | 2,524 | 0,165 | 0,286 |

Độ lệch chuẩn gộp σ (căn trung bình các phương sai của hai truyện, 4 bậc tự do): **Sonnet 0,082, Muse 0,117**. Khoảng tin cậy 95% của σ với 4 bậc tự do rất rộng (nhân 0,60 đến 2,88): Sonnet 0,05 đến 0,24, Muse 0,07 đến 0,34. Một tiêu chí lệch 1 điểm đổi điểm trung bình đúng 1/7 = 0,143, nên biên độ 0,143 là "một ô đổi một điểm".

## Mục nào dao động
- Mỗi giám khảo có 14 ô (2 truyện × 7 tiêu chí); **12 ô giống hệt qua 3 lần, 2 ô lệch đúng 1 điểm** (không ô nào lệch 2).
  - Sonnet: tiếng Việt tự nhiên của DeepSeek (3, 3, 2) và nhịp đẩy truyện của Luna (3, 2, 3).
  - Muse: giọng và độ sáng tạo của Luna (2, 3, 2) và bám nhân vật và bối cảnh của Luna (2, 3, 2): cả hai lệch ở cùng lần 2.
- Các tiêu chí còn lại không đổi ở cả hai giám khảo: liền mạch, lựa chọn có ý nghĩa, lỗi (Sonnet và Muse), thêm giọng, bám nhân vật (Sonnet), tiếng Việt, nhịp (Muse).
- Khác biệt giữa hai truyện ở mục "lỗi" (DeepSeek 2, Luna 3) và "liền mạch" của Sonnet (2 so với 3) lặp lại đủ 3 lần.
- Với mẫu này không đủ để kết luận "mục X ồn hơn mục Y": hai mục ồn mỗi bên chỉ một ô lệch một điểm.

## Hạng so sánh và thứ tự trình bày
| lần | Sonnet: nhất khi trình bày (DeepSeek, Luna) / (Luna, DeepSeek) | Muse: cùng hai thứ tự |
|---|---|---|
| 1 | Luna / Luna | Luna / **DeepSeek** |
| 2 | Luna / Luna | Luna / Luna |
| 3 | Luna / Luna | Luna / **DeepSeek** |
- **Sonnet:** Luna nhất ở cả 6 lượt, không đảo lần nào.
- **Muse:** đảo ở **2 trong 3 lần** (lần 1 và 3), và 5 trên 6 lượt người xếp nhất là truyện **trình bày sau**. Thứ tự (DeepSeek, Luna): Luna nhất 3/3 (Luna là truyện sau); thứ tự (Luna, DeepSeek): DeepSeek nhất 2/3 (DeepSeek là truyện sau), Luna nhất 1/3. Vậy phát hiện ở `2026-10-28-model-bakeoff-muse-1` **lặp lại**, nhưng không hoàn toàn: lần 2 không đảo. Hợp với "thiên lệch theo vị trí cộng nhiễu khi hai truyện sát nhau", không chứng minh thiên lệch (P(≥5/6 | thuần may) khoảng 0,11, với sáu lượt không độc lập). Với cặp này hạng so sánh của Muse không đáng tin; của Sonnet ổn định trên mẫu này.
- Số lần "nhất = truyện trình bày sau" của Sonnet là 3/6 theo đúng thiết kế (Luna nhất luôn, và Luna sau một lần trên hai).

## Câu trích và chi phí
Trích không có thật trên số trích đã kiểm: Sonnet 3/28, 2/27, 1/28; Muse 1/19, 0/22, 2/18. Cùng mức ở cả hai giám khảo. Chi phí mỗi lần của Muse dao động mạnh (0,65, 0,50, 0,29 USD) vì token suy luận khác nhau giữa các lần (ví dụ `solo:A` 0,1006 so với 0,0501 USD): ước tính chi phí chấm bằng Muse phải dự trù rộng. Sonnet ổn định hơn (0,49, 0,38, 0,35).

## Ngưỡng "chênh tối thiểu" đề xuất cho A/B
Cách tính. Hai hệ viết X và Y, mỗi hệ một truyện, mỗi truyện chấm một lần bằng một giám khảo; chênh quan sát là hiệu hai điểm trung bình solo. Nếu hai truyện thật ra bằng nhau thì chênh có độ lệch chuẩn σ·√2 (chỉ nhiễu của giám khảo), nên chênh chỉ đáng tin khi vượt **t(0,975; df) × σ × √(2/k)**, với σ gộp ở trên, df = 4 (t = 2,776), k = số lần chấm lấy trung bình cho mỗi truyện.

| | k = 1 | k = 2 | k = 3 |
|---|---|---|---|
| Sonnet (σ = 0,082) | 0,32 | 0,23 | 0,19 |
| Muse (σ = 0,117) | 0,46 | 0,32 | 0,26 |

Đề xuất tạm:
1. **Chênh điểm trung bình solo dưới 0,32 coi là chưa phân biệt được với nhiễu giám khảo** (Sonnet, một lần chấm); với Muse dưới 0,46. Dùng **0,45 (khoảng 3 điểm tiêu chí trên 7 tiêu chí) làm ngưỡng chung** cho một lần chấm; hạ xuống khoảng 0,25 nếu mỗi truyện chấm 3 lần.
2. **Cần hai giám khảo cùng dấu**: chênh Sonnet 0,29 giữa Luna và DeepSeek ở lần 1 chỉ ngang ngưỡng k = 1 (0,32), và Muse xếp ngược chiều với chênh 0,05 trung bình; kết luận "Luna hơn DeepSeek" theo điểm solo chưa vững.
3. **Không dùng hạng so sánh của Muse** làm số đo cho A/B (đảo theo vị trí 2/3 lần); hạng so sánh của Sonnet dùng được kèm hai thứ tự đảo.
4. Độ hạt: điểm trung bình chỉ nhận bội của 1/7 = 0,143; chênh dưới một hạt không có nghĩa.

Giới hạn quan trọng: σ ước lượng từ 2 truyện × 3 lần (df = 4); nếu lấy cận trên khoảng tin cậy của σ thì ngưỡng k = 1 lên khoảng 0,93 (Sonnet) và 1,32 (Muse). Tức là chưa loại trừ được nhiễu của giám khảo lớn hơn nhiều so với 0,3 đến 0,45; con số 0,3 đến 0,45 là ước lượng điểm, không phải chặn trên.

## Chưa kiểm
- **Nhiễu của lần viết:** chấm lại chỉ đo giám khảo. Hai lần chạy viết cùng một cấu hình (cùng thế giới, seed, model) cho truyện khác nhau, và nhiễu đó thường lớn hơn nhiễu chấm; ngưỡng thật cho A/B của đề viết phải cộng nhiễu này. Đề xuất đo: chạy `bench_run` hai đến ba lần cùng cấu hình (khoảng 0,07 USD mỗi lượt 6 chương theo `model-bakeoff-1`) rồi chấm mù, dùng cùng công thức.
- Chỉ hai truyện, 3 lần chấm mỗi giám khảo, một `effort`; điểm chấm lại chỉ 14 ô mỗi bên.
- Chưa so với đánh giá của người đọc; chưa biết giám khảo nào gần người đọc hơn.
- `compare` của Muse đảo ở 2/3 lần chỉ cho một cặp truyện; chưa biết với cặp khác.
