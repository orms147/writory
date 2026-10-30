# Khai trước: người kể đọc đoạn trên trang, `narrator-3` so với `narrator-4` (D-143)

Khai TRƯỚC khi gọi model thật: commit chứa bản này đi trước mọi lời gọi. Chưa có lời gọi trả tiền nào; mọi
số dưới đây là từ code và model giả. Soạn: Claude (nhánh `feature/narrator-page-passages`), 30/10/2026.
Chờ chủ dự án duyệt trước lượt chạy thật.

## Câu hỏi
Trên truyện dài, bộ trích bỏ sót nhiều sự thật nên sổ tay (`player_view`) thiếu điều người chơi đã đọc
(`evals/results/2026-10-22-memory-ky-ao-vua-1/notes.md`, `…-facts-s3/notes.md`). Cho người kể đọc thêm vài
đoạn văn của các chương đã đọc, tìm theo câu hỏi (đề `narrator-4`), thì người kể có trả lời đúng nhiều hơn
chỉ đọc sổ tay (`narrator-3`) không, mà không lộ và không trả lời sai nhiều hơn?

## Hai đường được so
- `narrator-3`: `limits.narrator_pages.top_k` ép về 0; đề và tin nhắn y như trước D-143 (test băm chữ vai
  system, `tests/unit/test_narrator_pages.py::test_switched_off_the_messages_are_exactly_narrator_3`).
- `narrator-4`: `limits.narrator_pages` của commit chạy, không đổi (ghi ở `meta.json`, `narrator_pages`).
  Đổi số trước khi chạy thì khai lại ở đây.
- Cả hai: đúng `pipeline/narrator.ask_narrator_reply` của sản phẩm (sổ tay, mã công khai, kiểm mã mục, bộ
  dò lộ, lưới úp mở); bài đo không qua kiểm duyệt và không áp trần số câu mỗi chương.

## Model và thứ tự chạy
1. **Lượt chính: Meta Muse**, qua client bài đo của D-140 (nhánh khác đang làm; lúc khai, `main` chưa có).
   Cờ chọn client và giá giữ chỗ của Muse ghi vào đây (phần "Bổ sung trước khi chạy") khi nhánh đó gộp,
   trước lời gọi đầu. Model và mức suy luận của vai `narrator` ghi ở `meta.json`.
2. **Xác nhận nhỏ: Luna** (`openai/gpt-6-luna`, vai `narrator` hiện hành của `config/models.yaml`), chỉ
   chạy khi lượt chính đã xong.

## Bài 1: bài E, cổng lộ (bắt buộc)
- Đề: `questions-v2.yaml` (truyện mẫu, có nhóm sổ tay đệm) và `questions-tu-tien-1.yaml` +
  `plan-tu-tien-1.yaml` (truyện do pipeline viết). `--samples 3`. **Không** `--judge`: giám khảo chỉ thấy
  sổ tay, lệnh từ chối khi bật đoạn trên trang.
- Lệnh (lượt chính thêm cờ client Meta của D-140):
  ```bash
  cd backend
  uv run python -m writory.pipeline.bench_e run --label passages-v2 --questions-file questions-v2.yaml --samples 3 --budget <USD>
  uv run python -m writory.pipeline.bench_e run --label passages-tu-tien-1 --questions-file questions-tu-tien-1.yaml \
      --plan-file plan-tu-tien-1.yaml --samples 3 --budget <USD>
  ```
- **Luật:** lộ ở câu cuối (bộ chấm chặt của bài E) bằng 0 trên cả hai đề. Khác 0 là bài 1 không đạt, kể cả
  khi mọi chuỗi trúng có cờ "có trên trang đã đọc": cờ đó chỉ giúp đọc tay, không trừ lộ.
- Ghi thêm, không phải cổng: lộ ở câu thô; số lượt lý do `leak` và `unknown_ref`; loại a trả lời được bao
  nhiêu và bao nhiêu nhờ đoạn (`grounded_by_page`). So với các lần `narrator-3` cũ chỉ để tham khảo (khác
  ngày, khác model).

## Bài 2: bài A, độ đúng của người kể trên truyện ky-ao 10 chương
- Đề chính (quyết định): `questions-ky-ao-vua-1-facts.yaml` (đồ thị có Fact mới, D-93, gần bộ trích hiện
  hành nhất). Đề phụ: `questions-ky-ao-vua-1.yaml` (đồ thị cũ, sổ tay nghèo hơn), chỉ chạy ở lượt chính,
  không dùng để quyết.
