# G6 vòng bốn, `overreach-4`: kết quả đo quyết định trên Luna, năm lượt (31/10/2026)

Khai trước: `expectations.md` (cùng thư mục, commit `5a41ddb` trước lượt đầu). Kết quả: `run1` đến `run5` (`result.json`); số đã tính ở `analysis.json` bằng `analyze.py` (chỉ đọc kết quả).

- Nhánh `fix/overreach-4` (xây trên `fix/overreach-3`, PR #136, thêm ca `round3` và gỡ `overreach-3` khỏi mã), commit lúc chạy `5a41ddb`. Model `openai/gpt-6-luna`, suy luận `low`, config mặc định, OpenRouter, đề `overreach-4`, bộ `g6_overreach.yaml` v3 (41 ca). Năm lệnh `bench_g6` riêng, tuần tự. Meta không chạy. Lúc chạy có một chuỗi `bench_run` của session khác, dùng config Meta (kiểm `models.yaml` của nó), không dùng OpenRouter.
- Chi phí thật: ~0,0138 USD cho cả năm lượt (run1 ~0,0072, bốn lượt còn lại ~0,0015 đến 0,0019; trần 0,05). Lượt đầu đắt gấp bốn, như lần đo `overreach-3`; có thể do chưa có bộ nhớ đệm prompt ở lượt đầu (chưa kiểm). Không chạm trần, không lời gọi lỗi.

## Kết quả theo luật khai trước
| Luật | Ngưỡng | Kết quả |
|---|---|---|
| D1 `truoc-nga-nay-im` ra `failed` | ≥ 4/5 lượt | **5/5** |
| D1 `hc2-thang-lai-bi-lo-chi-duoc-nhac` ra `granted` | ≥ 4/5 lượt | **5/5** |
| D1b `hc-canh-truoc-da-tra-gia` ra `cost` (đã vỡ ở `overreach-3`) | ≥ 4/5 lượt | **5/5** |
| D2a ca `round3` đạt (đúng ≥ 4/5 lượt) | ≥ 7/9 ca | **9/9** (mỗi ca 5/5) |
| D2b hai ca đối chứng đạt | 2/2 | **2/2** |
| D3 P1, P2, M1 (kể cả M1c, M1d) giữ trong mỗi lượt | giữ ở ≥ 4/5 lượt | **5/5** lượt (P1 = 0, P2 = 0, M1 bỏ sót = 0, M1 viết lại nhầm = 0 ở mọi lượt) |
| D4 lỗi gọi | ≤ 1 mỗi lượt | 0 |

**Kết luận theo luật khai trước: ĐẠT.** Theo luật, gộp `overreach-4` vào sản phẩm (mã đã nằm trong nhánh).

## Ghi thêm (không quyết)
- Ba ca có kết luận khác nhãn mong đợi ở **cả năm lượt**, nhưng không đổi quyết định sản phẩm: `doi-linh-cost` và `chem-nui-cost` (vượt sức nhân vật, mong đợi `cost`, ra `failed`: cả hai được qua) và `truoc-nga-nay-bay-duoc` (vượt luật thế giới, mong đợi `granted`, ra `cost`: cả hai bị viết lại). Đã thấy ở các lượt Luna trước.
- Bộ gốc 14 ca: không bỏ sót, không viết lại nhầm ở lượt nào.
- So với `overreach-2` (lượt đo lại [`g6-luna-repeat`](../2026-10-30-g6-luna-repeat/notes.md)): `truoc-nga-nay-im` hết sai (trước ổn định sai), `hc2-thang-lai-bi-lo-chi-duoc-nhac` hết sai (trước 2/4 sai), và `hc-canh-truoc-da-tra-gia` vẫn đúng (không hồi quy như `overreach-3`).

## Hạn chế
- Bộ v3 đã được dùng để đo `overreach-3`: 9 ca `round3` và các ca phát triển không còn là bộ giữ riêng đối với đề này, và do Claude viết sau khi biết điểm yếu. Kết quả chứng minh đề xử được các dạng đã nêu và không hồi quy ở bộ này, không chứng minh G6 kín (nhất là ở truyện thật, dạng cảnh khác).
- Năm lượt trên một model: chỉ đủ nói một ca ra cùng kết luận nhiều lần hay không. Chưa đo trên Meta (không bắt buộc ở luật này).
- Nguyên nhân (nghi ngờ trước đó) rằng câu về "cảnh trước" gây hồi quy được ủng hộ gián tiếp (bỏ câu đó thì ca vỡ đúng lại, các cải thiện khác giữ nguyên), nhưng chỉ là một so sánh hai đề, chưa tách riêng bằng thí nghiệm.
