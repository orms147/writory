# Dài trước/sau D-110..D-121 (tu-tiên 21 chương; kỳ ảo dừng ở ch12 rồi chạy lại đủ 24 chương)

Người đọc: Claude điều phối (writory-28) và chủ dự án, cân nhắc mở mức Dài cho người chơi, 29/10/2026. Nguồn: `report.json`, `calls.jsonl`, `truth_dump.json`, `rejected.jsonl`, `chapters/` của ba thư mục `2026-10-29-run-long-after-tu-tien`, `2026-10-29-run-long-after-ky-ao` và `2026-10-29-run-long-after-ky-ao-2`; baseline ở `../2026-10-29-run-long-baseline/notes.md`. Script ở thư mục này: `after_metrics.py` (đầu ra `after_metrics.jsonl`), `cost_decomp.py` (đầu ra `cost_decomp.txt`), và `long_metrics.py` của baseline chạy lại trên các lần mới (đầu ra `long_metrics_after.jsonl`, `long_metrics_ky2.jsonl`; số mốc/cờ của lượt chạy lại ở `after_metrics_ky2.jsonl`). Không đổi code sản phẩm trong PR này.

## Chạy gì
- Hai lượt đầu: main `9050696` (có D-110..D-121; **chưa** có PR #96 nên `phase_shift_every` tắt; chưa có D-122/D-123). Lượt chạy lại kỳ ảo: main `be4cc30` (thêm D-122 và D-123: chờ lùi cho lỗi tạm, lời thoại không người nghe), nhánh này gộp main đó nên `meta.json` ghi commit `e79bdbc` (merge, sạch); mã sản phẩm là của `be4cc30`. `phase_shift_every` vẫn tắt. `--setup-from` thế giới của baseline, cùng seed, 24 chương, `--budget 0.35`, mọi vai GPT-6 Luna. Dry-run hai đề trước (không `--setup-from`, vì model giả `DryRunLLM` dựng lựa chọn theo thế giới giả, không đọc được sổ tay thật; không phải lỗi sản phẩm). Một chuỗi, máy giữ không ngủ.
- **Cảnh báo so sánh:** các lần baseline có thể có nút lân cận trùng (D-117), nên token vào của baseline có thể cao hơn thực; số đo "mọi thứ chưa khớp" ở dưới đã tính điều đó là một nguồn lệch chưa tách. Mỗi cấu hình một lần chạy; model có nhiễu.

| lần | so với | kết quả | USD | ghi chú |
|---|---|---|---|---|
| `…run-long-after-tu-tien` | tu-tien-3 (cùng `--setup-from`, seed 20261022) | **21/24, dừng ở ch22**: `COST_LIMIT_STORY` | 0,2969 | dừng vì phần đặt trước của `--budget 0.35` (xấu nhất mỗi lời gọi), **không** phải trần `per_story` của config; bench dừng sớm khoảng 0,05 dưới trần danh nghĩa. Chủ dự án (qua writory-28) chấp nhận giữ 21 chương, không chạy lại |
| `…run-long-after-ky-ao` | ky-ao-1 và ky-ao-2 (seed 20261031) | **11/24, dừng ở ch12**: `RETRY_LIMIT_REACHED` do `LLM_UNAVAILABLE: ConnectError` (mạng đứt; các lời gọi hỏng sau 0,002 đến 0,012 giây) | 0,1078 | đã chạy lại sau khi PR #101 gộp (hàng dưới) |
| `…run-long-after-ky-ao-2` | ky-ao-2 baseline (cùng `--setup-from` ky-ao-1, seed 20261031) | **24/24, kết truyện**, `--budget 0.45` | 0,2558 | `report.json` ghi `estimated_unbilled_usd` 0,0270 (3 lời gọi hỏng không tính tiền); dòng tiến độ in 0,2827 là tổng đã cộng ước tính đó, **tiền thật là 0,2558** |

Tổng OpenRouter của ba lượt: 0,6605 USD (0,2969 + 0,1078 + 0,2558; trần đợt này 1,3). Meta, Anthropic: không dùng.

## Số chính (tu-tien, `long_metrics_after.jsonl`; cùng định nghĩa với baseline)
Dài khác nhau (21 chương so với 17), nên cột "trên 17 chương đầu" chỉ nêu khi tính lại được.

| | tu-tien-3 (17 ch) | sau (21 ch) |
|---|---|---|
| chương không đổi trạng thái | 7/17 | 11/21 (`stalled_wide` 7) |
| số nơi khác nhau của nhân vật chính / quay lại | 2 / không | 2 / ch12 |
| chương kết bằng cảnh đứng yên | 3/16 | 1/20 |
| bộ lựa chọn "chờ" | 2/17 | 2/21 |
| cặp chương mở trùng | 0 | 0 |
| từ thủ tục mỗi chương (đầu/giữa/cuối) | 0,7 / 0,4 / 0 | 0,7 / 0,3 / 0,4 |
| độ giống cặp âm tiết (đầu/giữa/cuối) | 0,083 / 0,071 / 0,075 | 0,081 / 0,082 / 0,081 |
| nhân vật chính không có nơi ở ở chương cuối | không | không |
| viết lại | 3 | 11 |
| USD mỗi chương | 0,0127 | 0,0141 |
| tóm tắt dùng đủ họ tên nhân vật chính (D-112) | 1/17 | 21/21 |

Đọc được: số chương "không đổi trạng thái" **không** giảm (11/21 so với 7/17), và độ giống chữ không đổi đáng kể. Số chương ghi ít hơn mục tiêu, và tín hiệu này mù với vòng lặp theo nghĩa (đã nói ở baseline). Trong tóm tắt chương, tôi đọc cả 21 câu: truyện đi từ thuyền/sương/chuông (ch1–10) sang đảo Ly Quang (ch11–21) với sự kiện thật (ch8–9 Cố Hành Chu nhận phá la bàn; ch10–11 Ninh Tuyết Anh lộ hộp và danh nghĩa; hải đồ bị xé ch13, ch15; thuỷ thủ bỏ đi ch16; đài sập ch18–21); **không thấy vòng thủ tục hay vòng "đi lại cùng chỗ" như baseline ky-ao-1 (quay lại Biển Muối ch7–8)**. Chữ "chuông" (motif lặp của baseline, 3 đến 7 lần mỗi chương đến ch11) xuống 0–1 lần mỗi chương sau ch8: bằng chứng yếu rằng mốc m3 xong ở ch5 chặn việc dùng lại cùng motif; chưa kiểm bằng thực nghiệm.

## Cờ `standstill` và `idle` (D-98, D-112)
Tính lại bằng chính `pacing.standstill` và `pacing.idle_chapters` trên đồ thị đến hết chương trước, ngưỡng của config, chương cuối của kế hoạch loại (`after_metrics.py`).
- **tu-tien sau:** `standstill` bật ở ch4–10, 16, 20–22 (11 chương). `idle` **không bao giờ** bật riêng (chỉ ≥ ngưỡng khi `standstill` cũng bật, mà `standstill` thắng, nên chỉ một lời giục).
- **ky-ao sau:** `standstill` bật ở ch4, 5, 12; `idle` không.
- Chạy lại cùng hàm trên dữ liệu **cũ** (baseline): tu-tien-3 `[4,5,6,10,14,18]`, ky-ao-1 `[4,5,15]`, ky-ao-2 `[4,5,9,10,14,15,16,20]`, `idle` không bao giờ. **Số cờ của dữ liệu cũ bị đếm thiếu**: nơi ở bị nêu lại làm `valid_from` đặt lại, cờ tưởng nhân vật vừa đổi chỗ (đã sửa ở D-112). Vì vậy không so sánh được "cờ nhiều hơn hay ít hơn" giữa cũ và mới; chỉ đọc được rằng ở lần mới, tu-tien bật cờ `standstill` ở một đoạn dài (ch4–10) và truyện vẫn đi tiếp, cờ không gây vòng.

## Mốc kế hoạch (D-116, `plan_vs_result.milestones`)
tu-tien (chương xảy ra so với khoảng): m1 ch1 (1–2) đúng hạn; m2 ch3 (4–6) sớm; m3 ch5 (9–11) sớm; m4 ch11 (12–13) sớm; m5 ch15 (16–17) sớm; m6 ch19 (20–22) sớm; m7 (24) chưa tới (dừng ở 21). ky-ao: m1 ch1 (1–2) đúng; m2 ch2 (4–6); m3 ch3 (7–9); m4 ch7 (10–12); m5 ch9 (13–15), đều sớm; m6 trở đi chưa tới (dừng ở 11).
- **Bị từ chối:** không có dấu mốc nào bị bộ trích từ chối (`milestone_rejections` rỗng ở cả hai); đếm bằng mục `rejected` có mô tả "mốc …" trong `truth_dump.json`.
- **Đọc tay 6 dấu (3 flag của tu-tien, 3 của ky-ao):** không thấy dấu sai rõ.
  - tu-tien m3 (ch5, khoảng 9–11, "phát hiện tiếng chuông báo chốt phong ấn đang suy yếu"; câu trích "Áp lực nước dồn vào chốt phong ấn, khiến nó phát tiếng."): đúng ý chính nhưng lỏng, chưa nói "suy yếu".
  - tu-tien m4 (ch11, "danh nghĩa Ninh Tuyết Anh bị vạch rõ"; câu trích "Ta là người đưa tin của Minh Ước Giữ Ấn. Không phải sứ giả Huyền Tiêu Tông."): đúng, rõ.
  - tu-tien m6 (ch19, cao trào "Trường Khanh phải chọn ai được dùng hộp ngọc"; câu trích "Nàng được dùng hộp để dò mạch."): đúng, nhưng là một quyết định cục bộ: **cao trào bị coi là xong ở ch19 nên ch20–22 không còn bị giục dựng nó**. Rủi ro cần theo dõi khi mở Dài.
  - ky-ao m3 (ch3, rời Biển Muối sang Rừng Rủ Sương; "Tôi quay lưng với phiên chợ."): đúng, sớm hơn baseline (ch5).
  - ky-ao m4 (ch7; "Đường cong ấy giống phần chân cầu cũ…"): đúng nhưng lỏng, nối với tuyến bản đồ qua đường mòn có khía.
  - ky-ao m5 (ch9; "Chuyến hàng ấy không mất khỏi sổ vì giấy mục."): đúng, rõ.
- Mọi mốc đều xong **sớm hơn khoảng** (trừ m1 ky-ao và tu-tien đúng hạn). Điều đó khớp với việc mốc không còn bị "diễn lại" sau khi đánh dấu, nhưng cũng nghĩa là truyện đi nhanh hơn kế hoạch: cần xem ở lượt 24 chương đủ xem chương cuối có đủ chuyện cho 24 chương hay không (tu-tien dừng ở 21 nên chưa xem được).

## `rejected.jsonl` (D-115)
- tu-tien: 0 dòng.
- ky-ao: 2 dòng, cả hai là vai `choices` ở ch10 (`choices.1: value_error`): thân thật có `lời thoại, tone silence, listeners []` trong bộ ba (action, dialogue, inner). Schema cũ bỏ cả bộ vì một lựa chọn lời thoại không có người nghe, dù D-121 đã định bỏ riêng lựa chọn đó ở bước `_resolve`. Đã sửa ở PR #101 kèm test hồi quy dùng đúng thân này (`backend/tests/fixtures/llm/choices_silence_no_listener_run_long_after_ky_ao_ch10.json`).

## Chi phí: vì sao tu-tien đắt hơn baseline (`cost_decomp.txt`)
Chia chênh chi phí mỗi vai theo `Δ = (số lời gọi sau − trước) × giá trước + số lời gọi sau × (giá sau − giá trước)`, trên dải chương chung ch1–17 (tu-tien-3 hết ở ch17). Tổng 0,2064 → 0,2413 USD, **Δ = +0,0350**:
- **94% (+0,0328) do nhiều lời gọi hơn**, tức nhiều lần viết lại: viết 39 → 49 lời gọi, trích 39 → 49, kiểm duyệt 56 → 66, lựa chọn 18 → 17, dàn ý 37 → 38. Viết lại 3 → 11.
- **6% (+0,0022) do giá mỗi lời gọi**: trích +7% token vào (12536 → 13414; +0,0046), tóm tắt +226 token vào mỗi lời gọi (câu tên nhân vật chính ở `summary-2`; +0,0010), kiểm duyệt +62 (+0,0010); dàn ý rẻ hơn (−0,0075 vì tổ hợp ngữ cảnh khác); viết và lựa chọn gần phẳng. Các số "đề trích có mốc chưa diễn ra" và "câu goals mới" cộng chung vào cột trích và dàn ý; **không tách riêng** từng câu.
- **Viết lại tập trung ở ch8–9** (viết 5 và 7 lời gọi thay vì 2; ch3, 7, 10, 11, 17 mỗi chương thêm 1 đến 2). Lỗi người canh: `early_reveal` 9 so với 3, `teller_does_not_know` 15 so với 4. Hai cảnh bị chặn. Ví dụ ch9 cảnh 2: "bí mật `fact_su_gia_that` lộ ở chương 9, kế hoạch cho lộ từ chương 11".
- **Nguyên nhân gốc chưa kiểm.** Giả thuyết đọc được từ code (`pacing._milestones`): sau khi m3 xong ở ch5, mục tiêu chương từ ch6 hiện mốc "kế tiếp" là m4 ("Danh nghĩa của Ninh Tuyết Anh bị vạch rõ", khoảng 12–13) kèm lời giục "đưa vào một sự kiện hay áp lực cụ thể đẩy nhân vật chính về phía đó"; ở baseline mốc kế tiếp tới ch9 vẫn là m3. Bí mật `fact_su_gia_that` có khoảng lộ từ ch11, nên giục về m4 sớm 6 chương có thể đẩy cảnh tới chỗ lộ bí mật sớm. **Đây là suy luận từ đọc code và cảnh bị chặn, chưa có đối chứng** (một lần chạy; các ứng viên khác: nhiễu lấy mẫu, D-117, tính cách NPC D-110). Muốn kiểm: chạy lại cùng thế giới với "kế tiếp" chỉ hiện khi mốc bắt đầu trong N chương tới, hoặc đọc đề dàn ý ch8–9 trong `calls.jsonl` (đề không lưu nguyên văn, chỉ số token).
- Chi phí mỗi chương: 0,0141 so với 0,0127; ở ky-ao dải ch1–11 **rẻ hơn** ky-ao-2 (Δ −0,0042: viết −0,0034, các vai khác ±0,001), một nửa do số lời gọi, một nửa do giá.

## ky-ao (11 chương, dừng vì mạng) so với ky-ao-2 / ky-ao-1 ở ch1–11
Chương không đổi trạng thái: 4/11 (ch3, 6, 9, 10) so với 3/11 (ky-ao-2: ch4, 9, 11) và 5/11 của ky-ao-1 (ch2, 4, 6, 9, 10); số nơi 3; **không quay lại nơi cũ** (ky-ao-1 quay lại Biển Muối ở ch7, ch8); chương kết đứng yên 1; bộ lựa chọn "chờ" 0/11; viết lại 2 (ky-ao-2: 5 trên 24 chương); USD mỗi chương 0,0098. Từ thủ tục tăng mạnh ở ch8–10 (18, 28, 15 từ mỗi chương): cùng đoạn "sổ cảng/giấy tờ" mà ky-ao-1 ch12 (29) và ky-ao-2 ch12–13 (16, 9) cũng có, đến sớm hơn ở lần này vì mốc xong sớm; chưa đọc hết văn bản để biết là vòng thủ tục hay cảnh có chủ đích (m5 ở ch9 là sổ bị sửa để giấu chuyến hàng, tức có chuyện thật).

## ky-ao chạy lại đủ 24 chương (`long-after-ky-ao-2`, main `be4cc30`)
24/24, kết truyện, 0,2558 USD thật (0,0107 mỗi chương; baseline ky-ao-2 0,2526 và 0,0105). Số từ `long_metrics_ky2.jsonl`, `after_metrics_ky2.jsonl`, `cost_decomp.txt`.

| | ky-ao-2 baseline | chạy lại |
|---|---|---|
| chương không đổi trạng thái | 10/24 | 8/24 (`stalled_wide` 7 so với 7) |
| quay lại nơi đã ở trong 3 chương trước | không | ch19 (Cảng Lơ → Rừng Rủ Sương; theo cốt truyện, không phải vòng) |
| chương kết bằng cảnh đứng yên | 2/23 | 3/23 |
| bộ lựa chọn "chờ" | 1/23 | 1/22 |
| từ thủ tục (đầu/giữa/cuối) | 1 / 4,75 / 0,5 | 0,6 / 8,5 / 1,9 |
| độ giống cặp âm tiết (đầu/giữa/cuối) | 0,067 / 0,060 / 0,073 | 0,066 / 0,055 / 0,061 |
| viết lại | 5 | 6 (lỗi: `overdue_thread` 2, `teller_does_not_know` 6) |
| cờ `standstill` / `idle` | `[4,5,9,10,14,15,16,20]` (tính lại trên dữ liệu cũ, bị đếm thiếu, xem trên) / không | `[4,8,9,17,18]` / không |
| `rejected.jsonl` | không có | 1 dòng (ch16) |

- **Chi phí** (ch1–23, `cost_decomp.txt`): Δ +0,0031 USD so với baseline, 97% do số lời gọi (+1 viết, +1 trích, +1 kiểm duyệt), giá mỗi lời gọi gần phẳng; trích +0,0025 vì +4,6% token vào. **Ở ky-ao, các thay đổi D-110..D-121 gần như không đổi chi phí**; mức tăng ở tu-tien (+0,0350 trên ch1–17) đến từ viết lại, không từ đề dài hơn.
- **Mốc** (`plan_vs_result.milestones`): m1 ch1 (1–2) đúng; m2 ch3 (4–6), m3 ch4 (7–9), m4 ch7 (10–12), m5 ch10 (13–15) sớm; m6 ch16 (16–18, cao trào "đối mặt với việc Đoàn Khương đứng sau") **đúng hạn**; m7 (20–23, cao trào "tới Bến Cầu Gãy và phải quyết định có dùng bản đồ để mở lại lối nối") **không được đánh dấu**; m8 (24, kết) cũng "missed" nhưng mốc kết **không được bộ trích theo dõi** (`pacing._pending_milestones` bỏ `ending`), nên "missed" ở m8 là hệ quả của cách báo cáo, không phải truyện bỏ mốc. Không có dấu mốc nào bị bộ trích từ chối (rỗng).
  - **m7: đọc tay ch20–23 thì nội dung mốc có diễn ra.** Ch20 Mai Thảo tới Bến Cầu Gãy, chém mối nối cầu, "nói chưa quyết định có dùng Bản đồ Nếp Gấp để mở lại lối nối"; ch22 bắt được bản đồ khi các nếp mực hiện; ch23 cô mở bản đồ cho lính xem lối dẫn về Bến Cầu Gãy "nơi có thể sửa lại các đường nối". Tức quyết định dùng bản đồ xảy ra ở ch22–23 trong khoảng 20–23, mà không có dấu. **Đây là bỏ sót của bộ trích (âm tính giả), chưa kiểm vì sao** (có thể bộ trích coi quyết định chưa trọn vì kết quả của việc mở lối nằm ở ch24). Hậu quả hiện chỉ là báo cáo "missed" sai; không có hiệu ứng ngược lên mục tiêu chương vì mốc chưa được đánh dấu vẫn tiếp tục được giục (đúng hướng).
  - Các dấu đã có ở ch1, 3, 4, 7, 10, 16 (6 dấu): chưa đọc tay thêm ngoài đã nêu; không có dấu từ chối.
- **Thủ tục**: từ thủ tục tăng ở ch9–12 (12, 14, 21, 21) và ch18 (9). Giống ky-ao-1 ch12 (29) và ky-ao-2 ch12–13: là đoạn sổ cảng/giấy tờ của thế giới này (m5 "sổ hàng ở Cảng Lơ bị sửa"); tăng mạnh hơn baseline ở đoạn giữa (8,5 so với 4,75). Chưa đọc hết văn bản để biết là vòng thủ tục hay cảnh có chủ đích.
- **Chương cuối**: ch23 đưa quyết định về bản đồ, ch24 là chương kết (không có tóm tắt/lựa chọn, đúng với `story_finished`); chưa đọc kỹ văn bản chương cuối, chưa chấm bằng giám khảo.
- **`rejected.jsonl` ch16** (`LLM_BAD_RESPONSE`, `choices.2: value_error`): thân thật có lựa chọn `inner` với `feeling` "quyết liệt" nhưng `about: []`; `ChoiceDraft._consistent` đòi nội tâm phải có `about`. Bộ lựa chọn ra đúng ở lần thử lại nên chương không dừng. **Cùng loại với lỗi D-123 đã sửa** (một lựa chọn sai bỏ cả bộ), chưa sửa phần nội tâm không có `about`: gợi ý một PR nhỏ cho `ChoiceDraft`. Không đổi code ở PR này.
- **Chờ lùi D-123**: `calls.jsonl` có 3 lời gọi `LLM_UNAVAILABLE` (seq 3 và 4 vai trích ở ch1, 4,2 giây và 0; seq 264 vai dàn ý ở ch23, 131,7 giây) và cả ba được thử lại thành công, truyện chạy tiếp tới ch24. `calls.jsonl` không ghi giây chờ nên chưa kiểm được khoảng chờ thật; chỉ biết không còn lỗi tạm nào dừng chuỗi như ch12 lần trước.

## Hạn chế
- tu-tien **không tới ch24** (dừng vì phần đặt trước của bench ở ch22, 21 chương): chưa có đánh giá chương cuối. ky-ao tới ch24 ở lượt chạy lại, nhưng lượt đó chạy trên mã khác lượt dừng ở ch12 (có D-123).
- Mỗi cấu hình một lần chạy; model có nhiễu; baseline có thể có nút lân cận trùng (D-117).
- Số cờ `standstill`/`idle` của baseline đếm thiếu (xem trên); không so sánh trực tiếp.
- Chất lượng văn không chấm bằng giám khảo (bài F) ở lượt này; đọc tay chỉ gồm 6 dấu mốc và 21 câu tóm tắt tu-tien.
- Nguyên nhân chi phí tăng (mục trên) chưa có đối chứng.
