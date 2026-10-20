# Bài đo C v1 — v1

- Commit: `356b4ef85a`; prompt: extract-1; config v1 (`791c154a985f`); truyện mẫu graph.yaml `e7a36786451a`.
- Chương [1, 2, 3, 4, 5], 2 mẫu mỗi (model, chương). Chấm bằng code, không giám khảo.
- **PV** = lớp người chơi biết (REVEALED_TO_PLAYER + KNOWS của nhân vật chính). **Hé lộ sai** = hé lộ một Fact mà dữ liệu vàng chưa hé lộ tới hết chương (rủi ro lộ bí mật).
- Toàn bộ cạnh gồm cả sự thật tác giả biết mà trang không viết ra, nên recall phần này có trần thấp.

| Model | n | PV P | PV R | PV F1 | Hé lộ sai | Toàn bộ P | Toàn bộ R | close P | close R | KNOWS how đúng | Cạnh bị bỏ | Lỗi gọi | USD/chương | Trễ s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | 10 | 0.57 | 0.76 | 0.65 | 4 | 0.55 | 0.62 | 0.44 | 0.50 | 6/6 | 16 | 0 | 0.00067 | 7.0 |
| DeepSeek V4.1 Flash | 10 | 0.40 | 0.38 | 0.39 | 2 | 0.55 | 0.44 | 0.59 | 0.71 | 5/5 | 8 | 0 | 0.00072 | 6.8 |
| Qwen 3.8 Flash | 2 | 0.86 | 0.60 | 0.71 | 0 | 0.74 | 0.56 | 1.00 | 0.50 | 1/2 | 3 | 8 | 0.00094 | 31.8 |

- Tổng chi phí OpenRouter: 0.0158 USD.
