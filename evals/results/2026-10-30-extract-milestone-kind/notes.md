# Phát lại bộ trích `extract-8` / `extract-9` trên chương đã lưu (D-129): kết quả

Khai trước: `expectations.md` (commit `f6f208c`, trước mọi lời gọi). Script `replay.py`, chạy từ `backend/` như docstring của nó; `meta.json` ghi trần 0,10 USD, đủ 12 ca. Đầu ra: `results.jsonl` (mốc nhận, mốc model trả, lý do từ chối), `calls.jsonl`, `meta.json`.

- **Commit:** `f6f208c155e1bcf91c80c947fc303603d5b92d0e` (`meta.json`, `dirty: false` cho `backend/` và `config/`).
- **Config:** sha256 gộp `a9c464cdef675b8b2dc100424bf2611fee4cf6c67c0d63d8a174980de8227e81` (`models.yaml` `703d6ab6d840`, `limits.yaml` `ea58835b2ef7`). `meta.json` không ghi hash: tính sau lượt chạy bằng `bench_run.config_sha256` trên `config/` của chính commit đó (`git diff f6f208c -- config` rỗng).
- **Model:** `openai/gpt-6-luna`, `reasoning.effort: low` (vai `extract`).
- **Chi:** 24 lời gọi, 0,049823 USD; không ca nào bị bỏ, không dừng vì trần, mọi lời gọi `finish_reason: stop`.
- **Chạy chung key:** lượt này chạy lúc 00:35 ngày 30/10/2026, trùng phần cuối của một lượt đo khác dùng cùng key OpenRouter, trái với dòng "một mình, không song song" trong docstring `replay.py`. Chi phí mỗi lời gọi lấy từ `usage` của chính phản hồi đó, và cả 24 lời gọi đều có kết quả (không ca nào bị bỏ hay lỗi), nên kết quả và chi phí của hai lượt không lẫn nhau. Ghi ra để minh bạch.

## Kết quả từng ca
"Gốc" = dấu đã có trong lượt chạy gốc. Số dòng là dòng trong `chapters/chNN.md` của lượt gốc.

| Ca | Mốc trong đề | Gốc | `extract-8` | `extract-9` |
|---|---|---|---|---|
| tu-tien ch19 | m6 cao trào (20–22) | m6 | nhận m6: "Nàng được dùng hộp để dò mạch." (dòng 135) | nhận m6: đoạn liền từ dòng 135 tới "…xẻ gờ thành hai mảnh." (dòng 151) |
| ky-ao ch24 | m7 cao trào (20–23) | không | không trả mốc | trả m7, **G3 từ chối**: ghép "Tôi sẽ dùng nó để mở đường…" với "Phần bản đồ còn lại…" bằng "[...]" |
| ky-ao ch16 | m6 cao trào (16–18), m7 | m6 | nhận m6: "Đoàn Khương thúc đẩy vụ bắt Đinh Lộc để thu hồi Bản đồ Nếp Gấp." (dòng 31) | **không trả mốc** |
| tu-tien ch11 | m4 bước ngoặt (12–13) | m4 | nhận m4: "Ta là người đưa tin của Minh Ước Giữ Ấn. Không phải sứ giả Huyền Tiêu Tông." | nhận m4, cùng câu |
| ky-ao ch10 | m5 bước ngoặt (13–15) | m5 | nhận m5: "Chỉ biết một chuyến đi từng nằm ở đó, rồi bị ai đó xóa đi." (dòng 79) | nhận m5, câu khác: "Ngày tháng ghi ở lề không khớp… nét nhỏ và đen hơn." (dòng 77) |
| tu-tien ch5 | m3 bước ngoặt (9–11) | m3 | nhận m3: "Áp lực nước dồn vào chốt phong ấn, khiến nó phát tiếng." (dòng 37) | **không trả mốc** |
| ngữ cảnh: tu-tien ch17, ch18 (m6); ky-ao ch22, ch23 (m7) | | không | không trả mốc | không trả mốc |
| lặp: tu-tien ch19 | m6 | m6 | nhận m6, cùng câu lần 1 | trả m6, **G3 từ chối**: như đoạn lần 1 nhưng bỏ dòng "Nàng không đáp ngay." |
| lặp: ky-ao ch24 | m7 | không | nhận m7: "Đường này sửa được những chỗ nối… quyền chọn thay tất cả mọi người." (dòng 87) | trả m7, **G3 từ chối**: "…không thể chỉ đường quay về." (chương ghi "…quay về nữa.", dòng 97) |

