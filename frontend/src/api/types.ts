// Kiểu dữ liệu của API, chép theo schema máy chủ:
// - `backend/src/writory/api/schemas.py` (sổ tay, key, khởi tạo, chơi);
// - `backend/src/writory/pipeline/events.py` (sự kiện SSE);
// - hợp đồng của nhánh backend cho giao diện (danh sách truyện, giới hạn công khai, chi phí,
//   người kể có số câu còn lại và nguồn; D-65).
// Giao diện hiện nguyên văn mọi chữ ở đây, không tự đổi (README bàn giao mục 4).

export interface ApiErrorBody {
  code: string;
  message: string;
  fields?: string[];
}

// --- giới hạn công khai (GET /config/public) ---------------------------------------------------

/** Mức độ dài thuộc đúng một kiểu truyện; `/setup` từ chối mức khác kiểu (`REQUEST_INVALID`,
 *  `fields: ["length_level"]`). `minutes`: số phút nghe của mức audio; null với mức truyện chữ. */
export interface StoryLengthOption {
  key: string;
  label: string;
  chapters_min: number;
  chapters_max: number;
  style: StoryStyle;
  minutes: number | null;
}

export interface DarknessLevelOption {
  key: string;
  label: string;
}

export interface PublicConfig {
  input: {
    custom_action_max_chars: number | null;
    character_name_max_chars: number | null;
    personality_max_chars: number | null;
    backstory_max_chars: number | null;
    narrator_question_max_chars: number | null;
  };
  narrator_questions_per_chapter: number | null;
  rewrite_per_scene: number | null;
  cost_usd: {
    per_scene: number | null;
    per_chapter: number | null;
    per_story: number | null;
  };
  story_lengths: StoryLengthOption[];
  darkness_levels: DarknessLevelOption[];
  default_darkness_level: string | null;
  writer_tier: { label: string };
  /** Số mặc định cho màn không gắn truyện (D-87); null: chưa đặt. */
  chapter_estimate_default_usd: number | null;
}

/** Ước tính chi phí chương tới của một truyện (D-87). `usd` null: không có số nào. */
export interface ChapterEstimateOut {
  chapter: number;
  usd: number | null;
  source: 'story_median' | 'default';
  chapters_used: number;
}

// --- tủ truyện, chi phí -------------------------------------------------------------------------

/** Kiểu truyện chọn lúc khởi tạo: văn xuôi, hay kịch bản để đọc thành tiếng bằng TTS một giọng. */
export type StoryStyle = 'prose' | 'audio';

export interface StorySummary {
  story_id: string;
  title: string;
  length_level: string;
  length_label: string;
  style: StoryStyle;
  chapter: number;
  finished: boolean;
  last_excerpt: string | null;
  updated_at: string;
}

export interface StoriesOut {
  stories: StorySummary[];
}

export interface PlayerCosts {
  total_usd: number;
  this_month_usd: number;
  stories: { story_id: string; spent_usd: number }[];
}

// --- key người chơi -----------------------------------------------------------------------------

/** `GET /auth/session`, `POST /auth/login`, `POST /auth/logout` (D-89). Không có token: phiên chỉ
 *  nằm trong cookie HttpOnly, trang không đọc được. */
export interface AuthSession {
  mode: 'dev' | 'invite';
  logged_in: boolean;
  name: string | null;
}

export interface PlayerKeyOut {
  has_key: boolean;
  last4: string | null;
}

// --- khởi tạo -----------------------------------------------------------------------------------

export type NamesStyle = 'han_viet' | 'viet';
export type PlacesStyle = 'hu_cau' | 'that';

export interface SetupStartIn {
  tags: { genre: string; voice?: string | null };
  length_level: string;
  darkness_level?: string | null;
  naming: { names: NamesStyle; places: PlacesStyle } | null;
  /** Bỏ trống là `prose`. */
  style?: StoryStyle;
}

export interface SettingOption {
  title: string;
  intro: string;
}

