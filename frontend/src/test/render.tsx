import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { setFetch } from '../api/client';
import type { PublicConfig } from '../api/types';
import { ConfigValue } from '../config/PublicConfig';
import { MOCK_CONFIG } from '../mock/data';
import { createMockServer, type MockOptions } from '../mock/server';
import { PlayerKeyProvider } from '../state/PlayerKey';

/** Config mẫu với số lạ, để test thấy giao diện lấy số từ config chứ không tự đặt. */
export function oddConfig(): PublicConfig {
  return {
    ...MOCK_CONFIG,
    input: {
      custom_action_max_chars: 137,
      character_name_max_chars: 23,
      personality_max_chars: 211,
      backstory_max_chars: 457,
      narrator_question_max_chars: 89,
    },
    cost_usd: { per_scene: 0.37, per_chapter: 1.23, per_story: 4.56 },
  };
}

export function withMock(options: MockOptions = {}) {
  const server = createMockServer({ delayScale: 0, ...options });
  setFetch(server.fetch);
  return server;
}

export function renderApp(ui: ReactElement, { config = oddConfig(), route = '/' }: { config?: PublicConfig; route?: string } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ConfigValue value={config}>
        <PlayerKeyProvider>{ui}</PlayerKeyProvider>
      </ConfigValue>
    </MemoryRouter>,
  );
}
