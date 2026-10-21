import { useId, useState, type KeyboardEvent } from 'react';
import { api } from '../../api/client';
import type { EntryKind, NotebookEntry, NotebookLie, NotebookOut } from '../../api/types';
import { Drawer } from '../../components/Drawer';
import { ErrorBlock } from '../../components/ErrorBlock';
import { Skeleton, cx } from '../../components/ui';
import { useResource } from '../../lib/useResource';

// Sổ tay (D-/M-SoTay): chỉ `player_view` máy chủ trả (G1). Tab chỉ hiện khi có mục; Faction là
// "Phe phái"; Fact và Event chung "Sự thật" (D-65). Không vai trò, thái độ, "đang ở", sơ đồ, ghim.

export type NotebookTabId = 'people' | 'places' | 'items' | 'factions' | 'facts' | 'known_lies' | 'lies';

const ENTRY_TABS: { id: NotebookTabId; label: string; kinds: EntryKind[] }[] = [
  { id: 'people', label: 'Nhân vật', kinds: ['Character'] },
  { id: 'places', label: 'Nơi chốn', kinds: ['Location'] },
  { id: 'items', label: 'Đồ vật', kinds: ['Item'] },
  { id: 'factions', label: 'Phe phái', kinds: ['Faction'] },
  { id: 'facts', label: 'Sự thật', kinds: ['Fact', 'Event'] },
  // Nút Lie đã hé lộ (lời nói dối của người khác mà người chơi đã biết): chưa có quyết định chỗ
  // hiện; tách tab riêng để không lẫn vào "Sự thật" (D-68, câu hỏi mở).
  { id: 'known_lies', label: 'Lời nói dối đã biết', kinds: ['Lie'] },
];

export interface NotebookTab {
  id: NotebookTabId;
  label: string;
  entries: NotebookEntry[];
  lies: NotebookLie[];
}

/** Các tab có mục, theo thứ tự cố định. Tab rỗng không có trong danh sách. */
export function notebookTabs(book: NotebookOut): NotebookTab[] {
  const tabs: NotebookTab[] = [];
  for (const t of ENTRY_TABS) {
    const entries = book.entries.filter((e) => t.kinds.includes(e.kind));
    if (entries.length) tabs.push({ id: t.id, label: t.label, entries, lies: [] });
  }
  if (book.lies.length) tabs.push({ id: 'lies', label: 'Lời nói dối của tôi', entries: [], lies: book.lies });
  return tabs;
}

function EntryCard({ e }: { e: NotebookEntry }) {
  return (
    <li className="border-b border-ink-750 py-5">
      <div className="flex items-baseline justify-between gap-4">
        <h3 className="font-display text-[24px] font-semibold leading-tight md:text-[26px]">{e.text}</h3>
        <span className="flex-none text-[12px] text-ink-400">
          <span className="max-md:hidden">biết từ chương {e.since_chapter}</span>
          <span className="md:hidden">từ ch. {e.since_chapter}</span>
        </span>
      </div>
      {e.aliases.length > 0 && <p className="mt-1 text-[13px] text-ink-400">còn được gọi: {e.aliases.join(', ')}</p>}
      {e.quote && (
        <blockquote className="mt-3 border-l-2 border-ink-600 pl-4 font-reading text-[15px] italic leading-relaxed text-ink-100">
          “{e.quote}”
        </blockquote>
      )}
    </li>
  );
}

function LieCard({ lie }: { lie: NotebookLie }) {
  return (
    <li className="border-b border-ink-750 py-5">
      <p className="text-[13px] text-ink-400">
        Nói với {lie.told_to.join(', ')} · chương {lie.chapter}
      </p>
      <p className="mt-2 font-reading text-[16px] leading-relaxed text-ink-50">{lie.content}</p>
    </li>
  );
}

export function NotebookView({ book }: { book: NotebookOut }) {
  const tabs = notebookTabs(book);
  const [active, setActive] = useState<NotebookTabId | null>(null);
  const baseId = useId();
  const current = tabs.find((t) => t.id === active) ?? tabs[0] ?? null;

  if (!current) {
    return <p className="px-5 py-6 text-[14px] text-ink-400 md:px-6">Sổ tay ghi lại điều bạn đọc được trên trang.</p>;
  }

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const next = tabs[(i + d + tabs.length) % tabs.length];
    if (next) {
      setActive(next.id);
      document.getElementById(`${baseId}-tab-${next.id}`)?.focus();
    }
  };

  return (
    <>
      <div role="tablist" aria-label="Mục sổ tay" className="flex gap-2 overflow-x-auto border-b border-ink-750 px-5 md:gap-1 md:px-6">
        {tabs.map((t, i) => {
          const selected = t.id === current.id;
          return (
            <button
              key={t.id}
              id={`${baseId}-tab-${t.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`${baseId}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(t.id)}
              onKeyDown={(e) => onKey(e, i)}
              className={cx(
                'min-h-tap flex-none whitespace-nowrap px-3 text-[14px] font-medium',
                'max-md:my-2 max-md:rounded-full max-md:border max-md:px-4',
                'md:border-b-2',
                selected
                  ? 'text-ink-50 max-md:border-ink-50 max-md:bg-ink-50 max-md:text-ink-950 md:border-cinnabar-400'
                  : 'text-ink-400 max-md:border-ink-700 md:border-transparent',
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div id={`${baseId}-panel`} role="tabpanel" aria-labelledby={`${baseId}-tab-${current.id}`} className="px-5 md:px-6">
        <ul>
          {current.entries.map((e) => (
            <EntryCard key={e.ref} e={e} />
          ))}
          {current.lies.map((lie, i) => (
            <LieCard key={`${lie.chapter}-${i}`} lie={lie} />
          ))}
        </ul>
      </div>
    </>
  );
}

export function NotebookPanel({
  storyId,
  chapter,
  open,
  onClose,
  onAskNarrator,
}: {
  storyId: string;
  chapter: number;
  open: boolean;
  onClose: () => void;
  onAskNarrator: () => void;
}) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      kicker="Sổ tay"
      title="Những gì bạn đã biết"
      footer={
        <div className="flex items-center justify-between gap-4 text-[13px]">
          <span className="text-ink-400">Chỉ ghi điều đã hiện trên trang.</span>
          <button type="button" onClick={onAskNarrator} className="wt-link inline-flex min-h-tap items-center font-semibold text-cinnabar-400">
            Hỏi người kể →
          </button>
        </div>
      }
    >
      {open && <NotebookBody storyId={storyId} chapter={chapter} />}
    </Drawer>
  );
}

function NotebookBody({ storyId, chapter }: { storyId: string; chapter: number }) {
  const res = useResource(() => api.notebook(storyId), `${storyId}:${chapter}`);
  if (res.error) {
    return (
      <div className="p-5 md:p-6">
        <ErrorBlock error={res.error} onRetry={res.reload} />
      </div>
    );
  }
  if (!res.data) {
    return (
      <div className="flex flex-col gap-4 p-5 md:p-6" aria-busy="true">
        <Skeleton className="h-7 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }
  return <NotebookView book={res.data} />;
}
