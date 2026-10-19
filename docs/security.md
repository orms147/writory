# Bảo mật và guardrail

Mỗi guardrail có: mối đe doạ, cách thi hành trong code, và test chứng minh. Guardrail không có test là chưa xong. Danh sách rút gọn nằm trong `CLAUDE.md` §5; file này là bản đầy đủ.

Nguyên tắc chung: **an toàn nằm trong code, không nằm trong prompt.** Prompt chỉ giúp model làm đúng, không được là hàng rào duy nhất (OWASP LLM01, LLM07 bản 2025).

## Mối đe doạ, xếp theo mức nghiêm trọng với app này

| # | Mối đe doạ | Đường vào |
|---|---|---|
| T1 | Lộ bí mật / plot twist | sổ tay, hỏi người kể, văn bản lựa chọn, văn chương do model viết, thông báo lỗi, phản hồi API |
| T2 | Prompt injection, kể cả **loại lưu trữ** | ô tự viết, tên nhân vật, tiểu sử, câu hỏi người kể; chữ người chơi lưu vào đồ thị rồi quay lại prompt các chương sau |
| T3 | Lộ key OpenRouter của người chơi | log, thông báo lỗi, phản hồi API, cơ sở dữ liệu bị đọc trộm |
| T4 | Đốt tiền (của người chơi hoặc của chủ dự án) | vòng viết lại vô hạn, gọi hỏi người kể liên tục, bot đăng ký |
| T5 | Nội dung cấm | người chơi lái truyện sang nội dung tình dục liên quan trẻ vị thành niên hoặc nội dung vượt mức u tối đã chọn |
| T6 | Lộ dữ liệu giữa người dùng | truy vấn đồ thị quên lọc `story_id` |
| T7 | Ghi dữ liệu hỏng vào đồ thị | JSON trích sai schema, thực thể bịa, ghi nửa chừng |

## Guardrail

| Mã | Chống | Thi hành | Test |
|---|---|---|---|
| G1 | T1 | Sổ tay, hỏi người kể, tạo lựa chọn **chỉ nhận dữ liệu từ `player_view`**, lọc bằng code. Model phục vụ các đường này không bao giờ thấy lớp `truth`. Phản hồi API dùng schema riêng cho người chơi, không có trường id/nội dung ẩn. | Mỗi đường ra một test: dựng đồ thị có bí mật, gọi đường ra, khẳng định không bí mật nào nằm trong **context model nhận** (`FakeLLM.calls`), dùng được cho mọi vai, kể cả vai trả JSON. Với đường trả chữ, thêm chế độ `echo` (trả lại nguyên context) để khẳng định chữ trả người chơi không chứa bí mật. |
| G2 | T1 | Bộ dò lộ chạy trên mọi chữ trả về người chơi: so tên, biệt danh, cụm từ khoá của các `Fact` chưa hé lộ (đã chuẩn hoá NFC, bỏ dấu khi so). Trúng thì không hiện, viết lại hoặc báo lỗi. | Fixture cảnh có chứa bí mật dưới nhiều dạng (có dấu, không dấu, biệt danh). |
| G3 | T1 | Đánh dấu `REVEALED_TO_PLAYER` cho một bí mật phải kèm câu trích nguyên văn; code kiểm câu trích có trong cảnh đã hiện. | Trích bịa câu → không đánh dấu. |
| G4 | T2 | Chữ có nguồn gốc người chơi **không bao giờ vào vai system**. Luôn bọc trong khối dữ liệu có nhãn (spotlighting), kể cả khi đọc lại từ đồ thị (mọi trường do người chơi viết mang cờ `user_authored`). | Bộ câu tấn công trong `evals/redteam/` (tiếng Việt có dấu, không dấu, teencode, tiếng Anh); test khẳng định prompt dựng ra đặt chúng trong khối dữ liệu. |
| G5 | T2 | Ô tự viết đi qua một lời gọi **phân loại có đầu ra enum** (hành động trong truyện / yêu cầu ngoài truyện / nội dung cấm / vô nghĩa) trước khi tới model viết. Không dùng regex để đọc ý định; regex chỉ để kiểm định dạng. | Bộ câu có nhãn `evals/redteam/g5_classify.yaml` (có dấu, không dấu, teencode, tiếng Anh; câu phủ định, câu dài, tấn công đội lốt hành động, bạo lực hợp lệ). Test nhanh bằng model giả: luồng, chữ người chơi không vào vai system, fail closed (D-27). Đo với model thật: `writory.safety.bench_g5`. |
| G6 | T2 | Hành động vượt luật thế giới hoặc khả năng nhân vật: truyện vẫn viết, nhưng hành động thất bại hoặc phải trả giá. Không chiều theo. | Kịch bản "tôi trở thành thần" → người canh đánh dấu nếu cảnh chiều theo. |
| G7 | T3 | Key mã hoá khi lưu (khoá mã hoá lấy từ biến môi trường, không nằm trong repo). Không bao giờ ghi vào log, thông báo lỗi hay phản hồi API; chỉ hiện 4 ký tự cuối. Bộ lọc log xoá chuỗi có dạng key. | Test log và phản hồi lỗi không chứa key giả đã cài. |
| G8 | T4 | Trần chi phí mỗi cảnh, mỗi chương, mỗi truyện, và giới hạn số lời gọi mỗi phút cho mỗi tài khoản, đặt trong `config/limits.yaml`. Lượt viết lại có giới hạn cứng. Ghi chi phí mọi lời gọi (lấy từ `usage` mà OpenRouter trả về). Bộ đo dùng key riêng có trần chi tiêu. | Model giả luôn trả lỗi → pipeline dừng sau đúng số lần thử đã đặt. |
| G9 | T5 | Chặn cứng nội dung tình dục liên quan trẻ vị thành niên, ở cả đầu vào lẫn đầu ra, độc lập với mức u tối. Mức u tối có trần. Model kiểm duyệt cho tiếng Việt chọn sau khi đo trên bộ câu riêng: chưa xác nhận Llama Guard hay OpenAI moderation hỗ trợ tốt tiếng Việt. | Bộ câu kiểm duyệt tiếng Việt trong `evals/redteam/`. |
| G10 | T6 | Mọi truy vấn Neo4j đi qua một lớp truy cập bắt buộc nhận `story_id`. Không có hàm nào chạy Cypher thô từ ngoài lớp đó. Mỗi request kiểm truyện thuộc người đang đăng nhập. | Hai truyện cùng tên nhân vật, truy vấn truyện A không trả gì của B; người dùng B gọi API truyện A → 404. |
| G11 | T7 | Kết quả trích qua schema pydantic. Sai → thử lại 1 lần → vẫn sai thì không ghi, báo lỗi. Chỉ tham chiếu id thực thể có sẵn; thực thể mới phải khai riêng. Ghi theo D-6 (tất cả hoặc không gì), và không đổi trạng thái phiên trước khi ghi thành công. | JSON hỏng, id bịa, lỗi giữa chừng khi ghi Neo4j → đồ thị và trạng thái phiên giữ nguyên như trước. |
| G12 | mọi loại | Lỗi trả người chơi có mã riêng và câu tiếng Việt nói chuyện gì xảy ra và nên làm gì tiếp. Không trả mã chung chung kiểu `TOOL_ERROR`. Chi tiết kỹ thuật chỉ vào log, và log không chứa bí mật truyện hay key. | Mỗi mã lỗi có câu thông báo; test không mã nào trả câu rỗng. |

