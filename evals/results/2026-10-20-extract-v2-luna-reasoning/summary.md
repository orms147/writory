# Bài đo C v1 — v2-luna-reasoning

- Commit: `689f64453d`; prompt: extract-2; config v2 (`3d3364efef9d`); truyện mẫu graph.yaml `e7a36786451a`.
- Chương [1, 2, 3, 4, 5], 2 mẫu mỗi (model, chương). Chấm bằng code, không giám khảo.
- **PV** = lớp người chơi biết (REVEALED_TO_PLAYER + KNOWS của nhân vật chính). **Hé lộ sai** = hé lộ một Fact mà dữ liệu vàng chưa hé lộ tới hết chương (rủi ro lộ bí mật).
- Toàn bộ cạnh gồm cả sự thật tác giả biết mà trang không viết ra, nên recall phần này có trần thấp.

| Model | n | PV P | PV R | PV F1 | Hé lộ sai | Toàn bộ P | Toàn bộ R | close P | close R | KNOWS how đúng | Cạnh bị bỏ | Lỗi gọi | USD/chương | Trễ s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6 Luna | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |
| DeepSeek V4.1 Flash | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |
| Qwen 3.8 Flash | 0 | — | — | — | — | — | — | — | — | — | — | 0 | — | — |
| GPT-6 Luna (suy luận thấp) | 10 | 0.75 | 0.82 | 0.78 | 0 | 0.77 | 0.60 | 1.00 | 0.64 | 6/6 | 4 | 0 | 0.00089 | 18.4 |

- Tổng chi phí OpenRouter: 0.0089 USD.
