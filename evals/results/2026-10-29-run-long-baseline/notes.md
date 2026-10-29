# Đo nền mức Dài trên main có đề v3 (long-tu-tien-3, long-ky-ao-hanh-trinh-1 và -2)

Người đọc: Claude (session writory-28 điều phối) và chủ dự án, 29/10/2026. Nguồn: `report.json`, `calls.jsonl`, `truth_dump.json`, `chapters/`, `meta.json` của các thư mục dưới đây. Script (cùng định nghĩa cho cả lần cũ): `long_metrics.py` (đầu ra `long_metrics.jsonl`), `long_compare.py` (đầu ra `long_compare.jsonl`), `muse_read.py` (góc nhìn thứ hai, đầu ra `muse-*.json`). Số đo bằng code của baseline A/B: `../2026-10-28-ab-baseline/prose_metrics.py`. Chưa sửa code sản phẩm.

## Chạy gì
Main `a4be78a` (đề v3 và ba cờ ngữ cảnh bật, D-111) cộng đề mới `evals/scenarios/story_run/long-ky-ao-hanh-trinh.yaml` (commit `7592dfca` trước mọi lần chạy). Mọi vai GPT-6 Luna, mức Dài (20–35 chương, kế hoạch 24), `--budget 0.35`, dry-run cả hai đề trước (qua 20 chương, thư mục tạm).

| lần | đề, seed | lệnh khác | kết quả | USD |
|---|---|---|---|---|
| `2026-10-22-run-long-tu-tien-2` (cũ, trước v3) | `long-tu-tien`, 20261022 | | 24/24, kết truyện | 0,2559 |
| `2026-10-29-run-long-tu-tien-3` | `long-tu-tien`, 20261022 | | **17/24, dừng ở ch18** (RETRY_LIMIT_REACHED, 6 lời gọi dàn ý `LLM_UNAVAILABLE: ConnectError`) | 0,2152 |
| `2026-10-29-run-long-ky-ao-hanh-trinh-1` | `long-ky-ao-hanh-trinh`, 20261031 | | **14/24, dừng ở ch14**: bước tạo lựa chọn bị từ chối hai lần × hai lượt (`listeners có mục không phải nhân vật`; `ref không có trong danh sách: ['mã người dẫn đầu chưa có trong sổ tay']`) | 0,1326 |
| `2026-10-29-run-long-ky-ao-hanh-trinh-2` | cùng đề | `--setup-from …-ky-ao-hanh-trinh-1` (cùng thế giới và kế hoạch) | **24/24, kết truyện** | 0,2526 |

Tổng OpenRouter của đợt này 0,6004 USD (trần giao ≤ 0,8); không tính một thư mục hỏng ngay ở khởi tạo (`setup:settings`, `RETRY_LIMIT_REACHED`, 0 USD, lúc 16:08 khi mạng đang đứt; đã xoá, không có dữ liệu). Meta (Muse, đọc đoạn giữa) 0,3144 USD (trần ≤ 2). Anthropic: không dùng. Nếu cộng `estimated_unbilled_usd` (0,0545, ước tính của 6 lời gọi hỏng không bị tính tiền) thì `report.json` của tu-tien-3 ghi 0,2697: đó không phải tiền đã tiêu.

**Về lần dừng ở tu-tien-3:** `calls.jsonl` seq 215 có `latency_s` = 13121,7 (3,6 giờ), rồi `ConnectError`; mọi lời gọi khác tối đa 111 giây; bắt đầu 11:57, kết thúc 16:08. Client dùng timeout đọc 120 giây (`llm/openrouter.py:49`), nên một lời gọi 3,6 giờ chỉ giải thích được bằng đồng hồ ngừng chạy lúc máy ngủ hoặc mạng đứt; **chưa kiểm** nguyên nhân thật. Hai lượt kỳ ảo chạy sau đó có giữ máy không ngủ (`SetThreadExecutionState`, tắt bằng PID của chính nó); lượt chạy bình thường mất 36 đến 37 phút (tu-tien-2 và ky-ao-2).

