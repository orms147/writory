# Cao trào bằng code (D-142) đo thật trên Muse: khai TRƯỚC khi chạy

Người đọc: Claude điều phối và chủ dự án, 30/10/2026. **Chưa có lượt nào gọi model; chưa có kết quả.** Khi chạy xong, kết quả ghi ở `notes.md` cùng thư mục và KHÔNG sửa các mục dưới đây. Main lúc soạn: `230e3da`. Việc chạy chờ D-140 (client Meta, nhánh `feature/meta-bench-provider` của session 1) gộp.

## Câu hỏi
D-142 đổi hai thứ (ứng viên cho dấu cao trào sớm; mục tiêu chương đòi hậu quả khi cao trào đã xong). Phép tính lại không gọi model (`../2026-10-30-climax-code/notes.md`) chỉ cho thấy chữ đề đổi ở đâu. Ba điều chưa biết: **(a)** bộ trích có đánh dấu lại ứng viên trong khoảng không; **(b)** model viết có viết hậu quả trên trang ở các chương `climax_aftermath` không; **(c)** có hồi quy gì ở truyện Dài không.

## Thiết kế
- **Model:** mọi vai `meta/muse-wonder-1.0` (chủ dự án: dùng credit Meta làm model đo chính; Luna chỉ xác nhận nhỏ trước khi đưa vào sản phẩm), cấu hình `evals/config/meta` của D-140 (mức suy luận theo `config/models.yaml`; `none` gửi thành `minimal`). **Mọi số đo ở đây là của Muse; không so thẳng với lượt Luna cũ** (khác model, khác giá, khác nhịp viết), nên có nhánh đối chứng cùng Muse.
- **Mã:** MỘT commit cho mọi lượt (main sau khi D-140 gộp; ghi SHA ở `notes.md`). Không merge giữa chừng.
- **Nhánh đối chứng "như trước D-142" không cần commit khác:** `ctrl` = cùng mã, `--prompt-variant climax-old` (`evals/scenarios/prompts/climax-old/goals.yaml`: câu của cao trào đã xong trở về đúng chữ `milestone_done` cũ) và `limits.yaml` của bản sao config đặt `climax_aftermath_chapters: null` (không liệt kê cao trào ngoài khoảng). Đã kiểm không gọi model: trên `long-after-ky-ao-2` ch17, ch18 `ctrl` ra đúng câu cũ, `treat` ra câu hậu quả, ch19 cả hai không có dòng cao trào. Phần ứng viên (dấu trước khoảng) là mã, không tắt được: nếu một lượt `ctrl` có dấu cao trào sớm thì luật ứng viên áp cho cả hai nhánh, và hai nhánh chỉ khác ở câu hậu quả; ghi rõ ở `notes.md`.
- **Thế giới:** `--setup-from` các khởi tạo đã có, cùng seed của đề (không `--seed`), nên các nhánh cùng kế hoạch:
  - **Pha 1, ky-ao** (`long-ky-ao-hanh-trinh`, seed 20261031, `--setup-from ../evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1`, kế hoạch 24 chương, cao trào m6 khoảng 16–18, m7 khoảng 20–23): `ctrl` và `treat`, mỗi nhánh một lượt, **`--chapters 20`**. Lý do: bốn lượt Luna trước đều đánh dấu m6 đúng ngày đầu khoảng (ch16), nên chắc có cao trào đã xong và đúng hai chương hậu quả (ch17, ch18) cộng hai chương sau để xem còn hậu quả không (ch19, ch20); không cần chạy ch21–24. Không có chương ngoài khoảng được liệt kê (16 + 2 = 18), nên Pha 1 đo câu mới, chưa đo `climax_aftermath_chapters`.
  - **Pha 2, tu-tien** (`long-tu-tien`, seed 20261022, `--setup-from ../evals/results/2026-10-29-run-long-tu-tien-3`, cao trào m6 khoảng 20–22): chỉ `treat`, **`--chapters 24`** (hết kế hoạch, có kết truyện). Lý do: đây là thế giới có dấu cao trào sớm (ch19) với Luna, nên là nơi duy nhất (a) có thể xảy ra, và cao trào xong ở ch21–22 thì hậu quả rơi ra ngoài khoảng (đo `climax_aftermath_chapters`). Không chạy `ctrl` ở thế giới này: (a) là hành vi của bộ trích, mã y nhau ở hai nhánh, còn (b) đã có đối chứng ở Pha 1.
  - Thứ tự: `ctrl-ky`, `treat-ky`, `treat-tu` (xen kẽ để trôi dạt của model rải đều). Một script nền nối tiếp, giữ máy không ngủ, kiểm không còn chuỗi `bench_run` khác dùng cùng key; lượt chết giữa chừng thì `--resume` (D-124), cùng commit nên không cần `--resume-allow-drift`.
