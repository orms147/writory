# Kết quả: cao trào bằng code (D-142) đo thật trên Muse

Người đọc: Claude điều phối và chủ dự án, 31/10/2026. Luật khai trước: `expectations.md` (commit `4ca3e8a`, trước
lời gọi trả tiền đầu tiên); không sửa mục nào ở đó. Mọi số ở đây là của `meta/muse-wonder-1.0`, không so thẳng với
lượt Luna cũ.

## Chạy gì
- Commit chạy: `4ca3e8a` cho mọi lượt (`meta.json.git`, `dirty: false`). Hai nhánh chỉ khác hash `limits.yaml`
  (ctrl `fb11ff27e6`, treat `46dbc56524`); `models.yaml`, `guard.yaml`, `quality.yaml`, `moderation.yaml`,
  `story_lengths.yaml` cùng hash. Thư mục config của ctrl chép vào `cfg-ckr-ctrl/` (`models.yaml` giống từng byte
  `evals/config/meta/models.yaml`; `limits.yaml` chỉ có trần Meta và `climax_aftermath_chapters: null`); ctrl thêm
  `--prompt-variant climax-old` (`meta.json.prompt_variant.overrides: goals:climax_aftermath`).

| Lượt | Thư mục | Chương | Lời gọi | Chi phí | Trần | Ghi chú |
|---|---|---|---|---|---|---|
| ky-ao ctrl | `../2026-10-31-run-ckr-ky-ctrl/` | 20/20 | 274 | 12,5374 USD | 16 | |
| ky-ao treat (mất) | `../2026-10-31-run-ckr-ky-treat/` | dừng ở ch15 | 191 | 8,1248 USD | 16 | máy khởi động lại khoảng 01:53; chưa có checkpoint nên không `--resume` được; `meta.json` còn `running`. Không dùng số nào của lượt này |
| ky-ao treat | `../2026-10-31-run-ckr-ky-treat-2/` | 20/20 | 274 | 13,6923 USD | 16 | chạy lại từ đầu, cùng commit, cùng lệnh, label `ckr-ky-treat-2` |
| tu-tien treat | `../2026-10-31-run-ckr-tu-treat/` | 24/24, kết truyện | 364 | 18,9051 USD | 26 | |
| chấm (b) | `judge/` | 10 mục | 1 | 0,1464 USD | 3 | |
| **Cộng** | | | | **53,41 USD** | **61** | gồm 8,12 USD của lượt mất |

- Lượt mất là lý do của D-148 (checkpoint mỗi chương); lượt chạy lại dùng commit cũ của nhánh này (không có D-148)
  để cả ba lượt cùng một mã như đã khai.
- Thời gian Muse: khoảng 57 đến 65 phút cho 20 chương ky-ao, 65 phút cho 24 chương tu-tien.

## Kết luận theo luật khai trước
**Chưa phân biệt được: giữ D-142 như đã gộp, không có bằng chứng thêm.**
- (a) **không thử được**: không lượt treat nào có dấu cao trào sớm.
- (b) giám khảo chấm treat tốt hơn (`HẬU QUẢ` 2 so với 0, `DIỄN LẠI` 0 so với 0), nhưng đọc tay mù lệch giám khảo ở
  2 trên 4 chương, cả hai đều của treat: đúng ngưỡng "≥ 2 chương", nên theo luật **không kết luận (b)**.
- (c) g1 đến g5 đạt cả năm.
- Luật quyết định: TỐT HƠN cần (b) treat tốt hơn, không có; TỆ HƠN cần (b) treat tệ hơn hoặc g1, g4 vi phạm, không
  có; còn lại là CHƯA PHÂN BIỆT ĐƯỢC. Hành động đã khai: giữ D-142, không chạy thêm lượt khi chưa có ngân sách. Không
  chạy xác nhận Luna, vì luật chỉ đòi bước đó khi kết quả là TỐT HƠN.

## (a) Đánh dấu lại ứng viên: không thử được
Không lượt `treat` nào có dấu cao trào trước khoảng (`truth_dump.json`, thuộc tính `milestones` của nút `Chapter`):

| Lượt | Mốc cao trào | Khoảng | Dấu | `early_mark` | `never_marked` |
|---|---|---|---|---|---|
| ky-ao treat | m6 | 16–18 | ch16 | không | không |
| ky-ao treat | m7 | 20–23 | ch20 | không | không |
| tu-tien treat | m6 | 20–22 | ch21 | không | không |

Số dấu cao trào sớm của Muse: 0 trên 3 dấu cao trào ở các lượt treat (0 trên 4 nếu tính ctrl, m6 ở ch16). Với Luna,
tu-tien m6 có dấu sớm ở ch19; Muse không lặp lại, nên câu hỏi (a) vẫn để ngỏ.

