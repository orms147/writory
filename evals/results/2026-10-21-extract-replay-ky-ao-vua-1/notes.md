# Nhận xét đọc tay: phát lại bộ trích trên ky-ao-vua-1 (D-82)

Người đọc: Claude, 21/10/2026. Lần chạy gốc: `evals/results/2026-10-21-run-ky-ao-vua-1/`. Đáp án khai trước khi gọi model: `answer_key.yaml` (sha256 trong `meta.json`).

## Cách làm
- Chương 6–10 của lần chạy gốc. Mỗi chương, mỗi bản gọi 2 lần, xen kẽ hai bản.
  - Bản `main` là `extract-2`, commit `9f0b013`.
  - Bản nhánh là `extract-3`, commit `0dd03d3`.
  - Cùng model và `extra` như sản phẩm: `openai/gpt-6-luna`, suy luận low, `max_tokens` 16000. Thử lại theo `limits.retries`. Hash config trong `meta.json`, trùng hash của lần chạy gốc.
- Đầu vào chương N:
  - trạng thái là gói chương 0..N-1 trong `truth_dump.json`;
  - danh mục và cạnh đang hiệu lực dựng như `ChapterRun._start`;
  - bản nhánh nhận thêm `ChapterGoals.threads` trên trạng thái đó.
  - Mỗi chương phát lại độc lập: gỡ ghi được ở chương trước của lần phát lại không chuyển sang chương sau.
- Khác sản phẩm: cả chương (hai cảnh nối lại) đi trong một lời gọi. Sản phẩm gọi mỗi cảnh một lần, và cảnh 2 thấy cạnh của cảnh 1.
- Script dùng một lần, để ngoài repo; mục này đủ để dựng lại. `results.jsonl` có gói trích ra, cạnh bị bỏ và điểm từng lượt. `calls.jsonl` có chi phí, token và model trả lời.
- Chi phí thật (usage của OpenRouter): 0,0188 USD cho 20 lời gọi. Bản main 0,0087 USD, bản nhánh 0,0101 USD. Trần đặt 0,05 USD, có giữ chỗ trước mỗi lời gọi.

## Kết quả

| | main (`extract-2`) | nhánh (`extract-3`) |
|---|---|---|
| Ô `must` ghi đúng | 2/6 | 6/6 |
| Gỡ giả (ô `must_not`, 28 ô mỗi bản) | 0 | 0 |
| Ô `may` có ghi | 1 | 11 |
| `RESOLVED_IN` bị code bỏ | 0 | 1 (câu trích không nguyên văn) |
| `RESOLVED_IN` không có câu trích | 3/3 | 0 |

Mạch ghi gỡ, từng lượt:

| Chương | main 1 | main 2 | nhánh 1 | nhánh 2 |
|---|---|---|---|---|
| 6 | — | — | dau_vet | — |
| 7 | — | — | dau_vet | dau_vet, mon_no |
| 8 | — | — | dau_vet, mon_no | dau_vet, mon_no |
| 9 | — | — | dau_vet, mon_no | dau_vet, mon_no |
| 10 | giao_uoc | giao_uoc, mon_no | dau_vet, mon_no, giao_uoc | dau_vet, giao_uoc (mon_no bị bỏ vì câu trích) |

- Bản main không ghi `RESOLVED_IN` nào ở chương 6–9, như lần chạy gốc. Điều này khẳng định chẩn đoán: văn có gỡ mà bộ trích bỏ sót.
- Bản nhánh ghi đúng cả ba ô chẩn đoán, cả hai lần:
  - `dau_vet_dau_gia` và `mon_no_tran_mac` ở chương 8;
  - `giao_uoc_nha_pho` ở chương 10.
- Không bản nào ghi gỡ mạch chưa gỡ (`so_phan_cho`; `giao_uoc_nha_pho` ở chương 6–9) hay ghi lại mạch đã gỡ (`doan_nguoi_luu_lac`).

