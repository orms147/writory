# Bài đo C v1 — v2-qwen

- Commit: `c0b2e9f09b`; prompt: extract-2; config v1 (`791c154a985f`); truyện mẫu graph.yaml `e7a36786451a`.
- Chương [1, 2, 3, 4, 5], 2 mẫu mỗi (model, chương). Chấm bằng code, không giám khảo.
- **PV** = lớp người chơi biết (REVEALED_TO_PLAYER + KNOWS của nhân vật chính). **Hé lộ sai** = hé lộ một Fact mà dữ liệu vàng chưa hé lộ tới hết chương (rủi ro lộ bí mật).
- Toàn bộ cạnh gồm cả sự thật tác giả biết mà trang không viết ra, nên recall phần này có trần thấp.

| Model | n | PV P | PV R | PV F1 | Hé lộ sai | Toàn bộ P | Toàn bộ R | close P | close R | KNOWS how đúng | Cạnh bị bỏ | Lỗi gọi | USD/chương | Trễ s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |
| DeepSeek V4.1 Flash | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |
| Qwen 3.8 Flash | 4 | 0.81 | 0.65 | 0.72 | 1 | 0.62 | 0.59 | 0.80 | 0.80 | 2/2 | 0 | 6 | 0.00093 | 23.1 |

- Tổng chi phí OpenRouter: 0.0037 USD.