## (b) Hậu quả trên trang
Chương cao trào xong `d`, đọc từ dấu: ky-ao ctrl m6 ở ch16, ky-ao treat m6 ở ch16, tu-tien treat m6 ở ch21
(`judge/spec.json`). Tính lại mục tiêu chương bằng code của commit chạy, không gọi model: ch17 và ch18 của cả hai
nhánh ky-ao có dòng "m6 đã xảy ra" (ctrl dùng chữ cũ `milestone_done` qua biến thể, treat dùng câu
`climax_aftermath`), ch19 và ch20 không nhánh nào có dòng m6; tu-tien ch22 (trong khoảng) và ch23 (ngoài khoảng,
chỉ có nhờ `climax_aftermath_chapters: 2`) có câu hậu quả. Đây là lần đầu cờ `climax_aftermath_chapters` thật sự
đổi đề một chương.

Chấm mù bằng Muse (`judge_aftermath.py`, seed 20261030, 10 mục, `judge/request.json`, `answer.json`,
`counts.json`; khoá `key.json` mở sau khi đếm). Nhãn từng chương:

| Nhánh | ch d+1 | ch d+2 | ch d+3 (báo cáo) | ch d+4 (báo cáo) |
|---|---|---|---|---|
| ky-ao ctrl (d = 16) | KHÁC | KHÁC | KHÁC | HẬU QUẢ |
| ky-ao treat (d = 16) | HẬU QUẢ | HẬU QUẢ | DIỄN LẠI | HẬU QUẢ |
| tu-tien treat (d = 21) | KHÁC | KHÁC | | |

Luật trên d+1, d+2 của Pha 1: `HẬU QUẢ` treat 2, ctrl 0 (2 ≥ 0 + 1); `DIỄN LẠI` treat 0, ctrl 0 (0 ≤ 0). Theo giám
khảo: **treat tốt hơn ctrl**. n = 2 chương mỗi nhánh, một lượt mỗi nhánh: rất thưa.

**Đọc tay: lệch giám khảo ở 2 chương, nên không kết luận (b).** Đọc tay giao cho một agent Claude mới, mù nhánh và
mù nhãn của giám khảo: điều phối đã thấy nhãn giám khảo trước khi đọc, nên tự đọc thì không còn mù. ch15 đến ch18 của
mỗi nhánh được chép nguyên văn sang hai thư mục tên trung tính, nên số dòng giữ nguyên. Agent dùng cùng định nghĩa
ba nhãn với giám khảo, thêm một điều kiện: hậu quả phải nối về chính cao trào ở ch16 của bản đó. Điều phối đã kiểm
12 câu trích của agent, câu nào cũng có thật ở đúng dòng.

| Chương | Giám khảo | Đọc tay | Lý do của đọc tay, câu trích |
|---|---|---|---|
| treat ch17 | `HẬU QUẢ` | `DIỄN LẠI` | Khương lại đòi bản đồ, Thảo lại từ chối, Khương lại đi trước: "Tôi không bán đường của người khác để mua đường cho mình." (`2026-10-31-run-ckr-ky-treat-2/chapters/ch17.md:140`). Agent ghi là phân vân: phần bẫy vệt muối chia đôi nhóm (dòng 38–93) là việc mới và dài hơn, nên chấm theo tỉ lệ chữ thì có thể ra `KHÁC` (vẫn lệch giám khảo) |
| treat ch18 | `HẬU QUẢ` | `KHÁC` | phần lớn chương là đường đi và mất nước dự trữ (`ch18.md:169`); đoạn Thảo mở bản đồ cho Ngân vì "Khương đã đi trước" (`ch18.md:143`) chỉ chiếm khoảng một phần tư chương |
| ctrl ch17 | `KHÁC` | `KHÁC` | vượt ván gãy, nắn vai cho Ngân, lần xuống hốc; không có Khương (`2026-10-31-run-ckr-ky-ctrl/chapters/ch17.md:139`) |
| ctrl ch18 | `KHÁC` | `KHÁC` | Thảo giấu bản đồ trước Ngân và Đinh Lộc; không nối về vụ khai sổ bến hay về Khương (`ch18.md:51`) |

Cao trào ở ch16 của hai nhánh là hai cảnh khác nhau. Ở treat, Thảo đối mặt Khương trên bãi muối, hiểu ra hắn là
người thúc lính thu bản đồ và không giao bản đồ (`ky-treat-2/chapters/ch16.md:159`, `:163`). Ở ctrl, Phùng Yên chỉ
mặt Khương là người bảo gạch sổ bến, rồi Thảo khai công khai điểm đến (`ky-ctrl/chapters/ch16.md:83`, `:105`); mối
nối với vụ thu hồi bản đồ chỉ nằm ở một câu suy nghĩ.

