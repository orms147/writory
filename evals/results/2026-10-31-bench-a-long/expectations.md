# Khai trước: bài A trên truyện dài 24 chương, sáu hệ, Meta Muse

Khai TRƯỚC khi gọi model thật: commit chứa bản này đi trước mọi lời gọi. Mọi số dưới đây là từ code và model
giả, chưa có lời gọi trả tiền nào. Soạn: Claude (điều phối, nhánh `eval/questions-long-ky-ao`), 31/10/2026.
Chủ dự án đã duyệt lượt đo (30/10/2026: sáu hệ, 1 lần hỏi, khoảng 21 USD Meta) và đề (31/10/2026).

## Câu hỏi
Truyện vừa 10 chương (`evals/results/2026-10-22-memory-ky-ao-vua-1/notes.md`, Luna, trước D-93 và D-144):
nhét cả truyện 91%, RAG 84%, đồ thị + câu trích 79%, đồ thị 49%. Đồ thị thua vì bộ trích thiếu sự thật. Trên
truyện dài gấp 2,4 lần, sau các sửa bộ trích (D-92, D-93) và sửa khung đo (D-144), thứ hạng có đổi không? Đồ
thị (đứng một mình, và lai với câu trích) có thêm gì so với RAG khi truyện dài ra không, và nhét cả truyện tốn
bao nhiêu?

## Đường chạy
- Đề: `evals/scenarios/memory/questions-long-ky-ao-2.yaml` (50 câu, chủ dự án duyệt 31/10/2026), truyện
  `evals/results/2026-10-29-run-long-after-ky-ao-2/` (24/24 chương, đã kết truyện).
- Sáu hệ mặc định (`docs/eval.md`, Bài A), `--samples 1`: 300 lời gọi trả lời và 23 lời gọi dựng tóm tắt.
- Model: Meta Muse `meta/muse-wonder-1.0` cho trả lời và tóm tắt (`--config-dir ../evals/config/meta`, D-140).
  Đồ thị đọc từ gói trong bộ nhớ (`--graph-backend memory`, cùng nghĩa với Neo4j theo
  `tests/graph/test_bench_a_graph_parity.py`), để lượt đo không đụng Neo4j đang dùng cho test.
- Ước thô (`bench_a plan --samples 1 --config-dir ../evals/config/meta`): 20,89 USD, trong đó nhét cả truyện
  12,71. Trần `--budget 30`.
- Lệnh:
  ```bash
  cd backend
  uv run python -m writory.pipeline.bench_a run --out ../evals/results/2026-10-31-memory-long-ky-ao-2-muse \
      --questions-file questions-long-ky-ao-2.yaml --samples 1 --concurrency 4 --graph-backend memory \
      --config-dir ../evals/config/meta --env-file C:/Work/AI/WriTory/.env --budget 30
  ```

## Trần chứng cứ (chạy khô, model giả `oracle`, không gọi model)
`oracle` trả đáp án khi mọi câu trích bằng chứng nằm trong ngữ cảnh hệ nhận, nên đây là phần đề mà hệ có
nguyên văn chứng cứ, không phải trần thật (model thật còn suy ra được từ chữ khác). Tóm tắt cuộn không có số
thật khi chạy khô (tóm tắt giả).

| Hệ | Oracle | Câu đồ thị có đáp án (34) | Câu đồ thị thiếu hoặc sai (16) |
|---|---|---|---|
| Đồ thị (`graph`) | 54% (27/50) | 26/34 | 1/16 |
| Đồ thị + câu trích (`graph_quotes`) | 72% (36/50) | 26/34 | 10/16 |
| RAG BM25 (`rag`) | 50% (25/50) | 15/34 | 10/16 |
| Nhét cả truyện (`full`) | 100% (50/50) | 34/34 | 16/16 |
| Không bộ nhớ (`none`) | 8% (4/50) | 3/34 | 1/16 |

## Luật đọc kết quả
1. Chỉ các so sánh sau được dùng để kết luận. Hai hệ chênh từ 10 điểm phần trăm (5 câu) trở lên thì ghi
   "hơn"; khoảng tin cậy 95% của hai hệ không chồng nhau thì ghi "hơn rõ"; dưới 10 điểm là "chưa phân biệt
   được".
   - (a) `graph_quotes` so với `rag`: đồ thị có thêm gì trên RAG ở truyện dài.
   - (b) `graph` so với `rag`.
   - (c) `graph_quotes` so với `full`, kèm USD mỗi câu của hai hệ.
   - (d) Như (a) và (c), chỉ trên 33 câu cách từ 10 chương trở lên.
2. Chẩn đoán phần đọc đồ thị: hệ `graph` trên 34 câu `graph_agrees: true`. Dưới 60% (20/34) thì nút thắt có
   cả phần đọc đồ thị (trần dòng, cách trình bày), không chỉ bộ trích. Truyện vừa: 97% (`notes.md` ở trên).
3. Lượt lỗi (`HARNESS_ERROR`, lỗi mạng hết lượt thử): chạy lại đúng các lượt đó vào cùng thư mục; số trong
   `summary.md` là sau khi chạy lại. Dừng vì trần thì các so sánh là "chưa kết luận"; không nâng trần khi chưa
   hỏi chủ dự án.
4. Không đổi đề, config hay hệ sau khi thấy kết quả. Kết quả chỉ nói về Muse. Không có lượt xác nhận Luna,
   vì lượt đo không đổi đề hay hành vi nào của sản phẩm.
5. Đọc tay, không sửa điểm: mọi lượt sai không kiêng của `graph_quotes` và `rag`; các câu Claude ghi "chưa
   chắc" trong đề (knows-07, knows-17, rel-06, alive-03, alive-04, rel-02, lie-04).

## Dự đoán của Claude (ghi để đối chiếu, không phải luật)
- `full` cao nhất, từ 85% trở lên, và đắt nhất mỗi câu.
- (a) chưa phân biệt được; `graph` thấp hơn `rag` (b).
- Chẩn đoán 2 đạt (từ 60% trở lên).
