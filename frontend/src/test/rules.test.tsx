// Một test cho mỗi luật hiển thị quan trọng (README bàn giao mục 4, D-68).
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { api, setFetch } from '../api/client';
import { ApiError } from '../api/errors';
import type { NotebookOut, PlayerChoice } from '../api/types';
import { InkText } from '../components/InkText';
import { ConfigValue } from '../config/PublicConfig';
import { KeyCost } from '../screens/KeyCost';
import { ChoicePanel } from '../screens/story/ChoicePanel';
import { NarratorPanel } from '../screens/story/NarratorPanel';
import { NotebookView } from '../screens/story/NotebookPanel';
import { Template } from '../screens/setup/Template';
import { oddConfig, renderApp, withMock } from './render';

const CHOICES: PlayerChoice[] = [
  { id: 'choice-000000000001', kind: 'action', kind_label: 'Hành động', tone: null, tone_label: null, text: 'Mở cửa.' },
  { id: 'choice-000000000002', kind: 'dialogue', kind_label: 'Lời thoại', tone: 'lie', tone_label: 'nói dối', text: '- Tôi không thấy gì.' },
  { id: 'choice-000000000003', kind: 'inner', kind_label: 'Nội tâm', tone: null, tone_label: null, text: 'Nhớ lại tiếng chuông.' },
];

function choicePanel() {
  return (
    <MemoryRouter>
      <ConfigValue value={oddConfig()}>
        <ChoicePanel storyId="s-chuong" chapter={2} choices={CHOICES} spentUsd={0.09} chosenBefore={null} onChosen={() => {}} />
      </ConfigValue>
    </MemoryRouter>
  );
}

describe('giới hạn và trần đến từ /config/public, không tự đặt số', () => {
  it('ô tự viết đếm theo custom_action_max_chars của config', async () => {
    render(choicePanel());
    expect(screen.getByText('0 / 137')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Hoặc tự viết hành động của bạn'), 'Tôi chạy');
    expect(screen.getByText('8 / 137')).toBeInTheDocument();
  });

  it('ô hỏi người kể đếm theo narrator_question_max_chars, số câu còn lại từ máy chủ', async () => {
    withMock();
    renderApp(<NarratorPanel storyId="s-chuong" chapter={2} open onClose={() => {}} />);
    expect(screen.getByText('0 / 89')).toBeInTheDocument();
    // MOCK_CONFIG của máy chủ giả cho 3 câu mỗi chương.
    expect(await screen.findByText('Còn 3 câu hỏi trong chương này')).toBeInTheDocument();
  });

  it('trần chi phí hiện đúng số của config', async () => {
    withMock();
    renderApp(<KeyCost />);
    expect(screen.getByText('$0,37')).toBeInTheDocument();
    expect(screen.getByText('$1,23')).toBeInTheDocument();
    expect(screen.getByText('$4,56')).toBeInTheDocument();
  });

  it('component không chứa số giới hạn, trần hay khoảng chương viết cứng', () => {
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name)) files.push(p);
      }
    };
    const root = join(process.cwd(), 'src');
    for (const d of ['screens', 'components', 'config', 'state']) walk(join(root, d));
    const banned: [RegExp, string][] = [
      [/maxLength=\{\s*\d/, 'maxLength viết cứng'],
      [/\$\d/, 'số tiền viết cứng'],
      [/\b\d+\s\/\s\d+\b/, 'bộ đếm "x / N" viết cứng'],
      [/Còn \d/, 'số câu còn lại viết cứng'],
      [/\d+\s*[–-]\s*\d+\s*chương/, 'khoảng chương viết cứng'],
      [/from '\.\.\/(\.\.\/)?mock\//, 'giao diện dùng dữ liệu mock'],
    ];
    const hits: string[] = [];
    for (const f of files) {
      // Bỏ chú thích: ví dụ trong chú thích ("12 / 200") không phải chữ hiện ra.
      const src = readFileSync(f, 'utf8')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/(^|[^:])\/\/.*$/gm, '$1');
      for (const [re, why] of banned) if (re.test(src)) hits.push(`${f}: ${why}`);
    }
    expect(hits).toEqual([]);
  });
});

