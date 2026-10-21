# Bàn giao thiết kế giao diện WriTory — bản 1

Đầu vào cho việc dựng `frontend/` (React + TypeScript + Tailwind, design §11). Đây **không phải code**: là ảnh màn, HTML tĩnh của từng màn, token, hiệu ứng và quy tắc hành vi để dựng lại bằng component.

> Lưu ý cho agent: theo `CLAUDE.md` §2, repo chỉ có các file tài liệu trong bản đồ tài liệu. Thư mục này do Chủ dự án yêu cầu xuất để làm đầu vào. Khi dựng xong frontend, hỏi Chủ dự án: giữ thư mục này, hay chuyển phần quy tắc còn dùng vào `docs/design.md` rồi xoá.

## 1. Đọc theo thứ tự

1. `screenshots/` — ảnh từng màn (máy tính rộng 1440, điện thoại 390×844).
2. `screens/index.html` — mở trong trình duyệt để xem cả bộ; mỗi màn là một file HTML tĩnh, bấm qua lại được theo luồng.
3. `tokens/tokens.css` + `tokens/tailwind-theme.js` — màu, chữ, bo góc, chuyển động.
4. `assets/effects.css` — hiệu ứng (con trỏ, nút, thẻ, chữ hiện dần, chờ, nền kẻ ô) và luật giảm chuyển động.
5. File này — hành vi, trạng thái, nối API, luật không lộ bí mật, điểm còn mở.
6. `source-dc/` — file gốc trên canvas (`.dc.html`): template `{{…}}`, `<sc-for>`, `<sc-if>` và lớp `Component` có state và logic tương tác. Đọc khi cần biết màn phản ứng thế nào.

Ảnh và HTML tĩnh được chụp ở **trạng thái đầu** của mỗi màn (chưa bấm gì, chưa chạy hẹn giờ). Các trạng thái khác nằm trong `source-dc/` và mục 5.

## 2. Hướng thiết kế

- **Khung tối "mực đêm"**, trang đọc là **giấy** sáng. Điểm nhấn duy nhất là **chu sa**, dùng cho hành động chính và dấu triện. Ngọc chỉ dùng cho trạng thái tốt (đã có khoá).
- **Ba họ chữ, đều đủ dấu tiếng Việt:**
  - Cormorant Garamond cho tiêu đề, chỉ dùng từ 20px trở lên.
  - Literata cho văn truyện và câu trích.
  - Be Vietnam Pro cho giao diện.
  
  Nên tự host bằng `@fontsource/cormorant-garamond`, `@fontsource/literata`, `@fontsource/be-vietnam-pro`, chỉ nạp subset `latin` + `vietnamese`. HTML tĩnh đang dùng Google Fonts.
- **Nền kẻ ô** 96px rất mờ, nhạt dần ra mép, chỉ trên khung tối (`.wt::before` trong `effects.css`).
- **Tủ truyện và màn chờ cảnh đầu theo kiểu "Mục lục":** chữ lớn, danh sách đánh số La Mã, không thẻ, không hộp.
- **Không** gradient chữ, emoji hay icon màu. Icon là nét mảnh (stroke 1.8–2).

## 3. Màn hình

Tên file trùng giữa `screenshots/`, `screens/` và `source-dc/`. Tiền tố `D-` là máy tính, `M-` là điện thoại. Cột "Route gợi ý" chỉ là gợi ý.

