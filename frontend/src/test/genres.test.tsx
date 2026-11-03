// Màn khuôn truyện: chọn nhiều thể loại từ /config/public, ô ý tưởng tuỳ chọn (D-160).
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it } from 'vitest';
import { setFetch } from '../api/client';
import { ApiError } from '../api/errors';
import { ErrorBlock } from '../components/ErrorBlock';
import type { PublicConfig } from '../api/types';
import { Template } from '../screens/setup/Template';
import { oddConfig, renderApp, withMock } from './render';

/** Config riêng: số tối đa và trần ký tự khác số thật, để thấy giao diện đọc số từ config. */
function genreConfig(): PublicConfig {
  return {
    ...oddConfig(),
    input: { ...oddConfig().input, story_idea_max_chars: 777 },
    max_genres: 2,
    genres: [
      { key: 'kinh_di', label: 'Kinh dị', hint: 'Sợ từ từ.', styles: ['prose', 'audio'] },
      { key: 'hai', label: 'Hài', hint: 'Cười.', styles: ['prose', 'audio'] },
      { key: 'tho', label: 'Chỉ để đọc', hint: 'Chữ đẹp.', styles: ['prose'] },
    ],
  };
}

function recording() {
  const server = withMock();
  const posts: Record<string, unknown>[] = [];
  setFetch(async (url, init) => {
    if (url.endsWith('/setup') && init?.method === 'POST' && typeof init.body === 'string') posts.push(JSON.parse(init.body));
    return server.fetch(url, init);
  });
  return posts;
}

const genreGroup = () => within(screen.getByRole('group', { name: /Thể loại/ }));

describe('khởi tạo: thể loại và ý tưởng', () => {
  beforeEach(() => sessionStorage.clear());

  it('liệt kê thể loại từ config theo kiểu truyện đang chọn', async () => {
    recording();
    renderApp(<Template />, { config: genreConfig() });
    expect(genreGroup().getAllByRole('checkbox').map((c) => c.getAttribute('name') ?? c.closest('label')?.textContent)).toEqual([
      'Kinh dị',
      'Hài',
      'Chỉ để đọc',
    ]);
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    expect(genreGroup().queryByRole('checkbox', { name: 'Chỉ để đọc' })).toBeNull();
  });

  it('chọn tối đa max_genres thể loại', async () => {
    recording();
    renderApp(<Template />, { config: genreConfig() });
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Kinh dị' }));
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Hài' }));
    expect(genreGroup().getByRole('checkbox', { name: 'Chỉ để đọc' })).toBeDisabled();
    expect(genreGroup().getByRole('checkbox', { name: 'Kinh dị' })).toBeChecked();
  });

  it('đổi kiểu truyện thì bỏ thể loại không dùng được cho kiểu mới', async () => {
    const posts = recording();
    renderApp(<Template />, { config: genreConfig() });
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Chỉ để đọc' }));
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Hài' }));
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ genres: ['hai'], style: 'audio' });
  });

  it('bộ đếm ô ý tưởng lấy trần từ config', () => {
    recording();
    renderApp(<Template />, { config: genreConfig() });
    expect(screen.getByRole('textbox', { name: /Ý tưởng của bạn/ })).toHaveAttribute('maxlength', '777');
    expect(screen.getByText('0/777')).toBeInTheDocument();
  });

  it('gửi khoá thể loại theo thứ tự chọn và ý tưởng đã cắt khoảng trắng; ý tưởng trắng thì không gửi', async () => {
    const posts = recording();
    renderApp(<Template />, { config: genreConfig() });
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Hài' }));
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Kinh dị' }));
    await userEvent.click(screen.getByRole('radio', { name: /Truyện ngắn/ }));
    await userEvent.type(screen.getByRole('textbox', { name: /Ý tưởng của bạn/ }), '  bạn thân ganh ghét  ');
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toMatchObject({ genres: ['hai', 'kinh_di'], idea: 'bạn thân ganh ghét' });
    expect(posts[0]).not.toHaveProperty('tags.genre');
  });

  it('chưa chọn thể loại thì chưa gửi được; ý tưởng chỉ có khoảng trắng thì không gửi', async () => {
    const posts = recording();
    renderApp(<Template />, { config: genreConfig() });
    await userEvent.click(screen.getByRole('radio', { name: /Truyện ngắn/ }));
    expect(screen.getByRole('button', { name: /Gợi ý bối cảnh/ })).toBeDisabled();
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Kinh dị' }));
    await userEvent.type(screen.getByRole('textbox', { name: /Ý tưởng của bạn/ }), '   ');
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).not.toHaveProperty('idea');
  });
});

describe('khởi tạo: ý tưởng bị chặn (sau review D-160)', () => {
  beforeEach(() => sessionStorage.clear());

  it('giữ nháp khuôn truyện: rời màn rồi mở lại vẫn còn ý tưởng và thể loại đã chọn', async () => {
    recording();
    const first = renderApp(<Template />, { config: genreConfig() });
    await userEvent.click(genreGroup().getByRole('checkbox', { name: 'Hài' }));
    await userEvent.type(screen.getByRole('textbox', { name: /Ý tưởng của bạn/ }), 'bạn thân ganh ghét');
    first.unmount();
    renderApp(<Template />, { config: genreConfig() });
    expect(screen.getByRole('textbox', { name: /Ý tưởng của bạn/ })).toHaveValue('bạn thân ganh ghét');
    expect(genreGroup().getByRole('checkbox', { name: 'Hài' })).toBeChecked();
  });

  it('INPUT_BLOCKED ở khởi tạo có nút "Sửa khuôn truyện" về /moi; ở ô tự viết thì không', () => {
    const error = new ApiError({ code: 'INPUT_BLOCKED', message: 'Nội dung bị chặn.' });
    const { unmount } = render(
      <MemoryRouter>
        <ErrorBlock error={error} context="setup" />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Sửa khuôn truyện' })).toHaveAttribute('href', '/moi');
    unmount();
    render(
      <MemoryRouter>
        <ErrorBlock error={error} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: 'Sửa khuôn truyện' })).toBeNull();
  });

  it('chữ hướng dẫn nói chọn được nhiều thể loại', () => {
    recording();
    renderApp(<Template />, { config: genreConfig() });
    expect(screen.queryByText('Chọn một thể loại chính. Phần còn lại để ngòi bút đề xuất.')).toBeNull();
    expect(screen.getByText(/Chọn tới 2 thể loại/)).toBeInTheDocument();
  });
});