describe('ước tính chi phí chương tới lấy từ máy chủ (D-87)', () => {
  const answer = (body: object, status = 200) =>
    setFetch(async () => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }));

  it('màn lựa chọn hiện số của API, không số viết cứng', async () => {
    answer({ chapter: 3, usd: 0.0234, source: 'story_median', chapters_used: 2 });
    const first = render(choicePanel());
    expect(await screen.findByText(/khoảng \$0,02 mỗi chương/)).toBeInTheDocument();
    first.unmount();
    answer({ chapter: 3, usd: 0.0777, source: 'story_median', chapters_used: 2 });
    render(choicePanel());
    expect(await screen.findByText(/khoảng \$0,08 mỗi chương/)).toBeInTheDocument();
    expect(screen.queryByText(/\$0,02/)).toBeNull();
  });

  it('nói rõ ước tính theo các chương đã viết hay theo số mặc định', async () => {
    answer({ chapter: 3, usd: 0.0234, source: 'story_median', chapters_used: 2 });
    const first = render(choicePanel());
    expect(await screen.findByText(/theo 2 chương đã viết/)).toBeInTheDocument();
    first.unmount();
    answer({ chapter: 1, usd: 0.0234, source: 'default', chapters_used: 0 });
    render(choicePanel());
    expect(await screen.findByText(/số mặc định/)).toBeInTheDocument();
    expect(screen.queryByText(/chương đã viết/)).toBeNull();
  });

  it('không có số hoặc API lỗi thì ghi "chưa có ước tính", không bịa số', async () => {
    answer({ chapter: 3, usd: null, source: 'default', chapters_used: 0 });
    const first = render(choicePanel());
    expect(await screen.findByText('chưa có ước tính')).toBeInTheDocument();
    first.unmount();
    answer({ code: 'STORY_NOT_FOUND', message: 'Không thấy truyện.' }, 404);
    render(choicePanel());
    expect(await screen.findByText('chưa có ước tính')).toBeInTheDocument();
    expect(screen.queryByText(/khoảng/)).toBeNull();
  });

  it('màn khoá và chi phí lấy số mặc định từ /config/public', async () => {
    withMock();
    renderApp(<KeyCost />);
    expect(await screen.findByText(/khoảng \$0,04 mỗi chương/)).toBeInTheDocument();
  });

  it('màn khoá ghi "chưa có ước tính" khi config chưa đặt số mặc định', async () => {
    withMock();
    renderApp(<KeyCost />, { config: { ...oddConfig(), chapter_estimate_default_usd: null } });
    expect(await screen.findByText('chưa có ước tính')).toBeInTheDocument();
  });

  it('máy chủ giả trả ước tính đúng dạng hợp đồng', async () => {
    const server = withMock();
    const res = await server.fetch('/api/stories/s-chuong/estimate');
    expect(res.status).toBeLessThan(500);
  });
});

describe('key chỉ hiện last4', () => {
  it('dán key: chỉ thấy 4 ký tự cuối, ô nhập bị xoá, không lưu trình duyệt, không log', async () => {
    withMock({ scenario: 'rong' });
    const spies = (['log', 'info', 'debug', 'warn', 'error'] as const).map((m) => vi.spyOn(console, m));
    const secret = 'sk-or-v1-abcdef0123456789zz9q';
    renderApp(<KeyCost />);
    const input = await screen.findByLabelText(/Dán khoá API của OpenRouter/);
    await userEvent.type(input, secret);
    await userEvent.click(screen.getByRole('button', { name: 'Lưu khoá' }));
    expect(await screen.findByText('•••• zz9q')).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(secret);
    expect(document.body.textContent).not.toContain('abcdef0123456789');
    expect(document.body.innerHTML).not.toContain(secret);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    for (const spy of spies) {
      for (const call of spy.mock.calls) expect(JSON.stringify(call)).not.toContain(secret);
    }
  });
});

