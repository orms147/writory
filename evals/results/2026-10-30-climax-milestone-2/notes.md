# Phát lại bộ trích `extract-8` / `extract-11` trên chương đã lưu, n=2 (D-139): kết quả

Khai trước: `expectations.md` (commit `ed533b7`, trước mọi lời gọi; không sửa sau đó). Script `replay.py`, chạy từ `backend/` như docstring của nó. Đầu ra: `results.jsonl` (mốc model trả, mốc code nhận, lý do từ chối), `calls.jsonl` (token, chi phí), `meta.json`.

- **Commit của lần chạy:** `3be488579d29b1d28d08b582fc2900e38e2febd7` (`meta.json`, `dirty: false` cho `backend/` và `config/`).
- **Config:** sha256 gộp `194e9aa655c67f9d1041f05b3735c87aa7051436e9217a9b5905778067497518` (`bench_run.config_sha256` trên `config/`, ghi trong `meta.json`).
- **Model:** `openai/gpt-6-luna`, `reasoning.effort: low` (vai `extract`). Đề: `extract-8` sha256 `7864ec8235ed…`, `extract-11` `7e96880d562a…` (12 ký tự đầu).
- **Chi:** lần chạy này 40 lời gọi, 0,06271 USD (mỗi bản đề khoảng một nửa: 0,03135 và 0,03136), không lời gọi nào hỏng, không dừng vì trần, mọi lời gọi `finish_reason: stop`. Cộng lần chạy đầu (dưới): 0,014295 USD đã biết và một lời gọi không có `usage`. Tổng đã biết 0,077005 USD; lời gọi không rõ chi phí nhiều nhất cỡ lời gọi đắt nhất đã thấy (0,0033), nên tổng dưới 0,081, trong trần 0,10 đã duyệt.

## Lần chạy đầu chết giữa chừng
- Lần đầu (commit `ed533b7`, `--budget 0.10`) chết ở lời gọi thứ 8/40 (ky-ao ch24, `extract-11`, lần 2): `LLM_UNAVAILABLE: ReadTimeout` (hạn đọc 120 giây của client). Script chỉ ghi `results.jsonl` lúc cuối và không bắt lỗi này, nên đầu ra của 7 lời gọi đã xong bị mất; chỉ còn token và chi phí (`attempt1_calls.jsonl`).
- Sửa script (commit `3be4885`): ghi mỗi dòng kết quả ngay khi có; lỗi tạm (`LLM_UNAVAILABLE`, `LLM_TIMEOUT`) thử lại một lần sau 10 giây; hỏng lần hai hay lỗi khác thì ghi vào `failed` của meta rồi chạy tiếp; lời gọi hỏng được tính vào trần như một lời gọi đắt nhất đã thấy. Không đổi ca, đề, schema hay cách chấm; `expectations.md` giữ nguyên.
- Chạy lại toàn bộ 40 lời gọi với `--budget 0.08` (0,10 trừ phần đã chi và lời gọi không rõ của lần đầu), để tổng không vượt trần đã duyệt. Lần chạy lại không có lỗi nào. Kết quả dưới đây chỉ từ lần chạy lại.

## Kết quả từng ca
"Gốc" = dấu đã có trong lượt chạy gốc. Số dòng là dòng trong `chapters/chNN.md` của lượt gốc. "Không trả" = model không đưa mốc nào.

