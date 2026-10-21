import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '../../api/client';
import { ErrorBlock } from '../../components/ErrorBlock';
import { Skeleton } from '../../components/ui';
import { lengthText, useStoryLength } from '../../config/PublicConfig';
import { useResource } from '../../lib/useResource';
import { ChapterPage } from './ChapterPage';
import { NarratorPanel } from './NarratorPanel';
import { NotebookPanel } from './NotebookPanel';
import { MobileReaderBar, READING_CLASS, ReaderHeader } from './ReaderChrome';
import { useReadingSize } from './StoryScreen';

/** Đọc lại một chương đã ghi (`GET /stories/{id}/chapters/{n}`), không gọi model. */
export function ReadBack() {
  const { id = '', n = '1' } = useParams();
  const number = Math.max(1, Number.parseInt(n, 10) || 1);
  const story = useResource(() => api.story(id), `story:${id}`);
  const list = useResource(() => api.stories(), 'stories');
  const chapter = useResource(() => api.chapter(id, number), `${id}:${number}`);
  const [size, cycleSize] = useReadingSize();
  const [notebookOpen, setNotebookOpen] = useState(false);
  const [narratorOpen, setNarratorOpen] = useState(false);
  const summary = list.data?.stories.find((s) => s.story_id === id) ?? null;
  const level = useStoryLength(story.data?.length_level ?? '');
  const last = story.data?.chapter ?? number;
  const base = `/truyen/${encodeURIComponent(id)}`;

  const nav = (
    <nav aria-label="Chương" className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-paper-400 pt-6 text-[14px] font-semibold">
      {number > 1 ? (
        <Link className="wt-link inline-flex min-h-tap items-center" to={`${base}/chuong/${number - 1}`}>
          ← Chương {number - 1}
        </Link>
      ) : (
        <span />
      )}
      {number < last ? (
        <Link className="wt-link inline-flex min-h-tap items-center" to={`${base}/chuong/${number + 1}`}>
          Chương {number + 1} →
        </Link>
      ) : (
        <Link className="wt-link inline-flex min-h-tap items-center" to={base}>
          Về trang truyện →
        </Link>
      )}
    </nav>
  );

  return (
    <div className="wt relative min-h-screen pb-28 md:pb-0">
      <ReaderHeader
        title={summary?.title ?? ''}
        chapter={number}
        sub={lengthText(level, summary?.length_label)}
        spentUsd={null}
        onNotebook={() => setNotebookOpen(true)}
        onNarrator={() => setNarratorOpen((o) => !o)}
        onCycleSize={cycleSize}
        narratorOpen={narratorOpen}
      />
      <div className="md:px-5 md:pt-9">
        {chapter.error ? (
          <div className="mx-auto max-w-reading px-4 py-10">
            <ErrorBlock error={chapter.error} onRetry={chapter.reload} />
          </div>
        ) : !chapter.data ? (
          <div className="mx-auto flex max-w-reading flex-col gap-3 px-6 py-10" aria-busy="true">
            <Skeleton className="h-8 w-1/2" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : (
          <ChapterPage
            key={number}
            revealKey={`${id}:${number}:readback`}
            chapter={number}
            scenes={chapter.data.scenes}
            live={false}
            writing={null}
            sizeClass={READING_CLASS[size]}
            footer={nav}
            onNotebook={() => setNotebookOpen(true)}
            onNarrator={() => setNarratorOpen(true)}
          />
        )}
      </div>
      <MobileReaderBar spentUsd={null} onNotebook={() => setNotebookOpen(true)} onNarrator={() => setNarratorOpen(true)} />
      <NotebookPanel
        storyId={id}
        chapter={last}
        open={notebookOpen}
        onClose={() => setNotebookOpen(false)}
        onAskNarrator={() => {
          setNotebookOpen(false);
          setNarratorOpen(true);
        }}
      />
      <NarratorPanel storyId={id} chapter={last} open={narratorOpen} onClose={() => setNarratorOpen(false)} />
    </div>
  );
}