| File | Màn | Route gợi ý | API |
|---|---|---|---|
| D-/M-DangNhap | Đăng nhập / tạo tài khoản | `/dang-nhap` | chưa có (đăng nhập chưa làm; người chơi dev) |
| D-/M-ThuVien | Tủ truyện (Mục lục) | `/` | **chưa có endpoint danh sách truyện** (mục 8) |
| D-ThuVienRong, M-Rong | Tủ trống, chưa có khoá | `/` | `GET /player/key` |
| D-/M-KetNoiKhoa | Khoá & chi phí | `/khoa` | `GET/PUT/DELETE /player/key` |
| D-KhoiTao-Khuon, M-Khuon | Khởi tạo · khuôn truyện | `/moi` | `POST /setup` |
| D-KhoiTao-BoiCanh, M-KhoiTao | Bối cảnh (D: kèm hướng truyện) | `/moi/:session` | `POST/PUT /setup/{id}/settings` |
| M-HuongTruyen | Hướng truyện | `/moi/:session` | `POST/PUT /setup/{id}/plots` |
| D-KhoiTao-NhanVat, M-NhanVat | Nhân vật chính | `/moi/:session` | `POST/PUT /setup/{id}/characters`, `POST /setup/{id}/finalize` |
| D-/M-Cho | Chờ cảnh đầu (Mục lục) | `/truyen/:id` | SSE `POST /stories/{id}/chapters/next` |
| D-/M-Doc | Đọc · cảnh đang hiện | `/truyen/:id` | SSE như trên; `GET /stories/{id}/chapters/{n}` |
| D-/M-DuoiKip | Đọc nhanh hơn ngòi bút | `/truyen/:id` | SSE (chờ `scene_ready` kế) |
| D-/M-LuaChon | Lựa chọn cuối chương | `/truyen/:id` | `POST /stories/{id}/choice`, `POST /stories/{id}/action` |
| D-/M-SoTay | Sổ tay (ngăn kéo / sheet) | lớp trên `/truyen/:id` | `GET /stories/{id}/notebook` |
| D-/M-HoiNguoiKe | Hỏi người kể | lớp trên `/truyen/:id` | `POST /stories/{id}/narrator` |
| D-KetTruyen, M-KetTruyen | Truyện đã kết | `/truyen/:id` | `GET /stories/{id}` (`finished`) |
| D-Loi, M-Loi* | Lỗi | toàn cục | mã lỗi `ErrorCode` |
| Main | Hệ nhận diện | — | — |

Luồng mẫu: Đăng nhập → Tủ truyện → Khoá & chi phí → Khuôn → Bối cảnh → Hướng truyện → Nhân vật → Chờ cảnh đầu → Đọc → Lựa chọn → Sổ tay → Hỏi người kể.

## 4. Luật hiển thị (bắt buộc)

**Không lộ bí mật qua giao diện** (design §6.6, G1–G3):
- Tiến độ chỉ hiện **"Chương N"**, có thể kèm nhãn và khoảng chương cố định của mức độ dài. Lấy từ `config/story_lengths.yaml`: `levels.<khoá>.label` và `chapters.min–max`. Không tổng số chương, không phần trăm, không vạch chia, không mốc hồi.
- Không ô xám, không lựa chọn bị khoá, không "???", không bộ đếm bí mật, không thẻ che mờ.
- **Sổ tay:**
  - Chỉ hiện mục có dữ liệu; tab không có mục thì ẩn hẳn, không ghi "chưa có".
  - Mỗi thẻ gồm: tên người chơi biết (`text`), tên gọi khác (`aliases`), "biết từ chương N" (`since_chapter`), câu trích nguyên văn (`quote`).
  - Không vai trò, không thái độ, không "đang ở", không sơ đồ quan hệ, không ghim.
  - Lời nói dối gồm: người nghe (`told_to`), chương, nội dung. Không có trạng thái lộ hay chưa lộ.
- **Hỏi người kể:** không có câu hỏi gợi ý soạn sẵn. Hiện nguyên văn câu trả lời của máy chủ.
- **Lựa chọn:** không chọn sẵn lựa chọn nào. Ba lựa chọn cùng kiểu dáng, không màu hay icon nào làm lộ "lựa chọn đúng".
- **Lời thoại trong văn truyện** mở đầu bằng "- " (gạch + khoảng trắng), không dùng "—". Máy chủ đã chuẩn hoá (D-31); giao diện hiện đúng chữ nhận được, không tự đổi.