export interface PlotOption {
  title: string;
  summary: string;
}

export interface CharacterOption {
  name: string;
  personality: string;
  backstory: string;
}

export type SetupStage = 'settings' | 'plots' | 'characters' | 'finalize' | 'done';

export interface SetupOut {
  session_id: string;
  step: SetupStage;
  tags: { genre: string; era: string | null; voice: string | null };
  darkness_level: string | null;
  length_level: string;
  style: StoryStyle;
  naming: { names: string; places: string };
  settings: SettingOption[] | null;
  setting_index: number | null;
  plots: PlotOption[] | null;
  plot_index: number | null;
  characters: CharacterOption[] | null;
  character_index: number | null;
  protagonist: CharacterOption | null;
  story_id: string | null;
}

export interface CharacterChoiceIn {
  index: number;
  name: string | null;
  personality: string | null;
  backstory: string | null;
}

// --- chơi ---------------------------------------------------------------------------------------

export type ChoiceKind = 'action' | 'dialogue' | 'inner';
export type Tone = 'truth' | 'lie' | 'silence';

export interface PlayerChoice {
  id: string;
  kind: ChoiceKind;
  kind_label: string;
  tone: Tone | null;
  tone_label: string | null;
  text: string;
}

export interface ActionOut {
  for_chapter: number;
  source: 'choice' | 'custom';
  text: string;
}

export interface ChoicesOut {
  chapter: number;
  choices: PlayerChoice[];
}

export interface ChapterOut {
  number: number;
  scenes: string[];
}

export interface StoryOut {
  story_id: string;
  length_level: string;
  style: StoryStyle;
  chapter: number;
  pending: boolean;
  choices: PlayerChoice[];
  action: ActionOut | null;
  next_ready: boolean;
  finished: boolean;
}

// --- sổ tay, người kể ---------------------------------------------------------------------------

export type EntryKind = 'Character' | 'Location' | 'Item' | 'Faction' | 'Fact' | 'Event' | 'Lie';

export interface NotebookEntry {
  ref: string;
  kind: EntryKind;
  text: string;
  aliases: string[];
  since_chapter: number;
  quote: string | null;
  about: string[];
  /** Mục là nhân vật chính, tức chính người chơi (D-74); thẻ sổ tay ghi nhãn "Bạn" (D-76). */
  is_protagonist: boolean;
}

export interface NotebookLie {
  content: string;
  chapter: number;
  told_to: string[];
}

export interface NotebookOut {
  chapter: number;
  entries: NotebookEntry[];
  lies: NotebookLie[];
}

export interface NarratorAnswerOut {
  answer: string;
  remaining: number;
  source_chapters: number[];
}

export interface NarratorQuotaOut {
  remaining: number;
}

// --- sự kiện SSE (pipeline/events.py) -----------------------------------------------------------

export interface StageEvent {
  type: 'stage';
  stage: 'context' | 'outline' | 'write' | 'review' | 'commit' | 'choices';
  scene: number | null;
  attempt: number | null;
  label: string;
}

export interface SceneReadyEvent {
  type: 'scene_ready';
  scene: number;
  text: string;
}

export interface SceneBlockedEvent {
  type: 'scene_blocked';
  scene: number;
  code: string;
  message: string;
}

export interface ChapterCommittedEvent {
  type: 'chapter_committed';
  chapter: number;
}

export interface ChoicesReadyEvent {
  type: 'choices_ready';
  chapter: number;
  choices: PlayerChoice[];
}

export interface StoryFinishedEvent {
  type: 'story_finished';
  chapter: number;
}

export interface ErrorEvent {
  type: 'error';
  code: string;
  message: string;
}

export type ChapterEvent =
  | StageEvent
  | SceneReadyEvent
  | SceneBlockedEvent
  | ChapterCommittedEvent
  | ChoicesReadyEvent
  | StoryFinishedEvent
  | ErrorEvent;
