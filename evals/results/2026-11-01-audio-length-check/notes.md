# Truyện audio trong app: độ dài theo phút, có kết, Muse chấm qua từng vòng sửa (D-153 tới D-157)

Người đọc: Claude (điều phối), 1/11/2026; chủ dự án giao tự quyết. Không phải bài đo khai trước: lượt chạy thật để
kiểm tính năng và tìm lỗi. Mỗi lượt đi đúng đường của giao diện qua API dev ở một backend riêng (cổng 8001, không đụng
backend của chủ dự án): `/setup` kiểu audio, tự viết đến hết (`chapters/next?auto=true`), tải `script.txt`. Model viết:
`openai/gpt-6-luna` (mọi vai, key người chơi `dev` lưu trong app). Giám khảo: Meta Muse `muse-wonder-1.0` đọc cả
`tts.txt` một lần, cùng một đề (`tools/meta_feedback.py`, chỉ đổi số phút mục tiêu). Một lượt mỗi ô: điểm Muse lệch
giữa các truyện lớn hơn khác biệt giữa các vòng, nên mọi so sánh là "chưa phân biệt được" trừ khi ghi khác.

## Các lượt
| Thư mục | Commit (main) | Mức | Chương | Chữ | Phút ở 150/160 âm tiết | Chi phí viết | Muse chung | Thoại cho TTS | Kết |
|---|---|---|---|---|---|---|---|---|---|
| `0-short-d154` | `ea4da61` (D-154) | short | 6 | 7.949 | 53 / 50 | 0,060 | 4,5 | 4 | 3 |
| `1-audio_30-d155` | `65ca9e6` (D-155) | audio_30 | 3 | 4.111 | 27 / 26 | 0,040 | 4,5 | 4 | 3 |
| `1-audio_60-d155` | `65ca9e6` (D-155) | audio_60 (7–8) | 8 | 10.913 | 73 / 68 | 0,085 | 5 | 4 | 5 |
| (không có thư mục) | `dc1edf1` (D-156) | audio_30 | – | – | – | – | – | – | – |
| `2-audio_60-d156` | `dc1edf1` (D-156) | audio_60 (6–7) | 6 | 8.133 | 54 / 51 | 0,054 | 5 | 4 | 4 |
| `3-audio_30-d157` | `75d973d` (D-157) | audio_30 | 4 | 4.855 | 32 / 30 | 0,051 | 4,5 | 4 | 4 |

Chi phí viết: USD trên key người chơi, theo `/player/costs` (lượt 0–2 là chênh lệch tổng trước và sau, gồm khởi tạo;
lượt 3 là chi phí ghi theo truyện). Muse: 0,057–0,085 USD Meta mỗi lượt.

- Lượt D-156 `audio_30`: khởi tạo thất bại `STORY_SETUP_INVALID` (log: "milestones ×1" sau lượt sửa). Nguyên nhân: đề
  khởi tạo đòi mỗi hồi một mốc và đúng một mốc kết, mức cho tối đa 3 mốc; kế hoạch 4 hồi không bao giờ hợp lệ. Sửa ở
  D-157 (2–4 mốc), lượt 3 khởi tạo qua.
- Lượt 3: khởi tạo qua (D-157). Chương 1 bị chặn một lần `SCENE_LEAK_BLOCKED` (bộ dò lộ, sau một lượt viết lại); viết tiếp bằng `tools/resume_auto.py` (thử lại như người chơi bấm "thử lại"), qua ngay, 4/4 chương, có kết. Chi phí là chi phí ghi theo truyện, không gồm khởi tạo.

## Độ dài
- Một chương audio 2 cảnh ra khoảng 1.360 âm tiết (4.111/3, 10.913/8, 8.133/6), tức khoảng 8,5 phút ở 160 âm tiết/phút.
  `target_chars` không vào đề viết; số chương quyết độ dài, và model thường chọn số chương tối đa của mức.
- Sau D-156 (`audio_60` 6–7 chương): 6 chương, khoảng 51–54 phút. `audio_30` (3–4 chương): khoảng 26–27 phút ở 3
  chương, 30–32 phút ở 4 chương (lượt 3). Tốc độ đọc thật của TTS tiếng Việt chưa đo; mọi số phút ở đây là ước tính.
- Mọi lượt khởi tạo được đều tự đi tới chương cuối và có `story_finished`.

## Thoại cho TTS: đo bằng code (`tools/dialogue_runs.py`, `tools/pronoun_attrib.py`)
| Lượt | Dòng thoại | Chuỗi quá 2 lượt | Chuỗi đúng 2 lượt | Câu dẫn chỉ có đại từ |
|---|---|---|---|---|
| 0 | 115 | 0 | 2 | 6,2% |
| 1 audio_30 | 72 | 0 | 4 | 23,5% |
| 1 audio_60 | 185 | 0 | 7 | 3,4% |
| 2 audio_60 | 123 | 0 | 6 | 4,3% |
| 3 audio_30 | 68 | 0 | 2 | 4,5% |

- Phép kiểm D-156 (quá 2 lượt thoại liền nhau) không bắt được gì trên các lượt này: model gần như luôn có một dòng kể
  trước mỗi lượt thoại. Điểm "không rõ ai nói" của Muse (4/10 ở mọi lượt) đi cùng câu dẫn chỉ dùng đại từ ("cô ta", "ông
  ta", "người đàn ông") khi nhiều người cùng giới có mặt, cách gọi một người đổi qua lại, và (lượt 2) câu dẫn gắn vào
  cuối dòng thoại ("..., bà nói.", 2/123 dòng; sửa ở D-157 bằng lời dặn).
- Đếm đại từ là gần đúng: tên riêng nhận theo chữ hoa không đứng đầu câu.

## Muse nói lặp lại qua các vòng
- Nhịp: lặp một kiểu vả mặt (khách im lặng, hạ ly), công bố lại điều đã công bố, kết lặp quyết định.
- Phản diện thắng thua bằng lời tuyên bố hay tự thú, ít chứng cứ trên trang.
- Tên và cách gọi đổi qua lại.
D-155, D-156 đã thêm chỉ dẫn cho từng điểm; điểm Muse không đổi rõ (4,5–5). Có thể phần lớn do bước khởi tạo và dàn ý
(chung với truyện chữ: hệ, mốc, bí mật, người canh) chứ không chỉ do chữ của đề (suy luận, chưa kiểm).

## Kết luận
- Độ dài và có kết: đạt. Mức audio ra khoảng 30 phút (`audio_30`) và khoảng 50–55 phút (`audio_60`, 6 chương), mọi
  truyện khởi tạo được đều tự viết tới chương cuối; một chương chặn vì lộ thì thử lại qua.
- Chất lượng theo Muse: chưa phân biệt được giữa các vòng (4,5–5/10 ở cả năm lượt). Các lời dặn trong đề (D-155, D-156,
  D-157) không đổi điểm thấy được; lỗi lớn nhất còn lại là cốt truyện lặp và câu dẫn thoại cho một giọng đọc.

## Chưa kiểm, hướng tiếp (chưa làm)
- Một lượt mỗi ô; muốn biết một thay đổi có giúp không thì cần A/B nhiều truyện mỗi bên và giám khảo khai trước.
- Phép kiểm câu dẫn chỉ có đại từ (kèm tên nhân vật có trong đồ thị, thay cho đoán chữ hoa), nếu muốn dồn cho TTS.
- Tự viết đến hết dừng ở chương bị chặn (lượt 3: `SCENE_LEAK_BLOCKED`); giao diện có thể tự thử lại một lần.
- Tốc độ đọc thật của TTS chủ dự án dùng, để chỉnh số chương.