**Số liệu:** giao diện không tự đặt số.
- Ước tính chi phí lấy từ hệ thống; chưa có thì ghi **"chưa có ước tính"**.
- Trần chi phí (`limits.cost_usd.*`), giới hạn ký tự (`limits.input.*`), số câu hỏi người kể mỗi chương (`limits.rate_limit.narrator_questions_per_chapter`) lấy từ máy chủ. Mọi con số trong ảnh mẫu ("Đã dùng $0,09", "/ 200", "Còn 1 câu hỏi"…) là **số mẫu**.
- Không hiện thời gian chờ ước đoán. Chỉ được đếm số giây đã trôi.

## 5. Hành vi từng phần

**Khởi tạo (khuôn truyện):**
- Chọn một **thể loại chính**; tag phụ tuỳ chọn.
- Quy ước tên gồm `naming.names` (`han_viet` | `viet`) và `naming.places` (`hu_cau` | `that`). Gửi `naming: null` thì máy chủ tự đặt theo thể loại (D-32, `pipeline/setup.py` `DEFAULT_NAMING`). Giao diện hiện "theo thể loại"; khi người chơi đổi thì hiện "đã đổi · dùng lại mặc định".
- Độ dài lấy từ `config/story_lengths.yaml`, gửi khoá `length_level`.
- Góc nhìn "Nhiều nhân vật" ghi "sắp có", không bấm được.

**Mỗi bước 3 lựa chọn (bối cảnh, hướng, nhân vật):**
- `POST` để tạo, kèm trạng thái chờ: khung xương nhạt, không vòng quay.
- `PUT` với `index` để chọn.
- Sửa nhân vật theo giới hạn `limits.input.character_name_max_chars`, `personality_max_chars` và `backstory_max_chars`, có đếm ký tự.

**Đọc (SSE):** sự kiện `stage` / `scene_ready` / `scene_blocked` / `chapter_committed` / `choices_ready` / `story_finished` / `error` (`pipeline/events.py`).
- `stage`: màn Chờ dùng `label` để hiện bước đang làm. Màn mẫu ghi 4 bước; dùng nhãn máy chủ gửi.
- `scene_ready`: máy chủ gửi **trọn chữ của cảnh**. Hiệu ứng "chữ chạy dần" là hoạt cảnh phía client (cụm chữ mờ → nét). Người đọc chạm thì hiện hết ngay. Khi bật giảm chuyển động thì hiện đủ ngay.
- Trong lúc đọc cảnh trước, hiện dòng "Cảnh N đang được viết" ở cuối trang. Nếu người đọc cuộn tới cuối trước khi có `scene_ready` kế tiếp thì hiện khối "Bạn đọc nhanh hơn ngòi bút" (D-/M-DuoiKip). Không hiện số giây còn lại; cảnh tự nối tiếp khi tới.
- `scene_blocked` và `error`: hiện theo mục 6.
- `story_finished`: chuyển sang màn Truyện đã kết.

**Lựa chọn cuối chương:**
- Ba lựa chọn từ `choices_ready`, mỗi cái mang `kind_label` và `tone_label`. **Xem mục 8, điểm 1** về sắc thái.
- Ô tự viết nhiều dòng, đếm ký tự theo `limits.input.custom_action_max_chars`.
- Nút gửi chỉ bật khi đã chọn một lựa chọn hoặc ô tự viết có chữ.
- Lỗi của ô tự viết hiện ngay dưới ô, không mở hộp thoại.

**Hỏi người kể:**
- Hiện số câu còn lại trong chương.
- Khi hết lượt (`NARRATOR_LIMIT_REACHED`) thì thay ô nhập bằng khối báo: lượt mới mở ở chương sau.
- Câu chưa hé lộ được máy chủ trả đúng "Bạn chưa biết điều này."