Hai cách đọc chỉ hai chiều ngược nhau ở treat. Giám khảo thấy hậu quả. Đọc tay thấy treat ch17 dựng lại đúng thế đối
đầu của cao trào, tức chính điều câu `climax_aftermath` bảo tránh; nếu chỉ tính đọc tay thì treat sẽ "tệ hơn"
(`DIỄN LẠI` 1 so với 0). Điều đếm được, không phụ thuộc nhãn: ở treat, cao trào còn trên trang ở ch17–18 (số dòng có
tên Khương: 11 và 7), ở ctrl thì không (0 và 0). Tức câu hậu quả giữ cao trào lại trong truyện, nhưng nó thành hậu
quả hay thành diễn lại thì hai chương mỗi nhánh không phân được. Đây là mô tả, không vào luật.

Ngoài luật:
- ky-ao treat ch19 (d+3, đã hết câu hậu quả) bị chấm `DIỄN LẠI`: Khương lại đòi đổi bản đồ lấy Đinh Lộc, đúng xung
  đột của cao trào. ky-ao treat ch20 có dấu m7 (cao trào thứ hai), ctrl chưa có dấu m7 tới ch20.
- tu-tien treat: câu hậu quả có ở cả ch22 và ch23 mà giám khảo chấm `KHÁC` cả hai (chương đi sang việc qua khe nước,
  cứu người, người đưa tin lộ thân phận). Không có ctrl ở thế giới này, nên chỉ ghi lại: câu hậu quả không bảo đảm
  chương viết hậu quả.

## (c) Chặn hồi quy (Pha 1, treat so với ctrl): đạt cả năm

| Chặn | ctrl | treat | Ngưỡng | Đạt |
|---|---|---|---|---|
| g1 `status`, chương đã ghi | `done`, 20 | `done`, 20 | cả hai đủ 20 | có |
| g2 `early_reveal` tìm thấy | 0 | 2 | ≤ ctrl + 2 | có, sát ngưỡng |
| g3 USD mỗi lời gọi | 0,04576 | 0,04997 (× 1,092) | ≤ × 1,15 | có |
| g4 mốc đúng hạn | 2 (m1, m6) | 4 (m1, m5, m6, m7) | ≥ ctrl − 1 | có |
| g5 `rewrites` | 18 | 15 | ≤ ctrl + 3 | có |

- ky-ao treat ch10: kiểm duyệt G9 (`moderation:gore`) chặn cảnh 2 sau một lượt viết lại, sự kiện
  `SCENE_LEAK_BLOCKED` (mã trung tính cho mọi lỗi chặn, D-37); bộ đo bấm thử lại một lần, lượt 2 ghi được. Không
  vào chặn nào.
- Pha 2, tu-tien treat (không áp chặn): `status` `done`, `story_finished` có, `early_reveal` 0, 0,05194 USD mỗi
  lời gọi, `rewrites` 34 (`guard:overdue_secret` ×13, `quality:length` ×25, `quality:repetition` ×13), mốc `ending`
  m7 `missed` (chương 24 kết truyện nhưng bộ trích không đánh dấu mốc kết).

## Giới hạn
Như khai trước: một lượt mỗi nhánh, hai chương mỗi nhánh vào luật, Muse chấm Muse, Muse không tất định. Hai nhánh
ky-ao rẽ khác nhau từ ch1 (cùng khởi tạo, khác văn), nên cao trào ở ch16 của hai nhánh là hai cảnh khác nhau; giám
khảo chỉ thấy câu mô tả mốc trong kế hoạch, không thấy ch16. (a) không thử được vì Muse không đánh dấu cao trào sớm.

## Lệnh
```
cd backend   # PYTHONIOENCODING=utf-8
# ba lượt: các lệnh ở expectations.md, mục "Bổ sung trước khi chạy", trần ở mục "Trần --budget nâng lên";
#   lượt treat chạy lại: như lượt treat, --label ckr-ky-treat-2
J=../evals/results/2026-10-30-climax-code-real/judge
uv run python ../evals/results/2026-10-30-climax-code-real/judge_aftermath.py pack --out $J --spec $J/spec.json
uv run python ../evals/results/2026-10-30-climax-code-real/judge_aftermath.py judge --out $J --env-file <.env> --budget 3.0
uv run python ../evals/results/2026-10-30-climax-code-real/judge_aftermath.py count --out $J
```
