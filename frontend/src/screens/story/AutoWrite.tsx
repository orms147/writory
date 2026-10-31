import { useId } from 'react';
import type { ApiError } from '../../api/errors';
import { ErrorBlock } from '../../components/ErrorBlock';
import { Button, Dots, cx } from '../../components/ui';
import { numberWords } from '../../lib/format';

// "Tự viết đến hết": nút bắt đầu, tiến độ và nút dừng. Tổng số chương của bản kế hoạch không lộ ra
// giao diện, nên tiến độ chỉ nói đã xong tới chương nào.

export function autoProgressText(written: number): string {
  return written >= 1 ? `Đang tự viết… đã xong chương ${numberWords(written)}` : 'Đang tự viết chương một…';
}

/** `running`: vòng tự viết đang chạy; `written`: số chương đã ghi; `error`: lỗi ngoài lần viết chương
 *  (lỗi của lần viết hiện ở giao diện lỗi của lần viết). */
export function AutoWriteBar({
  running,
  written,
  stopRequested,
  error,
  onStart,
  onStop,
  className,
}: {
  running: boolean;
  written: number;
  stopRequested: boolean;
  error: ApiError | null;
  onStart: () => void;
  onStop: () => void;
  className?: string;
}) {
  const hintId = useId();
  if (running) {
    return (
      <div className={cx('flex flex-wrap items-center gap-x-4 gap-y-2', className)}>
        <p role="status" className="flex items-center gap-2 text-[14px] text-ink-100">
          <Dots className="text-cinnabar-400" />
          {autoProgressText(written)}
        </p>
        <Button variant="ghost" onClick={onStop} disabled={stopRequested}>
          {stopRequested ? 'Sẽ dừng sau chương này' : 'Dừng sau chương này'}
        </Button>
      </div>
    );
  }
  if (error) {
    // "Thử lại" chạy tiếp vòng tự viết từ trạng thái máy chủ.
    return <ErrorBlock className={className} error={error} onRetry={onStart} />;
  }
  return (
    <div className={cx('flex flex-wrap items-center gap-x-3 gap-y-2', className)}>
      <Button variant="ghost" onClick={onStart} aria-describedby={hintId}>
        Tự viết đến hết
      </Button>
      <span id={hintId} className="text-[13px] text-ink-400">
        Không cần chọn: truyện tự đi theo kế hoạch tới chương cuối. Bỏ bước tạo lựa chọn nên rẻ hơn. Giữ trang này mở trong lúc viết.
      </span>
    </div>
  );
}

/** Cuối trang chương vừa ghi trong lúc tự viết: chương sau đang viết, xong thì hiện ở đây. */
export function AutoWritingFooter({ next }: { next: number }) {
  return (
    <div className="mt-10 flex flex-col items-center gap-2 border-t border-paper-400 pt-8 text-center">
      <span className="flex items-center gap-2.5 text-[14px] text-paper-800">
        <Dots className="text-cinnabar-600" />
        Chương {numberWords(next)} đang được viết
      </span>
      <span className="text-[13px] text-paper-700">Viết xong, chương mới sẽ hiện thay trang này.</span>
    </div>
  );
}