**Khoá & chi phí:**
- Chỉ hiện 4 ký tự cuối (`last4`).
- Đường chính là dán khoá. Nút "Kết nối với OpenRouter" (OAuth) ghi "sắp có".
- Có nút Đổi khoá và Ngắt khoá; ngắt khoá cần xác nhận.
- Bút "Tiêu chuẩn" chỉ đọc: không chọn mức, không điểm, không bảng giá.

**Tủ truyện:** truyện đang đọc dở hiện câu trích cuối và nút "Đọc tiếp". Dòng cuối là "Mở một trang chưa viết".

## 6. Lỗi

- **Chữ:** hiện **nguyên văn `message` của máy chủ** (`errors.py` `MESSAGES`, G12). Chữ trong ảnh mẫu chỉ để minh hoạ bố cục.
- **Bố cục và nút:** giao diện chỉ chọn theo `code`. Không hiện mã lỗi cho người chơi.
- Nếu payload có `fields` thì đánh dấu đúng ô cần sửa.

| Nhóm `code` | Hiện ở đâu | Nút |
|---|---|---|
| `PLAYER_KEY_MISSING`, `PLAYER_KEY_UNREADABLE`, `PLAYER_KEY_INVALID`, `LLM_AUTH_FAILED` | khối lỗi / sheet (điện thoại) | Dán khoá · Về tủ truyện |
| `LLM_INSUFFICIENT_CREDITS` | khối lỗi | Thử lại · Mở OpenRouter |
| `COST_LIMIT_SCENE`, `COST_LIMIT_CHAPTER`, `COST_LIMIT_STORY` | khối lỗi | Thử lại · Bắt đầu truyện mới (không có "Nâng trần") |
| `SCENE_LEAK_BLOCKED`, `CHOICES_LEAK_BLOCKED` | cuối trang đọc | Thử lại (cảnh chỉ viết lại được 1 lần: `limits.retries.rewrite_per_scene`) |
| `RETRY_LIMIT_REACHED` | khối lỗi | Quay về lựa chọn · Về tủ truyện |
| `LLM_RATE_LIMITED`, `WRITORY_RATE_LIMITED` | khối lỗi nhẹ | Thử lại (không đếm ngược, không "báo tôi lúc…") |
| `ACTION_EMPTY`, `ACTION_TOO_LONG`, `ACTION_OUT_OF_STORY`, `ACTION_UNCLEAR`, `ACTION_FORBIDDEN`, `LLM_CONTENT_BLOCKED` | ngay dưới ô tự viết | — |
| `NARRATOR_QUESTION_EMPTY`, `NARRATOR_QUESTION_TOO_LONG` | dưới ô hỏi | — |
| `NARRATOR_LIMIT_REACHED` | thay ô hỏi | Quay lại trang đọc |
| `STORY_BUSY`, `CHAPTER_OUT_OF_ORDER` | khối lỗi (mở ở hai nơi) | Tải lại |
| `STORY_NOT_FOUND`, `CHAPTER_NOT_FOUND`, `SETUP_NOT_FOUND` | trang lỗi | Về tủ truyện |
| `CHAPTER_PENDING`, `CHAPTER_SAVE_FAILED`, `CHAPTER_PACKAGE_INVALID` | khối lỗi | Thử lại |
| Mất mạng (phía client) | thanh dưới trang đọc | Thử lại ngay; giữ phần chữ đã hiện |
| `INTERNAL_ERROR`, `LLM_*` còn lại, `CONFIG_*`, `REQUEST_INVALID` | khối lỗi | Thử lại · Về tủ truyện |

## 7. Tương tác, chuyển động, truy cập

