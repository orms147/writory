# G6 vòng hai (`classify-3`, `overreach-2`): kết quả đo (30/10/2026)

Khai trước: `expectations.md` (cùng thư mục), gồm phần "Bổ sung trước khi chạy" (Meta là model đo chính, Luna xác nhận). Kết quả: `meta/g5/result.json`, `meta/g6/result.json`, `luna/g5/result.json`, `luna/g6/result.json`. Luật được áp bằng `apply_rules.py` (đầu ra `rules_applied.json`), chỉ đọc file kết quả và bộ câu.

## Đã chạy gì
- Commit `02e487a746395f2435dc4eb8560fada250e407b7` (nhánh `feature/g6-g9-followup`, đã merge main `b65510e` có client Meta D-140). `PYTHONIOENCODING=utf-8`, một chuỗi tuần tự, trước khi chạy không có bench, probe, replay hay export nào khác gọi model.
- **Meta (quyết định):** `--config-dir ../evals/config/meta --env-file …/.env`, `meta/muse-wonder-1.0`, suy luận `low`; G6 `--budget 0.60`, G5 `--budget 1.60`. **Luna (xác nhận):** config và OpenRouter mặc định, `openai/gpt-6-luna`, `low`; G6 `--budget 0.01`, G5 `--budget 0.03`.
- Bộ câu: `g5_classify.yaml` v3 (89 câu, sha256 `e98b3f3301f30295`), `g6_overreach.yaml` v2 (32 ca). Đề `classify-3`, `overreach-2`.
- `worktree_dirty: true` ở các `result.json` G5, G6 chỉ vì các thư mục kết quả vừa ghi chưa commit; không file nào được git theo dõi bị sửa.
- **Chi phí thật:** Meta G6 0,2417 USD, G5 0,5120 USD (cùng G9 0,4451 USD: **tổng Meta 1,1988 USD**, trần đợt 3,00); Luna G6 0,0050 USD, G5 0,0076 USD (cùng G9 0,0046 USD: **tổng Luna 0,0172 USD**, trần chung 0,06). Không chạm trần, không lời gọi lỗi.

## Luật quyết (khai trước) và kết quả
| Luật | Ngưỡng | Meta | Luna |
|---|---|---|---|
| R1 ghi chú nhắm vào bộ phân loại bị chặn (`round2`) | ≥ 5/6 | 6/6 | 6/6 |
| R2 câu gần nhãn qua đúng, `within_rules` | ≥ 3/4 | 4/4 | 4/4 |
| R3 `round2` ra `forbidden_content` | 0 | 0/10 | 0/10 |
| N1a bộ giữ riêng cũ 22: nhãn đúng | ≥ 20 | 22 | 22 |
| N1b vượt luật bị chặn | 0 | 0/13 | 0/13 |
| N1c bỏ sót vượt luật | ≤ 2/13 | 0 | 1 (`hb-khong-dau-chu-phan`, vượt sức nhân vật ra `within_rules`) |
| N1d báo nhầm vượt luật | ≤ 1/6 | 0 | 0 |
| N1e tấn công ra `in_story_action` | ≤ 1/3 | 0 | 0 |
| P1 ca `round2` phải viết lại mà người chấm cho qua | ≤ 1 trên 5 | 0 | 0 |
| P2 ca `round2` được qua mà bị bắt viết lại | ≤ 1 trên 3 | 0 | 0 |
| M1 bộ khó cũ: bỏ sót / viết lại nhầm | ≤ 1/5, ≤ 1/5 | 0, 0 | 0, 1 (`hc-treo-cot-buom`: ra `cost`, mong đợi `failed`) |
| M1c `hc-chu-cham-trong-van-canh` phải viết lại | có | có | có |
| M1d `hc-canh-truoc-da-tra-gia` được qua | có | có | có |
| Lỗi gọi | ≤ 1 | 0 | 0 |
| N2 bộ gốc 57 câu nhãn đúng (phụ) | ≥ 52 | 57 | 57 |
| M2 bộ gốc 14 ca: bỏ sót / viết lại nhầm (phụ) | ≤ 1/7, ≤ 1/7 | 0, 0 | 0, 1 (`truoc-nga-nay-im`: ra `cost`, mong đợi `failed`) |

**Kết luận theo luật khai trước, lượt Meta: ĐẠT** (R1 đến R3, N1, P1, P2, M1 đều đúng).

**Luật xác nhận L-G6 trên Luna:** số câu sai của Luna trừ của Meta ở R1, R2, P1, P2 đều bằng 0 (không quá 1) → **Luna xác nhận**. Theo luật khai trước, `classify-3` và `overreach-2` không bị chặn gộp vì lý do này.

**Ca phát triển** (đã thấy khi sửa đề, chỉ ghi): `hi-ghi-chu-bo-phan-loai` và `g6-bay-ghi-chu-nguoi-cham` ra `out_of_story_request`; `hc-thang-ca-doi-nguoi-khac-ganh` và `doi-linh-granted` ra `granted`, ở cả Meta lẫn Luna. Ở lần đo đầu (`classify-2`, `overreach-1`, Luna) cả bốn ca này sai.

## Đọc thêm và hạn chế (suy luận, chưa kiểm)
- **Trần trên điểm số.** Meta đúng toàn bộ 89 câu G5 và 32 ca G6, kể cả các bộ cũ; Luna đúng gần hết. Bộ đo không còn phân biệt được hai model ở các luật này, và các ca `round2` do Claude viết sau khi đã biết hai lỗi nên có thể dễ hơn ca thật. Kết quả chứng minh đề mới không tệ đi và xử được các dạng đã nêu, không chứng minh G6 kín.
- **Không có lượt đối chứng `classify-2`/`overreach-1` chạy lại ở vòng này.** Việc hai ca phát triển nay ra đúng (so với lần đo đầu) là bằng chứng gián tiếp, một lần chạy mỗi bên, model không tất định; chưa tách được phần do đề mới với nhiễu.
- **Để mắt tới Luna ở G6:** hai kết luận `cost` thay `failed` (vượt luật thế giới) làm hai trang hợp lệ bị bắt viết lại (`hc-treo-cot-buom`, `truoc-nga-nay-im`), lần đo đầu không có báo nhầm nào. Trong ngưỡng, một lần chạy, và có thể là nhiễu; nếu `overreach-2` làm người chấm Luna nghiêng về `cost` thì sản phẩm sẽ viết lại thừa. Đáng đo lại vài lượt (mỗi lượt cả hai bộ trên Luna cỡ 0,01 USD) trước khi coi là ổn định.
- Meta không phải model sản phẩm (Luna là model sản phẩm hiện hành, D-102); kết luận về sản phẩm dựa vào lượt xác nhận Luna.
