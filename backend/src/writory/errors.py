"""Danh mục mã lỗi trả người chơi (G12).

Mỗi mã có câu tiếng Việt: chuyện gì xảy ra và làm gì tiếp. Chi tiết kỹ thuật (`detail`)
chỉ để ghi log, không bao giờ vào phản hồi cho người chơi.
"""

from dataclasses import dataclass
from enum import StrEnum

from writory.safety.redact import redact


class ErrorCode(StrEnum):
    CONFIG_LIMIT_NOT_SET = "CONFIG_LIMIT_NOT_SET"
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
    LLM_BAD_RESPONSE = "LLM_BAD_RESPONSE"
    PLAYER_KEY_MISSING = "PLAYER_KEY_MISSING"
    PLAYER_KEY_UNREADABLE = "PLAYER_KEY_UNREADABLE"
    STORY_NOT_FOUND = "STORY_NOT_FOUND"
    CHAPTER_SAVE_FAILED = "CHAPTER_SAVE_FAILED"
    CHAPTER_PENDING = "CHAPTER_PENDING"
    CHAPTER_OUT_OF_ORDER = "CHAPTER_OUT_OF_ORDER"
    CHAPTER_PACKAGE_INVALID = "CHAPTER_PACKAGE_INVALID"
    ACTION_EMPTY = "ACTION_EMPTY"
    ACTION_TOO_LONG = "ACTION_TOO_LONG"
    ACTION_OUT_OF_STORY = "ACTION_OUT_OF_STORY"
    ACTION_FORBIDDEN = "ACTION_FORBIDDEN"
    ACTION_UNCLEAR = "ACTION_UNCLEAR"


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
    ErrorCode.COST_LIMIT_SCENE: PlayerMessage(
        "Cảnh này đã chạm trần chi phí cho một cảnh nên hệ thống dừng viết.",
        "Bấm thử lại để viết lại cảnh từ đầu, hoặc chọn mức model rẻ hơn.",
    ),
    ErrorCode.COST_LIMIT_CHAPTER: PlayerMessage(
        "Chương này đã chạm trần chi phí cho một chương nên hệ thống dừng viết.",
        "Bấm thử lại để viết lại chương, hoặc chọn mức model rẻ hơn.",
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
}


class WritoryError(Exception):
    """Lỗi có mã. `str()` dành cho log (đã xoá chuỗi giống key); người chơi nhận
    `player_payload()`."""

    def __init__(self, code: ErrorCode, detail: str = "") -> None:
        self.code = code
        self.detail = redact(detail)
        super().__init__(f"{code.value}: {self.detail}" if self.detail else code.value)

    def player_payload(self) -> dict[str, str]:
        return {"code": self.code.value, "message": MESSAGES[self.code].text()}
