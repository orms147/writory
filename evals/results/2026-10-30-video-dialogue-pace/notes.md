# Đếm lại lời thoại dày trên demo cũ của bộ xuất video

Người đọc: Claude, 30/10/2026. Kết quả đo bằng code, **không gọi model** (0 USD), cho D-127. Lệnh, commit và hash config ở `meta.json`; đầu ra nguyên văn ở `recount-zh.txt`.

## Đếm gì
`recount.py` đọc `script.json` của demo D-125 (một truyện, ba chương, sáu cảnh, lời thoại zh), dựng lại từng shot, áp nhịp thoại trong `config/limits.yaml` hiện hành và chạy chính `scene_problems` / `split_dense_shots` của mã.

## Kết quả (zh)
- 6 cảnh, 68 shot, 54 shot có thoại.
- **17 shot bị bắt** (lời thoại, không tính dấu câu, vượt nhịp nhân thời lượng). Đây là số của phép kiểm mới. Con số 22 trong `notes.md` của demo đếm mọi ký tự không phải khoảng trắng, kể cả dấu câu, nên không so thẳng với 17.
- **5 trong 6 cảnh có ít nhất một shot bị bắt**, tức nếu chạy demo lại thì 5 cảnh đó sẽ bị yêu cầu làm lại một lần (một lời gọi thêm mỗi cảnh).
- Nếu hết lượt thử lại mà vẫn dày thì code tách: 68 shot thành 72. Mọi shot sau tách có thời lượng trong khoảng cho phép.
- **2 shot vẫn quá dày sau khi tách**: chúng có một lượt thoại dài hơn nhịp nhân thời lượng tối đa, mà tách giữa lượt thoại thì phải tách cả `source_text`. Các shot này giữ nguyên và bản xuất đánh dấu `pace_over`.
- **1 cảnh (2.1) vượt trần số shot** sau khi tách: trần này ràng buộc model, không ràng buộc phép tách (D-127).

## Chưa kiểm
- Chưa chạy model thật với phép kiểm mới: số lượt làm lại thật có thể khác (model đã thấy nhịp trong đề `video-2` và có thể tự chia tốt hơn). Demo thật chạy lại sau khi chuỗi A/B của session 3 xong.
- Chỉ zh. Nhịp của ja, vi, en là số tạm chưa đối chiếu với giọng đọc thật.
- Chưa dán prompt đã tách vào app video: chưa biết hai clip liền nhau có lặp hành động khó chịu không.
