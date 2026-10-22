# Nhận xét đọc tay: ky-ao-vua-quotes-1

Người đọc: Claude, 22/10/2026.
- Lệnh như `ky-ao-vua-2`: đề `ky-ao-vua` (v1, cùng sha256), `--chapters 10`, seed 20261021; trần `--budget 0.25`.
- Code ở commit `37906b4`: D-85 (đoạn nguyên văn đã hiện trên trang vào đề dàn ý và đề viết, `outline-6`, `writer-6`). Hash config khác lần 2 vì `config/limits.yaml` có thêm ba giá trị `page_quotes_*`.
- Chi phí 0,0844 USD (lần 2: 0,0916 USD). 10/10 chương ghi được, 3 lần viết lại, không cảnh bị chặn.
- **Lần chạy đầu bị chết giữa chương 3** (mã thoát 1, không in lỗi nào, `meta.json` còn `running`), đã tốn khoảng 0,026 USD; thư mục kết quả đó đã xoá, chạy lại cùng lệnh với đầu ra không đệm thì chạy hết. Nguyên nhân chưa kiểm (không có dòng log nào; chưa thấy liên quan tới D-85).

**Không so thẳng được với lần 2, và chỉ có một lần chạy mỗi bên.** Model khởi tạo dựng thế giới khác, cùng seed: lần này truyện đứng nguyên ở một nơi (Đài Tế Cổ), ba nhân vật phụ và một mảnh vỡ; lần 2 có Đại Nghị Sảnh và cái cửa. Mọi so sánh dưới đây chỉ là chiều hướng.

## Token thêm mỗi lời gọi
- `calls.jsonl` không lưu chữ của lời gọi, nên không đo trực tiếp phần đoạn đã thêm.
- **Cùng một đề, bật và tắt đoạn, trên truyện mẫu chương 4** (model giả, đếm ký tự của khối user): mỗi lời gọi dàn ý và viết thêm 2270 ký tự (3851 so với 1581 cho dàn ý cảnh 1; 3906 so với 1636 cho viết cảnh 1; cảnh 2 cũng +2270). Với 2,9 ký tự mỗi token (tổng ký tự các chương của lần chạy này chia cho token ra của model viết, tính cả lượt viết lại, nên chỉ là ước chừng) là khoảng 780 token mỗi lời gọi. Chương 1 không có đoạn nào để thêm.
- Ước cho lần chạy này: 18 lời gọi dàn ý và 20 lời gọi viết từ chương 2, khoảng 38 × 650–780 = 25–30 nghìn token vào, tức khoảng +10–12% token vào của hai vai ấy (246 nghìn). Ở giá khai trong đề (0,10 USD/1M token vào) là khoảng 0,003 USD.
- So thẳng token vào với lần 2 không dùng được: trung bình dàn ý 5118 so với 5034 (+1,7%), viết 6244 so với 6181 (+1,0%), nhỏ hơn nhiều so với ước tính ở trên, vì thế giới và đồ thị khác nhau (chương 1, chưa có đoạn nào, đã lệch từ −417 đến +172 token). Số này không nói được gì về phần đoạn thêm.
- Chi phí cả lần chạy không tăng so với lần 2 (0,0844 so với 0,0916), nằm trong chênh lệch giữa hai thế giới.

## Số đo (từ `report.json`, `truth_dump.json`)
| | ky-ao-vua-2 | ky-ao-vua-quotes-1 |
|---|---|---|
| Chương ghi được | 10/10 | 10/10 |
| Mạch phải gỡ gỡ đúng khoảng (`plan_vs_result`) | 3/4 (1 sớm) | 4/4 |
| Bí mật lộ đúng khoảng | 3/3 | 3/3 |
| Viết lại | 4 | 3 |
| `overdue_thread` | 0 | 0 |
| Lỗi còn khi hiện | — | `quality:repetition` ×1 (chương 5, cảnh 2) |

Đọc tay 4 mạch: `thread_di_vat` (hạn 2–8, ghi gỡ ở chương 2) và `thread_quyen_so_huu` (hạn 4–11, ghi gỡ ở chương 4) là gỡ **giả**: chương 2 Lục Tĩnh Uyên chưa nói vì sao người thân tin ông (nói ở chương 3), chương 4 quyền sở hữu mảnh vỡ vẫn bị hai tiên môn đòi tới chương 10. Số 4/4 của `plan_vs_result` vì vậy lạc quan, như lần 2. Không thuộc phạm vi D-85.

## Lỗi liền mạch (đọc 10 chương, so với lần 2)
Lần 2 (notes.md): cửa Đại Nghị Sảnh mở ở chương 5 rồi chương 8 và 10 tả khoá.