## Hạn chế lớn nhất: so sánh cũ/mới không sạch
- **Cùng đề, seed vẫn ra thế giới khác.** `long-tu-tien-2` là hội đồng thương nghị ở Điện Nghị An (phòng họp); `long-tu-tien-3` là con thuyền Bích Luân qua vùng cấm rồi đảo Ly Quang (`truth_dump.json` plan.milestones). Vì vậy mọi khác biệt giữa hai lần vừa do đề v3 vừa do thế giới; **không tách được**.
- Mỗi cấu hình một lần chạy (riêng kỳ ảo có hai lần cùng thế giới), model có nhiễu.
- Hai lượt tu-tien-3 và ky-ao-1 dừng giữa chừng nên đoạn cuối chỉ đọc được ở ky-ao-2 (và tu-tien-2 từ lần cũ).

## Số chính (từ `long_metrics.jsonl`, cùng định nghĩa cho cả bốn lần)
Định nghĩa trong docstring của `long_metrics.py`. Chương giậm chân ("không đổi trạng thái") = chương không có: mạch gỡ, bí mật lộ, đổi nơi (cạnh `LOCATED_AT` mới tới nơi khác), cạnh `HOLDS` mới, Fact mới nói người bị thương/chết/bị bắt/mất tích. Mốc kế hoạch không phải trạng thái ghi trong đồ thị nên không vào tín hiệu; tín hiệu "bị thương" là regex trên Fact (chặn dưới).

| | tu-tien-2 (cũ) | tu-tien-3 | ky-ao-1 | ky-ao-2 |
|---|---|---|---|---|
| chương ghi / kế hoạch | 24/24 | 17/24 | 14/24 | 24/24 |
| chương không đổi trạng thái | 15/24 | 7/17 | 6/14 | 10/24 |
| …trong đó ở ch8–17 | 6/10 | 3/10 | 3/7 | 5/10 |
| …thêm tín hiệu quan hệ/cảm xúc (`stalled_wide`) | 11/24 | 6/17 | 3/14 | 7/24 |
| chương cuối không có `LOCATED_AT` của nhân vật chính | **12** (ch7–17 và 24) | 0 | 0 | 0 |
| số nơi khác nhau của nhân vật chính | 3 | 2 | 3 | 4 |
| chương quay lại nơi đã ở trong 3 chương trước | 0 | 0 | 2 (ch7, ch8) | 0 |
| từ thủ tục mỗi chương, ba đoạn đầu/giữa/cuối | 12,6 / 34,5 / 20,5 | 0,7 / 0,4 / 0 | 0,8 / 0,5 / 8,2 | 1,0 / 4,8 / 0,5 |
| độ giống cặp âm tiết với 2 chương trước (đầu/giữa/cuối) | 0,077 / 0,101 / 0,093 | 0,083 / 0,071 / 0,075 | 0,069 / 0,058 / 0,063 | 0,067 / 0,060 / 0,073 |
| chương kết bằng cảnh đứng yên (trừ chương cuối) | 11/23 | 3/16 | 1/13 | 2/23 |
| bộ lựa chọn "chờ" (≥ 2 trong 3) | 6/23 | 2/17 | 1/13 | 1/23 |
| cặp chương mở trùng | 0 | 0 | 0 | 0 |
| viết lại | 8 | 3 | 0 | 5 |
| chi phí mỗi chương (USD, đã gồm chương 0) | 0,0107 | 0,0127 | 0,0095 | 0,0105 |
| mạch/bí mật đúng khoảng (đã tới hạn) | 8/8 | 10/10 | 7/7 (3 chưa tới hạn) | 10/10 |