| Ca | Mốc | Gốc | `extract-8` lần 1 / lần 2 | `extract-11` lần 1 / lần 2 |
|---|---|---|---|---|
| tu-tien ch19 | m6 cao trào (20–22) | m6 | trả m6, **G3 từ chối** / trả m6, **G3 từ chối** | không trả / không trả |
| ky-ao ch24 | m7 cao trào (20–23) | không | nhận m7 (dòng 87) / không trả | nhận m7, 2 đoạn (dòng 75 + 97) / nhận m7, 2 đoạn (dòng 75 + 97) |
| ky-ao ch16 | m6 cao trào (16–18), m7 | m6 | nhận m6 (dòng 31) / nhận m6 (dòng 31) | nhận m6, 2 đoạn (dòng 31 + 49) / **không trả** |
| tu-tien ch11 | m4 bước ngoặt (12–13) | m4 | nhận m4 (dòng 99) / nhận m4 | **không trả** / nhận m4 (dòng 99) |
| ky-ao ch10 | m5 bước ngoặt (13–15) | m5 | nhận m5 (dòng 79) / nhận m5 | nhận m5 (dòng 79) / nhận m5, 2 đoạn (dòng 75 + 79) |
| tu-tien ch5 | m3 bước ngoặt (9–11) | m3 | không trả / không trả | không trả / nhận m3, 2 đoạn (dòng 35 + 37) |
| ngữ cảnh tu-tien ch18, ch17 (m6) | | không | không trả (cả 4 lời gọi) | không trả (cả 4 lời gọi) |
| ngữ cảnh ky-ao ch22 (m7) | | không | không trả / không trả | không trả / không trả |
| ngữ cảnh ky-ao ch23 (m7) | | không | **nhận m7** (dòng 111) / không trả | không trả / không trả |

Cộng lại: ở bốn ca đối chứng, `extract-8` nhận đúng mốc gốc 6/8 lần, `extract-11` 5/8. Ở hai ca mục tiêu, `extract-11` ra đúng hướng kỳ vọng 4/4 lần, `extract-8` 1/4. Ở chương ngữ cảnh, `extract-8` có 1 dấu mới, `extract-11` không có dấu nào. Câu trích mốc bị G3 từ chối: `extract-8` 2, `extract-11` 0. `extract-11` dùng câu trích nhiều đoạn 5 lần, cả 5 đều được nhận.

## K1–K5 và luật quyết (áp đúng như khai)
- **K1 đúng (2/2).** tu-tien ch19: `extract-11` không trả m6 cả hai lần (trong đầu ra của model, không chỉ là code không nhận).
- **K2 đúng (2/2).** ky-ao ch24: `extract-11` nhận m7 cả hai lần, đoạn 1 là quyết định (dòng 75), đoạn 2 là hậu quả "Phần bản đồ còn lại không thể chỉ đường quay về nữa." (dòng 97), đúng vùng khai trước.
- **K3 sai.** Đòi số lần `extract-11` nhận đúng mốc gốc ≥ `extract-8` ở mỗi ca đối chứng. ky-ao ch16: 1/2 so với 2/2 (vế riêng "ít nhất 1/2" thì đạt); tu-tien ch11: 1/2 so với 2/2. ky-ao ch10 (2/2 và 2/2) và tu-tien ch5 (1/2 và 0/2) đạt. `extract-11` không nhận mốc nào khác ở chương đối chứng.
- **K4 đúng.** Ở mọi chương ngữ cảnh, `extract-11` có 0 dấu; `extract-8` có 1 (ky-ao ch23).
- **K5 đúng.** Câu trích mốc bị G3 từ chối: `extract-11` 0, `extract-8` 2.
- **Tín hiệu tốt: không đạt**, vì K3 sai.
- **Tín hiệu xấu: không đạt.** `extract-11` không trả m6 ở tu-tien ch19 lần nào; có nhận m6 ở ky-ao ch16 (1/2); không có dấu mới ở ca đối chứng hay ngữ cảnh; K5 đúng.
- **Kết luận theo luật: không xác định.** Theo khai trước: không gộp mặc định, ghi lại và hỏi chủ dự án. Không sửa đề lần hai trong PR này.

