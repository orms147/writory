# Nhận xét đọc tay: memory-ky-ao-vua-1-facts-s3

Người đọc: Claude (nhánh eval/bench-a-facts), 22/10/2026. Nguồn: `summary.md`, `results.jsonl`, `meta.json`.

Chạy lại bài A với đồ thị có Fact mới (D-93), 3 lần mỗi câu, để kiểm số lần 1 một lượt hỏi. Đề `questions-ky-ao-vua-1-facts.yaml` (chủ dự án duyệt 22/10/2026), truyện `evals/results/2026-10-22-new-facts-replay-1/`, hai hệ `graph` và `graph_quotes`, model trả lời `openai/gpt-6-luna` suy luận low. Nền đồ thị Neo4j (id truyện `bench-a-run`; lúc đo không chạy `pytest -m graph`). Không có `errors.jsonl`: 234 lượt, không lỗi, không `HARNESS_ERROR`.

Lệnh: `uv run --group eval python -m writory.pipeline.bench_a run --label ky-ao-vua-1-facts-s3 --questions-file questions-ky-ao-vua-1-facts.yaml --systems graph,graph_quotes --samples 3 --budget 0.15 --env-file C:/Work/AI/WriTory/.env`. `meta.json` ghi commit `4380650` kèm "có sửa chưa commit": lúc chạy mới sửa trạng thái đề và D-93 (xem PR), mã không đổi.

## So với hai lần trước
| | đồ thị | đồ thị + câu trích |
|---|---|---|
| `memory-ky-ao-vua-1` (không Fact mới, 117 lượt) | 49% (57/117) [40–58] | 79% (92/117) [70–85] |
| `memory-ky-ao-vua-facts-1` (Fact mới, 1 lần hỏi, 39 lượt) | 74% (29/39) [59–85] | 82% (32/39) [67–91] |
| **lần này (Fact mới, 3 lần hỏi, 117 lượt)** | **71% (83/117) [62–78]** | **84% (98/117) [76–89]** |
| cùng đề `memory-ky-ao-vua-1`, hệ khác (tham khảo) | RAG 84% [76–89], tóm tắt cuộn 79% [70–85], nhét cả truyện 91% [85–95] | |

- **Số lần 1 đứng vững.** Đồ thị 74% → 71%, hệ lai 82% → 84%: hai khoảng tin cậy chồng nhau, không lệch hướng. Từ 49% lên 71% là chênh thật, vì khoảng tin cậy không chạm nhau (40–58 và 62–78), dù 12 câu đổi cờ sau khi thấy đồ thị (xem dưới).
- **Đồ thị một mình vẫn dưới RAG và nhét cả truyện** (so với lần chạy gốc; hệ RAG và nhét cả truyện không chạy lại ở đây, nên đây là so sánh giữa hai lần chạy khác ngày). Hệ lai (84%) ngang RAG (84%) và dưới nhét cả truyện (91%) trên số liệu hiện có. Không đủ để nói hệ lai hơn RAG.
- **Khoảng tin cậy rộng hơn vẻ ngoài:** 117 lượt là 39 câu × 3 lần hỏi, các lần hỏi cùng câu không độc lập, nên khoảng thật rộng hơn khoảng ghi ở trên (Wilson trên lượt, như mọi lần đo bài A).
- Chi phí thật: 0,0136 USD cho 234 lượt (đồ thị 0,0066, hệ lai 0,0070), trần `--budget` 0,15. Số token mỗi lời gọi gần như bằng lần `memory-ky-ao-vua-1` (vào ~4.000, ra ~30) nhưng USD mỗi lời gọi thấp hơn 3–4 lần (0,000057 so với 0,000196). Không rõ vì sao (suy đoán: nhà cung cấp tính giá hay cache khác); không dùng làm số chi phí chuẩn.

## Theo `graph_agrees` (đồ thị bộ trích có đáp án)
| | có đáp án | thiếu hoặc sai |
|---|---|---|
| đồ thị, lần này | 91% (68/75) | 36% (15/42) |
| hệ lai, lần này | 89% (67/75) | 74% (31/42) |
| đồ thị, lần gốc | 97% (38/39) | 24% (19/78) |