- Hai hệ trong cùng một lượt: `--systems narrator,narrator_pages`, `--samples 3` (117 lượt mỗi hệ).
  ```bash
  cd backend
  uv run python -m writory.pipeline.bench_a run --label narrator-passages-facts --questions-file questions-ky-ao-vua-1-facts.yaml \
      --systems narrator,narrator_pages --samples 3 --budget <USD>
  uv run python -m writory.pipeline.bench_a run --label narrator-passages-goc --questions-file questions-ky-ao-vua-1.yaml \
      --systems narrator,narrator_pages --samples 3 --budget <USD>
  ```
- Chấm bằng code của bài A; "Bạn chưa biết điều này." là kiêng. Câu có/không chấm theo từ đầu, nên câu văn
  xuôi không mở bằng "Có"/"Không" tính sai ở cả hai hệ như nhau. Đọc tay các lượt `parsed: null` của câu
  có/không và ghi số vào `notes.md`; không sửa điểm.
- **Luật giữ `narrator-4` bật mặc định** (đề chính, lượt chính), phải đạt CẢ BỐN:
  1. Đúng tổng của `narrator_pages` ≥ đúng tổng của `narrator` + 10 điểm phần trăm (từ 12 lượt trở lên
     trên 117).
  2. Lượt sai không kiêng của `narrator_pages` không hơn của `narrator` quá 10 điểm phần trăm (quá 11
     lượt): câu sai làm người chơi tin điều sai, tệ hơn "chưa biết".
  3. Lộ ngoài trang của `narrator_pages` bằng 0 (cột "Lộ ngoài trang" của `summary.md`: bộ chấm chặt trúng
     chuỗi không có trong văn chương 1..N).
  4. Bài 1 đạt.
  Không đạt thì đề xuất tắt (`narrator_pages.top_k: 0`, tức `narrator-3`), chủ dự án quyết. Chạy dở vì
  trần hay lỗi là "chưa kết luận", không tính đạt. Không thử số khác trong cùng lượt.
- Đọc thêm, không phải cổng: tách theo `graph_agrees` (mong đợi phần lớn chênh nằm ở câu đồ thị thiếu), theo
  khoảng cách, theo nhóm (nhóm nhỏ, chỉ mô tả); số lượt `narrator_pages` bị bộ dò lộ chặn (`leak`: trả lời
  dẫn điều trang đã nói mà `player_view` chưa có, tức trả lời oan có chủ ý); đọc tay mọi lượt sai của
  `narrator_pages`, chia: BM25 kéo sai đoạn, model đọc sai, chấm văn xuôi.

## Xác nhận Luna (sau lượt chính)
- Bài 2 đề chính, hai hệ, `--samples 1` (78 lượt); bài 1 chỉ `questions-tu-tien-1.yaml`, `--samples 1`
  (39 lượt).
- Đạt khi: `narrator_pages` − `narrator` ≥ 5 điểm phần trăm (từ 2 lượt trở lên trên 39), lộ ngoài trang 0,
  và lộ ở câu cuối của bài E bằng 0. Lượt chính đạt mà Luna không đạt thì báo chủ dự án, không tự quyết.

## Cỡ đo (ước tính, chưa gọi model)
Token vào ước bằng ký tự / 2 (`llm/cost.EST_CHARS_PER_TOKEN`) trên đúng tin nhắn sẽ gửi (từ lượt chạy
khô); token ra giả định 800 mỗi lời gọi như `bench_e plan` (chưa đo; câu trả lời người kể thường ngắn hơn
nhiều, trừ token suy luận). USD theo giá Luna trong `run.yaml` (0,10 / 0,50 USD mỗi triệu token) chỉ để
tham khảo; giá Muse chưa có.

| Lượt | Lời gọi | Token vào | Token ra (giả định) | USD nếu là Luna |
|---|---|---|---|---|
| Bài 1, `questions-v2.yaml` × 3 | 324 | ≈ 1,55 triệu | ≈ 259 nghìn | ≈ 0,29 |
| Bài 1, `questions-tu-tien-1.yaml` × 3 | 117 | ≈ 0,58 triệu | ≈ 94 nghìn | ≈ 0,11 |
| Bài 2 đề chính, 2 hệ × 3 | 234 | ≈ 1,50 triệu | ≈ 187 nghìn | ≈ 0,24 |
| Bài 2 đề phụ, 2 hệ × 3 | 234 | ≈ 0,94 triệu | ≈ 187 nghìn | ≈ 0,19 |
| **Lượt chính (Muse), cộng** | **909** | **≈ 4,6 triệu** | **≈ 727 nghìn** | (≈ 0,82) |
| Xác nhận Luna: bài 2 đề chính, 2 hệ × 1 | 78 | ≈ 0,50 triệu | ≈ 62 nghìn | ≈ 0,08 |
| Xác nhận Luna: bài 1 tu-tien-1 × 1 | 39 | ≈ 0,19 triệu | ≈ 31 nghìn | ≈ 0,035 |

