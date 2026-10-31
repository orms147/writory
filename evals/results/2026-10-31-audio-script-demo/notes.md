# Lượt chạy thật đầu của bộ viết kịch bản audio (D-151)

Người đọc: Claude (điều phối), 31/10/2026. Không phải bài đo khai trước: các lượt dưới đây để kiểm công cụ chạy hết
đường và thấy lỗi, rồi sửa. Model `openai/gpt-6-luna` (vai `audio` và `moderate`, OpenRouter, key của chủ dự án).

## File trong thư mục này
- `ideas.md`, `ideas.yaml`: `propose --tags "thiếu gia bị hoán đổi thân phận, tiểu thư giả, trà xanh, vả mặt, hào môn"
  --count 5` (1 lời gọi, 0,0007 USD). Đầu vào của lượt chính.
- `tts.txt`, `script.md`, `script.json`, `calls.jsonl`: lượt chính, `write --premise-file ideas.yaml --pick i1
  --minutes 80 --budget 0.50`. Commit `58148ff9c8d5`, không sửa chưa commit; hash config đã gộp
  `da52c30fad34…` (`script.json`, `meta`).

## Các lượt chạy
| Lượt | Code | Kết quả | Chi phí |
|---|---|---|---|
| 30 phút, hướng i2 | trước commit đầu | 5/5 đoạn, 5.184 chữ | 0,0181 USD |
| 80 phút, hướng i1 | `330b0f6` | dừng ở đoạn 5/12: hết lượt viết lại (khi đó chỉ 2 lượt), lý do không được ghi | 0,0170 USD |
| 80 phút, hướng i1 | `19b643a` (sửa: `schema_retries`, dời bí mật, ghi lý do) | 11/12 đoạn; đoạn kết bị kiểm duyệt chặn `real_world_harm`, bị giữ lại | 0,0363 USD |
| 80 phút, hướng i1 | `58148ff` (sửa: viết lại một lần khi bị chặn mức BLOCKED) | **12/12 đoạn**, 13.554 chữ, mọi đoạn qua kiểm duyệt ngay lần đầu | 0,0368 USD |

Tổng các lượt (kể cả `propose`): khoảng 0,109 USD OpenRouter.

## Lượt chính đọc được gì
- Kế hoạch 6 nhân vật, 4 bí mật lộ ở đoạn 3, 6, 8, 11; mỗi bí mật lộ đúng đoạn, kèm câu trích có thật (code kiểm).
  Không đoạn nào phải dời bí mật.
- 13.554 chữ so với mục tiêu 12.000 (thừa 13%): 11/12 đoạn trong ±25%, đoạn kết dài 1.371 chữ (`length_off`). Ở 150
  chữ/phút là khoảng 90 phút; tốc độ đọc thật của TTS chưa đo, nên chưa biết file audio dài bao nhiêu.
- Đọc tay đoạn 8 và đoạn 12: người kể ngôi thứ nhất, câu ngắn; lời thoại có câu dẫn nên TTS một giọng đọc được;
  `cue` hợp cảnh; nhân vật, tình tiết (bản ghi âm, cuốn sổ cũ, tiệc mừng thọ) nhất quán qua 12 đoạn; đoạn nào cũng
  kết bằng câu treo; đoạn kết khép đúng kế hoạch.
- Giọng văn "đứng đắn" hơn thể loại "chết não" thường thấy: phản diện bị xử bằng hồ sơ và kiểm toán hơn là màn vả mặt
  lố. Muốn lố hơn thì phải sửa đề (suy luận, chưa thử).

## Lượt chặn đoạn kết (`19b643a`)
Đoạn kết bị chặn `real_world_harm` (loại gồm "lừa đảo"). Nhịp của đoạn là hoàn trả tiền và công bố kết quả kiểm tra
tài chính sau vụ hợp đồng giả, nên có thể là chặn nhầm (suy luận: chữ của đoạn bị giữ lại theo luật fail-closed, không
đọc được). Sau sửa ở `58148ff`, đoạn bị chặn mức BLOCKED được viết lại một lần kèm loại bị chặn rồi kiểm lại; lượt
chính không cần tới bước này, nên đường viết lại mới chỉ được kiểm bằng test.

## Chưa kiểm
- Một hướng đi, một model; chưa chấm bằng giám khảo, chưa so model.
- Tốc độ đọc của TTS (`limits.audio_script.words_per_minute` là số tạm).
- Tỉ lệ chặn nhầm của kiểm duyệt trên thể loại này: một đoạn bị chặn trên 33 đoạn đã kiểm qua bốn lượt `write`.
