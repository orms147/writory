# A/B đổi pha (D-119) trên truyện Dài: khai trước khi chạy

Người đọc: writory-28 (điều phối) và chủ dự án, 29/10/2026. **Tài liệu này khai TRƯỚC khi chạy bất kỳ lượt nào có gọi model trả tiền.** Chưa có kết quả; khi chạy xong, phần kết quả thêm vào cuối file này mà KHÔNG sửa các mục trên. Commit đăng ký: ghi ở PR chứa file này (main `dfcc5fa` lúc soạn). Chưa gọi model trả tiền: chỉ dry-run bằng model giả và ước tính từ `calls.jsonl` của các lượt Dài cũ.

## Giả thuyết
**H1.** Bật `limits.context.phase_shift_every = 5` (câu `phase_shift` trong mục tiêu chương: đổi nơi, người nắm quyền quyết định hay luật chơi, KHÔNG thêm mối nguy cùng loại) làm truyện Dài **ít đứng yên theo vòng lặp mối nguy/cùng nơi** ở đoạn giữa (ch6–16) so với tắt, mà không làm mất mốc đúng hạn, không làm văn tệ hơn và không tốn thêm đáng kể.

Cơ sở: `../2026-10-29-run-long-baseline/notes.md` (nguyên nhân 1: một cơ chế nguy hiểm làm động cơ nhiều chương liền, kể cả khi nơi chốn đổi) và D-119. Cờ tắt mặc định; chưa biết số 5 là đúng.

## Thiết kế
- Thế giới: **một** khởi tạo cho mọi lượt, `--setup-from evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1` (kế hoạch 24 chương; lượt `-2` cũng dùng nó), đề `evals/scenarios/story_run/long-ky-ao-hanh-trinh.yaml`, seed của đề 20261031 (không `--seed`). Chọn kỳ ảo hành trình vì cả hai lượt đã chạy ở đó đều có đoạn lặp giữa truyện (ch8–10 ở lượt 1, ch10–19 ở lượt 2).
- Hai nhánh, chỉ khác một dòng config:
  - **A (đối chứng):** `config/` hiện hành, `phase_shift_every: null`.
  - **B:** `--config-dir` trỏ tới bản sao `config/` chỉ đổi `limits.yaml` dòng `phase_shift_every: 5` (cách ghi đè đã có, `docs/eval.md`; không sửa `limits.yaml` của repo). Bản sao dựng bằng `cp -r config <thư mục tạm>` rồi `sed -i 's/^\(\s*phase_shift_every:\).*/\1 5/'`; `diff` với `config/limits.yaml` phải đúng một dòng. `meta.json` ghi hash config khác nhau và `context_flags.phase_shift_every`.
- Cùng model (mọi vai GPT-6 Luna), cùng commit, **đề lựa chọn mặc định (không `--prompt-variant v4`)**: `v4` là thay đổi độc lập, so riêng sau (`docs/eval.md`: hai thay đổi so từng cái một).
- `--chapters 16`, `--budget` từng lượt ở mục Chi phí. Giữ máy không ngủ, một chuỗi nối tiếp, xen kẽ A và B để trôi dạt của model rải đều. Lượt chết giữa chừng thì chạy tiếp bằng `--resume` (D-124), ghi rõ `resume_points`.
- Số lượt: **A1, B1, A2** (A2 đo nhiễu của chính nhánh đối chứng), rồi **B2 chỉ khi luật bên dưới gọi** (điểm biên). Tối đa 4 lượt.
- Đối chiếu cũ không dùng làm đối chứng: `ky-ao-hanh-trinh-1/-2` chạy trước D-116 (theo dõi mốc), D-117/D-121, `setup-10`; nhánh A phải chạy lại trên main hiện hành.

## Chỉ số (dải ch6–16; ch1–5 là khởi động, cờ chưa thể bật trước ch5)
Chính, ba chỉ số bằng code (`psab_metrics.py`, đã chạy thử trên ky-ao-1/-2 và tu-tien-3) và một chỉ số đọc:
- **P1 `same_place_longest`** (thấp hơn là tốt): số chương liền dài nhất mà cuối chương nhân vật chính ở cùng một nơi. Tham chiếu cũ trong ch6–16: ky-ao-2 = 6, ky-ao-1 = 4 (ch6–14), tu-tien-3 = 4.
- **P2 `new_places`** (cao hơn là tốt): số nơi nhân vật chính tới lần đầu trong dải. Tham chiếu cũ: 1, 1, 1.
- **P3 `place_returns`** (số chương, thấp hơn là tốt): chương về lại nơi đã ở trong ba chương trước. Tham chiếu cũ: 0, 2, 0.
- **R1 chương lặp mô-típ theo đọc mù** (thấp hơn là tốt): Muse (`muse-wonder-1.0`, reasoning low) đọc nguyên văn ch6–16 của từng lượt bằng `../2026-10-29-run-long-baseline/muse_read.py ... 6 16 --no-ending`, không có nhãn nhánh (script chỉ gửi tag của đề và văn; tên thư mục đầu ra là mã ngẫu nhiên, bảng mã ↔ lượt ghi vào `key.json` và chỉ mở sau khi đã đếm). Đếm **cơ học** số dòng trả lời câu 1 bắt đầu bằng `GIẬM CHÂN` trong ch6–16, không cân nhắc. Cảnh báo: người đọc đơn, độ nhạy thấp (ở các lượt cũ Muse chỉ đánh dấu 0–2 chương mỗi lượt).

