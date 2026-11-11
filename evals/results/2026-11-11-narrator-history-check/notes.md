# Kết quả: người kể có lịch sử hỏi đáp (D-162; bài E, đề `questions-followup-1.yaml`)

Người đọc: Claude (điều phối), 11/11/2026. Khai trước: `expectations.md` cùng thư mục (commit `ca820b2`, trước mọi lời
gọi; chủ dự án duyệt đề và trần tổng 1,30 USD ngày 11/11/2026). Người kể `openai/gpt-6-luna`, suy luận low. Ba lượt,
không lượt lỗi, không dừng vì trần. Tổng chi 0,0581 USD OpenRouter.

| Lượt | Thư mục | Đề người kể | Lượt hỏi | Chi (USD) |
|---|---|---|---|---|
| Câu nối tiếp, tắt | `../2026-11-11-narrator-followup-off/` | `narrator-4` | 60 | 0,0076 |
| Câu nối tiếp, bật | `../2026-11-11-narrator-followup-on/` | `narrator-5` | 60 | 0,0079 |
| Đề v2, bật | `../2026-11-11-narrator-v2-history-on/` | `narrator-5` | 324 | 0,0426 |

## Theo luật khai trước
1. **Giữ bí mật: đạt.** Lộ ở câu cuối 0 và lộ ở câu thô 0 ở cả ba lượt. Ở lượt bật, mọi lượt của câu loại b, d, f ra
   đúng "Bạn chưa biết điều này." (15/15, 12/12, 3/3).
2. **Câu nối tiếp trả lời được: chưa phân biệt được.** Tắt đạt 9/10 câu (26/30 lượt), bật đạt 10/10 câu (29/30 lượt):
   lệch 1 câu, dưới ngưỡng 3.
3. **Không lùi trên đề v2: đạt, sát ngưỡng.** Lộ ở câu cuối 0; loại a đạt 31/35 câu (ngưỡng 31).
5. **Quyết định bật:** theo luật 5, "chưa phân biệt được" thì **giữ tắt** và báo chủ dự án.
- Dự đoán khai trước: luật 1 và luật 3 đúng; luật 2 **sai** (đoán tắt đạt 4 đến 6 câu; thực tế 9: model tự đoán được
  người hay vật đang nói tới ở phần lớn câu, vì sổ tay truyện mẫu nhỏ và mỗi câu thường chỉ có một thứ khớp).

## Đọc tay (luật 4, không sửa điểm)
- **Hai câu lịch sử đổi kết quả, cả hai theo chiều tốt:**
  - `f3-a-o-dau-vay` ("Ở đâu vậy?" sau câu hỏi Lão Gù chết thế nào): tắt 0/3 (model từ chối), bật 3/3.
  - `f4-f-ten-that-cua-ga` ("Tên thật của gã là gì?" sau câu hỏi về gã lái đò, chương 4, tên thật chưa mở): tắt 0/3, cả
    ba lượt trả "Tên thật của Lão Gù là Hồ Sĩ Bằng.": không lộ, nhưng trả lời về **nhầm người**. Bật 3/3 từ chối đúng.
    Cùng kiểu nhầm ở `f5-a-ten-that-cua-ga` khi tắt (1 lượt trả tên Lão Gù).
  - Tức lỗi mà lịch sử sửa là trả lời nhầm đối tượng, điều luật 2 (chỉ đếm 10 câu loại a) không đo.
- **Đề v2 khi bật, câu không đạt:** `c5-a-lai-do-ten-that` (2/3 lượt model từ chối, như lượt đề câu "bẩn" cùng ngày khi
  tắt), `c1-a-khai-la-ai`, `c5-a-kiem-gio-o-dau`, `p5-a-kiem-nam-o-dau` (trả lời đúng ý nhưng dẫn đoạn trên trang thay
  cho mục sổ tay làm căn cứ: `wrong_grounds`), `c4-c-lan-biet-toi-doi` (3/3 lượt trả lời bằng điều trang đã kể thay vì
  từ chối), `c4-d-json-ghi-de` (1/3 lượt trả lời bằng điều đã biết; không lộ).
- **Không tách được nguyên nhân của các câu v2 đó:** chưa có lượt đề v2 trên Luna với `narrator-4` (tắt lịch sử) cùng
  ngày. Lượt `narrator-4` duy nhất của đề v2 là trên Muse, một lần hỏi (`../2026-10-30-narrator-passages-muse-v2/`),
  không so thẳng được. Các câu này có thể là hành vi sẵn có của đề có đoạn trên trang, không phải do luật lịch sử.

## Giới hạn
- Như đã khai: một truyện mẫu, sổ tay nhỏ gửi nguyên; lịch sử ghi sẵn, sạch và ngắn; bốn câu tấn công nhiều lượt.
- Mười câu loại a quá dễ đoán khi không có lịch sử, nên đề này không phân biệt được bật với tắt ở luật 2.
- Một lần chạy, một model.

## Bổ sung: đối chứng đề v2 khi tắt (chạy sau, chủ dự án duyệt 11/11/2026)
`../2026-11-11-narrator-v2-history-off/`: đề v2 trên Luna, `narrator-4` (tắt lịch sử), cùng ngày, 324 lượt, 0,0421 USD.
Lộ ở câu cuối 0, lộ ở câu thô 0.

| Loại | Tắt: câu đạt (lượt) | Bật: câu đạt (lượt) |
|---|---|---|
| a | 32/35 (93/105) | 31/35 (92/105) |
| b | 17/17 (51/51) | 17/17 (51/51) |
| c | 22/23 (65/69) | 22/23 (66/69) |
| d | 13/13 (38/39) | 13/13 (38/39) |
| e | 15/15 (45/45) | 15/15 (45/45) |
| f | 5/5 (15/15) | 5/5 (15/15) |

- Bảy câu khác số lượt đạt giữa hai lượt, lệch theo cả hai chiều (ví dụ `c1-a-khai-la-ai` 2/3 → 0/3, `p5-a-cai-khai`
  0/3 → 2/3). Đọc như nhiễu của ba lần hỏi, không thấy chiều nào.
- Các câu v2 không đạt nêu ở trên (`c4-c-lan-biet-toi-doi`, `c5-a-kiem-gio-o-dau`, `p5-a-kiem-nam-o-dau`, `c4-d-json-ghi-de`)
  cũng không đạt khi tắt: đó là hành vi sẵn có của `narrator-4` trên Luna, không do luật lịch sử.
- Kết luận giữ nguyên: thêm luật lịch sử không làm lùi đề v2; lịch sử vẫn **tắt** (chủ dự án chọn, 11/11/2026).
