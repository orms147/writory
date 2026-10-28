# Nhánh A của phép so đề viết: nhiễu giữa các lần VIẾT trên 3 thế giới (đề hiện tại, GPT-6 Luna)

Người đọc: Claude (nhánh eval/ab-baseline), 28 đến 29/10/2026. Nguồn: `meta.json`, `report.json`, `results.jsonl` của các thư mục dưới đây. Script: `ab_analyze.py` (nhiễu viết; `python ab_analyze.py <gốc repo> 2026-10-28`) và `prose_metrics.py` (số đo bằng code) trong thư mục này.

## Chạy gì
Ba thế giới khác nhau, mỗi thế giới một đề riêng đã khai và commit trước khi chạy (`evals/scenarios/story_run/ab-*.yaml`, Truyện ngắn, seed riêng, GPT-6 Luna mọi vai), `--setup-only` một lần, rồi **hai lượt viết với đề hiện tại** (không cờ đề), `--chapters 6`, cùng `--setup-from`, trần `--budget` 0,15 mỗi lượt:
| thế giới | đề (seed) | thư mục khởi tạo | kế hoạch | hai lượt viết |
|---|---|---|---|---|
| tu tiên | `ab-tu-tien` (20261028): tông môn nhỏ bị thôn tính | `evals/results/2026-10-28-run-ab-tu-tien-setup/` | 6 chương | `…-run-ab-tu-tien-cu-1`, `-cu-2` (6/6, kết truyện) |
| kỳ ảo dân gian | `ab-ky-ao` (20261029): đầm lầy, thuỷ thần trở mình, tên Việt | `evals/results/2026-10-28-run-ab-ky-ao-setup/` | 7 chương | `…-run-ab-ky-ao-cu-1`, `-cu-2` (6/7, chưa kết) |
| trinh thám | `ab-trinh-tham` (20261030): Hà Nội cuối thập niên 1980, tên Việt, địa danh thật | `evals/results/2026-10-28-run-ab-trinh-tham-setup/` | 6 chương | `…-run-ab-trinh-tham-cu-1`, `-cu-2` (6/6, kết truyện) |

Mã lúc chạy là `main` trước D-110 (không có biến thể v3) cộng ba file đề; `meta.json` ghi commit `51a13a83` (trước một lần rebase, nội dung tương đương `74478b2`) và "có sửa chưa commit" do `bench_bakeoff.py` đang sửa dở, file mà `bench_run` không đọc. Chạy tuần tự một chuỗi từ 22:59 đến 23:57 ngày 28/10 (trước nửa đêm); thư mục đặt bằng `--out` theo ngày bắt đầu. Chấm 23:58 đến 00:07 ngày 29/10: **chạy qua nửa đêm**, thư mục vẫn mang ngày 28 vì `--out` cố định, không có thư mục nào bị tách đôi.

Chấm: `pack --replicates --seed 20261028 --judge <sonnet|muse>` mỗi thế giới và mỗi giám khảo (6 thư mục `evals/results/2026-10-28-ab-<thế giới>-cu-<giám khảo>/`), `judge` đủ solo và compare, một lần mỗi truyện.

## Điểm trung bình solo (7 tiêu chí) của hai lượt viết cùng cấu hình
| thế giới | Sonnet cu-1 / cu-2 | chênh d | Muse cu-1 / cu-2 | chênh d |
|---|---|---|---|---|
| tu tiên | 2,714 / 3,000 | −0,286 | 2,429 / 3,286 | −0,857 |
| kỳ ảo dân gian | 3,000 / 3,429 | −0,429 | 3,429 / 3,714 | −0,286 |
| trinh thám | 2,429 / 2,857 | −0,429 | 3,286 / 3,000 | +0,286 |