Chỉ số **không** dùng để quyết (chỉ báo cáo): `stalled_count` (chương không đổi trạng thái, `long_metrics.py`), `rewrites`, số lần `phase_shift` bật, đọc tay của Claude (ghi chương nào, kèm câu trích `chNN.md:dòng`).

Không dùng `pacing._phase_changes` làm chỉ số kết quả vì nhánh B được nhắc làm đúng việc đó (vòng tròn); chỉ dùng nó như kiểm tra thao tác bên dưới.

## Kiểm tra thao tác (không phải kết quả)
Nhánh B phải thật sự bật câu nhắc và model phải theo: `report.json.phase_shift_chapters` không rỗng, và trong các chương đó, ít nhất một nửa có nơi mới hoặc mốc xong ở chương đó hoặc chương kế (`psab_metrics.py`: `phase_shift_followed`). Nhánh A phải rỗng.
- B không bao giờ bật (truyện tự đổi pha trước, hoặc `standstill`/`idle` nhường chỗ): kết luận **"không thử được"**, không phải "không có tác dụng".
- B bật nhưng dưới nửa số lần được theo: kết luận **"câu nhắc không đổi hành vi model"**, bất kể chỉ số chính.

## Chặn (guard): vi phạm thì B không thể "tốt hơn"
- **g1 mốc:** `milestones_due_on_time` của B ≥ giá trị nhỏ nhất của A trừ 1 (D-116 ghi mốc; kỳ vọng không mất mốc vì mục tiêu đổi pha không tranh với mốc).
- **g2 chi phí:** `usd_per_chapter` của B ≤ 1,15 × giá trị lớn nhất của A.
- **g3 văn:** điểm solo trung bình (Muse, bài F `pack --replicates` rồi `judge --kinds solo`, mỗi truyện chấm một lần) của B ≥ điểm trung bình của A trừ 0,77 (= 2 σ_tổng của Muse, 0,387 ở `../2026-10-28-ab-baseline/notes.md`). Cặp pack: (A1, B1) và (A2, B1); B1 được chấm hai lần, lấy trung bình hai lần.

## Luật quyết định (khai trước; áp một lần sau khi có đủ số liệu)
Gọi **a** là các giá trị của A (hai lượt A1, A2), **b** là các giá trị của B (một lượt, hoặc hai nếu có B2). Với mỗi chỉ số trong P1, P2, P3, R1:
- B **tốt hơn** khi MỌI giá trị của b tốt hơn MỌI giá trị của a ít nhất một đơn vị (P1: b ≤ min a − 1; P2: b ≥ max a + 1; P3 và R1: b ≤ min a − 1).
- B **tệ hơn** khi mọi giá trị của b tệ hơn mọi giá trị của a ít nhất một đơn vị (đối xứng).
- Còn lại: không rõ.
Điểm = số chỉ số "B tốt hơn" − số chỉ số "B tệ hơn".
- **B TỐT HƠN** khi điểm ≥ +3 và kiểm tra thao tác đạt và cả ba chặn g1–g3 đạt.
- **B TỆ HƠN** khi điểm ≤ −2 hoặc có chặn g1 hoặc g3 bị vi phạm (g2 vi phạm thì ghi "tốn hơn", không tự thành "tệ hơn").
- **Chạy B2** khi sau A1, B1, A2 mà điểm đúng +2, hoặc đúng +1 và hai trong P1–P3 tốt hơn; tính lại với b = (B1, B2).
- Còn lại: **CHƯA PHÂN BIỆT ĐƯỢC.** Đây là kết quả dự kiến nếu hiệu ứng nhỏ.

Giới hạn đã biết của thiết kế: hai lượt A cho ước lượng nhiễu rất thô (hai điểm); R1 là một người đọc; một thế giới, một seed; model không tất định, nên cùng nhánh hai lượt có thể lệch như ky-ao-1 và ky-ao-2 (đoạn lặp ở ch8–10 và ch10–19). Phép này chỉ đủ nhìn thấy hiệu ứng lớn. Nếu kết quả "chưa phân biệt được" thì không kết luận gì về D-119, và không bật cờ mặc định.

