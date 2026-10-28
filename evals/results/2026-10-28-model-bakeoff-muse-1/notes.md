# Bài F chấm lại bằng Meta Muse Wonder (D-108): so với Sonnet trên cùng hai truyện

Người đọc: Claude (nhánh eval/second-judge), 28/10/2026. Nguồn: `results.jsonl`, `summary.md`, `traces/` của thư mục này và `../2026-10-22-model-bakeoff-1/` (giám khảo Sonnet 5.5).

Chấm lại đúng hai truyện của `2026-10-22-model-bakeoff-1` (DeepSeek V4 Flash và GPT-6 Luna, 6 chương): `pack --seed 20261022 --judge muse` với cùng thứ tự `--run`, nên cùng nhãn (A = DeepSeek, B = Luna), cùng `story_sha256`, cùng `brief.md` (đã kiểm). Giám khảo `muse` = `muse-wonder-1.0` (không dùng bản `-contributor`), `reasoning_effort: high`, `max_tokens` 20000, structured output `json_schema` strict, thang và hướng dẫn y hệt `judge.yaml` (version 3 chỉ thêm giám khảo). Lệnh: `bench_bakeoff judge` rồi `value`, `--budget-meta 5`, rồi `summary --dir <thư mục này> --with ../2026-10-22-model-bakeoff-1`. 5 lượt gọi, không lỗi, không thử lại, không `errors.jsonl`.

## Số đo (hai giám khảo, cùng hai truyện)
| | Sonnet | Muse |
|---|---|---|
| điểm TB solo: DeepSeek / Luna | 2,71 / **3,00** | **2,57** / 2,43 |
| hạng so sánh TB (hai thứ tự): DeepSeek / Luna | 2,00 / **1,00** | 1,50 / 1,50 (hoà) |
| khuyến nghị đáng tiền | Luna | Luna |
| chi phí giám khảo (5 lượt) | 0,4921 USD | 0,6493 USD |
| câu trích không có thật / đã kiểm | 3/28 | 1/19 |
| token vào / ra (gồm suy luận) | xem `results.jsonl` | 92,3 nghìn / 14,0 nghìn (suy luận 10,3 nghìn) |

Điểm từng mục (DeepSeek / Luna): Sonnet 3/3, 3/3, 3/3, 2/3, 3/3, 3/3, 2/3; Muse 3/3, 3/2, 2/2, 2/2, 3/2, 3/3, 2/3 (thứ tự tiêu chí trong `judge.yaml`).

## Độ đồng thuận và điểm gộp (bảng đầy đủ ở `summary.md`)
- **Không cùng thứ tự:** theo điểm trung bình solo Sonnet xếp Luna trên (chênh 0,29), Muse xếp DeepSeek trên (chênh 0,14). Theo hạng so sánh Sonnet xếp Luna nhất ở cả hai thứ tự, Muse hoà. Cả hai chênh nhỏ (một điểm ở một hai tiêu chí) nên không đọc là bất đồng sâu.
- **Chênh điểm từng mục:** trung bình tuyệt đối 0,00 ở tiếng Việt tự nhiên, lựa chọn, lỗi; 0,50 ở giọng, liền mạch, nhịp; 1,00 ở bám nhân vật và bối cảnh (Sonnet 3/3, Muse 2/2). "Cùng chiều" 0,50 ở sáu mục và 1,00 ở mục lỗi: không mục nào hai giám khảo nói ngược chiều (không có 0,00); sáu mục 0,50 là vì ít nhất một giám khảo cho hai truyện bằng điểm. Muse khắt khe hơn: không cho điểm 3 nào ở bám nhân vật, liền mạch.
- **Điểm gộp** (trung bình cộng điểm TB solo, trọng số bằng nhau, không chuẩn hoá thang): Luna 2,71, DeepSeek 2,64; hạng gộp Luna 1,25, DeepSeek 1,75. Hai giám khảo không có đa số, nên điểm gộp chỉ là cách tóm tắt, không phải phán quyết.
- **Cả hai khuyến nghị đáng tiền chọn Luna** (DeepSeek "chấp nhận được", Luna "đáng tiền"), với lý do chi phí và độ ổn định (số lượt viết lại, lỗi lặp), không vì điểm chất lượng: Muse tự nói điểm hai truyện gần nhau.

