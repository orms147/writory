# Nhận xét đọc tay: memory-deepseek-1 (DeepSeek V4 Flash, bài A đề facts)

Người đọc: Claude (nhánh feature/model-deepseek), 22/10/2026. Nguồn: `summary.md`, `results.jsonl`, `errors.jsonl`. D-100.

Lệnh: `uv run --group eval python -m writory.pipeline.bench_a run --label deepseek-1 --questions-file questions-ky-ao-vua-1-facts.yaml --systems graph,graph_quotes --samples 1 --budget 0.04 --env-file C:/Work/AI/WriTory/.env`.

## Lượt chạy BỊ TRẦN CẮT, `summary.md` không dùng được thẳng
Trần `--budget 0.04` (giữ chỗ tính cả lượt đang bay) dừng lượt chạy sau 50 lượt có kết quả + 2 lỗi trên 78 lượt khai. `summary.md` chia cho 39 câu mỗi hệ, nên các lượt chưa chạy (26) tính là chưa đúng: 54% và 59% ghi trong đó là **thấp giả**, và nhóm "quan hệ" 0/7 là toàn lượt chưa chạy. Chạy tiếp vào cùng thư mục cần trần lớn hơn (đã tiêu 0,0381 USD của tổng trần 0,15 mà D-100 được giao).

## So trên đúng các câu đã chạy (thứ tự đề: alive, item, knows-01..10; chưa tới relation)
| Hệ | DeepSeek (1 lần) | Luna `facts-s3` (3 lần), cùng câu |
|---|---|---|
| đồ thị | 21/26 = 81% (5 kiêng, 0 lỗi) | 64/78 = 82% |
| đồ thị + câu trích | 23/24 = 96% (2 lỗi `json_invalid` không tính) | 64/72 = 89% |
- Trên phần đã chạy, DeepSeek ngang Luna (chênh nằm trong nhiễu của 24–26 lượt). **Không có số cho toàn đề** nên không so được 71% và 84% của Luna.
- **Lỗi:** 2/26 lượt của `graph_quotes` (`item-10`, `knows-10`) là `RETRY_LIMIT_REACHED` do `AnswerOutput: json_invalid`, finish_reason `stop`. Thăm dò sau đó (D-100): nhà cung cấp DigitalOcean trả `{"{ "answer": ...}`; bỏ nó (`provider.ignore`) thì 8/8 hợp lệ. Bài A chạy dưới config chưa có `provider_ignore`.
- **Chi phí:** 0,0381 USD cho 50 lượt, khoảng 0,00076 mỗi lượt (lạnh), token ra trung bình 372 mỗi lời gọi, vào 5.942; Luna `nb1` lạnh 0,00061. 7/52 lời gọi có token cache.

## Chưa kiểm
- 28 lượt (nhóm quan hệ, phần cuối nhóm "ai biết gì") chưa chạy; 1 lần hỏi; số trên là trên tập con chọn theo thứ tự đề, không ngẫu nhiên.