- **Dry-run bằng model giả (đã làm, 0 USD):** hai nhánh `--dry-run --chapters 20` chạy hết trên main `230e3da`, hash `limits.yaml` khác nhau, `outline-13`. Giới hạn: thế giới giả không bao giờ đánh dấu cao trào, nên không chứng minh dòng hậu quả bật; việc đó đã kiểm bằng tính lại trên truyện đã lưu.

## Chỉ số khai trước
**(a) Đánh dấu lại ứng viên.** Chỉ đếm ở các lượt `treat` (cả hai pha), từ `truth_dump.json` (dấu `milestones` ở nút `Chapter`) và `plan_vs_result.milestones` (`done_chapter`, `candidate_chapter`): với mỗi mốc cao trào, `early_mark` (có dấu trước `from_chapter`), `confirmed` (sau đó có dấu trong khoảng), `never_marked` (hết lượt chạy mà không có dấu từ khoảng trở đi, mốc đã tới hạn). Kết quả:
- **Không thử được** nếu không lượt nào có `early_mark` (không nói gì về ứng viên; ghi số `never_marked`).
- **Đạt** nếu có ít nhất một ứng viên `confirmed`. **Không đạt** nếu có `early_mark` mà không cái nào `confirmed` (khi đó đọc tay ch của khoảng và ghi cao trào thật có diễn ra trên trang không, kèm câu trích).
- Số dấu cao trào sớm của Muse (`early_mark` trên số mốc cao trào có dấu) báo cáo riêng, không đưa vào luật.

**(b) Hậu quả trên trang.** Mục chấm = mỗi chương `d+1` và `d+2` của mỗi lượt Pha 1 (d = chương cao trào xong, đọc từ dấu; ctrl và treat mỗi nhánh d riêng), cộng ch `d+3`, `d+4` (báo cáo, không vào luật), và ở Pha 2 các chương `d+1`, `d+2` của `treat-tu`. Chấm **mù** bằng Muse, `judge_aftermath.py` cùng thư mục: mục trộn ngẫu nhiên (seed 20261030), người chấm thấy câu mô tả cao trào, chương nó xảy ra và văn chương, KHÔNG thấy nhánh hay tên lượt; mỗi mục một nhãn đúng một trong `HẬU QUẢ`, `DIỄN LẠI`, `KHÁC` (câu hỏi nguyên văn trong script, in ở `request.json`); nhãn đếm cơ học (`count`), khoá giải nhãn chỉ mở sau đó. Hai chương `d+1`, `d+2` của Pha 1:
- **treat TỐT HƠN ctrl** khi: (số `HẬU QUẢ` của treat) ≥ (số của ctrl) + 1 VÀ (số `DIỄN LẠI` của treat) ≤ (số của ctrl).
- **treat TỆ HƠN** khi: (số `HẬU QUẢ` của treat) ≤ (số của ctrl) − 1 HOẶC (số `DIỄN LẠI` của treat) ≥ (số của ctrl) + 1.
- Còn lại: **chưa phân biệt được** (n = 2 chương mỗi nhánh; rất thưa, ghi rõ).
- Đọc tay của Claude trên đúng các chương đó (mỗi chương một dòng, có câu trích `chNN.md:dòng`) ghi riêng; không vào luật, nhưng nếu trái với giám khảo ở ≥ 2 chương thì ghi là "giám khảo và đọc tay không khớp" và không kết luận (b).
- Pha 2: nhãn của `d+1`, `d+2` báo cáo; so với Pha 1 chỉ để mô tả.