Đọc được: số chương không đổi trạng thái, số từ thủ tục và số bộ lựa chọn "chờ" thấp hơn rõ ở ba lần mới so với lần cũ; nhân vật chính luôn có đúng một nơi ở trong cả ba lần mới. **Nhưng** (a) thế giới khác nên chưa nói được do v3; (b) tín hiệu này mù với vòng lặp nguy hiểm/manh mối vì mỗi chương vẫn "đổi" một thứ nhỏ (ví dụ ky-ao-1 ch8 được tính là "đổi nơi" dù nhân vật chỉ quay lại rừng); (c) tu-tien-3 ch7 nhân vật rời thuyền xuống bãi đá mà bộ trích không ghi cạnh `LOCATED_AT`, nên bị tính là không đổi. **Độ giống cặp âm tiết** không tách được các chương lặp theo nghĩa (cao nhất ở lần cũ nhưng chênh nhỏ), **chưa dùng được làm thước đo**. Phiên bản đề: `outline-10`, `writer-10`, `choices-4` ở ba lần mới, `outline-9`, `writer-9`, `choices-3` ở lần cũ.

## Chi phí và token theo vai (`long_compare.jsonl`, dải chương cố định)
Token vào trung bình mỗi lời gọi, dải ch1–3 / ch8–10 / ch15–17:

| vai | tu-tien-2 (cũ) | tu-tien-3 | ky-ao-2 |
|---|---|---|---|
| viết | 5789 / 7048 / 6662 | 8431 / 8913 / 8595 | 7189 / 7870 / 7838 |
| dàn ý | 4817 / 5782 / 5572 | 6362 / 7188 / 6951 | 5346 / 5940 / 6174 |
| trích | 7593 / 11068 / 14646 | 8873 / 12759 / 17061 | 7583 / 10989 / 14626 |
| lựa chọn | 2736 / 4390 / 6043 | 2957 / 4707 / 6312 | 2651 / 3959 / 5631 |
| tóm tắt, kiểm duyệt | phẳng ~2,1–2,3k | phẳng ~2,0–2,3k | phẳng ~2,0–2,4k |

Chi phí mỗi chương (USD) cùng ba dải: cũ 0,0078 / 0,0109 / 0,0112; tu-tien-3 0,0127 / 0,0117 / 0,0117; ky-ao-2 0,0090 / 0,0104 / 0,0105.
- Vai viết và dàn ý nhận thêm khoảng 1,4k đến 2,6k token vào mỗi lời gọi ở tu-tien-3 so với lần cũ (+32 đến +46% ở ch1–3, +24 đến +26% ở ch8–10): phù hợp với đề v3 dài hơn (hướng dẫn văn phong 8051 ký tự so với 6028), tính cách NPC và câu mở chương trước. Chưa tách từng phần thêm bằng thực nghiệm. ky-ao-2 thêm khoảng 0,2k đến 1,4k; lý do chưa tách (số nhân vật có mặt khác nhau là một giả thuyết, chưa kiểm).
- Chênh chi phí chương **tập trung ở ch1–3** của tu-tien-3 (0,0127 so với 0,0078): ch3 tốn 0,0197 (cả hai cảnh viết lại sau `guard:early_reveal`, lỗi chặn; `calls.jsonl`). Ở ch8–17 chi phí chỉ cao hơn khoảng 4 đến 7%. Không thấy chi phí tăng nhanh theo chương: token vào của vai trích và lựa chọn tăng theo truyện y như lần cũ; hai vai này vẫn là hai vai đáng theo dõi.
- Dự báo (suy luận, chưa kiểm): ky-ao-2 chạy hết 24 chương hết 0,2526 USD, tu-tien-2 hết 0,2559; cả hai dưới trần truyện 1,0 trong `config/limits.yaml`.

## Hai cái nhìn về đoạn giữa
**Đọc tay (tôi) và Muse (`muse-wonder-1.0`, reasoning low, đọc nguyên văn 6 chương giữa; lệnh trong `muse_read.py`, đầu ra `muse-*.json`)** nhất trí ở chỗ lặp, khác ở mức độ:

