// Khung hỏi người kể hiện lại các lượt đã hỏi của chương (D-162): tải lại trang không mất.
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { api, setFetch } from '../api/client';
import { NarratorPanel } from '../screens/story/NarratorPanel';
import { renderApp, withMock } from './render';

describe('hỏi người kể: lượt đã hỏi', () => {
  it('mở lại khung thì thấy câu đã hỏi và câu đã đáp của chương, kèm nguồn', async () => {
    withMock();
    const asked = await api.askNarrator('s-chuong', 'Lão Gù là ai?');
    const view = renderApp(<NarratorPanel storyId="s-chuong" chapter={2} open onClose={() => {}} />);
    expect(await screen.findByText('Lão Gù là ai?')).toBeInTheDocument();
    expect(screen.getByText(asked.answer)).toBeInTheDocument();
    view.unmount();
  });

  it('lượt mới nối sau lượt cũ, không lặp lượt cũ', async () => {
    withMock();
    await api.askNarrator('s-chuong', 'Câu thứ nhất?');
    renderApp(<NarratorPanel storyId="s-chuong" chapter={2} open onClose={() => {}} />);
    await screen.findByText('Câu thứ nhất?');
    await userEvent.type(screen.getByRole('textbox', { name: /Câu hỏi của bạn/ }), 'Câu thứ hai?');
    await userEvent.click(screen.getByRole('button', { name: 'Gửi câu hỏi' }));
    await waitFor(() => expect(screen.getAllByText(/Bạn hỏi:/)).toHaveLength(2), { timeout: 4000 });
    expect(screen.getAllByText('Câu thứ nhất?')).toHaveLength(1);
    const mine = screen.getAllByText(/Bạn hỏi:/).map((el) => el.parentElement?.textContent);
    expect(mine).toEqual(['Bạn hỏi: Câu thứ nhất?', 'Bạn hỏi: Câu thứ hai?']);
  });

  it('không tải được lượt cũ thì khung vẫn hỏi được', async () => {
    const server = withMock();
    setFetch(async (url, init) => {
      if (url.endsWith('/narrator/turns')) return new Response('{}', { status: 500 });
      return server.fetch(url, init);
    });
    renderApp(<NarratorPanel storyId="s-chuong" chapter={2} open onClose={() => {}} />);
    expect(await screen.findByText(/Còn \d+ câu hỏi trong chương này/)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /Câu hỏi của bạn/ })).toBeEnabled();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
