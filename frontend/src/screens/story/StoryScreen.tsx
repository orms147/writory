import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router';
import { api } from '../../api/client';
import { ApiError, asApiError } from '../../api/errors';
import type { StoryOut } from '../../api/types';
import { ErrorBlock } from '../../components/ErrorBlock';
import { Button, Skeleton } from '../../components/ui';
import { lengthText, useStoryLength } from '../../config/PublicConfig';
import { errorGroup } from '../../lib/errorGroups';
import { useResource } from '../../lib/useResource';
import { clearRun, isRunning, startRun, useChapterRun, type ChapterRunState } from '../../state/chapterRun';
import { ScriptDownload } from './AudioScript';
import { ChapterPage, type Writing } from './ChapterPage';
import { ChoicePanel } from './ChoicePanel';
import { Finished } from './Finished';
import { NarratorPanel } from './NarratorPanel';
import { NotebookPanel } from './NotebookPanel';
import { MobileReaderBar, READING_CLASS, READING_SIZES, ReaderHeader, type ReadingSize } from './ReaderChrome';
import { Waiting } from './Waiting';

const SIZE_KEY = 'wt-reading-size';

/** Cỡ chữ trang đọc: tiện ích riêng của người xem, lưu ở trình duyệt nếu được (không phải dữ liệu
 *  truyện). */
export function useReadingSize(): [ReadingSize, () => void] {
  const [size, setSize] = useState<ReadingSize>(() => {
    try {
      const v = window.localStorage.getItem(SIZE_KEY);
      return READING_SIZES.includes(v as ReadingSize) ? (v as ReadingSize) : 'md';
    } catch {
      return 'md';
    }
  });
  const cycle = useCallback(() => {
    setSize((s) => {
      const next = READING_SIZES[(READING_SIZES.indexOf(s) + 1) % READING_SIZES.length] ?? 'md';
      try {
        window.localStorage.setItem(SIZE_KEY, next);
      } catch {
        /* không lưu được thì thôi */
      }
      return next;
    });
  }, []);
  return [size, cycle];
}

/** Nhãn "đang viết" ở cuối trang: bước gần nhất máy chủ gửi sau cảnh cuối đã hiện. */
export function currentWriting(run: ChapterRunState): Writing | null {
  if (run.status !== 'running') return null;
  const last = run.stages[run.stages.length - 1];
  if (!last) return null;
  const lastScene = run.scenes.reduce((m, s) => Math.max(m, s.scene), 0);
  if (last.scene !== null && last.scene > lastScene) return { scene: last.scene, label: last.label };
  if (last.scene !== null) return null; // cảnh vừa hiện, chưa có bước kế
  return { scene: null, label: last.label };
}

interface NavState {
  autostart?: boolean;
  chosen?: string | null;
}