Thử lại có thể nhân số lời gọi (`retries`), nên đặt `--budget` cao hơn vài lần; lệnh giữ chỗ chi phí tối
đa trước mỗi lời gọi. Ngữ cảnh trung bình mỗi lời gọi: bài 2 đề chính 10 661 ký tự (`narrator`) và
15 028 ký tự (`narrator_pages`); đề phụ 5 834 và 10 200; bài E khoảng 9 600 (v2) và 9 900 (tu-tien-1).

## Đã chạy khô (model giả, không tốn tiền)
Lệnh (trong `backend/`, ghi ra thư mục `*-dryrun/` không commit hay thư mục tạm):
```bash
uv run python -m writory.pipeline.bench_a run --dry-run --label nguoi-ke-khung --questions-file questions-ky-ao-vua-1-facts.yaml --systems narrator,narrator_pages --samples 1
uv run python -m writory.pipeline.bench_a plan --questions-file questions-ky-ao-vua-1-facts.yaml --systems narrator,narrator_pages --samples 3
uv run python -m writory.pipeline.bench_e run --dry-run --label passages-v2 --questions-file questions-v2.yaml --samples 1            # và --fake leaker
uv run python -m writory.pipeline.bench_e run --dry-run --label passages-tt1 --questions-file questions-tu-tien-1.yaml --plan-file plan-tu-tien-1.yaml --samples 1
PYTHONIOENCODING=utf-8 uv run python ../evals/results/2026-10-30-narrator-passages/recall_grid.py
```
- Bài E, oracle và kẻ lộ, cả hai đề: lộ ở câu cuối 0, không lỗi; gần như mọi lượt có đoạn.
- Bài 2, model giả `oracle` (trả đáp án chỉ khi mọi câu trích bằng chứng nằm nguyên văn trong sổ tay hay
  đoạn nó nhận; đây là trần chứng cứ nguyên văn, KHÔNG phải dự đoán): đề chính `narrator` 10/39,
  `narrator_pages` 23/39; đề phụ 6/39 và 21/39. Trần của `narrator` bị đánh thấp: sổ tay ghi lại sự thật
  bằng chữ khác trang (Fact, Event), model thật đọc được mà câu trích không khớp nguyên văn. Hệ `graph` của
  bài A ra 51% ở model giả nhưng 71% với Luna (`…-facts-s3`) vì cùng lý do.
- Chọn số tạm `narrator_pages` bằng độ phủ câu trích (`recall_grid.py` trong thư mục này), không gọi
  model. Đề chính, 39 câu, "đủ chứng cứ" = mọi câu trích nằm trong sổ tay + đoạn:

  | top_k | max_chars | đoạn kế | đủ chứng cứ | chỉ trong đoạn | ký tự đoạn TB |
  |---|---|---|---|---|---|
  | 3 | 2400 | 1 | 21/39 | 18/39 | 2191 |
  | 3 | 2400 | 0 | 20/39 | 17/39 | 1780 |
  | 4 | 2400 | 1 | 21/39 | 19/39 | 2235 |
  | 4 | 3600 | 1 | 23/39 | 21/39 | 3442 |
  | 5 | 4000 | 1 | 22/39 | 20/39 | 3898 |
  | 6 | 4800 | 1 | 23/39 | 21/39 | 4715 |
  | 8 | 6000 | 1 | 23/39 | 21/39 | 5946 |

  Chọn 4 / 3600 / 1: chạm mức trần của bảng với ít chữ nhất. Đề phụ cùng chiều (19, 18, 19, 21, 20, 21, 21).
  BM25 chỉ theo chữ câu hỏi nên khoảng 16 câu không kéo được câu trích nào dù tăng chữ; người kể không nhận
  nguyên chương N như các hệ của bài A.

## Hạn chế đã biết trước khi chạy
- Một truyện dài, một lần phát lại bộ trích; 39 câu, các lần hỏi cùng câu không độc lập (khoảng tin cậy
  Wilson trên lượt hẹp hơn thật).
- Bài 2 không qua kiểm duyệt và trần số câu: đo người kể, không đo hai lớp đó.
- Giám khảo bài E chưa đọc đoạn trên trang; "vượt sổ tay" và "gợi ý" của `narrator-4` chưa có cách chấm
  bằng giám khảo.
- Lệnh chạy cụ thể của lượt chính phụ thuộc client Meta của D-140; phần đó bổ sung ở đây trước lời gọi đầu.

## Bổ sung trước khi chạy
(Chưa có. Ghi cờ client Meta, giá giữ chỗ của Muse, commit chạy và mọi thay đổi khác so với bản khai này.)