## Đọc tay
**Đã kiểm** (đọc chương và `results.jsonl`):
- Mọi câu trích được nhận, kể cả từng đoạn của câu nhiều đoạn, có nguyên văn trong chương (code G3 đã kiểm; dòng ghi ở bảng).
- ky-ao ch24, `extract-11` (cả hai lần): dòng 75 "Dùng lối tới Bến Cầu Gãy. Tôi sẽ nói trước mặt lính rằng tôi chọn đường ấy, và tôi chịu trách nhiệm." là quyết định; dòng 97 là hậu quả không đảo được của việc xé dải đường về. Lần 1 đoạn 1 có cả gạch đầu dòng thoại "- ", vẫn nguyên văn. `extract-8` lần 1 nhận bằng dòng 87 (quyết định, không có hậu quả); lần 2 không trả.
- ky-ao ch16, `extract-11` lần 1: dòng 31 (sự thật được nói ra) cộng dòng 49 "Tôi không còn chờ chị đổi ý rồi quay sang giúp mình." (quan hệ đã đổi), đúng như đọc trước khi chạy. Lần 2 không trả m6, dù hậu quả có trên trang (dòng 41, 49, 61): đây là âm tính giả của `extract-11`.
- tu-tien ch11, `extract-11` lần 1 không trả m4 (bước ngoặt, câu dòng 99 rõ ràng, `extract-8` nhận 2/2): âm tính giả. Luật mới của bước ngoặt chỉ thêm "không cần chờ hậu quả".
- tu-tien ch19, `extract-8` cả hai lần trả m6 nhưng câu trích là nhiều dòng thoại nối bằng xuống dòng, bỏ qua dòng ở giữa (lần 1 bỏ dòng 137, 139, 143; lần 2 bỏ dòng 137), nên G3 từ chối. Ở D-129, `extract-8` nhận m6 ở đây cả hai lần bằng một câu (dòng 135). Vậy dấu sớm của `extract-8` vẫn còn ý định; lần này chỉ mất vì câu trích.
- ky-ao ch23, `extract-8` lần 1 nhận m7 bằng "Tôi chỉ thẳng vào lối mực dẫn về Bến Cầu Gãy." (dòng 111). Đọc quanh đó: Mai Thảo chỉ đường cho lính chạy khỏi cầu đang sập (dòng 109–113), lựa chọn cuối chương còn mở chuyện giao bản đồ (dòng 121); quyết định dùng bản đồ để mở lối nối chỉ có ở ch24 (như chẩn đoán `../2026-10-29-milestone-diagnosis/notes.md` mục 2). Dấu này sai: dương tính giả của `extract-8`.
- tu-tien ch5, `extract-11` lần 2 nhận m3 bằng dòng 35 (vệt sáng lóe theo tiếng chuông) cộng dòng 37 (câu của lượt gốc: áp lực nước dồn vào chốt phong ấn). Đúng mốc của lượt gốc. Cả hai lần `extract-8` không trả (ở D-129 nó nhận một lần).
- ky-ao ch10, `extract-11` lần 2 dùng hai đoạn, đoạn 1 "Một dòng khiến tôi dừng lại." (dòng 75) chỉ là câu dẫn; mốc vẫn đúng nhờ đoạn 2 (dòng 79). Không sai, nhưng cho thấy model có khi dùng nhiều đoạn khi không cần.

**Suy luận (chưa kiểm):**
- Phần đề về cao trào làm đúng việc của nó: không còn dấu sớm ở tu-tien ch19, dấu ky-ao ch24 có cả hậu quả, không có dương tính giả ở chương ngữ cảnh. Câu trích nhiều đoạn bỏ hẳn lỗi ghép của D-129 (0 lần G3 từ chối, 5/5 câu nhiều đoạn được nhận).
- Hai lần mất dấu ở đối chứng (ky-ao ch16 lần 2, tu-tien ch11 lần 1) có thể là nhiễu: chính `extract-8` cũng đổi kết quả giữa hai lần ở ky-ao ch24 và ky-ao ch23, và ở tu-tien ch5 nó ra khác D-129. Cũng có thể đề dài hơn làm model dè dặt hơn với mọi mốc, như D-129 đã nghi ở tu-tien ch5. Với n=2 không tách được hai khả năng.
- Mất dấu cao trào đúng hạn (ky-ao ch16 lần 2) là cái giá có thật của luật "đòi hậu quả": khi model không chắc về hậu quả thì nó bỏ mốc. Hại của âm tính giả ở mốc cao trào là đề dàn ý và đề viết giục lại cao trào đã diễn ra (D-116); hại của dương tính giả là coi cao trào chưa diễn ra là đã xong (D-129). Cân hai cái hại này là việc của chủ dự án, không suy ra được từ phép đo này.

