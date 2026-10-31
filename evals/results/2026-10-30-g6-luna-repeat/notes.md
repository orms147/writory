# G6 (`overreach-2`) trên Luna, đo lại ba lượt: nhiễu hay điểm yếu (30/10/2026)

Khai trước: `expectations.md` (cùng thư mục, commit trước lượt đầu). Kết quả: `run1/`, `run2/`, `run3/` (`result.json`), số đã tính ở `analysis.json` bằng `analyze.py` (chỉ đọc kết quả). Lượt đã có: [`2026-10-30-g6-check-2/luna/g6`](../2026-10-30-g6-check-2/luna/g6/result.json).

- Commit lúc chạy: nhánh `eval/g6-luna-repeat` trên main `d1464e3` (đề `overreach-2`, bộ câu `g6_overreach.yaml` v2, không đổi). Model `openai/gpt-6-luna`, suy luận `low`, config mặc định, OpenRouter. Ba lệnh `bench_g6` riêng, tuần tự; trước khi chạy không có bench, probe, replay hay export nào khác đang chạy.
- Chi phí thật: mỗi lượt ~0,0015 USD (ba lượt cộng lại ~0,0045 USD, trần 0,05). Không chạm trần, không lời gọi lỗi.

## Kết quả theo luật khai trước
| Luật (mỗi lượt mới) | Ngưỡng | run1 | run2 | run3 |
|---|---|---|---|---|
| T1 viết lại nhầm, cả bộ | ≤ 2 | 1 | 0 | 1 |
| T2 bỏ sót (trang phải viết lại mà cho qua), cả bộ | = 0 | **1** | 0 | **1** |
| T3 P1 / P2 (ca `round2`), M1 bộ khó cũ | ≤ 1 | 1 / 0, M1 đúng | 0 / 0, M1 đúng | 1 / 0, M1 đúng |
| T4 lỗi gọi | ≤ 1 | 0 | 0 | 0 |

**Kết luận theo luật khai trước: KHÔNG ỔN ĐỊNH**, vì T2 bị vi phạm ở hai trong ba lượt (run1 và run3). T1, T3, T4 đúng ở cả ba lượt.

- **Bỏ sót ở cả hai lượt là cùng một ca:** `hc2-thang-lai-bi-lo-chi-duoc-nhac` (ca `round2`, vượt sức nhân vật, mong đợi `granted`): trang chỉ nhắc rằng Minh sẽ phải trả giá một ngày nào đó, đêm nay chưa có gì xảy ra. Người chấm ra `cost` ở 2 trên 4 lần chấm (lượt đã có và run2 ra `granted`). Với vượt sức nhân vật `cost` được qua, nên sản phẩm sẽ cho qua một cảnh nhân vật thắng mà không mất gì. Đây đúng là dạng `overreach-2` (và `overreach-1`) định chặn ("giá chỉ được nhắc thì không tính"), nên là lỗ hổng thật nhưng không ổn định: một số lượt đọc đúng.

## Hai ca được chỉ định
| Ca | Số lần bị viết lại nhầm trên 4 lần chấm | Theo luật |
|---|---|---|
| `hc-treo-cot-buom` (bộ khó, vượt luật thế giới) | 1/4 (chỉ lượt đã có; ba lượt mới đều `failed`) | **nhiễu** |
| `truoc-nga-nay-im` (bộ gốc, vượt luật thế giới, cảnh trước có cú ngã) | 3/4 (sai ở lượt đã có, run1, run3) | **ổn định: điểm yếu thật** |

Đọc tay `truoc-nga-nay-im` (suy luận từ văn bản, chưa kiểm lý do của model, kết quả không lưu `reason`): cảnh trước trong chương có cú ngã làm Minh bị thương cổ chân; cảnh đang chấm là Lan hỏi về thanh kiếm, không còn nhắc tới chuyện bay. Bay không xảy ra trên trang nên mong đợi `failed` là đúng theo định nghĩa của đề; người chấm tính cú ngã (cái giá của việc thử) như "cái giá của điều bất khả", tức đọc `cost` ở vượt luật thế giới. Ở vượt luật thế giới `cost` bị viết lại, nên trang hợp lệ sẽ bị bắt viết lại. Đây là điểm yếu của `overreach-2` trên Luna ở ca "đã thất bại rồi chịu hậu quả", chưa rõ có do đề mới hay đã có từ `overreach-1` (không đo ca này trên `overreach-1` lần nào ngoài lần đo đầu, ở đó Luna ra đúng).

## Các ca khác có kết luận lệch giữa các lượt (không đổi quyết định sản phẩm)
`doi-linh-cost`, `chem-nui-cost` (vượt sức nhân vật, mong đợi `cost`, thi thoảng ra `failed`): cả hai đều được qua nên không ảnh hưởng. `truoc-nga-nay-bay-duoc` (mong đợi `granted`, luôn ra `cost` ở cả bốn lần): cả hai kết luận đều bị viết lại ở vượt luật thế giới, không ảnh hưởng quyết định.

## Hệ quả (khuyến nghị, chưa làm)
- Không sửa đề, bộ câu hay nhãn trong PR này (theo luật khai trước).
- Hai việc đáng xem ở một quyết định sau: (1) nói rõ hơn trong đề `overreach` rằng ở vượt luật thế giới một cú ngã hay hậu quả của việc THỬ không biến `failed` thành `cost` (cái bị tính là giá chỉ khi điều bất khả đã xảy ra); (2) ca "giá chỉ được nhắc" còn bị đọc nhầm ở Luna, có thể thêm ví dụ trong đề hoặc đo lại trên model khác. Meta đúng cả hai ca ở lượt trước ([`g6-check-2`](../2026-10-30-g6-check-2/notes.md)), nên khác biệt có thể là của model, không của bộ câu.
- Mẫu nhỏ: bốn lần chấm mỗi ca; không đủ để nói tỉ lệ.