## K1–K4 và luật quyết (áp đúng như khai)
- **K1 sai.** Lần 1: `extract-9` nhận m6 ở tu-tien ch19. Lần lặp: không nhận, nhưng chỉ vì câu trích không nguyên văn; cả hai lần model vẫn đánh dấu m6.
- **K2 sai.** `extract-9` không nhận m7 ở ky-ao ch24 lần nào; cả hai lần model trả m7, cả hai bị G3 từ chối. `extract-8` nhận m7 ở lần lặp.
- **K3 sai.** `extract-9` mất dấu đúng ở ky-ao ch16 (m6, cao trào đúng hạn) và tu-tien ch5 (m3, bước ngoặt); giữ tu-tien ch11 (m4) và ky-ao ch10 (m5); không thêm dấu mới nào.
- **K4 đúng.** Bốn chương ngữ cảnh: cả hai bản đều không nhận mốc nào.
- **Luật quyết.** "Tín hiệu tốt" không đạt (K1, K2 sai ở lần đầu; ca đối chứng mất dấu). "Tín hiệu xấu" đạt: `extract-9` làm mất dấu đúng của ky-ao ch16.
- **Kết luận: tín hiệu xấu.** Theo luật khai trước: ghi lại, không chỉnh đề cho khớp, không sửa đề lần hai trong PR này.

## Đọc tay
**Đã kiểm** (đọc chương và `results.jsonl`):
- Mọi câu trích được nhận đều có nguyên văn trong chương (code G3 đã kiểm; dòng ghi ở bảng).
- tu-tien ch19, `extract-9` lần 1: đoạn trích gồm quyết định cho Ninh Tuyết Anh dùng hộp (dòng 135) và vết nứt dưới chân mở rộng (dòng 151). Việc tự cắt đường lui ("Lối quay lên bị nó lấp kín", dòng 121) xảy ra trước quyết định.
- ky-ao ch24: cả hai câu trích của `extract-9` trỏ đúng vùng có quyết định dùng bản đồ và việc xé dải đường về (dòng 87–97). Bị từ chối chỉ vì không nguyên văn (ghép bằng "[...]"; thiếu chữ "nữa").
- ky-ao ch16: chương có câu Tạ Vân nói ra Đoàn Khương đứng sau vụ bắt (dòng 31), sau đó Mai Thảo bỏ đi và tự xoá dấu ("Đường quay lại cũng đi luôn"). `extract-9` không trả mốc nào.
- tu-tien ch5: m3 là bước ngoặt, luật mới của `extract-9` chỉ nói về cao trào.
- Câu trích mốc bị G3 từ chối: `extract-9` 3 câu, cả 3 ở ca mục tiêu cao trào; `extract-8` không câu nào.

**Suy luận (chưa kiểm):**
- Luật "bước ngoặt VÀ hậu quả" có vẻ khiến model ghép hai đoạn xa nhau vào một câu trích, nên G3 từ chối. Ở ky-ao ch24, model chọn đúng hướng K2 nhưng câu trích làm hỏng; K2 sai vì câu trích, không vì model bỏ mốc.
- tu-tien ch19: "hậu quả" model dùng (vết nứt mở rộng) lặp lại suốt chương, không phải cái giá không đảo được của quyết định. Luật mới chưa đủ chặt để chặn dấu sớm này.
- ky-ao ch16 là cao trào kiểu đối mặt với sự thật. Đòi "hậu quả" hợp với cao trào kiểu quyết định hơn, nên có thể làm mất dấu đúng ở loại này.
- tu-tien ch5: mất dấu bước ngoặt có thể là nhiễu, hoặc đề dài hơn làm model dè dặt hơn; một mẫu không tách được.

## Lưu ý
- Một lời gọi mỗi bản đề mỗi ca (hai lời gọi ở hai ca mục tiêu) là nhiễu, như luật khai trước nói. Chính `extract-8` cũng đổi kết quả giữa lần 1 và lần lặp ở ky-ao ch24 (không trả mốc, rồi nhận m7).
- Phát lại một lời gọi cho cả chương, khác sản phẩm (mỗi cảnh một lời gọi); danh mục không có `Lie` của lựa chọn (`expectations.md`).
- Lời gọi 21–24 có chi phí thấp hơn ba đến năm lần so với lần 1 cùng ca, với cùng số token đề (có thể do cache phía nhà cung cấp; chưa kiểm).

## Quyết định sau phép đo
Theo luật khai trước (tín hiệu xấu), `extract-9` không gộp vào main (D-129); PR #109 chỉ còn kết quả đo. Chữ đề `extract-9` lưu ở `extract9_system_prompt.txt`; dòng mốc có cột loại do code của commit 7ea8812 sinh, nên chạy lại đúng như lần đo cần checkout commit đó.