## Lưu ý
- n=2 vẫn là nhiễu, như luật khai trước nói. Kết quả là "tín hiệu", không phải "đã đo".
- Phát lại một lời gọi cho cả chương, khác sản phẩm (mỗi cảnh một lời gọi); danh mục không có `Lie` của lựa chọn (`expectations.md`).
- Lời gọi lặp (lần 2) rẻ hơn khoảng ba lần (trung bình 0,00075 so với 0,00239 USD mỗi lời gọi) nhờ cache phía nhà cung cấp: ở mọi lời gọi lần 2, `cached_tokens` trong `calls.jsonl` gần bằng `prompt_tokens`.

## Quyết định sau lần chạy đầu
Theo luật khai trước, kết quả là không xác định, nên mặc định không gộp. Chủ dự án chọn đo thêm trên ca đối chứng (30/10/2026). Luật của lần đo thêm được khai trước ở cuối `expectations.md` (commit `b1f5b2d`, trước mọi lời gọi của lần đo thêm).

## Đo thêm ca đối chứng, n=6 (`control-n6/`)
- **Commit của lần chạy:** `b1f5b2dc6122e9f60533d99a6d195566881ba38f` (`control-n6/meta.json`, `dirty: false`). Nhánh đã gộp origin/main (D-138) giữa hai lần chạy.
- **Config:** sha256 gộp `13c01f720c75f52bd4f5ec290b6c292c00abb5635d39fd496226d2267d8bfc6a`. Khác lần chạy đầu chỉ ở `config/models.yaml`, chỗ thêm vai `overreach` của D-138 (`git diff 3be4885 b1f5b2d -- config`); vai `extract` không đổi model, không đổi mức suy luận.
- **Đề:** sha256 của chữ đề hai bản đề trùng lần chạy đầu. Số token đề của từng ca và từng bản đề cũng trùng đúng lần chạy đầu (`calls.jsonl` của hai thư mục), nên phần đề dựng từ dữ liệu cũng không đổi. Đây là suy từ số token, không phải so từng byte.
- **Model:** `openai/gpt-6-luna`, `reasoning.effort: low`.
- **Chi:** 32 lời gọi, 0,035138 USD. Không lời gọi nào hỏng, không dừng vì trần (trần 0,08). Cả phép đo D-139: 0,112143 USD đã biết (0,014295 lần chạy hỏng, 0,06271 lần chạy đầu, 0,035138 lần đo thêm), cộng một lời gọi không rõ chi phí của lần chạy hỏng (nhiều nhất cỡ 0,0033).
- **Lệnh:** như phần bổ sung của `expectations.md` (`--only 2- --first-rep 3 --repeats 4 --budget 0.08 --out …/control-n6`).

### Gộp lần 1–6 (`python evals/results/2026-10-30-climax-milestone-2/pool.py`)
| Ca | `extract-8` nhận đúng | `extract-11` nhận đúng |
|---|---|---|
| ky-ao ch16 (m6 cao trào) | 6/6 | 3/6 |
| tu-tien ch11 (m4 bước ngoặt) | 6/6 | 5/6 |
| ky-ao ch10 (m5 bước ngoặt) | 6/6 | 6/6 |
| tu-tien ch5 (m3 bước ngoặt) | 3/6 | 4/6 |
| **Gộp** | **21/24** | **18/24** |

Không bản đề nào có dấu của mốc khác mốc gốc ở chương đối chứng. Câu trích mốc bị G3 từ chối: 0 và 0. Mọi lời gọi đều có cặp, đủ 24 cặp gộp mỗi bản đề.

### Luật của lần đo thêm (áp đúng như khai)
- **Tốt: không đạt.** R11 − R8 = 18 − 21 = −3, không ≥ −1. R11(16) − R8(16) = 3 − 6 = −3, không ≥ −1.
- **Xấu: đạt.** R11(16) = 3 ≤ R8(16) − 3 = 3. Điều R11 ≤ R8 − 4 thì không đạt (−3).
- **Kết luận: tín hiệu xấu.** Theo khai trước: không gộp `extract-11`; gỡ code và đề khỏi PR, giữ kết quả đo; D-139 ghi "đã thử, không dùng".
- Điều "dấu sai" của phần bổ sung viết chưa rõ: "câu trích (hay một đoạn) không cho thấy điều mốc mô tả" đọc được theo cả câu hay theo từng đoạn. Đọc theo cả câu thì `extract-11` không có dấu sai nào. Đọc theo từng đoạn thì có đoạn chỉ là ngữ cảnh (xem dưới). Kết luận không đổi theo cách đọc, vì riêng điều của ky-ao ch16 đã đủ để là xấu.

