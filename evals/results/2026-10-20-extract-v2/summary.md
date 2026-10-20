# Bài đo C v1 — v2

- Commit: `c0b2e9f09b`; prompt: extract-2; config v1 (`791c154a985f`); truyện mẫu graph.yaml `e7a36786451a`.
- Chương [1, 2, 3, 4, 5], 2 mẫu mỗi (model, chương). Chấm bằng code, không giám khảo.
- **PV** = lớp người chơi biết (REVEALED_TO_PLAYER + KNOWS của nhân vật chính). **Hé lộ sai** = hé lộ một Fact mà dữ liệu vàng chưa hé lộ tới hết chương (rủi ro lộ bí mật).
- Toàn bộ cạnh gồm cả sự thật tác giả biết mà trang không viết ra, nên recall phần này có trần thấp.

| Model | n | PV P | PV R | PV F1 | Hé lộ sai | Toàn bộ P | Toàn bộ R | close P | close R | KNOWS how đúng | Cạnh bị bỏ | Lỗi gọi | USD/chương | Trễ s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | 10 | 0.56 | 0.72 | 0.63 | 0 | 0.49 | 0.61 | 1.00 | 0.29 | 6/6 | 8 | 0 | 0.00067 | 6.3 |
| DeepSeek V4.1 Flash | 10 | 0.35 | 0.34 | 0.35 | 1 | 0.51 | 0.40 | 1.00 | 0.57 | 5/5 | 12 | 0 | 0.00073 | 5.7 |
| Qwen 3.8 Flash | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |

- Tổng chi phí OpenRouter: 0.0140 USD.