**Không so thẳng được:** lần gốc có 13 câu "có đáp án"; ở đề này 25 câu có cờ, vì 12 câu được khai cờ SAU khi đã thấy đồ thị mới (đầu file đề). Cờ chỉ mô tả, không phải đáp án khai trước. Điều đọc được an toàn: ở câu đồ thị có chữ trả lời, đồ thị đúng 91%; ở câu đồ thị thiếu, hệ lai cứu 74% so với 36%.

## Theo nhóm (đồ thị / hệ lai)
- đồ vật 88% / 76%; sống–chết 73% / 100%; ai biết gì 62% / 83%; quan hệ 62% / 86%. Không có câu nhóm lời nói dối trong đề này.
- Khoảng cách 0 chương: 100% cả hai. 1–2 chương: 40% / 87% (15 lượt). 3+ chương: 62% / 74% (66 lượt).

## Các câu vẫn sai (đọc câu trả lời thô trong `results.jsonl`)
1. **Chữ chỉ có trên trang, đồ thị không có nút (cờ `false`):** `alive-02` (ai đỡ ông lão), `rel-07` (rời nhánh xuống khe cùng ai), `knows-10`, `knows-11`, `knows-14`. Đồ thị đáp "Không biết" 3/3 ở bốn câu đầu. Hệ lai cứu `alive-02` và `rel-07` (3/3), nhưng `knows-11` ("mồi nhử") không hệ nào đúng, và `knows-14` (dấu "giả") hệ lai đáp "chỉ là vết nứt tự nhiên" 3/3, tức BM25 kéo đoạn gần chủ đề nhưng không đúng đoạn, và model trả lời sai thay vì kiêng.
2. **Đồ thị có chữ nhưng model đọc sai:** `knows-05` (cờ `true`): ngữ cảnh đồ thị có dòng "Đã biết: Gia tộc Phó từng cất giữ Mảnh Khiếp Tàn Thiên theo một giao ước…; cách biết: suy ra (từ cuối chương 8)", câu hỏi hỏi đúng điều đó ở chương 9, vậy mà đồ thị đáp "Không" 3/3; hệ lai đúng 3/3. Phần đọc đồ thị vẫn có lỗi, không chỉ độ phủ bộ trích. Chưa tìm nguyên nhân (suy đoán: câu hỏi nhắc "giao ước" và "Điện Tàn Tinh" có trong khối khác, model coi là chưa đủ).
3. **Fact mới chỉ nói gián tiếp:** `item-04` ("cho ai mượn Thẻ Định Phong") Fact ghi Trần Mặc "xin mượn": đồ thị kiêng 2/3, hệ lai kiêng 2/3. `item-07` (Trần Mặc đòi gì): đồ thị đúng 2/3, hệ lai kiêng 3/3 dù đồ thị đã có Fact.
4. **Đoạn BM25 có thể làm hệ lai tệ hơn đồ thị:** `item-06` ("Thẻ đã trở lại tay… chưa", gold Có): đồ thị đúng 3/3, hệ lai đáp "Không" 3/3. Nhóm đồ vật hệ lai 76% so với đồ thị 88% cho thấy cùng chiều. Chưa đọc đoạn BM25 nào được chọn.
5. `rel-02` (còn đi cùng Trần Mặc không, gold Không): lẫn lộn ở cả hai hệ (đồ thị sai 2/3, hệ lai kiêng 2/3).

## Kết luận (đọc được vs suy luận)
- Đọc được: Fact mới (D-93) nâng đồ thị một mình từ 49% lên khoảng 71% trên cùng 39 câu, và hệ lai từ 79% lên 84%; số lần 1 (74%, 82%) đúng hướng và cỡ.
- Đọc được: đồ thị một mình vẫn dưới RAG; hệ lai chỉ ngang RAG; cả hai dưới nhét cả truyện (khác lần chạy).
- Suy luận, chưa đo: hai hướng còn lại là (a) thêm nút cho chi tiết trang (10 câu không có nút trong danh mục, D-92) và (b) chỉnh cách đọc đồ thị (câu `knows-05`) hoặc cách chọn đoạn BM25 cho hệ lai (`item-06`, `knows-14`).

## Chưa kiểm
- Một truyện, một lần chạy, đồ thị từ một lần phát lại bộ trích duy nhất (model có nhiễu).
- 12 câu đổi cờ sau khi thấy đồ thị; số "có đáp án" của lần này không so trực tiếp với lần gốc.
- RAG, tóm tắt cuộn, nhét cả truyện không chạy lại: so sánh với chúng lấy từ `memory-ky-ao-vua-1`.