σ_tổng = √(trung bình d²/2 qua 3 thế giới), 3 bậc tự do: **Sonnet 0,274, Muse 0,387**. σ_tổng đã gồm nhiễu viết và nhiễu của MỘT lần chấm. Trừ nhiễu chấm đo ở `../2026-10-28-judge-noise-sonnet-2/notes.md` (0,082 và 0,117; σ_viết² = σ_tổng² − σ_chấm²): **σ_viết ≈ 0,26 (Sonnet) và ≈ 0,37 (Muse)**, tức nhiễu giữa hai lần viết lớn gấp ba đến bốn lần nhiễu chấm lại cùng một văn. Khoảng tin cậy 95% của σ với 3 bậc tự do rất rộng (nhân khoảng 0,57 đến 3,7); đây là ước lượng điểm.

## Ngưỡng tổng cho A/B
Một cặp A/B có chênh trung bình của n hiệu độc lập, mỗi hiệu giữa hai truyện chấm một lần: độ lệch chuẩn σ_tổng·√(2/n). Ngưỡng 95% hai phía = t(0,975; 3) × σ_tổng × √(2/n), t = 3,182:
| | 1 hiệu (một thế giới, một cặp) | 6 hiệu (3 thế giới × 2 cặp) |
|---|---|---|
| Sonnet | 1,23 | **0,50** |
| Muse | 1,74 | **0,71** |
Với thiết kế cũ/v3 (3 thế giới × 2 cặp) ngưỡng là **0,50 (Sonnet) và 0,71 (Muse)**, rất cao so với thang 1 đến 5 (điểm TB của các truyện nằm 2,4 đến 3,7; một hạt tiêu chí là 0,143): v3 phải hơn khoảng 3,5 điểm tiêu chí (Sonnet) hay 5 điểm tiêu chí (Muse) trên mỗi truyện, cộng dồn qua 7 tiêu chí. Luật quyết định dùng đúng hai số này (`docs/eval.md`, mục "Luật quyết định cũ/v3"). Ngưỡng chỉ nói A/B sẽ phân biệt được gì với bộ đo hiện tại, không nói v3 có hơn hay không.

## Đọc tay
- **Mục dao động giữa hai lượt viết:** mỗi giám khảo 8 trên 21 ô (3 thế giới × 7 tiêu chí) khác nhau giữa cu-1 và cu-2. Sonnet: lựa chọn có ý nghĩa (−1 ở cả 3 thế giới), nhịp (0, −1, −1), lỗi (−1, 0, −1), tiếng Việt (0, −1, 0); giọng, bám nhân vật, liền mạch không đổi ở cả ba. Muse: lỗi (−2, −1, 0), tiếng Việt (−1, −1, 0), lựa chọn (−1, 0, +2), liền mạch và nhịp (−1, 0, 0); giọng, bám nhân vật không đổi. Giọng và bám nhân vật là hai tiêu chí ổn nhất ở cả hai giám khảo.
- **cu-2 cao hơn cu-1 ở cả 3 thế giới theo Sonnet** (và 2/3 theo Muse). Chưa giải thích: với ba thế giới độc lập, xác suất cùng dấu thuần may là 25% mỗi giám khảo. Không có cơ chế nào nối cu-2 với điểm cao hơn (hai lượt cùng khởi tạo, cùng mã, chạy nối nhau; `rewrites` 4/5, 2/2, 2/4), nên coi là may rủi, nhưng nếu lặp lại ở nhánh B thì hiệu cũ/v3 phải tính theo cặp (cu-i, v3-i) như luật đã khai.
- **Chấm solo và so sánh trực tiếp không nhất quán ở chất lượng ngang nhau:** trên cùng cặp, hạng so sánh cho cùng một truyện nhất ở cả hai thứ tự trình bày trong 5/6 ô (giám khảo × thế giới); ngoại lệ Sonnet tu tiên (truyện trình bày sau nhất ở cả hai thứ tự). Nhưng truyện nhất theo so sánh trùng với truyện điểm solo cao hơn chỉ ở 1 trong 5 ô có kết luận (Sonnet kỳ ảo; Sonnet trinh thám và cả ba ô của Muse ngược nhau). Với hai truyện ngang chất lượng, kỳ vọng ngẫu nhiên là 50%: mẫu nhỏ, nhưng không có dấu hiệu hai thước đo của một giám khảo đo cùng một thứ ở mức chênh nhỏ.
- **Thiên lệch vị trí của Muse không xuất hiện ở bộ này** (không đảo ở cả ba thế giới, khác với cặp DeepSeek/Luna ở `../2026-10-28-judge-noise-sonnet-2/notes.md`); Sonnet đảo ở 1/3 thế giới (tu tiên). Một lượt `compare:AB` của Muse (tu tiên) hỏng `JUDGE_BAD_JSON` ("tốt nhất và kém nhất cùng là B", tốn 0,17 USD, ghi ở `errors.jsonl`) rồi chạy lại đúng lượt đó (0,12 USD), không chạy lại cả thư mục.

