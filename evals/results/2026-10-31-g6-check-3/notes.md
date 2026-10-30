# G6 vòng ba, `overreach-3`: kết quả đo quyết định trên Luna, năm lượt (31/10/2026)

Khai trước: `expectations.md` (cùng thư mục, commit `91d75a9` trước lượt đầu). Kết quả: `run1` đến `run5` (`result.json`); số đã tính ở `analysis.json` bằng `analyze.py` (chỉ đọc kết quả).

- Nhánh `fix/overreach-3` trên main `6277964`, commit lúc chạy `91d75a9`. Model `openai/gpt-6-luna`, suy luận `low`, config mặc định, OpenRouter, đề `overreach-3`, bộ `g6_overreach.yaml` v3 (41 ca). Năm lệnh `bench_g6` riêng, tuần tự. Meta không chạy. Lúc chạy có một chuỗi `bench_run` khác của session khác nhưng dùng Meta (config riêng), không dùng OpenRouter.
- Chi phí thật: ~0,0143 USD cho cả năm lượt (run1 ~0,0072, bốn lượt còn lại ~0,0016 đến 0,0017; chưa kiểm vì sao run1 đắt hơn, có thể do một lần thử lại). Trần 0,05 USD, không chạm trần, không lời gọi lỗi.

## Kết quả theo luật khai trước
| Luật | Ngưỡng | Kết quả |
|---|---|---|
| D1 `truoc-nga-nay-im` ra `failed` | ≥ 4/5 lượt | **5/5** |
| D1 `hc2-thang-lai-bi-lo-chi-duoc-nhac` ra `granted` | ≥ 4/5 lượt | **5/5** |
| D2a ca `round3` đạt (đúng ≥ 4/5 lượt) | ≥ 7/9 ca | **9/9** (mỗi ca 5/5) |
| D2b hai ca đối chứng đạt | 2/2 | **2/2** |
| D3 không hồi quy (P1, P2, M1 giữ trong mỗi lượt) | giữ ở ≥ 4/5 lượt | **3/5**: run3 và run5 vi phạm M1 |
| D4 lỗi gọi | ≤ 1 mỗi lượt | 0 |

**Kết luận theo luật khai trước: KHÔNG ĐẠT** (D3). Hai điểm yếu đã sửa (D1) và ca mới đều đúng ở mọi lượt (D2), nhưng một luật không hồi quy vỡ.

## Chỗ vỡ: `hc-canh-truoc-da-tra-gia` (M1d)
- Ca bộ khó cũ, vượt sức nhân vật, **mong đợi `cost`** (được qua): cảnh trước trong chương, Minh thắng nhưng bị gãy tay (cái giá); cảnh đang chấm là đêm đó Minh thắng nốt sáu tên lính, không mất gì thêm. Chỉ khi tính cả cảnh trước thì mới thấy cái giá.
- Với `overreach-3` người chấm ra **`granted`** ở run3 và run5 (2 trên 5 lượt) ⇒ trang hợp lệ bị bắt viết lại. Ở `overreach-2` ca này ra `cost` ở cả bốn lần chấm (lượt xác nhận cộng ba lượt đo lại: [`g6-luna-repeat`](../2026-10-30-g6-luna-repeat/notes.md)), nên đây là hồi quy do đề mới, không phải nhiễu có sẵn.
- **Suy luận chưa kiểm:** câu thêm vào đề cho (i) kết bằng "Hậu quả của việc thử ở một cảnh trước cũng không đổi điều này cho cảnh sau" (nhằm ca `truoc-nga-nay-im`, cú ngã ở cảnh trước). Câu này có thể làm người chấm bỏ qua cái giá THẬT đã xảy ra ở cảnh trước khi chấm cảnh sau, trái với "tính tới hết cảnh vừa viết, gồm cả cảnh trước". Cú ngã ở `truoc-nga-nay-im` là hậu quả của việc thử (điều muốn không xảy ra), còn cái giá ở `hc-canh-truoc-da-tra-gia` là cái giá của điều muốn ĐÃ xảy ra: hai tình huống khác nhau mà một câu chung dễ làm lẫn.

## Ghi thêm (không quyết)
- Hai ca `doi-linh-cost`, `chem-nui-cost` (mong đợi `cost`, vượt sức nhân vật) ra `failed` ở cả năm lượt: cả hai đều được qua nên không đổi quyết định sản phẩm (đã thấy ở các lượt Luna trước, vẫn không ảnh hưởng).
- Bộ gốc 14 ca: không bỏ sót, không viết lại nhầm ở lượt nào. Các luật P1, P2 và M1 bỏ sót/viết lại nhầm khác giữ ở mọi lượt; chỉ M1d (và M1 viết lại nhầm = 1, vẫn ≤ 1) vỡ ở hai lượt.

## Hạn chế
- Ca `round3` do Claude viết sau khi biết điểm yếu; đúng 5/5 ở cả 9 ca cho thấy đề xử được các dạng đã nêu và không sửa quá tay ở hai ca đối chứng, không chứng minh G6 kín.
- Năm lượt: chỉ đủ nói một ca ra cùng kết luận nhiều lần hay không.
- Không sửa đề trong PR này (luật khai trước). Gợi ý cho một quyết định sau, cần khai trước và đo lại: bỏ riêng câu về "cảnh trước" trong (i) (hoặc nói rõ nó chỉ áp cho hậu quả của việc thử khi điều muốn không xảy ra, còn cái giá của điều đã xảy ra ở cảnh trước vẫn tính), rồi chạy lại bộ này trên Luna.

## Sau đo: quyết định (điều phối, 31/10/2026)
Không gộp `overreach-3` (D-146 "đã thử, không dùng"): sản phẩm giữ `overreach-2`. Chữ của đề đã đo nằm ở `overreach3_system_prompt.txt` cạnh file này (mã không còn nó; `meta.prompt` trong `result.json` ghi `overreach-3`). Các ca `round3` giữ trong `g6_overreach.yaml` v3. Bước kế (D-147): thu hẹp câu về "cảnh trước", khai trước, đo lại cùng bộ trên Luna.
