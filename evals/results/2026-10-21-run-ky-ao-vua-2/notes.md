# Nhận xét đọc tay: ky-ao-vua-2

Người đọc: Claude, 22/10/2026.
- Lệnh như lần `ky-ao-vua-1`: cùng đề `ky-ao-vua` (v1, cùng sha256), `--chapters 10`, seed của đề 20261021. Chỉ khác trần: `--budget 0.20`.
- Code ở commit `0dd03d3`: D-82, đề `extract-3`, `outline-5`, `writer-5`. Hash config trùng lần 1.
- Chi phí 0,0916 USD (lần 1: 0,0972 USD).

**Không so thẳng được với lần 1.** Model khởi tạo dựng thế giới khác, cùng seed:
- Kế hoạch có 4 mạch phải gỡ, hạn gỡ rộng (2–6, 3–10, 4–12, 5–12). Lần 1 có 5 mạch, hạn hẹp hơn.
- Số đếm dưới đây chỉ là chiều hướng.

## Số đo (từ `report.json`, `truth_dump.json`)
| | ky-ao-vua-1 | ky-ao-vua-2 |
|---|---|---|
| Chương ghi được | 10/10 | 10/10 |
| Mạch phải gỡ gỡ đúng khoảng (`plan_vs_result`) | 1/5 | 3/4 (1 sớm) |
| `overdue_thread` tìm thấy / còn khi hiện | 17 / 8 | 0 / 0 |
| `RESOLVED_IN` ghi được | 2, không câu trích | 5, đều có câu trích nguyên văn |
| Viết lại | 8 | 4 |
| Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử | (chưa có) | 0 |

- Lần này không dàn ý nào bị thử lại vì bỏ mạch (20 lời gọi dàn ý cho 20 cảnh).
- `resolves` chỉ khác rỗng ở cảnh 2 chương 4 (`tim_nguoi_giu_an`) và cảnh 2 chương 5 (`thoat_khoi_dai_nghi`, `quyen_quan_giu_than_khi`). Trong ba mạch đó, bộ trích ghi gỡ đúng chương dàn ý định.

## Đọc từng `RESOLVED_IN` (câu trích kiểm với `chapters/`)
1. **ch01 `loi_khai_cua_min_vi`** (hạn 5–12). Câu trích ch01:43: "Tôi sẽ kể đúng những gì mình biết. Nhưng tôi không xác nhận lời buộc tội thay cho bất kỳ môn phái nào."
   - Mạch hỏi lời khai và lập trường của Lục Minh Vi đặt nền cho luật mới đến đâu. Chương 1 mới có lập trường, chưa có luật nào.
   - **Gỡ giả, sớm.** Ở chương 1 mạch chưa tới khoảng gỡ, nên không có trong mục "Mạch phải gỡ đang mở". Bộ trích lấy nó từ danh mục.
2. **ch04 `tim_nguoi_giu_an`** (hạn 2–6). Câu trích ch04:87: "Ở cuối gian, có người ngồi tựa lưng vào vách, đầu cúi thấp."
   - Gỡ thật: ch04:89–99 tìm thấy Thiệu Kiếm Hoài còn sống, và ông nói vì sao giấu ấn lệnh.
   - Câu trích yếu: chỉ là câu trước câu nhận ra ông, không phải câu trả lời.
3. **ch05 `thoat_khoi_dai_nghi`** (hạn 3–10). Câu trích ch05:177: "Khi tất cả đã ra ngoài, tôi quay lại đặt tờ biên bản lên bệ đá."
   - Gỡ thật ở chương 5: cửa mở (ch05:171), mọi người ra, không ai rút kiếm.
   - Nhưng chương 8 và 10 lại tả cửa Đại Nghị Sảnh khoá (ch08:61, ch10:45, ch10:121), mọi người vẫn trong sảnh. Đây là lỗi liền mạch của model viết, người canh không bắt.