## Số đo bằng code (`prose_metrics.py`, cùng định nghĩa cho cả hai nhánh)
Định nghĩa: tỉ lệ chương (trừ chương cuối) có đoạn cuối của cảnh cuối là "tranh đứng yên" (chờ / không ai / vẫn chưa, regex của `2026-10-28-prose-diagnosis/stats.py`); số cặp chương (mọi cặp) có câu mở giống nhau (Jaccard từ ≥ 0,5, cách `stats2.py`); số bộ lựa chọn có ít nhất hai trong ba lựa chọn khớp họ từ "chờ / đợi / giữ / đứng / ngồi / trông / im lặng" (proxy YẾU cho "ba cách của cùng một việc chờ": hiệu chuẩn trên `2026-10-22-run-ky-ao-vua-3` với nhãn tay của session 2, bắt 3 trên 5 bộ, không bắt nhầm bộ nào; là chặn dưới); chi phí mỗi chương.
| lượt | chương kết đứng yên | cặp câu mở trùng | bộ lựa chọn "chờ" | USD/chương | viết lại |
|---|---|---|---|---|---|
| tu-tien-cu-1 | 2/5 | 0 | 1/5 | 0,00984 | 4 |
| tu-tien-cu-2 | 5/5 | 0 | 2/5 | 0,01046 | 5 |
| ky-ao-cu-1 | 0/5 | 0 | 0/6 | 0,00807 | 2 |
| ky-ao-cu-2 | 0/5 | 0 | 0/6 | 0,00789 | 2 |
| trinh-tham-cu-1 | 2/5 | 0 | 0/5 | 0,00792 | 2 |
| trinh-tham-cu-2 | 3/5 | 0 | 0/5 | 0,00885 | 4 |
Hai lượt cùng cấu hình khác nhau nhiều ở tỉ lệ kết đứng yên (tu tiên 2/5 so với 5/5), nên số này nhiễu và dễ đảo bằng chuyện may rủi; câu mở trùng 0 ở cả sáu lượt (không có chỗ để cải thiện ở bộ này); chi phí ổn định (khoảng 0,008 đến 0,010).

## Chi phí
OpenRouter: 3 lượt khởi tạo 0,0121 USD, 6 lượt viết 0,3181 USD (0,0475 đến 0,0627 mỗi lượt, trần 0,15), tổng 0,3302 USD (trần 1,0). Anthropic (Sonnet, 6 thư mục `judge` đủ 4 lượt): 1,0388 USD (trần 2). Meta (Muse): 1,6386 USD gồm 0,1701 cho lượt `compare` hỏng (trần 3).

## Chưa kiểm
- 3 thế giới × 2 lần viết: σ ước lượng từ 3 bậc tự do; ngưỡng 0,50 và 0,71 có thể lệch xa theo cả hai chiều.
- Mỗi cấu hình chỉ hai lần viết; hai lần khác nhau cũng gồm khác biệt thật của cốt truyện (lựa chọn cuối chương rẽ nhánh), không chỉ nhiễu của model.
- Một mô hình viết (Luna), ba thể loại; chưa biết ngưỡng với model khác hay thể loại khác.
- Chưa so Sonnet và Muse với đọc tay của người, nên "điểm cao hơn" chỉ là điểm của giám khảo.