## Đã cài trong code
Bảng này chỉ trỏ tới code và test, không chép lại cách làm.

| Mã | Code | Test |
|---|---|---|
| G4 | `backend/src/writory/safety/wrap.py` (D-12) | `tests/unit/test_safety_wrap.py`, chạy trên bộ câu `evals/redteam/g4_prompt_injection.yaml` |
| G7 | `safety/crypto.py` (D-11), `safety/redact.py` (bộ lọc log, gắn bằng `install_log_redaction`; app gắn cho root và logger `uvicorn*` lúc khởi động, D-29) | `tests/unit/test_safety_keys.py`, `test_llm_openrouter.py::test_key_never_appears_in_error_even_if_server_echoes_it` |
| G8 | `llm/cost.py` (`CostTracker`, `MeteredClient`) (D-10), `llm/retry.py` (D-14) | `tests/unit/test_llm_cost.py`, `test_llm_retry.py` |
| G5 | `safety/classify.py` (`classify_action`, `ensure_in_story`, D-27) | `tests/unit/test_classify.py` |
| G12 | `backend/src/writory/errors.py`; `api/errors.py` (bảng `HTTP_STATUS`, lỗi lạ → `INTERNAL_ERROR`, D-29) | `tests/unit/test_errors.py`, `test_api.py` |

Model giả (`llm/fake.py`) có chế độ `echo` trả lại nguyên context, dùng cho test G1.

## Đo guardrail
- Test nhanh (mỗi commit): G1–G12 với model giả, không mạng.
- Red-team với model thật: chạy tay hoặc định kỳ, có trần chi phí; báo tỉ lệ tấn công thành công. Lệnh và kết quả: `docs/eval.md`, `evals/results/`.
- Mỗi lỗi bảo mật tìm được thêm thành một test hồi quy trước khi sửa.

## Chưa giải quyết
- Nghị định 147/2024/NĐ-CP có áp dụng cho app này không (design §14). Phải kiểm trước khi mở cho người lạ.
- Model kiểm duyệt cho tiếng Việt (G9).
- Model vẫn có thể *tự suy ra* bí mật từ manh mối hợp lệ. Đó là việc của bản kế hoạch truyện và người canh, không phải lỗi rò rỉ.
- Stream đứt giữa chừng thì không ghi được chi phí, nên trần G8 bị hụt. Hướng xử lý: sau lời gọi, tra chi phí theo id generation (chưa kiểm endpoint này). Làm ở tuần 2.
- `response_format` strict với schema do pydantic sinh chưa thử với model thật. Kiểm ở tuần 2.
