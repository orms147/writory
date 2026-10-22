# Nhận xét đọc tay: D-99, ba cách trình bày khối đồ thị của hệ `graph`

Người đọc: Claude (nhánh eval/graph-presentation-ab), 23/10/2026. Nguồn: `summary.md`, `results.jsonl`, `meta.json` của ba thư mục `2026-10-23-memory-ky-ao-vua-1-facts-{natural,relevance,noplace}`. Notes này là của cả ba; hai thư mục kia chỉ trỏ về đây.

Đo hệ `graph` với ba kiểu trình bày (`--graph-style natural|relevance|no_item_place`, `evals/results/.../meta.json` ghi `graph_style`), đề `questions-ky-ao-vua-1-facts.yaml`, truyện `2026-10-22-new-facts-replay-1`, 39 câu × 3 lần hỏi = 117 lượt mỗi kiểu, GPT-6 Luna suy luận low, nền Neo4j (id `bench-a-run`). Mã: nhánh `eval/graph-presentation-ab`; luật quyết định khai TRƯỚC khi chạy ở `docs/eval.md` (commit `3754252`). Nền so sánh là hệ `graph` của `2026-10-22-memory-ky-ao-vua-1-facts-s3` (không chạy lại).

## Kết quả
| | nền `s3` | `natural` | `relevance` | `no_item_place` |
|---|---|---|---|---|
| đúng | 71% (83/117) [62–78] | 73% (85/117) [64–80] | 74% (86/117) [65–81] | 74% (86/117) [65–81] |
| kiêng | 25 | 30 | 28 | 30 |
| ngữ cảnh TB (ký tự) | 11281 | 11170 | 11278 | 11265 |
| đồ vật | 29/33 | 27/33 | 28/33 | 28/33 |
| sống–chết | 11/15 | 12/15 | 11/15 | 11/15 |
| ai biết gì | 30/48 | 32/48 | 34/48 | 33/48 |
| quan hệ | 13/21 | 14/21 | 13/21 | 14/21 |

## Áp luật đã khai
- Điều kiện (1) đúng tổng ≥ 89/117: **cả ba trượt** (85, 86, 86).
- Điều kiện (2) không nhóm nào tụt quá 10 điểm (đồ vật ≥ 26/33, sống–chết ≥ 10/15, ai biết gì ≥ 26/48, quan hệ ≥ 11/21): cả ba đạt.
- Kết luận theo luật: **BỎ cả ba**, giữ cách trình bày nền. Không có biến thể thắng nên không có đề xuất cho ngữ cảnh người viết (`graph/context.py`), không sửa file đó.

## Đọc tay (số lượt đúng trên 3 lần hỏi, nền → biến thể)
- Mỗi biến thể đổi 5–6 câu, cả hai chiều: `natural` item-04 1→0, item-07 2→3, item-08 2→0, alive-03 2→3, knows-05 0→2, rel-02 1→2; `relevance` item-04 1→0, item-07 2→1, item-08 2→3, knows-05 0→3, knows-15 0→1; `no_item_place` item-02 3→2, item-04 1→0, item-08 2→3, knows-05 0→2, knows-15 0→1, rel-02 1→2. Chênh ròng +2 đến +3 lượt, khoảng tin cậy chồng nhau gần hết (117 lượt là 39 câu × 3 lần, không độc lập): không phân biệt được với nhiễu.
- **`knows-05` (câu chẩn đoán gốc) đổi từ 0/3 sang 2/3, 3/3, 2/3 ở CẢ BA biến thể**, dù mỗi biến thể sửa một thứ khác nhau (H1 chữ "suy ra", H3 dòng chìm trong danh sách, H2 dòng "Ở Điện Tàn Tinh"). Không giả thuyết nào được phân biệt: ba thay đổi khác nhau đều lật câu này, nên "câu này nhạy với mọi đổi ngữ cảnh" (hoặc nhiễu của model ở một câu) cũng giải thích được, ngang với việc mỗi giả thuyết đúng một phần. Không rút ra H1–H3.
- `item-04` ("cho ai mượn Thẻ Định Phong", Fact ghi "xin mượn") tụt 1→0 ở cả ba: model kiêng; không biến thể nào chạm tới chữ của Fact.
- Chưa đọc từng câu trả lời thô cho các câu trên; chỉ so điểm.

## Sự cố trong lúc đo (lỗi của tôi) và cách xử lý
- Tôi chạy chuỗi ba biến thể bằng `( ... ) &` trong một lệnh nền; lệnh bọc báo xong nhưng chuỗi con vẫn chạy, tôi tưởng nó chết nên khởi động chuỗi thứ hai. Hai chuỗi chạy chồng lên cùng thư mục kết quả và cùng truyện Neo4j `bench-a-run` (nạp lại truyện của nhau): 12 lượt `HARNESS_ERROR` ("truyện có 0 nhân vật chính"), dòng trùng (id, sample) (natural 149 dòng, 113 duy nhất; relevance 185 dòng, 105 duy nhất; 6 cặp trùng đáp án khác nhau), dừng sớm vì trần. Chi 0,0518 USD cho hai thư mục đó.
- Đã gộp trùng (giữ dòng đầu) và kiểm mọi dòng giữ lại: `context_chars` khớp 100% với ngữ cảnh dựng lại bằng `ContextBuilder` cho đúng kiểu. Sau đó bench_a chạy tiếp lại sang ngày 23/10 nên tạo thư mục mới (`resolve_out` lấy ngày hiện tại) và chạy lại cả 117 lượt từ đầu: **số trong bảng trên là của các lượt chạy sạch này, một chuỗi, không phải dữ liệu đã gộp.** Hai thư mục nhiễu đã xoá, chỉ giữ số liệu ở đây.
- `no_item_place` dừng hai lần vì trần: bench_a giữ chỗ cho mọi lời gọi đang bay (ba lời gọi song song), nên cạn trần danh nghĩa trước chi tiêu thật; chạy tiếp với `--concurrency 1`.

## Chi phí
Tổng thật khoảng 0,0925 USD (nhiễu 0,0518 + natural 0,0072 + relevance 0,0091 + no_item_place 0,0244), vượt mục tiêu 0,09 một chút, dưới trần được duyệt 0,11. Chi phí lượt sạch của `natural` và `relevance` thấp vì prompt đã nằm trong cache từ các lượt nhiễu; `no_item_place` (cold) 0,0244 là con số gần giá lạnh của một biến thể.

## Chưa kiểm
- Một truyện, một lần chạy mỗi biến thể, nền là số của lần chạy khác ngày (`s3`), không chạy lại: chênh +2 đến +3 lượt không tách khỏi nhiễu.
- Không thử tổ hợp biến thể; không đo hệ `graph_quotes`; không đọc câu trả lời thô.
- Không biết vì sao `knows-05` lật ở cả ba biến thể (xem trên).
