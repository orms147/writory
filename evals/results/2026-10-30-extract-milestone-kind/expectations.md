# Khai trước: phát lại bộ trích `extract-8` và `extract-9` trên chương đã lưu

Khai TRƯỚC khi gọi model thật (commit này đi trước mọi lời gọi). Mục đích: đo thay đổi D-127 (dòng mốc có loại, cao trào đòi hậu quả đã diễn ra) mà không viết lại cả truyện. Nguồn chương và đồ thị: `evals/results/2026-10-29-run-long-after-tu-tien/` và `…-after-ky-ao-2/` (lượt chạy sau D-116, bộ trích `extract-8`).

## Cách phát lại
- Mỗi ca = một chương đã ghi. Đề dựng lại từ `truth_dump.json`: danh mục thực thể và cạnh đang hiệu lực đến hết chương trước, mạch phải gỡ, mốc chưa xảy ra và mốc đã xong tính bằng `chapter_goals` (cờ `milestone_lookahead` của config), luật Fact mới của config. Chữ chương là toàn bộ chương (`chapters/chNN.md`, bỏ tiêu đề và phần lựa chọn), **một lời gọi cho cả chương**, khác sản phẩm (mỗi cảnh một lời gọi, cảnh sau thấy mốc cảnh trước đã đánh dấu). Không có nút `Lie` của lựa chọn dẫn tới chương (tác động lựa chọn) trong danh mục.
- Hai bản đề: `extract-8` (đề ở main `935fff6`, lưu ở `extract8_system_prompt.txt`, dòng mốc không có loại) và `extract-9` (đề trên nhánh này). Cùng model, cùng mức suy luận, cùng mọi thứ khác. Chỉ so mục `milestones` của đầu ra (id + câu trích) sau `accept_milestones` (cùng luật nhận như sản phẩm). Các phần khác của đầu ra không chấm.
- Dấu "sản xuất" = dấu đã có trong lượt gốc (`milestones` của nút Chapter trong gói chương). Trần chi phí cứng `--budget 0.10`.

## Các ca (thứ tự ưu tiên; hết ngân sách thì các ca sau không chạy và ghi là không chạy)
1. **Mục tiêu:** tu-tien ch19; ky-ao ch24.
2. **Ca đối chứng có dấu đúng:** ky-ao ch16 (m6 cao trào, đúng hạn, nhận trong lượt gốc); tu-tien ch11 (m4); ky-ao ch10 (m5); tu-tien ch5 (m3).
3. **Chương ngữ cảnh:** tu-tien ch18; ky-ao ch22, ch23; tu-tien ch17. (Tu-tien ch20, ch21 bỏ: m6 đã đánh dấu ở ch19 nên đề không còn mốc nào để đánh dấu, phát lại không cho thông tin; ch22 không có gói chương vì lượt gốc dừng trước khi ghi.)
4. **Lặp lại mục tiêu** (nếu còn ngân sách): tu-tien ch19 và ky-ao ch24, mỗi bản đề thêm một lần.

## Kỳ vọng
- **K1:** tu-tien ch19: `extract-8` nhận m6 (như lượt gốc); `extract-9` không nhận m6.
- **K2:** ky-ao ch24: `extract-9` nhận m7 (câu trích "Tôi sẽ dùng nó để mở đường…" hoặc tương đương); `extract-8` có thể không nhận (như lượt gốc).
- **K3:** ca đối chứng (ky-ao ch16 m6, tu-tien ch11 m4, ky-ao ch10 m5, tu-tien ch5 m3): `extract-9` nhận lại đúng các mốc mà lượt gốc nhận, **không thêm** dấu cho mốc nào lượt gốc không nhận ở chương đó.
- **K4:** chương ngữ cảnh: `extract-9` không nhận nhiều hơn `extract-8` ở bất kỳ chương nào (đề mới chỉ siết cao trào).

## Luật quyết (khai trước)
- Một lời gọi mỗi bản đề mỗi ca là NHIỄU: model không tất định, K1/K2 đúng một lần chưa chứng minh gì. Đọc kết quả là "tín hiệu", không phải "đã đo".
- **Tín hiệu tốt** nếu K1 và K2 cùng đúng ở lần chạy đầu, và không ca đối chứng nào của K3 mất một dấu đúng hay thêm một dấu mới, và (nếu chạy tầng 4) hướng K1/K2 giữ ở lần lặp.
- **Tín hiệu xấu** nếu `extract-9` làm mất dấu đúng của ky-ao ch16 (cao trào đúng hạn) hoặc thêm bất kỳ dấu mới nào ở ca đối chứng. Khi đó ghi lại, không chỉnh đề để cho khớp.
- Dấu mới hay dấu mất đều được đọc tay (câu trích có thật nói điều mốc mô tả không) và ghi vào notes; không dựa vào đếm.
- Kết luận không sửa đề lần hai trong PR này.
