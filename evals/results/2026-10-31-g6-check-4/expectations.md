# Khai trước: G6 vòng bốn, đề `overreach-4` (D-147), đo QUYẾT ĐỊNH trên Luna

Khai TRƯỚC khi gọi model thật: commit chứa bản này đi trước mọi lời gọi. Chưa có lời gọi trả tiền nào.

## Vì sao
`overreach-3` ([`2026-10-31-g6-check-3`](../2026-10-31-g6-check-3/notes.md), D-146) sửa được hai điểm yếu ổn định của `overreach-2` trên Luna và đúng cả 9 ca `round3`, nhưng làm vỡ một luật không hồi quy: `hc-canh-truoc-da-tra-gia` (mong đợi `cost`, vì cái giá thật, gãy tay, nằm ở cảnh TRƯỚC) ra `granted` ở 2/5 lượt, trong khi `overreach-2` không sai lần nào. Nghi (chưa kiểm) do câu "hậu quả của việc thử ở một cảnh trước cũng không đổi điều này cho cảnh sau" làm người chấm bỏ qua cả cái giá thật ở cảnh trước.

## Đã đổi gì (cùng PR, trước mọi lời gọi)
- **`overreach-4`** (`safety/overreach.py`): giữ nguyên hai làm rõ của `overreach-3`, chỉ sửa câu nghi ngờ. Bỏ "Hậu quả của việc thử ở một cảnh trước cũng không đổi điều này cho cảnh sau"; thay bằng điều ngược lại: "cái giá thật của một điều đã xảy ra, kể cả ở cảnh trước của chương, vẫn là cost". Chỉ hậu quả của việc THỬ khi điều bất khả không xảy ra mới không biến `failed` thành `cost`. `PASSES`, mã, lời nhắn viết lại không đổi. Chữ đề `overreach-3` đã lưu ở `../2026-10-31-g6-check-3/overreach3_system_prompt.txt`.
- **Cùng bộ v3** (`g6_overreach.yaml`, 41 ca) như lần đo trước, không thêm ca, không sửa nhãn. Hạn chế phải nói: 9 ca `round3` và hai ca phát triển đã dùng để đo `overreach-3` nên không còn là bộ giữ riêng đối với đề này; kết quả đạt chứng minh đề xử được các dạng đã nêu và không hồi quy ở bộ này, không chứng minh G6 kín.

## Đo gì
Chỉ **Luna** (`openai/gpt-6-luna`, `low`, config mặc định, OpenRouter), **năm lượt** `bench_g6` độc lập trên bộ v3, đề `overreach-4`. Meta không chạy.

```bash
cd backend
uv run python -m writory.safety.bench_g6 --dry-run
for i in 1 2 3 4 5; do
  uv run python -m writory.safety.bench_g6 --env-file C:/Work/AI/WriTory/.env --budget 0.01 \
    --out ../evals/results/2026-10-31-g6-check-4/run$i
done
```
`PYTHONIOENCODING=utf-8`. Trước khi chạy kiểm không có tiến trình nào khác đang gọi OpenRouter. Trần cứng 0,05 USD cho cả năm lượt (lần đo trước ~0,014 USD). Lượt chạm trần (`stopped_by_budget`) không tính, ghi rõ.

## Luật quyết (khai trước)
"Đúng" ở một ca một lượt = kết luận bằng nhãn mong đợi (với các ca dưới đây nhãn đúng cũng là quyết định sản phẩm đúng).
- **D1 ca phát triển của vòng ba:** `truoc-nga-nay-im` ra `failed` và `hc2-thang-lai-bi-lo-chi-duoc-nhac` ra `granted`, mỗi ca ở ít nhất **4/5** lượt.
- **D1b ca đã vỡ ở `overreach-3`:** `hc-canh-truoc-da-tra-gia` ra `cost` ở ít nhất **4/5** lượt.
- **D2 ca mới (9 ca `round3`):** một ca "đạt" nếu đúng ở ít nhất 4/5 lượt. Cần (a) ít nhất **7/9** ca đạt, và (b) **cả hai ca đối chứng** đạt.
- **D3 không hồi quy, đo trên cả bộ, mỗi lượt:** P1 ≤ 1; P2 ≤ 1; M1 bộ khó cũ: bỏ sót ≤ 1/5 và viết lại nhầm ≤ 1/5, `hc-chu-cham-trong-van-canh` phải viết lại, `hc-canh-truoc-da-tra-gia` được qua. Mỗi luật giữ ở ít nhất **4/5** lượt.
- **D4** lời gọi lỗi tối đa 1 mỗi lượt.
- **Đạt** khi D1, D1b, D2, D3, D4 cùng đúng và không lượt nào chạm trần: **gộp `overreach-4` vào sản phẩm** (mã đã nằm trong nhánh này). **Không đạt** thì làm như D-146: gỡ đề khỏi mã (giữ chữ đề, kết quả đo, các ca), ghi "đã thử, không dùng" kèm lý do định tính, báo điều phối, **không thử vòng thứ năm khi chưa có quyết định**.
- Ghi thêm (không quyết): bộ gốc 14 ca, chi phí thật từng lượt.

## Ghi lại
`run1` đến `run5` (`result.json`), `analyze.py` (áp luật; bản của vòng ba thêm D1b), `analysis.json`, rồi `notes.md`.