### Đọc tay (lần 3–6)
**Đã kiểm:**
- ky-ao ch16, `extract-11`: lần 3 và 5 nhận m6 bằng dòng 31 (Tạ Vân nói ra Đoàn Khương đứng sau vụ bắt) cộng dòng 49 (Mai Thảo thôi chờ Tạ Vân giúp). Đúng. Lần 4 và 6 model không trả mốc nào, dù hậu quả có trên trang (dòng 41, 49, 61). `extract-8` nhận m6 cả 4 lần bằng dòng 31.
- tu-tien ch11, `extract-11`: nhận m4 cả 4 lần bằng dòng 99 ("Ta là người đưa tin của Minh Ước Giữ Ấn…"). Lần 6 thêm đoạn thứ hai là dòng 101–107 (Thẩm Mặc Ngôn đòi hộp, Ninh Tuyết Anh giữ hộp): một đoạn liền nhiều dòng, nguyên văn, nhưng chỉ là ngữ cảnh, không nói điều mốc m4 mô tả.
- ky-ao ch10, `extract-11`: nhận m5 cả 4 lần, 2 hay 3 đoạn: dòng 77 (ô sổ bị cạo, viết đè) và dòng 79; lần 3 và 5 có thêm câu dẫn dòng 75 "Một dòng khiến tôi dừng lại.", câu này tự nó không nói điều mốc mô tả.
- tu-tien ch5: `extract-11` nhận m3 ở lần 4, 5, 6 bằng dòng 37 (có lần thêm dòng 35); `extract-8` nhận ở lần 4, 5, 6 bằng câu của lượt gốc ở dòng 37. Ở lần 3 cả hai bản đề đều không trả mốc nào.

**Suy luận (chưa kiểm):**
- Luật "cao trào phải có cả hậu quả" làm mất dấu cao trào kiểu đối mặt với sự thật một nửa số lần (ky-ao ch16: 3/6 so với 6/6), dù hậu quả có trên trang. Model hình như không chắc "thôi chờ giúp, bỏ đi, xoá dấu" có tính là "điều đã đổi hẳn" không, nên bỏ mốc. Đó cũng là chỗ `extract-9` hỏng ở D-129. Hai lần thử với hai cách viết luật cùng hỏng ở ca này.
- Câu trích nhiều đoạn chạy đúng như thiết kế: 0 lần G3 từ chối trên 36 lời gọi `extract-11` (20 lần chạy đầu, 16 lần đo thêm), ở ca đối chứng không có dấu sai về mốc, không có dấu của mốc khác. Nhưng model dùng nhiều đoạn cả khi một đoạn là đủ, và có đoạn chỉ là ngữ cảnh: trần số đoạn và số chữ tối thiểu chặn được câu ghép từ mảnh vụn, không chặn được đoạn thừa.
- Ở bước ngoặt, `extract-11` ngang `extract-8` (15/18 so với 15/18 trên ba ca bước ngoặt gộp lại). Phần mất nằm gần hết ở ca cao trào.

## Quyết định sau phép đo
Theo luật khai trước của lần đo thêm (tín hiệu xấu): không gộp `extract-11` và code câu trích nhiều đoạn; bộ trích giữ `extract-8` (D-139). PR chỉ còn kết quả đo này. Chữ đề `extract-11` ở `extract11_system_prompt.txt`. Code (schema `quotes`, `graph.quote_parts_in_text`, cách lưu, test) ở commit `b1f5b2d` của nhánh `feature/climax-milestone-2`: `replay.py` dùng code đó, nên chạy lại đúng như lần đo cần checkout commit này; `pool.py` chỉ đọc `results.jsonl`.