**(c) Chặn hồi quy** (Pha 1, treat so với ctrl; mỗi chặn là điều kiện cần cho "treat tốt hơn" và, với g1–g2, là điều kiện để không "tệ hơn"):
- **g1** cả hai lượt ghi đủ 20 chương, không dừng vì lỗi hay trần (`report.json.status == "done"` hoặc dừng đúng ở `--chapters`).
- **g2** `early_reveal` tìm thấy (`report.issues.found`, khoá chứa `early_reveal`) của treat ≤ ctrl + 2.
- **g3** chi phí mỗi lời gọi (`cost.total_usd / calls.total`) của treat ≤ 1,15 × ctrl.
- **g4** mốc đúng hạn (`milestones` có `status == "on_time"` trong số mốc đã tới hạn) của treat ≥ của ctrl − 1.
- **g5** `rewrites` của treat ≤ ctrl + 3.
Pha 2 (không có ctrl): chỉ ghi `story_finished`, `status`, `early_reveal` tìm thấy, chi phí mỗi lời gọi, `rewrites`; không áp chặn, không so với Luna.

## Luật quyết định và hành động đề xuất (chủ dự án quyết)
- **TỐT HƠN:** (b) treat tốt hơn ctrl, g1–g5 đạt, và (a) không "không đạt". Hành động: giữ D-142; xác nhận nhỏ bằng Luna trước khi tin ở sản phẩm (một lượt ky-ao ch1–20 mỗi nhánh khoảng 0,2 USD OpenRouter, tính từ 0,0105 USD mỗi chương của `long-after-ky-ao-2`).
- **TỆ HƠN:** (b) treat tệ hơn ctrl, hoặc g1 hay g4 vi phạm. Hành động: mở PR đặt lại câu `climax_aftermath` về chữ `milestone_done` (mặc định) và `climax_aftermath_chapters: null`; giữ phần ứng viên nếu (a) không xấu.
- **CHƯA PHÂN BIỆT ĐƯỢC** (kết quả dự kiến vì n = 2 chương mỗi nhánh, một lượt mỗi nhánh): giữ D-142 như đã gộp, ghi rõ không có bằng chứng thêm; không chạy thêm lượt nếu chưa có ngân sách.
- Chặn g2, g3, g5 vi phạm riêng thì ghi lại và báo, không tự thành "tệ hơn".

## Giới hạn đã biết (khai trước)
Một lượt mỗi nhánh; Muse không tất định nên hai lượt cùng cấu hình có thể khác nhau lớn; hai chương mỗi nhánh làm (b) rất thô; giám khảo là cùng họ model với người viết (Muse chấm Muse); (a) có thể "không thử được" nếu Muse không đánh dấu sớm. Client Meta (D-140) chưa chạy thật, nên lượt đầu có thể lộ lỗi của client (strict schema, `max_tokens`, `usage`); nếu client sai thì dừng, không đo bằng số của client sai.

## Chi phí ước tính (Meta, chưa chạy)
Nguồn: token vào và ra của các lượt Luna `long-after-ky-ao-2` (24 chương) và `long-after-tu-tien` (21 chương) trong `calls.jsonl`, cộng dồn tới chương cần, nhân giá Muse ở `evals/scenarios/bakeoff/judge.yaml` (vào 4, vào đã cache 0,2, ra 20 USD/1 triệu token). Luna báo 21–22% token vào là cache (`cached_tokens`); giả định Muse cache tương tự (chưa kiểm). Token ra của Muse gồm cả suy luận nên có thể gấp 1–3 lần của Luna (ghi chú chủ dự án về Muse: tốn hết `max_tokens` cho suy luận nếu không đặt effort thấp); khoảng dưới = ra ×1 và có cache, giữa = ra ×2 và có cache, trên = ra ×3 và không cache.

| lượt | tới chương | token vào (Luna) | token ra (Luna) | dưới | giữa | trên | `--budget` đề xuất |
|---|---|---|---|---|---|---|---|
| ky-ao `ctrl` | 20 | 1,43 triệu | 137 nghìn | 7,4 | 10,1 | 13,9 | 14 |
| ky-ao `treat` | 20 | 1,43 triệu | 137 nghìn | 7,4 | 10,1 | 13,9 | 14 |
| tu-tien `treat` | 24 | khoảng 2,4 triệu (ngoại suy từ ch22: 2,02 triệu) | khoảng 216 nghìn | 12,0 | 16,3 | 22,5 | 23 |
| chấm (b), đọc mù | khoảng 9–12 mục | khoảng 60 nghìn | nhỏ | 0,5 | 0,8 | 1,2 | 3 (trần của `judge_aftermath.py`) |
| **Tổng** | | | | **27** | **37** | **51** | **54 (cộng các trần)** |

