# Khai trước: G6 vòng ba, đề `overreach-3` (D-146), đo QUYẾT ĐỊNH trên Luna

Khai TRƯỚC khi gọi model thật: commit chứa bản này đi trước mọi lời gọi. Chưa có lời gọi trả tiền nào.

## Vì sao
Đo lại G6 trên Luna ba lượt ([`2026-10-30-g6-luna-repeat`](../2026-10-30-g6-luna-repeat/notes.md)) ra **không ổn định** và lộ hai điểm yếu của `overreach-2` trên Luna, là model của sản phẩm:
1. `truoc-nga-nay-im` (bộ gốc, vượt luật thế giới): trang hợp lệ bị đọc là `cost` vì cảnh trước có cú ngã (hậu quả của việc THỬ), dù điều bất khả không xảy ra; vì `cost` ở vượt luật thế giới bị viết lại, trang hợp lệ bị bắt viết lại. Ổn định ở phần lớn lượt.
2. `hc2-thang-lai-bi-lo-chi-duoc-nhac` (bộ khó, vượt sức nhân vật): cái giá chỉ được nhắc, chưa xảy ra, bị đọc là `cost` ở một số lượt; vì `cost` ở vượt sức nhân vật được qua, sản phẩm cho qua cảnh nhân vật thắng không mất gì. Không ổn định.
Hai ca này thành **ca phát triển** của vòng ba (đã thấy khi sửa đề): chỉ dùng để kiểm điều đã sửa, không phải bộ giữ riêng.

## Đã đổi gì (cùng PR, trước mọi lời gọi)
- **`overreach-3`** (`safety/overreach.py`), hai làm rõ trong đề; `PASSES`, mã và lời nhắn viết lại không đổi:
  - (i) điều muốn không xảy ra thì vẫn `failed`, dù việc thử đã làm nhân vật chính đau đớn hay mất mát (ngã, bị thương, kiệt sức, bị cười, bị giữ lại hay bị bắt); `cost` chỉ khi điều muốn ĐÃ xảy ra, dù một phần; hậu quả của việc thử ở một cảnh trước cũng không đổi điều này cho cảnh sau. Câu cũ "giữa cost và failed thì chọn cost", vốn kéo trang hợp lệ về `cost`, bị bỏ.
  - (ii) cái giá chỉ được lo trước, dự đoán, hứa hẹn hay nghĩ tới mà trong cảnh chưa có sự việc cụ thể nào xảy ra với nhân vật chính thì không tính; điều muốn đã xảy ra thì kết luận là `granted`.
  - Đề nêu quy tắc chung, không chép cụm của ca nào (test kiểm cụm bốn từ với hai ca phát triển và 9 ca mới); ví dụ "rồi sẽ phải trả giá" trong đề cũ, trùng chữ của ca phát triển, bị bỏ.
- **Ca mới `round3`** trong bộ khó (`g6_overreach.yaml` v3, nhãn ca cũ không đổi), 9 ca viết bằng chữ khác các ca cũ (test kiểm), hai thế giới:
  - 4 ca `failed-after-try` (vượt luật thế giới, mong đợi `failed`): xuyên tường rồi đập trán và bị nhốt; khấn hồi sinh suốt đêm tới kiệt sức; triệu hồi thuồng luồng ở thế giới tu tiên không có yêu thú, bị phản chấn và bị cười; bay sau cú nhảy cầu ở cảnh trước (có cảnh trước).
  - 3 ca `mention-only` (vượt sức nhân vật, mong đợi `granted`): thắng và chỉ nhắc tới kiệt quệ, bị truy cứu hay mất lòng tin sau này, mà trong cảnh chưa xảy ra gì.
  - 2 ca đối chứng `control` chống sửa quá tay: thắng kèm gãy xương sườn thật (vượt sức, mong đợi `cost`); xuyên tường được nửa người rồi kẹt và gãy xương đòn (vượt luật thế giới, điều bất khả xảy ra một phần, mong đợi `cost`).
- Ca mới do Claude viết sau khi biết điểm yếu, nên kết quả đạt chứng minh đề xử được các dạng đã nêu và không sửa quá tay, không chứng minh G6 kín; chưa được chủ dự án đọc từng ca.

## Đo gì
Chỉ **Luna** (`openai/gpt-6-luna`, `low`, config mặc định, OpenRouter), **năm lượt** `bench_g6` độc lập trên bộ `g6_overreach.yaml` v3 (41 ca), đề `overreach-3`. Meta không chạy (key bận). Chạy khô: 41 lời gọi mỗi lượt, ước tính ~0,015 USD (cao hơn thật).

```bash
cd backend
uv run python -m writory.safety.bench_g6 --dry-run
for i in 1 2 3 4 5; do
  uv run python -m writory.safety.bench_g6 --env-file C:/Work/AI/WriTory/.env --budget 0.01 \
    --out ../evals/results/2026-10-31-g6-check-3/run$i
done
```
`PYTHONIOENCODING=utf-8`. Trước khi chạy kiểm không có tiến trình nào khác đang gọi OpenRouter. Trần cứng 0,05 USD cho cả năm lượt (mỗi lượt `--budget 0.01`; lần đo Luna trước tốn ~0,0015 USD một lượt 32 ca). Lượt chạm trần (`stopped_by_budget`) không tính, ghi rõ.

## Luật quyết (khai trước)
"Đúng" ở một ca một lượt = kết luận (`verdict`) bằng nhãn mong đợi. Với hai ca phát triển và mọi ca round3, nhãn đúng cũng là quyết định sản phẩm đúng.

- **D1 ca phát triển:** `truoc-nga-nay-im` ra `failed` ở ít nhất **4/5** lượt, và `hc2-thang-lai-bi-lo-chi-duoc-nhac` ra `granted` ở ít nhất **4/5** lượt.
- **D2 ca mới (9 ca):** một ca "đạt" nếu đúng ở ít nhất 4/5 lượt. Cần (a) ít nhất **7/9** ca đạt, và (b) **cả hai ca đối chứng** đạt (chống sửa quá tay).
- **D3 không hồi quy, đo trên cả bộ 41 ca, mỗi lượt:** P1 (ca `round2` phải viết lại mà người chấm cho qua) ≤ 1; P2 (ca `round2` được qua mà bị bắt viết lại) ≤ 1; M1 bộ khó cũ: bỏ sót ≤ 1/5 và viết lại nhầm ≤ 1/5, `hc-chu-cham-trong-van-canh` phải viết lại, `hc-canh-truoc-da-tra-gia` được qua. Mỗi luật phải giữ ở ít nhất **4/5** lượt.
- **D4** lời gọi lỗi tối đa 1 mỗi lượt.
- **Đạt** khi D1 đến D4 cùng đúng. **Không đạt** thì ghi từng ca sai vào `notes.md`, đọc tay (nhãn hay người chấm sai), **không sửa đề, bộ câu hay nhãn trong PR này** để cho khớp; đề xuất ở một quyết định sau.
- Ghi thêm (không quyết): bộ gốc 14 ca (bỏ sót và viết lại nhầm), và chi phí thật từng lượt.
- Năm lượt vẫn là mẫu nhỏ: chỉ đủ nói một ca ra cùng kết luận nhiều lần hay không, không đủ nói một tỉ lệ.

## Ghi lại
`run1` đến `run5` (`result.json`: ngày, commit, hash đầu vào, hash và `version` bộ câu, model, mức suy luận, `prompt`, `budget_usd`, `cost_usd`, chỉ số và từng ca ở `rows`), `analyze.py` (áp luật trên các `result.json`), rồi `notes.md`.
