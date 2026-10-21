# Nhận xét đọc tay: narrator-v2-d78

Người đọc: Claude (điều phối), 21/10/2026. Prompt người kể `narrator-3` có lưới `meta_hedge` (D-78). **Không có giám khảo**: key Anthropic bị từ chối (401) ở lần chạy trước, nên lần này chấm hoàn toàn bằng code. Chi phí người kể 0,0239 USD.

| | narrator-1 (v2) | narrator-2 (v2-d77) | narrator-3 (v2-d78) |
|---|---|---|---|
| Lộ ở câu cuối / câu thô | 0 / 0 | 0 / 0 | 0 / 0 |
| Loại a (đã mở khoá) | 95/105 | 99/105 | **101/105** |
| Loại b, c, e, f | 100% | 90–98% | **100%** |
| Loại d | 38/39 | 30/39 | 37/39 |

- `narrator-3` lấy được cả hai cái tốt: trả lời câu đã mở khoá nhiều hơn `narrator-1`, mà câu cố moi bí mật vẫn ra đúng NOT_KNOWN như `narrator-1`.
- Lưới `meta_hedge` không phải bắt lượt nào, vì model tự giữ. Lưới vẫn là lớp dự phòng.
- **Chưa đo kiểu úp mở bằng giám khảo**: chưa có key Anthropic hợp lệ. Chạy lại `--judge` khi có key.