- Ước tính giữa 37 USD Meta; trần cộng lại 54 USD. **Cần chủ dự án xác nhận ngân sách Meta còn lại** (tôi không biết số đã tiêu: sổ ghi nhớ của tôi chỉ có khoảng 4,8 USD tới tối 29/10, trần giao 130 USD, và khoá hết hạn trong vài ngày). Nếu thiếu: bỏ Pha 2 (cắt 12–23 USD, mất (a)) hoặc chạy Pha 1 tới `--chapters 18` (cắt khoảng 1,5 USD mỗi nhánh nhưng mất ch19–20).
- Giữ chỗ ngân sách của `bench_run` tính theo trường hợp xấu nhất mỗi lời gọi (`max_tokens_per_call` 16000 × 20 / 10⁶ ≈ 0,32 USD mỗi lời gọi chưa tính phần vào), nên `--budget` phải rộng hơn chi phí thật (hệ số khoảng 1,4 như các lượt Dài trước); `--concurrency` mặc định là 1.
- Thời gian: Luna chạy 24 chương mất khoảng 36 phút; Muse chưa đo (suy luận nhiều hơn nên chậm hơn, chưa biết bao nhiêu). Không gọi model trả tiền ở bước chuẩn bị này.

## Lệnh dự kiến (chưa chạy; sau khi D-140 gộp)
```
cd backend
# thư mục config ctrl: cp -r ../evals/config/meta <tạm>; cp ../config/limits.yaml <tạm>/limits.yaml;
#   sed -i 's/^\(\s*climax_aftermath_chapters:\).*/\1 null/' <tạm>/limits.yaml     (diff với config/limits.yaml phải đúng một dòng)
uv run python -m writory.pipeline.bench_run --scenario ../evals/scenarios/story_run/long-ky-ao-hanh-trinh.yaml \
  --setup-from ../evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1 --chapters 20 --budget 14 \
  --config-dir <tạm> --prompt-variant climax-old --label ckr-ky-ctrl          # ctrl
# treat: như trên, --config-dir ../evals/config/meta, bỏ --prompt-variant, --label ckr-ky-treat
# Pha 2: --scenario .../long-tu-tien.yaml --setup-from ../evals/results/2026-10-29-run-long-tu-tien-3 --chapters 24 --budget 23 --config-dir ../evals/config/meta --label ckr-tu-treat
# số đo: python ../evals/results/2026-10-30-climax-code-real/judge_aftermath.py pack|judge|count (spec.json khai sau khi biết d)
```