export function StoryScreen() {
  const { id = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const nav = (location.state as NavState | null) ?? null;

  const story = useResource(() => api.story(id), `story:${id}`);
  const list = useResource(() => api.stories(), `stories:${id}`);
  const costs = useResource(() => api.costs(), `costs:${id}`);
  const run = useChapterRun(id);
  const [notebookOpen, setNotebookOpen] = useState(false);
  const [narratorOpen, setNarratorOpen] = useState(false);
  const [size, cycleSize] = useReadingSize();

  const summary = list.data?.stories.find((s) => s.story_id === id) ?? null;
  const level = useStoryLength(story.data?.length_level ?? summary?.length_level ?? '');
  const title = summary?.title ?? '';
  const sub = lengthText(level, summary?.length_label);
  const spent = costs.data?.stories.find((s) => s.story_id === id)?.spent_usd ?? null;

  // Tự viết chỉ khi người chơi vừa bấm (chốt khởi tạo, chọn hướng); mở lại trang thì không gọi model.
  const autostarted = useRef(false);
  useEffect(() => {
    if (!nav?.autostart || autostarted.current || !story.data) return;
    autostarted.current = true;
    if (story.data.next_ready && !isRunning(id)) {
      startRun(id, story.data.chapter + 1, nav.chosen ?? story.data.action?.text ?? null);
    }
    navigate(location.pathname, { replace: true, state: null });
  }, [nav, story.data, id, navigate, location.pathname]);

  // Chương vừa ghi: cập nhật chi phí đã dùng.
  const committed = run?.committed ?? false;
  const reloadCosts = costs.reload;
  useEffect(() => {
    if (committed) reloadCosts();
  }, [committed, reloadCosts]);

  const refresh = useCallback(() => {
    clearRun(id);
    story.reload();
    list.reload();
    costs.reload();
  }, [id, story, list, costs]);

  const begin = useCallback(
    (data: StoryOut, chosen: string | null) => {
      startRun(id, data.chapter + 1, chosen);
    },
    [id],
  );

  /** Thử lại sau lỗi của lần viết. Chương đã ghi thì chỉ lấy lại trạng thái (lựa chọn tạo lại
   *  được); chưa ghi thì viết lại chương từ đầu (máy chủ không giữ gì của lần lỗi, D-6). */
  const retryRun = useCallback(async () => {
    if (!run) return;
    if (run.committed) return refresh();
    if (run.error && errorGroup(run.error.code) === 'network') {
      try {
        const fresh = await api.story(id);
        if (fresh.chapter >= run.chapter) return refresh();
      } catch {
        return; // vẫn mất mạng: giữ nguyên chữ đã hiện
      }
    }
    const chosen = run.chosen;
    const chapter = run.chapter;
    clearRun(id);
    startRun(id, chapter, chosen);
  }, [run, id, refresh]);

  if (story.error) {
    return (
      <main className="wt relative grid min-h-screen place-items-center px-4">
        <div className="w-full max-w-[520px]">
          <ErrorBlock error={story.error} onRetry={story.reload} />
        </div>
      </main>
    );
  }
  if (!story.data) {
    return (
      <main className="wt relative min-h-screen px-4 pt-6 md:px-[100px]" aria-busy="true">
        <Skeleton className="h-6 w-48" />
      </main>
    );
  }
  const data = story.data;

  const chapterShown = run ? run.chapter : data.chapter;
  // Số chương đã ghi: kịch bản audio chỉ gồm chương đã ghi.
  const committedChapters = run?.committed ? run.chapter : data.chapter;
  const script = (className?: string) =>
    data.style === 'audio' ? <ScriptDownload storyId={id} chapters={committedChapters} className={className} /> : null;
  const panels = (
    <>
      <NotebookPanel
        storyId={id}
        chapter={run?.committed ? run.chapter : data.chapter}
        open={notebookOpen}
        onClose={() => setNotebookOpen(false)}
        onAskNarrator={() => {
          setNotebookOpen(false);
          setNarratorOpen(true);
        }}
      />
      <NarratorPanel
        storyId={id}
        chapter={run?.committed ? run.chapter : data.chapter}
        open={narratorOpen}
        onClose={() => setNarratorOpen(false)}
      />
    </>
  );

  // --- đang viết, chưa có cảnh nào: màn chờ ---------------------------------------------------
  if (run && run.scenes.length === 0) {
    const err = run.error ?? (run.blocked ? new ApiError({ code: run.blocked.code, message: run.blocked.message }) : null);
    return (
      <Waiting
        title={title}
        chapter={run.chapter}
        stages={run.stages}
        startedAt={run.startedAt}
        chosen={run.chosen}
        error={err}
        idle={false}
        handlers={{ onRetry: () => void retryRun(), onReload: refresh, onBackToChoices: refresh }}
        extra={script('justify-end')}
      />
    );
  }

  if (!run && data.finished) {
    return (
      <Finished
        storyId={id}
        title={title}
        meta={summary?.length_label ?? ''}
        lastExcerpt={summary?.last_excerpt ?? null}
        chapters={data.chapter}
        spentUsd={spent}
        extra={script('justify-center')}
      />
    );
  }

  if (!run && data.chapter === 0) {
    return (
      <Waiting
        title={title}
        chapter={1}
        stages={[]}
        startedAt={null}
        chosen={null}
        error={null}
        idle={data.next_ready}
        onStart={() => begin(data, null)}
        handlers={{ onReload: refresh }}
        extra={script('justify-end')}
      />
    );
  }

  return (
    <div className="wt relative min-h-screen pb-28 md:pb-0">
      <ReaderHeader
        title={title}
        chapter={chapterShown}
        sub={sub}
        spentUsd={spent}
        onNotebook={() => setNotebookOpen(true)}
        onNarrator={() => setNarratorOpen((o) => !o)}
        onCycleSize={cycleSize}
        narratorOpen={narratorOpen}
      />
      {data.style === 'audio' && <div className="px-4 pt-3 md:px-5">{script('mx-auto max-w-reading')}</div>}
      <div className="px-0 pt-0 md:px-5 md:pt-9">
        {run ? (
          <RunPage
            run={run}
            storyId={id}
            sizeClass={READING_CLASS[size]}
            spent={spent}
            onRetry={() => void retryRun()}
            onRefresh={refresh}
            onChosen={(text) => {
              const next = run.chapter + 1;
              clearRun(id);
              startRun(id, next, text);
            }}
            onNotebook={() => setNotebookOpen(true)}
            onNarrator={() => setNarratorOpen(true)}
          />
        ) : (
          <StaticPage
            story={data}
            sizeClass={READING_CLASS[size]}
            spent={spent}
            onReload={story.reload}
            onChosen={(text) => begin(data, text)}
            onNotebook={() => setNotebookOpen(true)}
            onNarrator={() => setNarratorOpen(true)}
          />
        )}
      </div>
      <MobileReaderBar spentUsd={spent} onNotebook={() => setNotebookOpen(true)} onNarrator={() => setNarratorOpen(true)} />
      {panels}
    </div>
  );
}

function RunPage({
  run,
  storyId,
  sizeClass,
  spent,
  onRetry,
  onRefresh,
  onChosen,
  onNotebook,
  onNarrator,
}: {
  run: ChapterRunState;
  storyId: string;
  sizeClass: string;
  spent: number | null;
  onRetry: () => void;
  onRefresh: () => void;
  onChosen: (text: string) => void;
  onNotebook: () => void;
  onNarrator: () => void;
}) {
  const scenes = [...run.scenes].sort((a, b) => a.scene - b.scene).map((s) => s.text);
  const blocked = run.blocked ? new ApiError({ code: run.blocked.code, message: run.blocked.message }) : null;
  const error = run.error;
  const network = error && errorGroup(error.code) === 'network';

  let footer = null;
  if (blocked) {
    footer = <ErrorBlock className="mt-10" tone="paper" error={blocked} onRetry={onRetry} onBackToChoices={onRefresh} />;
  } else if (error && !network) {
    footer = (
      <ErrorBlock className="mt-10" tone="paper" sheetOnMobile error={error} onRetry={onRetry} onReload={onRefresh} onBackToChoices={onRefresh} />
    );
  } else if (run.choices) {
    footer = <ChoicePanel storyId={storyId} chapter={run.chapter} choices={run.choices} spentUsd={spent} chosenBefore={null} onChosen={onChosen} />;
  } else if (run.finished) {
    footer = <StoryEnd onClose={onRefresh} />;
  }

  return (
    <>
      <ChapterPage
        revealKey={`${storyId}:${run.chapter}:${run.startedAt}`}
        chapter={run.chapter}
        scenes={scenes}
        live
        writing={currentWriting(run)}
        sizeClass={sizeClass}
        footer={footer}
        onNotebook={onNotebook}
        onNarrator={onNarrator}
      />
      {network && error && (
        <div role="alert" className="fixed inset-x-0 bottom-0 z-40 border-t border-ink-700 bg-ink-900 px-4 py-3 md:bottom-0">
          <div className="mx-auto flex max-w-reading flex-wrap items-center justify-between gap-3">
            <p className="text-[14px] text-ink-100">{error.message}</p>
            <Button onClick={onRetry}>Thử lại ngay</Button>
          </div>
        </div>
      )}
    </>
  );
}

function StoryEnd({ onClose }: { onClose: () => void }) {
  return (
    <div className="mt-12 flex flex-col items-center gap-4 border-t border-paper-400 pt-10 text-center">
      <span className="grid h-16 w-16 -rotate-6 place-items-center rounded-[12px] border-2 border-cinnabar-600 font-display text-[22px] font-semibold text-cinnabar-600">
        Hết
      </span>
      <p className="text-[14px] text-paper-700">Truyện đã khép ở chương này.</p>
      <Button onClick={onClose} arrow>
        Khép truyện
      </Button>
    </div>
  );
}

function StaticPage({
  story,
  sizeClass,
  spent,
  onReload,
  onChosen,
  onNotebook,
  onNarrator,
}: {
  story: StoryOut;
  sizeClass: string;
  spent: number | null;
  onReload: () => void;
  onChosen: (text: string) => void;
  onNotebook: () => void;
  onNarrator: () => void;
}) {
  const chapter = useResource(() => api.chapter(story.story_id, story.chapter), `${story.story_id}:${story.chapter}`);
  const [regen, setRegen] = useState<{ busy: boolean; error: ApiError | null }>({ busy: false, error: null });

  if (chapter.error) {
    return (
      <div className="mx-auto max-w-reading px-4 py-10">
        <ErrorBlock error={chapter.error} onRetry={chapter.reload} />
      </div>
    );
  }
  if (!chapter.data) {
    return (
      <div className="mx-auto flex max-w-reading flex-col gap-3 px-6 py-10" aria-busy="true">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  const regenerate = async () => {
    setRegen({ busy: true, error: null });
    try {
      await api.choices(story.story_id);
      onReload();
    } catch (err) {
      setRegen({ busy: false, error: asApiError(err) });
    }
  };

  let footer;
  if (story.choices.length > 0) {
    footer = (
      <ChoicePanel
        storyId={story.story_id}
        chapter={story.chapter}
        choices={story.choices}
        spentUsd={spent}
        chosenBefore={story.action?.text ?? null}
        onChosen={onChosen}
      />
    );
  } else {
    footer = (
      <div className="mt-10 flex flex-col items-center gap-3 border-t border-paper-400 pt-8 text-center">
        <p className="text-[14px] text-paper-700">Chương này chưa có lựa chọn.</p>
        <Button onClick={regenerate} disabled={regen.busy}>
          {regen.busy ? 'Đang nghĩ lựa chọn…' : 'Tạo lựa chọn'}
        </Button>
        {regen.error && <ErrorBlock className="mt-3 w-full" tone="paper" error={regen.error} onRetry={regenerate} onReload={onReload} />}
      </div>
    );
  }

  return (
    <ChapterPage
      revealKey={`${story.story_id}:${story.chapter}:static`}
      chapter={story.chapter}
      scenes={chapter.data.scenes}
      live={false}
      writing={null}
      sizeClass={sizeClass}
      footer={footer}
      onNotebook={onNotebook}
      onNarrator={onNarrator}
    />
  );
}