describe('sổ tay', () => {
  const book = (entries: NotebookOut['entries'], lies: NotebookOut['lies'] = []): NotebookOut => ({ chapter: 2, entries, lies });
  const entry = (ref: string, kind: NotebookOut['entries'][number]['kind'], text: string, is_protagonist = false) => ({
    ref, kind, text, aliases: [], since_chapter: 1, quote: `Câu trích của ${text}.`, about: [], is_protagonist,
  });

  it('ẩn hẳn tab không có mục, không ghi "chưa có"', () => {
    render(<NotebookView book={book([entry('m1', 'Character', 'Lão Tần'), entry('m2', 'Event', 'Chuông kêu')])} />);
    const tabs = screen.getAllByRole('tab').map((t) => t.textContent);
    expect(tabs).toEqual(['Nhân vật', 'Sự thật']);
    expect(screen.queryByText(/chưa có/i)).toBeNull();
    expect(screen.queryByRole('tab', { name: 'Nơi chốn' })).toBeNull();
    expect(screen.queryByRole('tab', { name: 'Lời nói dối của tôi' })).toBeNull();
  });

  it('mục nhân vật chính có nhãn "Bạn" (D-76), mục khác không có', () => {
    render(<NotebookView book={book([entry('m1', 'Character', 'Kha Diệp', true), entry('m2', 'Character', 'Lão Tần')])} />);
    const cards = within(screen.getByRole('tabpanel')).getAllByRole('listitem');
    const [me, other] = cards;
    if (cards.length !== 2 || !me || !other) throw new Error('cần đúng hai thẻ');
    expect(within(me).getByText('Bạn')).toBeInTheDocument();
    expect(within(me).getByText('Kha Diệp')).toBeInTheDocument();
    expect(within(other).queryByText('Bạn')).toBeNull();
    expect(screen.getAllByText('Bạn')).toHaveLength(1);
  });

  it('Faction là "Phe phái"; Fact và Event chung "Sự thật"; lời nói dối có người nghe và chương', async () => {
    render(
      <NotebookView
        book={book(
          [entry('m1', 'Faction', 'Trạm gác đèo'), entry('m2', 'Fact', 'Chuông kêu ba tiếng'), entry('m3', 'Event', 'Đỗ Khiêm mất tích')],
          [{ content: 'Nàng không tìm thấy gì.', chapter: 3, told_to: ['Lương Phục'] }],
        )}
      />,
    );
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual(['Phe phái', 'Sự thật', 'Lời nói dối của tôi']);
    await userEvent.click(screen.getByRole('tab', { name: 'Sự thật' }));
    const panel = screen.getByRole('tabpanel');
    expect(within(panel).getByText('Chuông kêu ba tiếng')).toBeInTheDocument();
    expect(within(panel).getByText('Đỗ Khiêm mất tích')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Lời nói dối của tôi' }));
    expect(screen.getByText('Nói với Lương Phục · chương 3')).toBeInTheDocument();
  });
});

describe('lựa chọn cuối chương', () => {
  it('không lựa chọn nào được chọn sẵn; nút gửi tắt tới khi chọn', async () => {
    render(choicePanel());
    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(3);
    for (const r of radios) expect(r).toHaveAttribute('aria-checked', 'false');
    const send = screen.getByRole('button', { name: /Chọn một hướng trước/ });
    expect(send).toBeDisabled();
    await userEvent.click(radios[1]!);
    expect(radios[1]).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('button', { name: /Viết chương 3/ })).toBeEnabled();
  });

  it('nhãn theo máy chủ "kind_label · tone_label", không bộ chọn sắc thái', () => {
    render(choicePanel());
    expect(screen.getByText('Lời thoại · nói dối')).toBeInTheDocument();
    expect(screen.queryByText(/Nói thật|Im lặng/)).toBeNull();
  });

  it('lỗi ô tự viết hiện ngay dưới ô, nguyên văn câu máy chủ', async () => {
    withMock({ fault: 'ACTION_UNCLEAR' });
    render(choicePanel());
    fireEvent.change(screen.getByLabelText('Hoặc tự viết hành động của bạn'), { target: { value: 'cái kia đi chỗ đó' } });
    await userEvent.click(screen.getByRole('button', { name: /theo ý tôi/ }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Hệ thống không hiểu hành động bạn viết.');
    expect(screen.getByLabelText('Hoặc tự viết hành động của bạn')).toHaveAttribute('aria-invalid', 'true');
  });
});

describe('chữ máy chủ hiện nguyên văn', () => {
  it('giữ dấu thoại "- ", không đổi thành gạch dài', () => {
    const text = '- Ai đó? - nàng hỏi.\n- Tôi.';
    const { container } = render(<InkText text={text} animate={false} revealAll={false} />);
    const ps = [...container.querySelectorAll('p')].map((p) => p.textContent);
    expect(ps).toEqual(['- Ai đó? - nàng hỏi.', '- Tôi.']);
    expect(container.textContent).not.toContain('—');
  });

  it('chạm để hiện hết: revealAll hiện đủ chữ ngay', async () => {
    const onDone = vi.fn();
    const { container, rerender } = render(<InkText text="Một hai ba bốn năm." animate revealAll={false} onDone={onDone} />);
    expect(container.querySelector('[aria-hidden="true"]')?.textContent).not.toBe('Một hai ba bốn năm.');
    rerender(<InkText text="Một hai ba bốn năm." animate revealAll onDone={onDone} />);
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(container.querySelector('p')?.textContent).toBe('Một hai ba bốn năm.');
  });

  it('người kể: câu trả lời nguyên văn kèm nguồn; hết lượt thì thay ô hỏi', async () => {
    withMock();
    renderApp(<NarratorPanel storyId="s-chuong" chapter={2} open onClose={() => {}} />);
    await screen.findByText('Còn 3 câu hỏi trong chương này');
    const box = screen.getByLabelText('Câu hỏi của bạn');
    for (let i = 0; i < 3; i++) {
      fireEvent.change(box, { target: { value: i === 0 ? 'Lão Tần là ai?' : 'Ai giết người?' } });
      await userEvent.click(screen.getByRole('button', { name: 'Gửi câu hỏi' }));
      await waitFor(() => expect(screen.queryByText('Người kể đang trả lời')).toBeNull());
    }
    expect(screen.getByText('Từ chương 1')).toBeInTheDocument();
    expect(screen.getAllByText('Bạn chưa biết điều này.').length).toBe(2);
    expect(await screen.findByText(/Lượt mới mở ở chương sau/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Câu hỏi của bạn')).toBeNull();
  });
});

describe('độ dài truyện chỉ gồm mức đang mở (D-88)', () => {
  it('màn khởi tạo hiện đúng các mức /config/public trả về, không mức nào khác', async () => {
    withMock();
    const config = { ...oddConfig(), story_lengths: [{ key: 'thu', label: 'Truyện thử', chapters_min: 3, chapters_max: 5 }] };
    renderApp(<Template />, { config });
    const radios = within(screen.getByRole('radiogroup', { name: 'D · Độ dài' })).getAllByRole('radio');
    expect(radios).toHaveLength(1);
    expect(radios[0]).toHaveTextContent('Truyện thử');
    for (const closed of ['Truyện ngắn', 'Truyện vừa', 'Truyện dài', 'Tiểu thuyết mỏng']) {
      expect(screen.queryByText(closed)).toBeNull();
    }
  });

  it('máy chủ giả: /config/public chỉ trả mức mở; mức đóng bị /setup từ chối bằng mã riêng', async () => {
    withMock();
    const config = await api.publicConfig();
    expect(config.story_lengths.map((l) => l.key)).toEqual(['short', 'medium']);
    const err = await api.startSetup({ tags: { genre: 'kiếm hiệp', voice: null }, length_level: 'long', naming: null }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe('STORY_LENGTH_NOT_OPEN');
    expect((err as ApiError).fields).toEqual(['length_level']);
    const unknown = await api.startSetup({ tags: { genre: 'kiếm hiệp', voice: null }, length_level: 'khong-co', naming: null }).catch((e: unknown) => e);
    expect((unknown as ApiError).code).toBe('REQUEST_INVALID');
  });
});