## Bổ sung trước khi chạy (30/10/2026, sau khi D-140 gộp; main `b65510e`). Các mục trên không đổi.
- **Config gộp từng khoá (D-140):** thư mục config bộ đo chỉ chứa phần khác `config/`, nên `ctrl` là một thư mục nhỏ thay cho bản sao toàn bộ `limits.yaml` ở mục "Lệnh dự kiến" phía trên: `models.yaml` (sao nguyên `evals/config/meta/models.yaml`, vì thiếu file này loader lấy `config/models.yaml` của Luna) và `limits.yaml` chỉ có `cost_usd` của Meta (0,80 / 3,20 / 40,0) và `context.climax_aftermath_chapters: null`. Đã kiểm bằng `load_config`: config gộp của `ctrl` và `treat` khác đúng một khoá (`context.climax_aftermath_chapters`, 2 so với null), cùng `models.roles`, cùng trần Meta. `treat` dùng thẳng `--config-dir ../evals/config/meta`.
- **Thay đổi mã nhỏ ở nhánh này để kiểm được cờ từ `meta.json`:** `CONTEXT_FLAGS` của `bench_run` thêm `climax_aftermath_chapters`, nên `meta.json.context_flags` ghi giá trị đã dùng (2 hay null); test `test_meta_records_the_three_context_flags` cập nhật. Mọi lượt chạy trên đúng một commit của nhánh sau khi thay đổi này nằm trong; không merge giữa chừng.
- **Dry-run lại (0 USD)** với hai thư mục config trên, `--chapters 20`: chạy hết; `meta.json` ghi `provider: meta`, model viết `meta/muse-wonder-1.0`, hash `limits.yaml` khác nhau ở hai nhánh và hash `models.yaml` giống nhau, `prompt_variant: climax-old` chỉ ở `ctrl`.
- **Trần per_story của Meta (40) so với ước tính:** lượt tu-tien dài nhất ước tính trên 22,5 USD < 40; trần chương 3,20 và cảnh 0,80 cao hơn chi phí cảnh/chương Luna nhân 40 (0,0033 và 0,015 nhân 40 = 0,13 và 0,6) nên không chặn trước `--budget`.
- **Ước tính lại từ lượt thử Muse (`../2026-10-30-run-meta-thu/`):** ba bước khởi tạo ra 3518 token so với 1402–1606 của Luna ở các bước tương ứng (`ab-*-setup`), tức khoảng **2,2 đến 2,5 lần**; session 1 báo khoảng 38% token ra là suy luận. `cached` của Meta là 0 ở cả ba lời gọi, nhưng các lời gọi đó ngắn (dưới ~1.200 token vào) nên chưa biết cache có hoạt động ở lời gọi dài không. Vì vậy bảng giữa dùng token ra ×2,4 và KHÔNG cache; bảng dưới giữ ×2 có cache 21%; bảng trên giữ ×3 không cache (như trước).

  | lượt | dưới | giữa | trên | `--budget` |
  |---|---|---|---|---|
  | ky-ao `ctrl`, tới ch20 | 10,1 | 12,3 | 13,9 | 14 |
  | ky-ao `treat`, tới ch20 | 10,1 | 12,3 | 13,9 | 14 |
  | tu-tien `treat`, tới ch24 | 16,4 | 19,9 | 22,5 | 23 |
  | chấm (b) | 0,5 | 0,8 | 1,2 | 3 |
  | **Tổng** | **37** | **45** | **52** | **54** |

  Ước tính giữa tăng từ 37 lên 45 USD. Rủi ro đã thấy: `--budget` 14 và 23 sát ước tính trên (13,9 và 22,5); nếu chi phí thật vượt, `bench_run` dừng đúng ở trần và chạy tiếp bằng `--resume` cần nâng trần. Tôi sẽ không tự nâng trần: dừng và báo.
- **Thứ tự key Meta (điều phối xếp):** (1) PR #127 của session 2 (~1,5 USD), (2) người kể (~12 USD), (3) phép đo này. Không chạy trước khi điều phối báo tới lượt.
- **Lệnh (thay mục "Lệnh dự kiến"; trong `backend/`, `PYTHONIOENCODING=utf-8`):**
  ```
  CTRL=<thư mục tạm>   # mkdir; cp ../evals/config/meta/models.yaml $CTRL/; limits.yaml như trên
  uv run python -m writory.pipeline.bench_run --scenario ../evals/scenarios/story_run/long-ky-ao-hanh-trinh.yaml \
    --setup-from ../evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1 --chapters 20 --budget 14 \
    --config-dir $CTRL --prompt-variant climax-old --env-file <.env> --label ckr-ky-ctrl
  # treat: --config-dir ../evals/config/meta, bỏ --prompt-variant, --label ckr-ky-treat, cùng --budget 14
  # Pha 2: --scenario .../long-tu-tien.yaml --setup-from ../evals/results/2026-10-29-run-long-tu-tien-3 --chapters 24 \
  #        --budget 23 --config-dir ../evals/config/meta --label ckr-tu-treat
  ```

## Trần `--budget` nâng lên (30/10/2026, điều phối quyết, ghi TRƯỚC lời gọi đầu tiên)
Lý do (điều phối): trần 14 và 23 sát ước tính trên (13,9 và 22,5); lượt bị cắt giữa chừng tốn tiền hơn là nâng trần một chút. **Trần mới:** ky-ao `ctrl` 16, ky-ao `treat` 16, tu-tien `treat` 26, chấm (b) 3; **tổng trần 61 USD Meta** (trước đó 54). Ước tính chi phí không đổi (37 / 45 / 52 USD); chỉ thêm khoảng đệm cho giữ chỗ ngân sách. Chạm trần thì vẫn dừng và báo điều phối, không tự nâng thêm. Các lệnh ở mục trên dùng `--budget 16`, `16`, `26` thay cho `14`, `14`, `23`.
