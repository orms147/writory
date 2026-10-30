# Khai trước: đo lại G6 (`overreach-2`) trên Luna ba lượt, để phân biệt nhiễu với điểm yếu

Khai TRƯỚC khi gọi model thật: commit chứa bản này đi trước mọi lời gọi. Chưa có lời gọi trả tiền nào.

## Vì sao
Lượt xác nhận Luna của vòng hai ([`2026-10-30-g6-check-2`](../2026-10-30-g6-check-2/notes.md), `luna/g6`) đạt luật, nhưng có hai trang hợp lệ bị người chấm đọc là `cost` thay `failed` (nên sản phẩm viết lại thừa): `hc-treo-cot-buom` (bộ khó) và `truoc-nga-nay-im` (bộ gốc), cả hai vượt luật thế giới. Lần đo đầu của `overreach-1` không có báo nhầm nào. Một lần chạy mỗi bộ không cho biết đó là nhiễu hay một thiên lệch thật của `overreach-2` trên Luna.

## Đo gì
Chạy lại **chỉ bộ G6** (`evals/redteam/g6_overreach.yaml` v2, 32 ca) trên model sản phẩm hiện hành: Luna (`openai/gpt-6-luna`, `low`, config mặc định, OpenRouter), đề `overreach-2`, **ba lượt độc lập** (ba lệnh `bench_g6` riêng, cùng bộ câu và đề, mỗi lệnh ghi một thư mục). Không đổi đề, bộ câu hay nhãn. Ba lượt mới cộng với lượt đã có (`g6-check-2/luna/g6`) thành **bốn lần chấm** cho mỗi ca.

```bash
cd backend
for i in 1 2 3; do
  uv run python -m writory.safety.bench_g6 --env-file C:/Work/AI/WriTory/.env --budget 0.0166 \
    --out ../evals/results/2026-10-30-g6-luna-repeat/run$i
done
```
Cần `PYTHONIOENCODING=utf-8`. Trước khi chạy: kiểm không có tiến trình nào khác đang gọi OpenRouter (bench, probe, replay, export); lượt Meta của người kể chạy song song thì được (khác key). Trần cứng 0,05 USD cho cả ba lượt (mỗi lượt `--budget 0.0166`). Chi phí kỳ vọng: lượt đã có tốn cỡ nửa xu USD (suy luận từ một lần chạy), nên ba lượt cỡ 0,015 USD; chạy khô `bench_g6 --dry-run` ước tính cao hơn thật.

## Chỉ số và luật quyết (khai trước)
Tính theo quyết định của sản phẩm (`overreach.needs_rewrite`), như `expectations.md` của vòng hai: `false_rewrite` (trang được qua mà người chấm bắt viết lại) và `rewrite_missed` (trang phải viết lại mà người chấm cho qua), cả bộ 32 ca và từng bộ (`original` 14, `hard` 18).

**Mỗi lượt mới:**
- **T1** `false_rewrite` cả bộ ≤ 2 (bằng số đã thấy ở lượt đầu).
- **T2** `rewrite_missed` cả bộ = 0 (lượt đầu không có).
- **T3** các luật của vòng hai còn giữ: P1 (≤ 1), P2 (≤ 1) trên 8 ca `round2`; M1 bộ khó cũ (bỏ sót ≤ 1/5, viết lại nhầm ≤ 1/5, `hc-chu-cham-trong-van-canh` phải viết lại, `hc-canh-truoc-da-tra-gia` được qua).
- **T4** lời gọi lỗi ≤ 1 mỗi lượt.

**Hai ca được chỉ định** (`hc-treo-cot-buom`, `truoc-nga-nay-im`), mỗi ca đếm số lần bị viết lại nhầm trên **4 lần chấm** (ba lượt mới cộng lượt đã có, ở đó cả hai đều sai):
- **4/4 hoặc 3/4 → "ổn định": điểm yếu thật** của `overreach-2` trên Luna cho ca đó.
- **0/4 hoặc 1/4 → "nhiễu".**
- **2/4 → chưa kết luận.**

**Kết luận chung:**
- **Ổn định trong ngưỡng** khi T1 đến T4 đúng ở cả ba lượt mới (kể cả khi hai ca chỉ định ổn định mà số `false_rewrite` vẫn ≤ 2).
- **Không ổn định** nếu một lượt mới vi phạm T1, T2, T3 hoặc T4: ghi từng ca vào `notes.md`, đọc tay (nhãn hay người chấm sai), **không sửa đề, bộ câu hay nhãn trong PR này**; đề xuất ở một quyết định sau.
- Chạm trần của một lượt (`stopped_by_budget`) thì lượt đó không tính; ghi rõ.
- Ba lượt vẫn là mẫu nhỏ: không đủ chứng minh một tỉ lệ, chỉ đủ nói một ca ra cùng kết luận nhiều lần hay không.