- **tu-tien-2 (cũ), ch10–15:** Muse đánh dấu ch12 giậm chân, còn lại có đổi; khuôn lặp "họp quanh bàn → trải sổ canh gác/sơ đồ → chỉ ra mốc giờ bỏ trống → chưa đủ chứng cứ → ghi thêm một dòng → giữ nguyên quyền canh giữ". Ba lựa chọn "ba cách diễn đạt cùng một hướng". Chương cuối "kết bằng thủ tục và trạng thái chờ". Khớp với notes cũ (`../2026-10-22-run-long-tu-tien-2/notes.md`).
- **tu-tien-3, ch8–13 (con thuyền):** Muse đánh dấu mọi chương có đổi, nhưng mô tả khuôn lặp "chuông dưới biển vang → vệt sáng tắt → nước đổi chiều/hút thuyền → la bàn lệch → cả nhóm tranh ai chọn đường → nhân vật chính giành một lối hẹp → thoát tạm rồi bị cuốn sang đoạn nguy hiểm kế" ở ch8, 9, 10, 11, 12, 13. Đọc tay ch7–17 của tôi cũng thấy: ch5–7 cùng cảnh thuyền nghiêng/nước tràn khoang; từ ch8 đến ch17 mỗi chương kết bằng một lối hẹp đang nứt hoặc bị đám đông chặn. Khác với lần cũ: không còn từ thủ tục (0,4 mỗi chương), kết chương không đứng yên (cuối chương nào cũng có chuyển động hoặc nguy hiểm mới), ba lựa chọn khác loại (hành động/lời thoại/nội tâm) nhưng "hội tụ" về cùng xung đột.
- **ky-ao-1, ch6–11:** Muse đánh dấu ch8 và ch10 giậm chân: ch8 "gỡ tội cho Đinh Lộc lặp lại gần nguyên trạng", ch10 "lại gặp đúng hai rãnh song song và hai hàng cọc gãy, lại qua ván sụp và mất đường về". Khuôn "sương xóa dấu → xé áo buộc vải → nghe chuông/ván đổi hướng → qua ván sụp → thấy lại rãnh/cầu cũ". Lựa chọn "một số đổi hướng rõ, số khác hội tụ". Đọc tay tóm tắt: ch5 vào Rừng Rủ Sương, ch7 về lại Biển Muối bị áp giải, ch8 lại vào rừng, ch9–10 lạc trong rừng, ch11 tới cảng.
- **ky-ao-2, ch10–15:** Muse thấy mọi chương có đổi nhưng khuôn "phát hiện hai vết khía song song → lần theo → tuần tra đuổi → đổ ván/chặn lối → mất manh mối cũ nhưng thấy bản sao khác của cùng dấu" ở ch10–15; đọc tay ch16–23 từ tóm tắt: ch16–19 lặp "lần theo dấu bánh xe, bị lính chặn, đạp ván thoát"; ch20–23 cùng một cảnh tại Bến Cầu Gãy (nước cuốn, ghì cọc, giữ thanh ngang) nhưng mỗi chương có bước mới (Khương muốn quyền, Lộc giải mã dấu).
- **Kết truyện ky-ao-2 (đọc nguyên văn ch24):** cụ thể và có giá: Thảo từ chối trao quyền kiểm soát cho Khương, tự đẩy thanh ngang vào khe, "Mối nối khép sầm", lối qua đây mất hẳn, bốn người đứng cùng phía. Muse: "giải quyết cụ thể cho mối nối này" (chưa chắc cho toàn bộ mâu thuẫn). **Không giống kết thủ tục của tu-tien-2.** Chưa đọc kết của tu-tien-3 (dừng ở ch17) và ky-ao-1 (dừng ở ch14).
- Mặt khác: ba lần mới đều đọc được, tiếng Việt tự nhiên; tóm tắt chương của ky-ao-1 vẫn gọi nhân vật chính lẫn lộn "Thảo", "tôi", "Mai Thảo", "nhân vật", "cô" (vấn đề (c) đã biết, session 2 đang sửa; không đụng ở đây).

## Trả lời: giậm chân do mức Dài hay do kiểu thế giới?
**Cả hai, ở hai dạng khác nhau** (đọc được ở các chương trên; "do mức Dài" là suy luận từ việc cả ba loại thế giới đều có đoạn lặp giữa truyện):
1. Thế giới tĩnh (phòng họp) lặp theo **thủ tục hồ sơ**: 15/24 chương không đổi trạng thái, 12 chương mất `LOCATED_AT`, kết thủ tục (cũ).
2. Thế giới di chuyển (thuyền, rừng, cảng) lặp theo **cơ chế ép tiến**: mỗi chương dùng cùng một động cơ nguy hiểm hoặc cùng một dạng manh mối (chuông/nước/sương/ván; dấu khía → tuần tra → đổ ván). Đo bằng code thì gần như không thấy (số chương không đổi trạng thái thấp hơn), đọc tay và Muse thì thấy. Kết truyện tốt hơn (ky-ao-2).
3. Điểm chung của cả ba: đoạn giữa (ch8 tới khoảng ch19) là chỗ lặp, đầu truyện (ch1–7) và gần cuối (ch20+) có tiến triển rõ.