## Đọc từng câu trích của bản nhánh
- **dau_vet_dau_gia.** Có 9 lần ghi. Mọi câu trích đều chỉ trả lời vế một của mạch: chuyện gì xảy ra với người dự đấu giá.
  - ch06: "những người còn sống đã rời khỏi chợ trước khi Huyền Kính lần tới".
  - ch07: "Những dấu chân cho thấy người dự đấu giá đã rời nơi ấy thành nhóm…".
  - ch08: "Lưu Tố Nguyệt đã hộ tống người dự đấu giá ra khỏi khu chợ…".
  - ch09 và ch10 cũng vậy.
  - Không câu nào trích vế hai (dấu vết dẫn tới mảnh thần khí), dù ch08:91 và ch09:129 có câu đó.
  - Ở ch08 câu trích có thật và đúng nghĩa. Ở ch06 thì vế hai chưa có trên trang mà mạch vẫn bị ghi gỡ. Model hiểu "chi tiết phụ còn bỏ ngỏ không giữ mạch mở" theo nghĩa rộng: coi vế hai là chi tiết phụ.
  - Trong sản phẩm (ghi tuần tự), mạch này sẽ được ghi gỡ ở chương 6. Theo đồng hồ thì đúng hạn (2–6), nhưng gỡ một nửa. Đáp án khai trước chấm ô này là `may`.
- **mon_no_tran_mac.**
  - ch08: "Vậy từ giờ, ngươi sẽ không còn tự chọn thay ta điều gì cần hy sinh." Đúng quyết định mạch đòi.
  - ch09: "Ta chưa tin ngươi vô điều kiện…". Đúng, là câu nhắc lại quyết định.
  - ch10 lượt 1: "Tôi không thể trả lại lòng tin cũ chỉ bằng một câu nhận tội…". Đúng.
  - ch07 lượt 2: "Ta không quay lại với ngươi lúc này." Đây là quyết định tạm ("lúc này"). Đáp án chấm `may`, nhưng đọc kỹ thì là gỡ sớm và lỏng.
  - ch10 lượt 2: câu trích không nguyên văn, code bỏ cạnh (G3).
- **giao_uoc_nha_pho.** ch10, cả hai lượt: "Ta không giao nó cho Huyền Kính." Đúng quyết định về số phận món đồ. Giao ước được đọc ngay trước đó (ch10:153).
- Các cạnh khác: số cạnh theo kiểu của hai bản gần như nhau (xem `edges_by_type` trong `results.jsonl`). Chưa chấm đúng sai các cạnh đó.

## Ghi chú thêm về bộ trích ở truyện dài
Từ agent bài A (PR #55), đọc `truth_dump.json` của lần chạy gốc, không thuộc phạm vi D-82:
- Gói chương 2 và 3 có 0 cạnh. Không cạnh nào bị bỏ, không có dự phòng: bộ trích trả rỗng.
- Nhân vật chính `KNOWS` bí mật Trần Mặc bán tin từ chương 9, trong khi trang lộ ở chương 6.
- Nhân vật chính `KNOWS` giao ước gia tộc Phó từ chương 10, trong khi trang lộ ở chương 8.

Đây là thêm bằng chứng bộ trích ghi thiếu ở truyện dài, không chỉ với `RESOLVED_IN`. Lần phát lại này chỉ chấm `RESOLVED_IN`.

## Kết luận và điều chưa kiểm
- Bản nhánh tốt hơn rõ ở việc ghi gỡ (6/6 so với 2/6), không thêm gỡ giả trên đáp án này. Đủ để chạy lại cả truyện (bước B, `evals/results/2026-10-21-run-ky-ao-vua-2/`).
- **Rủi ro còn lại:** mạch có hai vế bị ghi gỡ khi mới có câu trả lời cho một vế. Code không kiểm được nghĩa của câu trích. Có hai hướng, chưa làm:
  - đề khởi tạo viết mỗi mạch thành một câu hỏi;
  - đề bộ trích đòi câu trả lời cho mọi vế.
- **Chưa kiểm:**
  - Hiệu quả khi gọi theo từng cảnh như sản phẩm.
  - Phát lại tuần tự (gỡ ở chương trước chuyển sang chương sau).
  - Truyện khác, model khác.
  - Mỗi ô chỉ có 2 lượt: số nhỏ, chỉ nói được chiều hướng.