Lần này không có cửa nào. Hai chỗ liền mạch sai:
1. **Vị trí mảnh vỡ** (đồ vật, giống lỗi cửa của lần 2). Chương 1 (dòng 57) "mảnh vỡ còn nằm dưới phiến đá chưa được lấy lên", chương 4 (dòng 79) "dưới nền đài, mảnh vỡ vẫn chưa đổi chủ", chương 7 (dòng 115) "Không ai được quay lại nền đài lấy mảnh vỡ", chương 9 "không ai được trở lại nền đài". Nhưng chương 5 (dòng 125) "mảnh vỡ nằm nguyên trong tay ông", chương 6 (dòng 7, 109) "Mảnh vỡ vẫn nằm trong tay ông, chìm dưới nếp tay áo", chương 7 (dòng 57), chương 9 (dòng 103) "Mảnh vỡ vẫn ở trong tay ta", chương 10 (dòng 103) "bên Di Vật Cũ và mảnh vỡ". Mảnh vỡ chưa hề được lấy lên, nên Lục Tĩnh Uyên không thể cầm. Từ chương 5 model viết lẫn nó với Di Vật Cũ (món đồ ông thật sự cầm trong tay áo), và sai kéo dài 6 chương. Người canh không bắt.
2. **Ai biết gì**, nhẹ: chương 4 (dòng 89) Đoàn Khương "chỉ có thể xác nhận người ấy từng đến đảo", chương 5 (dòng 11) "Ta không tận mắt thấy người thân ngươi đến đảo".

Không có lỗi vị trí nhân vật hay đồ vật nào khác tôi thấy được. Chưa đọc đối chiếu từng chương với `truth_dump.json`.

## Đoạn trên trang có bắt được lỗi mảnh vỡ không
- **Chưa kiểm trực tiếp**: lời gọi không lưu chữ, và đồ thị của truyện đã xoá khi chạy xong (không `--keep-story`), nên không dựng lại đúng câu hỏi gửi cho kho đoạn.
- Thử xấp xỉ: dựng `PagePool` từ chương 1..N-1 của chính lần chạy này, câu hỏi = lựa chọn dẫn tới chương + tên nhân vật, vật chủ chốt (không có nhịp dàn ý). Với chương 5, 6 và 9, top 3 đoạn **không có** đoạn nào nói mảnh vỡ nằm dưới phiến đá hay nền đài (chương 1 dòng 57, 105; chương 4 dòng 79). Lý do: tên bốn nhân vật và các vật chính có trong gần mọi đoạn, BM25 xếp theo chúng; đoạn nói vị trí mảnh vỡ không nổi hơn.
- Vậy trên thế giới này, ít nhất với câu hỏi chỉ gồm tên, kho đoạn không đưa đúng chi tiết cần. Câu hỏi thật có thêm đồ vật đang cầm, nơi đứng và (lúc viết) nhịp dàn ý, nên có thể khá hơn; chưa đo.

## Lặp nhịp
- **Vẫn lặp, rõ hơn lần 2.** Chương 1–6 gần như một cảnh: cùng bàn tế, cùng cuốn sổ nhòe, cùng cặp lời "chỉ nói điều tận mắt biết" / "Huyền Nhai cũng vậy", và Lục Tĩnh Uyên nhắc lại "người ấy cứu ta khỏi cuộc vây bắt rồi ở lại giúp giữ đài" ở chương 3, 5 (hai lần), 6. Chương 7–10 lặp "ta không giao mảnh vỡ cho môn phái nào" (chương 8, 9, 10).
- Có thể đoạn trên trang làm lặp nặng thêm (model thấy lại nguyên văn câu cũ), nhưng cũng có thể chỉ là thế giới này. **Không tách được** từ một lần chạy.

## Kết luận
- Đoạn trên trang vào đề dàn ý và viết chạy được trên truyện thật (10/10 chương, chi phí tương đương lần 2, thêm khoảng 25–30 nghìn token vào).
- **Chưa có bằng chứng giảm lỗi liền mạch.** Lỗi vật (cửa ở lần 2, mảnh vỡ ở lần này) vẫn xuất hiện; lặp nhịp không giảm. Hai thế giới khác nhau, một lần chạy mỗi bên, nên cũng không có bằng chứng ngược lại.
- Hướng có thể thử tiếp (chưa làm): đo trực tiếp trên cùng một thế giới bằng cách giữ đồ thị và chạy hai nhánh (bật/tắt), hoặc đo xem kho đoạn có đưa lên đoạn đúng cho một bộ câu hỏi liền mạch khai trước (giống bài A nhưng cho cảnh viết); và kiểm liền mạch trạng thái đồ vật bằng người canh.
- **Chưa kiểm:** nguyên nhân lần chạy đầu chết; câu hỏi thật gửi cho kho đoạn ở từng cảnh; liệu model viết có đọc các đoạn (không có cách nhìn lời gọi sau khi chạy).