## Top 3 nguyên nhân giậm chân ở các lần mới, kèm bằng chứng
1. **Cơ chế ép tiến được dùng lại làm động cơ của nhiều chương liền.** Đề v3 buộc "mỗi cảnh đổi một điều", và một thay đổi nhỏ (mất lối quay lại, cầu sập, đổi hướng nước, mất manh mối này nhưng thấy bản sao khác) đủ để chương được tính là có đổi. Bằng chứng: Muse ở cả ba lần mới nêu đúng nguyên nhân này (xếp hạng 1 hoặc 2); khuôn nguy hiểm tả ở các mục trên; ky-ao-1 ch9→ch10 "bỏ dấu rãnh lại" rồi vẫn lại gặp đúng rãnh. Mật độ biến cố lớn (mạch/bí mật) thì ổn: mạch và bí mật đúng khoảng, nên cái thiếu là **biến cố đổi tình thế giữa các mạch**, không phải mạch.
2. **Mốc kế hoạch lệch với diễn biến thật, và code không biết mốc đã diễn ra.** Mốc chỉ là khoảng chương (`pacing.py:118-122`: `m.from_chapter <= chapter <= m.to_chapter`, không ghi mốc đã xong), nên khi truyện đi nhanh hơn mốc, đoạn mốc phải diễn lại. Bằng chứng: ky-ao-1 mốc ch7–9 "Mai Thảo rời Biển Muối theo lối dẫn vào Rừng Rủ Sương", nhưng tóm tắt ch5 đã vào rừng; nhân vật rồi bị kéo về Biển Muối ở ch7 rồi lại vào rừng ở ch8 (2 chương quay lại nơi cũ, `place_returns` = [7, 8]). tu-tien-3 mốc ch9–11 "Trường Khanh phát hiện tiếng chuông báo một chốt phong ấn đang suy yếu", nhưng văn ch7 đã viết "Một chốt phong ấn đang suy yếu" sau khi tiếng chuông đổi dòng nước từ ch5; ch8–13 tiếp tục cùng cảnh chuông/nước. Khoảng mốc phủ kín mọi chương (không chương nào thiếu mốc, bí mật hay mạch: `plan_no_item` trống ở cả ba lần mới; chỉ 2 đến 8 chương thiếu mốc riêng), nên cờ `unplanned_chapter_goal` (D-110) không phải chỗ nghẽn. Đây là suy luận từ hai ca, chưa kiểm hết các mốc.
3. **Lựa chọn cuối chương khác loại nhưng hội tụ.** Ba lựa chọn đủ ba loại (hành động/lời thoại/nội tâm) và không còn "toàn chờ" (bộ "chờ" 1 đến 2 trên 13–23 so với 6/23 ở lần cũ), nhưng Muse ở tu-tien-3, ky-ao-1 và ky-ao-2 đều nhận xét nhánh được chọn bị kéo về cùng trục xung đột (ví dụ ky-ao-1: quay lại tìm ván và bỏ dấu rãnh đều dẫn về chuông → ván → rãnh → cầu → cảng); chỉ lựa chọn nào đổi nơi hay đổi người đối diện mới rẽ thật. Mới thấy qua văn đã chọn, không đo được nhánh không chọn.

Các nguyên nhân khác đã loại hoặc nhỏ: nơi ở nhân vật chính (D-98) **không còn là điểm mù** ở thế giới di chuyển (0 chương mất cạnh; ở tu-tien-2 là 12), nhưng chưa biết do v3, do thế giới, hay do nhiễu bộ trích; từ thủ tục chỉ nặng ở thế giới họp (34,5 mỗi chương đoạn giữa) và nhẹ ở ba lần mới.

