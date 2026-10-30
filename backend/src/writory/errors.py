"""Danh mục mã lỗi trả người chơi (G12).

Mỗi mã có câu tiếng Việt: chuyện gì xảy ra và làm gì tiếp. Chi tiết kỹ thuật (`detail`)
chỉ để ghi log, không bao giờ vào phản hồi cho người chơi.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from writory.safety.redact import redact


class ErrorCode(StrEnum):
    CONFIG_LIMIT_NOT_SET = "CONFIG_LIMIT_NOT_SET"
    CONFIG_MODEL_NOT_SET = "CONFIG_MODEL_NOT_SET"
    COST_LIMIT_SCENE = "COST_LIMIT_SCENE"
    COST_LIMIT_CHAPTER = "COST_LIMIT_CHAPTER"
    COST_LIMIT_STORY = "COST_LIMIT_STORY"
    LLM_COST_UNKNOWN = "LLM_COST_UNKNOWN"
    RETRY_LIMIT_REACHED = "RETRY_LIMIT_REACHED"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"
    LLM_INSUFFICIENT_CREDITS = "LLM_INSUFFICIENT_CREDITS"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_CONTENT_BLOCKED = "LLM_CONTENT_BLOCKED"
    LLM_REQUEST_INVALID = "LLM_REQUEST_INVALID"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_BAD_RESPONSE = "LLM_BAD_RESPONSE"
    PLAYER_KEY_MISSING = "PLAYER_KEY_MISSING"
    PLAYER_KEY_UNREADABLE = "PLAYER_KEY_UNREADABLE"
    STORY_NOT_FOUND = "STORY_NOT_FOUND"
    CHAPTER_SAVE_FAILED = "CHAPTER_SAVE_FAILED"
    CHAPTER_PENDING = "CHAPTER_PENDING"
    CHAPTER_OUT_OF_ORDER = "CHAPTER_OUT_OF_ORDER"
    CHAPTER_PACKAGE_INVALID = "CHAPTER_PACKAGE_INVALID"
    CHAPTER_QUOTE_NOT_IN_TEXT = "CHAPTER_QUOTE_NOT_IN_TEXT"
    ACTION_EMPTY = "ACTION_EMPTY"
    ACTION_TOO_LONG = "ACTION_TOO_LONG"
    ACTION_OUT_OF_STORY = "ACTION_OUT_OF_STORY"
    ACTION_FORBIDDEN = "ACTION_FORBIDDEN"
    ACTION_UNCLEAR = "ACTION_UNCLEAR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SCENE_LEAK_BLOCKED = "SCENE_LEAK_BLOCKED"
    NARRATOR_QUESTION_EMPTY = "NARRATOR_QUESTION_EMPTY"
    NARRATOR_QUESTION_TOO_LONG = "NARRATOR_QUESTION_TOO_LONG"
    NARRATOR_LIMIT_REACHED = "NARRATOR_LIMIT_REACHED"
    WRITORY_RATE_LIMITED = "WRITORY_RATE_LIMITED"
    STORY_SETUP_INVALID = "STORY_SETUP_INVALID"
    STORY_LENGTH_NOT_OPEN = "STORY_LENGTH_NOT_OPEN"
    CHOICES_LEAK_BLOCKED = "CHOICES_LEAK_BLOCKED"
    INPUT_BLOCKED = "INPUT_BLOCKED"
    SETUP_NOT_FOUND = "SETUP_NOT_FOUND"
    SETUP_STEP_NOT_READY = "SETUP_STEP_NOT_READY"
    PLAYER_KEY_INVALID = "PLAYER_KEY_INVALID"
    REQUEST_INVALID = "REQUEST_INVALID"
    CHARACTER_EDIT_INVALID = "CHARACTER_EDIT_INVALID"
    CHOICE_NOT_FOUND = "CHOICE_NOT_FOUND"
    CHOICE_REQUIRED = "CHOICE_REQUIRED"
    CHAPTER_NOT_FOUND = "CHAPTER_NOT_FOUND"
    STORY_COMPLETE = "STORY_COMPLETE"
    STORY_BUSY = "STORY_BUSY"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    INVITE_CODE_INVALID = "INVITE_CODE_INVALID"
    LOGIN_RATE_LIMITED = "LOGIN_RATE_LIMITED"
    REQUEST_ORIGIN_INVALID = "REQUEST_ORIGIN_INVALID"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"


@dataclass(frozen=True)
class PlayerMessage:
    what: str
    next_step: str

    def text(self) -> str:
        return f"{self.what} {self.next_step}"


_REPORT = "Nếu lỗi lặp lại, hãy báo cho người quản trị."

MESSAGES: dict[ErrorCode, PlayerMessage] = {
    ErrorCode.CONFIG_LIMIT_NOT_SET: PlayerMessage(
        "Máy chủ chưa đặt giới hạn cần cho thao tác này nên đã dừng lại.",
        "Đây là lỗi cấu hình phía máy chủ, không phải do bạn; hãy báo cho người quản trị.",
    ),
    ErrorCode.CONFIG_MODEL_NOT_SET: PlayerMessage(
        "Máy chủ chưa chọn model cho bước này nên đã dừng lại.",
        "Đây là lỗi cấu hình phía máy chủ, không phải do bạn; hãy báo cho người quản trị.",
    ),
    # Bản 1 chỉ có một mức model viết (D-33): không bảo người chơi đổi mức (D-66). Trần mỗi cảnh
    # cũng áp cho bước tóm tắt và bước lựa chọn sau khi chương đã ghi, nên câu không nói chương
    # chưa lưu; G11 bảo đảm không có gì ghi nửa chừng.
    ErrorCode.COST_LIMIT_SCENE: PlayerMessage(
        "Lần viết vừa rồi đã chạm trần chi phí mỗi cảnh nên hệ thống dừng lại. Phần đã hiện và "
        "đã lưu vẫn còn.",
        "Bấm thử lại để viết lại phần còn dở. Trần do hệ thống đặt; nếu lần nào cũng dừng ở "
        "đây, hãy báo cho người quản trị.",
    ),
    ErrorCode.COST_LIMIT_CHAPTER: PlayerMessage(
        "Chương đang viết đã chạm trần chi phí mỗi chương nên hệ thống dừng lại. Phần đã hiện và "
        "đã lưu vẫn còn.",
        "Bấm thử lại để viết lại phần còn dở. Trần do hệ thống đặt; nếu lần nào cũng dừng ở "
        "đây, hãy báo cho người quản trị.",
    ),
    ErrorCode.COST_LIMIT_STORY: PlayerMessage(
        "Truyện này đã dùng hết trần chi phí cho một truyện.",
        "Bạn vẫn đọc lại được các chương đã có; muốn viết tiếp thì bắt đầu truyện mới.",
    ),
    ErrorCode.LLM_COST_UNKNOWN: PlayerMessage(
        "Không đọc được chi phí của lời gọi model vừa rồi, nên hệ thống dừng để bảo vệ key "
        "của bạn khỏi bị trừ tiền ngoài kiểm soát.",
        "Bấm thử lại. " + _REPORT,
    ),
    ErrorCode.RETRY_LIMIT_REACHED: PlayerMessage(
        "Hệ thống đã thử lại đủ số lần cho phép mà vẫn chưa xong.",
        "Đợi một lát rồi bấm thử lại. " + _REPORT,
    ),
    ErrorCode.LLM_AUTH_FAILED: PlayerMessage(
        "OpenRouter từ chối key của bạn (key sai, đã bị khoá hoặc đã hết hạn).",
        "Kiểm tra key trên openrouter.ai rồi nhập lại trong phần cài đặt.",
    ),
    ErrorCode.LLM_INSUFFICIENT_CREDITS: PlayerMessage(
        "Tài khoản OpenRouter của bạn không đủ credit cho lời gọi này.",
        "Nạp thêm credit trên openrouter.ai rồi bấm thử lại.",
    ),
    ErrorCode.LLM_RATE_LIMITED: PlayerMessage(
        "OpenRouter đang giới hạn tần suất gọi với key của bạn.",
        "Đợi khoảng một phút rồi bấm thử lại.",
    ),
    ErrorCode.LLM_CONTENT_BLOCKED: PlayerMessage(
        "Nhà cung cấp model từ chối nội dung của yêu cầu này.",
        "Thử chọn hoặc viết một hành động khác.",
    ),
    ErrorCode.LLM_REQUEST_INVALID: PlayerMessage(
        "Yêu cầu gửi tới model bị từ chối vì lỗi phía hệ thống, không phải do bạn.",
        "Bấm thử lại. " + _REPORT,
    ),
    ErrorCode.LLM_UNAVAILABLE: PlayerMessage(
        "Model đang không phản hồi hoặc mạng tới OpenRouter bị gián đoạn.",
        "Đợi một lát rồi bấm thử lại.",
    ),
    ErrorCode.LLM_TIMEOUT: PlayerMessage(
        "Model không trả lời trong thời gian cho phép nên hệ thống đã dừng chờ.",
        "Đợi một lát rồi bấm thử lại. Phần đã lưu vẫn còn nguyên.",
    ),
    ErrorCode.LLM_BAD_RESPONSE: PlayerMessage(
        "Model trả về kết quả sai định dạng nên hệ thống không dùng được.",
        "Bấm thử lại. " + _REPORT,
    ),
    ErrorCode.PLAYER_KEY_MISSING: PlayerMessage(
        "Bạn chưa nhập key OpenRouter.",
        "Nhập key trong phần cài đặt để tiếp tục.",
    ),
    ErrorCode.PLAYER_KEY_UNREADABLE: PlayerMessage(
        "Không đọc được key OpenRouter đã lưu của bạn.",
        "Nhập lại key trong phần cài đặt.",
    ),
    ErrorCode.STORY_NOT_FOUND: PlayerMessage(
        "Không tìm thấy truyện này.",
        "Quay về danh sách truyện của bạn và mở lại.",
    ),
    ErrorCode.CHAPTER_SAVE_FAILED: PlayerMessage(
        "Không lưu được chương vừa viết vì dữ liệu của chương không khớp với truyện. "
        "Truyện vẫn ở chương trước, không mất gì.",
        "Bấm thử lại để viết lại chương này. " + _REPORT,
    ),
    ErrorCode.CHAPTER_PENDING: PlayerMessage(
        "Chương trước vẫn đang được lưu dở nên chưa viết tiếp được.",
        "Đợi một lát rồi bấm thử lại; hệ thống sẽ hoàn tất việc lưu chương trước.",
    ),
    ErrorCode.CHAPTER_OUT_OF_ORDER: PlayerMessage(
        "Truyện đã sang chương khác so với trang bạn đang xem (có thể truyện đang mở ở hai nơi).",
        "Tải lại trang để thấy chương mới nhất.",
    ),
    ErrorCode.CHAPTER_PACKAGE_INVALID: PlayerMessage(
        "Hệ thống tạo ra thay đổi không hợp lệ cho chương này nên chưa lưu gì. "
        "Lỗi ở phía hệ thống, không phải do bạn.",
        "Bấm thử lại. " + _REPORT,
    ),
    # G3 ở bước ghi (D-106). Câu trung tính: không nói điều gì được ghi là đã hé lộ.
    ErrorCode.CHAPTER_QUOTE_NOT_IN_TEXT: PlayerMessage(
        "Chương vừa viết ghi lại một điều không có trên trang nên chưa lưu gì. "
        "Truyện vẫn ở chương trước, không mất gì. Lỗi ở phía hệ thống, không phải do bạn.",
        "Bấm thử lại để viết lại chương này. " + _REPORT,
    ),
    # Ô tự viết hành động (G5, D-27). Câu trung tính: không nhắc lại chữ người chơi, không kể lý do
    # của bộ phân loại.
    ErrorCode.ACTION_EMPTY: PlayerMessage(
        "Bạn chưa viết hành động nào.",
        "Viết điều nhân vật của bạn làm, nói hoặc nghĩ rồi gửi.",
    ),
    ErrorCode.ACTION_TOO_LONG: PlayerMessage(
        "Hành động bạn viết dài hơn mức cho phép.",
        "Rút gọn lại rồi gửi.",
    ),
    ErrorCode.ACTION_OUT_OF_STORY: PlayerMessage(
        "Ô này chỉ nhận hành động của nhân vật trong truyện.",
        "Viết lại điều nhân vật của bạn làm, nói hoặc nghĩ.",
    ),
    ErrorCode.ACTION_FORBIDDEN: PlayerMessage(
        "Hành động này thuộc loại nội dung truyện không viết.",
        "Chọn hoặc viết một hành động khác.",
    ),
    ErrorCode.ACTION_UNCLEAR: PlayerMessage(
        "Hệ thống không hiểu hành động bạn viết.",
        "Viết lại rõ hơn, ví dụ: \"Tôi mở cửa bước ra ngoài.\"",
    ),
    # Lỗi không lường trước (exception không phải WritoryError). Chi tiết chỉ vào log (D-29).
    ErrorCode.INTERNAL_ERROR: PlayerMessage(
        "Hệ thống gặp lỗi không lường trước nên chưa làm xong việc bạn yêu cầu.",
        "Bấm thử lại. " + _REPORT,
    ),
    # Trung tính có chủ ý: không nói cảnh "lộ điều bạn chưa biết", vì câu đó đã cho biết có bí
    # mật (design §6.6: không úp mở về sự tồn tại của bí mật). D-26.
    ErrorCode.SCENE_LEAK_BLOCKED: PlayerMessage(
        "Cảnh vừa viết không qua được bước kiểm tra cuối nên hệ thống không hiện nó.",
        "Bấm thử lại để viết lại cảnh này.",
    ),
    # Hỏi người kể (design §6.6, D-40). Câu trung tính: không nói gì về điều người chơi chưa biết.
    ErrorCode.NARRATOR_QUESTION_EMPTY: PlayerMessage(
        "Bạn chưa viết câu hỏi nào.",
        "Viết điều bạn muốn hỏi người kể chuyện rồi gửi.",
    ),
    ErrorCode.NARRATOR_QUESTION_TOO_LONG: PlayerMessage(
        "Câu hỏi bạn viết dài hơn mức cho phép.",
        "Rút gọn câu hỏi rồi gửi lại.",
    ),
    ErrorCode.NARRATOR_LIMIT_REACHED: PlayerMessage(
        "Bạn đã dùng hết số câu hỏi người kể chuyện cho chương này.",
        "Đọc tiếp sang chương sau để hỏi thêm.",
    ),
    # Giới hạn tần suất của chính WriTory (G8, limits.rate_limit.llm_calls_per_minute_per_user),
    # khác LLM_RATE_LIMITED là giới hạn của OpenRouter với key người chơi.
    ErrorCode.WRITORY_RATE_LIMITED: PlayerMessage(
        "Bạn đang gửi yêu cầu nhanh hơn mức WriTory cho phép.",
        "Đợi khoảng một phút rồi thử lại.",
    ),
    # Khởi tạo truyện (D-39): kết quả model sai quy tắc. Không nói sai ở đâu, vì chi tiết có thể
    # nhắc tới bản kế hoạch ẩn (bí mật, khoảng lộ).
    ErrorCode.STORY_SETUP_INVALID: PlayerMessage(
        "Bước khởi tạo truyện vừa rồi cho ra kết quả không hợp lệ nên hệ thống chưa dùng và chưa "
        "lưu gì. Lỗi ở phía hệ thống, không phải do bạn.",
        "Bấm thử lại bước này. " + _REPORT,
    ),
    # Mức độ dài có trong config nhưng chưa mở cho người chơi (D-88). Không nêu tên mức: danh sách
    # mức mở nằm ở config, giao diện lấy từ /config/public.
    ErrorCode.STORY_LENGTH_NOT_OPEN: PlayerMessage(
        "Độ dài truyện bạn chọn chưa mở cho người chơi ở bản này.",
        "Tải lại trang rồi chọn một độ dài trong danh sách đang có.",
    ),
    # Cùng lý do trung tính như SCENE_LEAK_BLOCKED (D-37). Chương đã ghi xong trước bước này.
    # Kiểm duyệt đầu vào (G9, D-57). Một câu cho mọi loại: không nêu loại nội dung, không nhắc
    # lại chữ.
    ErrorCode.INPUT_BLOCKED: PlayerMessage(
        "Nội dung bạn vừa nhập thuộc loại WriTory không hỗ trợ nên hệ thống không dùng nó.",
        "Sửa lại nội dung rồi gửi lại.",
    ),
    ErrorCode.CHOICES_LEAK_BLOCKED: PlayerMessage(
        "Các lựa chọn vừa tạo không qua được bước kiểm tra cuối nên hệ thống không hiện chúng. "
        "Chương bạn vừa đọc đã được lưu.",
        "Bấm thử lại để tạo lựa chọn mới.",
    ),
    # Phiên khởi tạo truyện (design §4.1, D-44).
    ErrorCode.SETUP_NOT_FOUND: PlayerMessage(
        "Không tìm thấy phiên tạo truyện này.",
        "Bắt đầu tạo truyện mới.",
    ),
    ErrorCode.SETUP_STEP_NOT_READY: PlayerMessage(
        "Bước tạo truyện này chưa làm được: bước trước chưa xong, hoặc truyện đã được tạo từ "
        "phiên này.",
        "Tải lại trang để thấy bước hiện tại.",
    ),
    # Key người chơi dán vào (G7, D-45). Không nhắc lại chữ đã dán.
    ErrorCode.PLAYER_KEY_INVALID: PlayerMessage(
        "Chuỗi bạn dán không phải key OpenRouter (key OpenRouter bắt đầu bằng \"sk-or-\").",
        "Sao chép lại key từ trang openrouter.ai/keys rồi dán vào.",
    ),
    # Thân yêu cầu sai dạng (D-45). Không chép lại đầu vào, vì đầu vào có thể là key (G7).
    ErrorCode.REQUEST_INVALID: PlayerMessage(
        "Yêu cầu gửi lên không đúng dạng: thiếu trường, sai kiểu, hoặc giá trị nằm ngoài khoảng "
        "cho phép.",
        "Tải lại trang rồi thử lại. " + _REPORT,
    ),
    # Sửa nhân vật chính lúc khởi tạo (D-45): giới hạn trong config/limits.yaml `input`.
    ErrorCode.CHARACTER_EDIT_INVALID: PlayerMessage(
        "Tên, tính cách hoặc quá khứ bạn sửa đang để trống hoặc dài hơn mức cho phép.",
        "Sửa lại cho ngắn gọn rồi gửi.",
    ),
    # Chơi: lựa chọn, hành động, chương (D-46).
    ErrorCode.CHOICE_NOT_FOUND: PlayerMessage(
        "Không tìm thấy lựa chọn này trong chương hiện tại (có thể truyện đã sang chương khác).",
        "Tải lại trang để thấy các lựa chọn mới nhất.",
    ),
    ErrorCode.CHOICE_REQUIRED: PlayerMessage(
        "Bạn chưa chọn hành động cho chương tiếp theo.",
        "Chọn một lựa chọn hoặc tự viết hành động, rồi bấm viết tiếp.",
    ),
    ErrorCode.CHAPTER_NOT_FOUND: PlayerMessage(
        "Không tìm thấy chương này.",
        "Quay về truyện để đọc chương mới nhất.",
    ),
    ErrorCode.STORY_COMPLETE: PlayerMessage(
        "Truyện đã tới chương cuối.",
        "Bạn vẫn đọc lại được các chương đã có; muốn chơi tiếp thì bắt đầu truyện mới.",
    ),
    # Chống chạy đôi (G8, D-46): một truyện chỉ một lần viết, một phiên chỉ một lần chốt.
    ErrorCode.STORY_BUSY: PlayerMessage(
        "Truyện này đang được viết hoặc tạo ở một yêu cầu khác (có thể bạn mở nó ở hai nơi), "
        "nên hệ thống không chạy thêm lần nữa để khỏi trừ tiền key của bạn hai lần.",
        "Đợi việc đang chạy xong rồi tải lại trang.",
    ),
    # Đăng nhập bằng mã mời (D-89). Không nhắc lại mã hay token, không nói mã sai ở phần nào.
    ErrorCode.AUTH_REQUIRED: PlayerMessage(
        "Bạn chưa đăng nhập, hoặc phiên đăng nhập đã hết hạn hay đã bị đăng xuất.",
        "Vào trang đăng nhập và nhập mã mời của bạn.",
    ),
    ErrorCode.INVITE_CODE_INVALID: PlayerMessage(
        "Mã mời không đúng hoặc đã bị thu hồi.",
        "Chép lại nguyên mã mời (bắt đầu bằng \"wt-\") rồi thử lại; vẫn không được thì hỏi người "
        "đã mời bạn.",
    ),
    ErrorCode.LOGIN_RATE_LIMITED: PlayerMessage(
        "Máy này đã nhập mã mời quá nhiều lần trong thời gian ngắn nên tạm bị chặn.",
        "Đợi một lúc rồi thử lại; nếu vẫn bị chặn, hỏi người đã mời bạn.",
    ),
    # Chống CSRF (D-89): yêu cầu ghi không phải JSON cùng origin.
    ErrorCode.REQUEST_ORIGIN_INVALID: PlayerMessage(
        "Yêu cầu bị từ chối vì không được gửi từ trang WriTory.",
        "Mở WriTory trực tiếp, tải lại trang rồi thử lại.",
    ),
    # Lỗi của bộ định tuyến (`api/errors.py`, G12): đường dẫn không có, router của người chơi chưa
    # bật (D-41), sai phương thức. Không chép lại đường dẫn hay phương thức đã gửi.
    ErrorCode.ROUTE_NOT_FOUND: PlayerMessage(
        "Máy chủ không có chức năng ở địa chỉ vừa gọi.",
        "Mở WriTory từ trang chủ rồi thử lại. " + _REPORT,
    ),
    ErrorCode.METHOD_NOT_ALLOWED: PlayerMessage(
        "Máy chủ không nhận kiểu yêu cầu này ở địa chỉ vừa gọi.",
        "Tải lại trang rồi thử lại. " + _REPORT,
    ),
}


class WritoryError(Exception):
    """Lỗi có mã. `str()` dành cho log (đã xoá chuỗi giống key); người chơi nhận
    `player_payload()`.

    `fields`: đường dẫn các trường người chơi cần sửa (ví dụ "index", "tags.genre"), để giao diện
    chỉ đúng chỗ (G12). Chỉ là tên trường, không bao giờ là giá trị người chơi gửi lên (G7)."""

    def __init__(self, code: ErrorCode, detail: str = "", *,
                 fields: Sequence[str] = ()) -> None:
        self.code = code
        self.detail = redact(detail)
        self.fields = tuple(fields)
        super().__init__(f"{code.value}: {self.detail}" if self.detail else code.value)

    def player_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code.value, "message": MESSAGES[self.code].text()}
        if self.fields:
            payload["fields"] = list(self.fields)
        return payload