## Chi phí ước tính (chưa chạy)
Nguồn: `cost.by_chapter` trong `report.json` của các lượt Dài gần nhất (mọi vai Luna). Chi phí cộng dồn tới chương N:

| lượt | tới ch12 | tới ch16 | tới ch24 | trung vị mỗi chương | lớn nhất mỗi chương |
|---|---|---|---|---|---|
| ky-ao-hanh-trinh-2 (24/24) | 0,1165 | 0,1613 | 0,2526 | 0,0104 | 0,0148 |
| tu-tien-3 (17/24) | 0,1480 | 0,1946 | | 0,0113 | 0,0197 |
| ky-ao-hanh-trinh-1 (14/24) | 0,1069 | | | 0,0089 | 0,0107 |

Ước tính mỗi lượt 16 chương: **0,16 đến 0,19 USD** (lấy 0,175), cộng một biên nhỏ chưa đo vì theo dõi mốc (D-116) thêm vài dòng vào đề trích mà các lượt trên chưa có; cờ đổi pha chỉ thêm một câu mục tiêu chương, không đáng kể.
- **Đề xuất `--budget` mỗi lượt 0,25 USD** (hệ số khoảng 1,4 so với chi phí thật, như hai lượt Dài trước: trần 0,35 cho chi phí 0,25; giữ chỗ tối đa mỗi lời gọi nên trần chạm trước chi phí thật).
- **3 lượt (A1, B1, A2):** kỳ vọng 0,53 USD, trần cộng lại 0,75. **4 lượt (thêm B2):** kỳ vọng 0,70, trần 1,00. OpenRouter còn khoảng 4 USD dưới trần 10, nên cả hai nằm trong mức cho phép.
- Meta (Muse): đọc R1 mỗi lượt khoảng 0,1–0,15 USD (đọc 7 chương ở đo nền tốn 0,08 trung bình: 0,3144 USD cho bốn lần); chấm solo mỗi truyện 16 chương khoảng 0,25–0,3 USD (1,1595 USD cho 6 thư mục solo, mỗi thư mục hai truyện 6 chương, ở `../2026-10-29-ab-v3/notes.md`, nhân lên theo độ dài); 3 lượt gồm bốn lần chấm khoảng 1,5 USD tất cả, trên trần Meta còn nhiều. Anthropic: không dùng.
- Phương án gọn nếu cần cắt: 12 chương mỗi lượt giảm chi phí xuống khoảng 0,12 USD mỗi lượt (3 lượt 0,36), **nhưng không nên** (suy luận từ `pacing.phase_shift`, chưa thấy trên lượt thật) vì câu bật khi đã 5 chương không có đổi pha thật nên lần nhắc đầu rơi vào khoảng ch5–10 tuỳ truyện tự đổi pha lúc nào (ở ky-ao-1 nhân vật vào rừng ở ch5, nên nhắc đầu khoảng ch10); 12 chương chỉ cho nhánh B một lần nhắc và hai chương dưới tác dụng của nó, 16 chương cho khoảng hai lần nhắc.

## Kiểm tra trước khi chạy (đã làm, không tốn tiền)
- Dry-run hai nhánh, `--dry-run --chapters 16` trên `long-ky-ao-hanh-trinh.yaml`: cả hai chạy hết 16 chương; `meta.json` ghi `context_flags.phase_shift_every` là `null` (A) và `5` (B), hash config khác nhau (`e2c8343b233c…` và `e41337d6de42…`), và chỉ khác một dòng của `limits.yaml`. **Giới hạn của dry-run:** `phase_shift_chapters` rỗng ở B vì thế giới giả đổi nơi/mốc đủ nhanh nên câu không bao giờ bật; dry-run chỉ chứng minh đường ống (cờ → meta → report), không chứng minh câu nhắc bật đúng. Việc đó được test ở PR #96 (`test_pipeline_pacing.py`).
- Dry-run `--setup-from …-ky-ao-hanh-trinh-1` với model giả: đọc được khởi tạo (kế hoạch 24 chương, đề và seed khớp) rồi dừng ở bước lựa chọn chương 1 vì model giả không biết các id của thế giới thật. Đó là hạn chế của model giả, không phải của khởi tạo; lượt thật dùng model thật.
- `psab_metrics.py` chạy được trên ba lượt Dài cũ (dải ch6–16), cho các số tham chiếu ở mục Chỉ số.

