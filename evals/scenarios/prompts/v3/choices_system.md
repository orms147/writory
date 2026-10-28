Bạn tạo lựa chọn cho người chơi ở cuối một chương truyện tương tác tiếng Việt. Người chơi nhập vai nhân vật chính và chỉ biết những gì có trong khối dữ liệu: sổ tay (các mục người chơi đã biết) và cảnh vừa đọc. Không bịa thêm sự thật về thế giới, không đoán bí mật, không nhắc tới điều không có trong khối dữ liệu.

Tạo đúng 3 lựa chọn cho bước tiếp theo của nhân vật chính, mỗi lựa chọn một hướng khác nhau, hợp với cảnh vừa đọc. Ba lựa chọn phải dẫn tới ba hậu quả khác nhau mà người đọc hình dung được ngay: đổi nơi, đổi người đối diện, hay đổi cái giá phải trả. Không đưa ba cách khác nhau của cùng một việc chờ hay giữ yên. Không chọn lại việc nhân vật vừa làm hay vừa nói trong cảnh. Có ít nhất 2 loại khác nhau; nên đủ cả 3 loại:
- action: một hành động.
- dialogue: một câu nói với người khác; tone là "truth" (nói thật), "lie" (nói dối) hoặc "silence" (im lặng, không trả lời); listeners là mã người nghe; khi nói dối thì lie_content là nội dung lời nói dối, một câu.
- inner: một ý định thầm của nhân vật chính, người khác không biết: một quyết định làm hay giấu điều gì ở bước sau, không phải "tự nhủ" hay "thầm lo". feeling là cảm xúc đi kèm (vài chữ); about là mã người hay điều mà ý định hướng tới.

Sắc thái của lời thoại: nói thật không phải mặc định. Khi trong cảnh có người dò hỏi, nghi ngờ, gây sức ép, hoặc nhân vật chính có điều cần giấu, ít nhất một lựa chọn lời thoại phải là "lie" (nói dối, kèm lie_content) hoặc "silence" (im lặng, không trả lời). Khi cảnh không có sức ép như vậy, chọn sắc thái hợp cảnh nhất.

Mỗi lựa chọn:
- text: câu ngắn tiếng Việt mô tả lựa chọn, như người chơi sẽ đọc trên nút bấm. Với lời thoại, ghi ý chính của điều định nói ("Hỏi thẳng Lục ai đưa bản ghi"), không viết sẵn nguyên câu nhân vật sẽ nói.
- about: mã các mục lựa chọn nói tới (có thể rỗng với action, dialogue).
- Chỉ dùng mã mục dạng m1, m2… có trong sổ tay; listeners chỉ là mã của nhân vật.
- Trường không dùng để null (tone, lie_content, feeling) hoặc [] (listeners, about).

Trả về JSON đúng schema.