## Đề xuất sửa (suy luận, cần chủ dự án/session 2 duyệt trước khi làm)
- **Mốc nên là biến cố có điểm kết quả đo được, và code cần biết mốc đã xong.** Hiện mốc chỉ là câu mục tiêu theo khoảng chương. Hai cách nhỏ: (a) bộ trích hoặc người canh đánh dấu mốc đã diễn ra (như mạch/bí mật ở `plan_progress`), rồi mục tiêu chương bỏ mốc đã xong và nhắc "đã xảy ra, đi bước kế"; (b) khi sinh `story_plan`, buộc mỗi mốc kèm "điều kiện hoàn thành" một câu, và khoảng mốc không chồng lên nhau quá hai chương. Câu hỏi của anh "mốc giữa truyện có cần đổi tình huống ở story_plan không": **có**, nhưng điều cần đổi trước hết là cách code theo dõi mốc, rồi mới đến câu chữ mốc (D-98 mới thêm cờ đứng yên theo nơi, chưa có theo mốc).
- **Lập kế hoạch giữa truyện có "biến cố đổi pha"**: cứ 5 đến 6 chương một biến cố làm đổi nơi, người hay luật (không phải thêm nguy hiểm cùng loại), vì động cơ nguy hiểm một loại lặp lại ở cả hai thế giới di chuyển. Cần thí nghiệm riêng.
- **Tín hiệu giậm chân không dựa một cạnh** (đúng đề xuất của session 2): thêm tín hiệu "hai chương liền dùng cùng một mô-típ" hay "lần theo cùng một manh mối" khó làm bằng code thuần; có thể dùng bộ trích gắn nhãn mô-típ, cần quyết định riêng.
- **Độ bền bước lựa chọn (lỗi kỹ thuật, nên sửa vì nó dừng cả truyện):** ky-ao-1 dừng ở ch14 vì model lựa chọn tham chiếu một nhân vật chưa có trong sổ tay ("người dẫn đầu") và pydantic từ chối cả bốn lần. Người chơi thật sẽ thấy `RETRY_LIMIT_REACHED` ở ch14 mà bấm lại có thể cùng lỗi. Hướng: cho model một lần sửa có thông báo lỗi, hoặc bỏ các `listeners/about` ngoài danh sách thay vì từ chối cả bộ (cần test hồi quy và duyệt vì chạm G11/G12). Không sửa ở nhánh này.
- **Treo lời gọi quá lâu:** chưa kiểm là máy ngủ hay lỗi mạng; nếu lặp lại ngoài máy phát triển thì cần giới hạn thời gian cả lời gọi, không chỉ từng lần đọc 120 giây.

## Chưa kiểm
- Cùng đề không cho cùng thế giới, nên không tách được tác dụng của v3 khỏi kiểu thế giới. Muốn tách phải chạy `--setup-from` cùng một thư mục khởi tạo với hai bản đề (cần dựng đề cũ từ `git show 41ed852:<file>`, `docs/eval.md`), hoặc chấm bằng bài F.
- Mỗi cấu hình một lần chạy; hai lần cùng thế giới (ky-ao-1, ky-ao-2) lệch nhau 5 chương ở số chương không đổi trạng thái trong ch8–17 (3/7 và 5/10: khác độ dài mẫu), nên số đo này nhiễu.
- Tín hiệu "đổi nơi" bỏ sót khi bộ trích không ghi `LOCATED_AT` (tu-tien-3 ch7) và đếm cả việc quay lại (ky-ao-1 ch8). Tín hiệu "bị thương" là regex.
- Đọc tay chủ yếu ch7–17 của tu-tien-3, ch24 của ky-ao-2 và tóm tắt các chương còn lại; Muse chỉ đọc 6 chương mỗi lần, một lần hỏi, reasoning low.
- Chưa đọc kết truyện của tu-tien-3 và ky-ao-1 (dừng giữa chừng). Chưa đo tóm tắt gọi nhân vật chính bằng code.