## Đọc tay: điều đáng chú ý
- **Muse đảo hạng theo thứ tự trình bày.** `compare:AB` (A rồi B): B nhất; `compare:BA` (B rồi A): A nhất. Cả hai lần truyện trình bày SAU được xếp nhất, và các tiêu chí tốt nhất/kém nhất lật theo (ví dụ giọng và lựa chọn: B tốt nhất ở lần đầu, A tốt nhất ở lần sau). Lý do viết ra cũng đổi: lần đầu khen B ở đối chất căng và liền mạch, lần sau khen A ở nhịp và giọng. Sonnet xếp Luna nhất ở cả hai thứ tự. Với một cặp truyện và một lần chạy mỗi thứ tự, không tách được "thiên lệch vị trí" khỏi "hai truyện sát nhau và Muse nhiễu", nhưng đúng là thứ phép chạy hai thứ tự đảo sinh ra để thấy: **hạng so sánh của Muse không dùng được cho cặp này**; điểm solo (không có vị trí) dùng được.
- **Câu trích bịa của Muse:** một bằng chứng ở `compare:AB` (truyện A) ghép hai câu, câu mở "Hắn bước lên một bước, đứng ngang hàng với Triệu Vân Sơn…" không có nguyên văn trong truyện, hai câu sau thì có ở chỗ khác. Code bắt đúng (G3, `quote_found: false`). Sonnet có 3 trích không có thật trên 28; hai giám khảo cùng mức, không giám khảo nào đáng tin hơn về trích.
- Muse chỉ dùng khoảng 1,3 đến 2,3 nghìn token suy luận mỗi lượt ở `effort: high`; `max_tokens` 20000 không bao giờ chạm (ra tối đa 3,2 nghìn gồm suy luận). Độ trễ 17–32 giây mỗi lượt.
- `cached_tokens` = 0 ở mọi lượt, kể cả hai lượt `compare` cùng tiền tố hệ thống và đề bài chung: không thấy cache tự động của Meta trong phép đo này (chi phí tính theo giá đầy đủ).

## Thăm dò API (trước khi viết mã, khoảng 0,03 USD)
`reasoning_effort: none` bị từ chối (HTTP 400, nhận minimal, low, medium, high, xhigh, max); không gửi tham số này thì mô hình vẫn suy luận. `response_format` `json_schema` strict trả JSON đúng schema; `json_object` bỏ qua schema (trả `{"answer": ...}`), nên không dùng. `usage.completion_tokens` đã gồm `reasoning_tokens`. `max_tokens` và `max_completion_tokens` đều nhận; `temperature` nhận (không dùng, như Sonnet). Phản hồi trả `model: "muse-wonder-1.0"` đúng yêu cầu.

## Chưa kiểm
- **Một cặp truyện, một lần chạy mỗi giám khảo.** Độ nhiễu của từng giám khảo (chạy lại cùng truyện có ra cùng điểm không) chưa đo; chênh 0,14 và 0,29 điểm nhỏ hơn mức nhiễu có thể có.
- Chưa thử `effort` khác ngoài `high`, và chưa biết điểm Muse đổi thế nào giữa các mức.
- Hai giám khảo nên chưa có đa số; muốn gộp có ý nghĩa cần giám khảo thứ ba hoặc chạy lặp.
- Giá Muse là giá niêm yết chủ dự án cung cấp (28/10/2026, `judge.yaml`); chi phí thật lấy từ `usage` của Meta nhân với giá đó, không có chi phí do Meta tự báo để đối chiếu.
- Chưa so Muse với đọc tay của người cho tiêu chí nào.
