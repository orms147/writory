# Nhận xét đọc tay: memory-ky-ao-vua-1-facts-nb1

Người đọc: Claude (nhánh feature/retrieval-and-cache), 22/10/2026. Nguồn: `summary.md`, `results.jsonl`, `meta.json`.

Đo hệ `graph_quotes` với đoạn kế (D-96): mỗi đoạn BM25 trúng kéo theo 1 đoạn liền sau trong cùng chương (`limits.context.page_quotes_neighbors` = 1), trần 2400 ký tự, `top_k` 2 như cũ. Cùng đề `questions-ky-ao-vua-1-facts.yaml` (duyệt 22/10/2026), cùng truyện `2026-10-22-new-facts-replay-1`, 3 lần hỏi, GPT-6 Luna low, Neo4j. Không có `errors.jsonl`: 117 lượt, không lỗi. Chi phí thật 0,0292 USD, trần `--budget` 0,05. `meta.json` ghi commit `02089c9` kèm "có sửa chưa commit" (lúc chạy mã D-96 chưa commit). Lệnh: `uv run --group eval python -m writory.pipeline.bench_a run --label ky-ao-vua-1-facts-nb1 --questions-file questions-ky-ao-vua-1-facts.yaml --systems graph_quotes --samples 3 --budget 0.05 --env-file C:/Work/AI/WriTory/.env`.

## So với `memory-ky-ao-vua-1-facts-s3` (hệ lai, không đoạn kế)
| | s3 (đoạn kế 0) | nb1 (đoạn kế 1) |
|---|---|---|
| đúng | 84% (98/117) [76–89] | **87% (102/117) [80–92]** |
| kiêng | 11 | 9 |
| ngữ cảnh TB (ký tự) | 12455 | 13385 (+930) |
| nhóm đồ vật / sống–chết / ai biết gì / quan hệ | 76% / 100% / 83% / 86% | 76% / 100% / 92% / 86% |
| đồ thị có đáp án / thiếu hoặc sai | 89% / 74% | 89% / 83% |

- **Chênh +3 điểm (4 lượt) nằm gọn trong nhiễu:** khoảng tin cậy chồng nhau gần hết, và 117 lượt chỉ là 39 câu × 3 lần hỏi (không độc lập). Không kết luận "đoạn kế có lợi" từ số này một mình.
- **Cơ chế có bằng chứng ở 2 câu** (dựng lại ngữ cảnh bằng code, không gọi model): `knows-11` (0/3 → 3/3) và `rel-06` (2/3 → 3/3): câu trích bằng chứng chỉ có trong đoạn kế thêm vào (`(1,3)` sau `(1,2)`; `(1,8)` sau `(1,7)`), không có ở bản không đoạn kế.
- **Câu đổi mà đoạn kế không phải nguyên nhân:** `item-07` 0/3 → 3/3 và `knows-10` 1/3 → 2/3 (bằng chứng đã có trong đoạn từ trước hoặc vẫn không có); `item-02` 3/3 → 1/3, `item-04` 1/3 → 0/3, `rel-02` 1/3 → 0/3 (bằng chứng không đổi, mô hình đáp "Không biết"). Cùng prompt lặp ở lần hỏi 2, 3 mà đáp khác lần 1 (ví dụ `item-02` đúng rồi kiêng, kiêng): model có nhiễu, và thêm đoạn có thể làm model thận trọng hơn. Không đo được riêng.
- **Hai câu chẩn đoán trước vẫn sai y nguyên, 3/3 mỗi câu:** `item-06` ("Không", đoạn đúng là `(4,#12)`, đoạn kế của `(4,#4)` chỉ là `(4,#5)`) và `knows-14` ("vết nứt tự nhiên", đoạn đúng `(3,#5)` không phải đoạn trúng nào, `(3,#7)` có đoạn kế rỗng, `(2,#7)` kéo `(2,#8)`). Đoạn kế chỉ giúp khi đoạn cần tìm nằm NGAY sau đoạn trúng.
- Phép kiểm không tốn tiền (`bench_a retrieval`, trần 2400): top_k 2: 16/27 → 19/27 câu có bằng chứng trong đoạn lấy về; còn 8 câu không có bằng chứng trong đoạn nào, gồm `item-06` và `knows-14`.

## Cache prompt (D-96): đã có số
`calls` của `results.jsonl` giờ có `cached_tokens` cho cả 117 lời gọi (không lời gọi nào "không rõ").
| lần hỏi | lời gọi | lạnh (0 token cache) | token vào được cache |
|---|---|---|---|
| 0 | 39 | 36 | 7% |
| 1 | 39 | 4 | 89% |
| 2 | 39 | 0 | 100% |
- USD mỗi lời gọi: lạnh 0,000610 (40 lời gọi), có cache 0,000062 (77 lời gọi): chênh khoảng 10 lần. Tổng 0,0292 USD, trong khi hệ lai ở `s3` tốn 0,0070 USD (prompt của `s3` đã nằm trong cache từ lần chạy trước đó). Vậy "hệ lai tốn gấp 4 lần" chỉ là chênh cache, không phải chênh ngữ cảnh (+7%).
- Bằng chứng cho giả thuyết của chẩn đoán trước ("cache prompt lặp"): lần hỏi 0 gần như lạnh, lần hỏi 1 và 2 gần như hoàn toàn từ cache. Vài lời gọi lần hỏi 0 vẫn có cache một phần (ví dụ 2725 token đầu tiên): phần đầu giống nhau giữa các câu (đề hệ thống và khối nhân vật).
- Chi phí lạnh mỗi lời gọi của lần này (0,00061) cao hơn con số 0,000415 trong chẩn đoán trước, vì ngữ cảnh lần này dài hơn (+930 ký tự, khối đồ thị dài ~11 nghìn ký tự).

## Đề xuất làm sau (mục (a), chưa làm)
Trình bày ngữ cảnh đồ thị cho `knows-05` (đồ thị có dòng đúng mà model đáp "Không"; H1: "cách biết: suy ra" bị coi là chưa chắc; H2: dòng "ở Điện Tàn Tinh" nghe mâu thuẫn; H3: dòng chìm trong danh sách dài). Thử bằng A/B có model, 3 biến thể × 3 lần hỏi, chi phí cỡ 0,03 USD lạnh:
1. viết cách biết bằng câu thường ("tự nhận ra: …") thay vì "Đã biết: …; cách biết: suy ra";
2. đưa 3–5 dòng "Đã biết" khớp từ vựng câu hỏi lên đầu khối;
3. bỏ dòng vị trí đồ vật khi đã có Fact nói về nó.
Chưa kiểm được H1–H3 nếu không gọi model.

## Chưa kiểm
- Một truyện, một lần phát lại bộ trích, 39 câu; model có nhiễu.
- `nb1` chỉ chạy hệ `graph_quotes`; `graph`, `rag`, `rolling`, `full` không chạy lại, nên không có số mới để so với RAG và nhét cả truyện.
- Chưa bật D-85 (đoạn trên trang cho model viết) với đoạn kế; không có số đo chất lượng văn.
