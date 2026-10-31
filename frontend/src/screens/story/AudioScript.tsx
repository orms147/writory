import { useId, useState } from 'react';
import { api } from '../../api/client';
import { asApiError, type ApiError } from '../../api/errors';
import { Button, cx } from '../../components/ui';
import { saveTextFile } from '../../lib/download';

// Truyện kiểu kịch bản audio: nhãn và nút tải kịch bản .txt (văn mọi chương đã ghi). Truyện chữ
// không hiện gì ở đây.

export function AudioBadge({ label, className }: { label: string; className?: string }) {
  return (
    <span
      className={cx(
        'inline-flex items-center whitespace-nowrap rounded-full border border-cinnabar-400/60 px-2.5 py-0.5 text-[12px] font-medium text-cinnabar-100',
        className,
      )}
    >
      {label}
    </span>
  );
}

/** `chapters`: số chương đã ghi; chưa có chương nào thì nút tắt kèm lý do. */
export function ScriptDownload({ storyId, chapters, className }: { storyId: string; chapters: number; className?: string }) {
  const reasonId = useId();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const empty = chapters < 1;

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      const text = await api.script(storyId);
      saveTextFile(`${storyId}.txt`, text);
    } catch (err) {
      setError(asApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={cx('flex flex-wrap items-center gap-x-3 gap-y-2', className)}>
      <AudioBadge label="Kịch bản audio" />
      <Button variant="ghost" onClick={download} disabled={empty || busy} aria-describedby={empty ? reasonId : undefined}>
        {busy ? 'Đang tải kịch bản…' : 'Tải kịch bản (.txt)'}
      </Button>
      {empty && (
        <span id={reasonId} className="text-[13px] text-ink-400">
          Chưa có chương nào để tải.
        </span>
      )}
      {error && (
        <p role="alert" className="w-full text-[13px] text-cinnabar-200">
          {error.message}
        </p>
      )}
    </div>
  );
}