## Cách chạy dự kiến (không chạy ở đợt này)
```
cd backend
# thư mục config cho B: cp -r ../config <tạm>; sed -i 's/^\(\s*phase_shift_every:\).*/\1 5/' <tạm>/limits.yaml
uv run python -m writory.pipeline.bench_run --scenario ../evals/scenarios/story_run/long-ky-ao-hanh-trinh.yaml \
  --setup-from ../evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1 --chapters 16 --budget 0.25 \
  --label psab-a1                                   # A; B thêm --config-dir <tạm>, nhãn psab-b1
# thứ tự: psab-a1, psab-b1, psab-a2 (rồi psab-b2 nếu luật gọi)
# số đo: python evals/results/2026-10-29-phase-shift-ab/psab_metrics.py 6 16 <các thư mục chạy>
```
Mỗi lượt một script nền nối tiếp, kiểm không còn chuỗi cũ đang chạy trước khi bắt đầu, giữ máy không ngủ (như `paid-run-hygiene`).

## Kết quả
**Kết luận theo luật khai trước: "không thử được".** Kiểm tra thao tác không đạt: ở nhánh B (`phase_shift_every: 5`) câu nhắc đổi pha **không bật ở chương nào** trong 16 chương (`report.json` `phase_shift_chapters` rỗng, `phase_shift` không có ở attempt nào). Không kết luận gì về tác dụng của D-119; cờ giữ tắt. Không chạy B2, không chấm R1 và văn bằng giám khảo (không đổi được kết luận; tiết kiệm phần Meta đã duyệt).

**Vì sao không bật (đã kiểm trên dữ liệu):** mốc kế hoạch xong là một lần "đổi pha" (`pacing._phase_changes`, D-119) và đặt lại đồng hồ. Ở B1 bộ trích đánh dấu mốc xong ở ch1, 2, 3, 7, 11, 16 (`plan_vs_result.milestones`: 4 trong 6 mốc "early"), không lần nào cách nhau quá 5 chương, nên đồng hồ không bao giờ chạm 5. **Suy luận, chưa kiểm:** cờ này mù chừng nào dấu mốc còn dễ dãi (cùng loại lỗi với tu-tiên m6, D-129); muốn thử lại D-119 thì hoặc không tính mốc xong làm đổi pha, hoặc thử trên thế giới ít mốc, hoặc N nhỏ hơn: mỗi lựa chọn là thiết kế mới, cần khai trước mới.

| Lượt | Commit | Config (gộp) | Cờ | Chương | Chi phí USD | Nơi liền dài nhất (P1) | Nơi mới (P2) | Quay lại nơi cũ (P3) | Chương đứng yên (code) | Mốc xong / đúng hạn |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | d9a196a | e2c8343b233c | tắt | 16 | 0,1556 (+0,0088 ước tính chưa tính tiền) | 7 | 1 | 1 (ch7) | 4 | 6 / 1 |
| A2 | d9a196a | e2c8343b233c | tắt | 16 | 0,1680 | 5 | 1 | 0 | 4 | 6 / 1 |
| B1 | ch1–11 d9a196a, ch12–16 d916311 | e41337d6de42 → 2c4fa9ce7f63 | 5 | 16 | 0,1740 | 4 | 1 | 0 | 5 | 6 / 1 |

Số tính bằng `psab_metrics.py 6 16` (dải ch6–16). Model mọi vai: `config/models.yaml` (meta.json của từng lượt). Chênh A1–A2 ở P1 (7 so với 5) cho thấy nhiễu giữa hai lượt cùng cấu hình cỡ hai chương; số của B1 nằm trong khoảng đó, và vì câu nhắc chưa từng bật nên B1 thực chất là một lượt A thứ ba.

**B1 chạy làm ba chặng:**
- `2026-10-29-run-psab-b1` dừng ở chương 12, `INTERNAL_ERROR` trước mọi lời gọi model. Nguyên nhân: cạnh `HOLDS` tới một Fact làm sập ngữ cảnh viết. Đây là lỗi sản phẩm, đã sửa ở D-128.
- Hai lần `--resume` ngay sau đó (`b1-r1`, `b1-r2`) trên cùng commit ra đúng lỗi đó và không tốn tiền. Hai thư mục này không commit vì chỉ là bản sao.
- `2026-10-30-run-psab-b1-r3` chạy tiếp từ chương 12 bằng `--resume --resume-allow-drift` trên d916311, là main có D-128 cùng D-125 tới D-127. `resume_drift` chỉ có `git.commit` và `config.sha256`; phần config khác là các số của bộ xuất video, còn cờ ngữ cảnh, đề và model không đổi.
- Chương 12–16 của B1 chạy trên code có thêm D-126 (lựa chọn sai bỏ riêng) và D-128. Nó lệch so với A1 và A2, nhưng chỉ ảnh hưởng lựa chọn và cạnh, không ảnh hưởng câu nhắc đổi pha.

**Chi phí cả đợt:** OpenRouter 0,4975 USD thật cộng 0,0088 USD ước tính chưa tính tiền, trên trần 1,00. Meta 0 USD.