4. **ch05 `quyen_quan_giu_than_khi`** (hạn 4–12). Câu trích ch05:153 kéo qua nhiều đoạn, vẫn nguyên văn: thoả thuận tạm, giám sát chung, "Việc quản giữ lâu dài để hội nghị bàn sau khi cửa mở".
   - Mạch đòi "một phương thức quản giữ được chấp nhận". Các bên chấp nhận một cách tạm, còn cách lâu dài thì hoãn.
   - **Gỡ một phần, sớm.** Model hiểu rộng câu "chi tiết phụ còn bỏ ngỏ không giữ mạch mở", như ở lần phát lại (`2026-10-21-extract-replay-ky-ao-vua-1/notes.md`).
5. **ch07 `hanh_lang_so_tan`** (mạch không phải gỡ, dự kiến 4–8). Câu trích ch07: "Người dân thoát được khỏi vùng tranh chấp. Đổi lại, các môn phái mất lòng tin vào ta." Đúng cái giá và hệ quả mạch hỏi.

Đọc tay, mạch phải gỡ được gỡ thật và đúng khoảng là 2/4 (`tim_nguoi_giu_an`, `thoat_khoi_dai_nghi`). Một mạch gỡ một phần, một mạch gỡ giả. Số 3/4 của `plan_vs_result` vì vậy lạc quan.

## Lặp nhịp
- **Vẫn lặp.** Bạch Kinh Luân thú nhận sắp đặt việc lấy Mảnh Thiên Khuyết ở ch07:63 (bí mật lộ đúng khoảng 7–9). Rồi nói lại hay được nhắc lại ở ch08:71/79, ch09:39, ch10:87. Cùng kiểu lời thú nhận của Trần Mặc ở lần 1.
  - Một phần do lựa chọn tự chọn: lựa chọn cuối chương 8 hỏi thẳng Bạch xác nhận lại.
  - Câu "không diễn lại nhịp đã xảy ra" của D-82 chỉ nằm trong mục mạch phải gỡ. Bí mật đã lộ thì không có câu đó.
- Chương 6–10 giậm chân một chỗ: cùng phiên nghị sự, cùng biên bản có "ô ký để trống" (ch09:105, ch10:37, ch10:79, ch10:121), cửa vẫn khoá.
  - Ba trong bốn mạch phải gỡ đã ghi gỡ ở chương 5. Từ chương 6 không còn mạch nào đến hạn (hạn cuối 12). Đề chỉ còn mốc thúc truyện đi.

## Phát hiện phụ: lưới úp mở của người kể (D-78)
- Câu văn ch06 "Còn quyền quản giữ lâu dài vẫn chưa được nhắc đến trên giấy." bị `meta_hedge` bắt (cụm `chua_duoc_ke`). Người kể kể lại câu này sẽ bị đổi thành "Bạn chưa biết điều này.". Đây là giới hạn đã ghi ở D-78.
- `tests/unit/test_narrator.py::test_no_sentence_of_any_story_text_in_the_repo_is_caught` đọc mọi chương trong `evals/results/`, nên đỏ khi thêm truyện này. Câu được ghi vào `KNOWN_STORY_FALSE_POSITIVES`, và test kiểm nó vẫn bị bắt. Chưa sửa cụm (ngoài phạm vi D-82): cần chủ dự án quyết định.

## Kết luận
- Bộ trích ghi `RESOLVED_IN` nhiều hơn, mọi cạnh có câu trích thật, và `overdue_thread` không còn. Nhưng lần này cái hỏng chuyển sang chiều ngược lại: **gỡ sớm và gỡ một phần**, cộng với một mạch ghi gỡ khi chưa tới khoảng.
- Việc nên làm tiếp (chưa làm, ngoài phạm vi D-82):
  - Code bỏ `RESOLVED_IN` của mạch phải gỡ khi mạch chưa tới khoảng gỡ, hoặc chỉ cho khi trang thật sự kết.
  - Định nghĩa gỡ chặt hơn cho mạch nhiều vế, hoặc kế hoạch viết mỗi mạch một câu hỏi.
  - Đưa câu "không diễn lại nhịp" sang bí mật đã lộ.
  - Kiểm liền mạch trạng thái nơi chốn (cửa đã mở) bằng người canh.
- **Chưa kiểm:**
  - Chạy lại cùng thế giới với lần 1 (setup khác nhau nên không cô lập được tác dụng của D-82).
  - Nhiều lần chạy.
  - Chương 11–12 (kết truyện).