- **Con trỏ giọt mực** (`assets/cursor-ink*.svg`) và vầng mực đi theo chuột chỉ dùng khi `(hover: hover) and (pointer: fine)`. Không dùng trên màn cảm ứng.
- **Khi `prefers-reduced-motion: reduce`:**
  - tắt vầng mực theo chuột và chữ chạy (chữ hiện đủ ngay, không con trỏ nhấp nháy);
  - tắt dịch chuyển khi rê chuột;
  - mọi hoạt cảnh rút về tức thì.
  
  Đã có trong `effects.css`; React cần tôn trọng thêm ở chỗ dùng JS.
- **Vầng mực theo chuột:** một phần tử `.wt-halo` trong gốc màn. JS cập nhật `transform` bằng `requestAnimationFrame`, đặt `data-hover="1"` khi trỏ vào `a, button, label, input, textarea`. Xem `onMove` trong mọi file `source-dc/D-*.dc.html`.
- **Truy cập:**
  - Phần tử thật (`button`, `a`, `input` + `label`), `role="radiogroup"/"radio"`, `aria-checked`, `aria-current`, `role="status"` / `aria-live` cho chờ và người kể.
  - Vùng chạm từ 44px.
  - Tương phản chữ từ 4.5:1: `ink-400` là mức mờ nhất được dùng cho chữ nhỏ.

## 8. Chưa khớp giữa thiết kế và code (cần Chủ dự án quyết trước khi dựng)

1. **Sắc thái lời thoại.**
   - Máy chủ gắn **một** `tone` cố định cho mỗi lựa chọn lời thoại (`PlayerChoice.tone`, `pipeline/choices.py`).
   - Ảnh mẫu lại có bộ chọn "Nói thật / Nói dối / Im lặng" bên trong lựa chọn lời thoại.
   - Đề xuất: theo code, hiện nhãn "Lời thoại · nói dối" và bỏ bộ chọn.
2. **Câu lỗi trần chi phí:** `COST_LIMIT_SCENE` / `COST_LIMIT_CHAPTER` trong `errors.py` còn ghi "chọn mức model rẻ hơn", trong khi bản 1 chỉ có một bút.
3. **Tag thời đại:** API có `tags.era` (tuỳ chọn) và design §4.1 còn nhắc "thời đại". Màn khuôn truyện mới đã gộp vào thể loại chính, không còn ô thời đại.
4. **Sổ tay:** API có thêm loại `Faction`, `Event` và trường `about`. Đề xuất: `Faction` → tab "Phe phái", `Fact` + `Event` → tab "Sự thật"; chỉ hiện tab khi có mục; chưa dùng `about`.
5. **Người kể:** `NarratorAnswerOut` chỉ có `answer`. Ảnh mẫu có dòng nguồn ("Từ chương 2") và số câu còn lại; cả hai cần thêm trường, nếu không thì bỏ khỏi giao diện.
6. **Endpoint còn thiếu cho giao diện:**
   - danh sách truyện của người chơi (tủ truyện);
   - chi phí đã dùng theo truyện và theo tháng;
   - ước tính chương tới;
   - các giới hạn công khai (ký tự, số câu hỏi, trần) để giao diện không chép số.
7. **Giới hạn quá khứ nhân vật:** ảnh mẫu ghi "/ 400"; số đúng lấy từ `limits.input.backstory_max_chars`.
8. **Đăng nhập** chưa có ở máy chủ (người chơi dev, D-44); màn đăng nhập mới là thiết kế.

## 9. Nội dung thư mục

```
design-handoff/
  README.md            file này
  screenshots/*.png    ảnh từng màn (trạng thái đầu)
  screens/*.html       HTML tĩnh từng màn + index.html; manifest.json (kích thước khung)
  source-dc/*.dc.html  file gốc trên canvas, có state và logic
  tokens/              tokens.css, tailwind-theme.js
  assets/              effects.css, cursor-ink.svg, cursor-ink-pointer.svg, grain.svg, mountains.svg
```
Không có trang "Phương án" (3 kiểu thư viện / màn chờ). Bản đã chọn là kiểu A "Mục lục", đã nằm trong D-/M-ThuVien và D-/M-Cho.
