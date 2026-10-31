// Dữ liệu mẫu cho lớp mock (D-69). Truyện bịa riêng cho giao diện; không chép truyện mẫu của repo
// (`data/sample-story/`) hay chữ trong ảnh thiết kế. Mọi con số ở đây là số mẫu của máy chủ giả.

import type {
  CharacterOption,
  NotebookOut,
  PlayerChoice,
  PlotOption,
  PublicConfig,
  SettingOption,
  StoryLengthOption,
  StoryStyle,
} from '../api/types';

/** Mọi mức độ dài của máy chủ giả, như `config/story_lengths.yaml`. `/config/public` chỉ trả mức
 *  `player_selectable`; `/setup` từ chối mức đóng bằng `STORY_LENGTH_NOT_OPEN` (D-88). */
export const MOCK_LENGTH_LEVELS: (StoryLengthOption & { player_selectable: boolean })[] = [
  { key: 'short', label: 'Truyện ngắn', chapters_min: 4, chapters_max: 8, style: 'prose', minutes: null, player_selectable: true },
  { key: 'medium', label: 'Truyện vừa', chapters_min: 10, chapters_max: 20, style: 'prose', minutes: null, player_selectable: true },
  { key: 'long', label: 'Truyện dài', chapters_min: 20, chapters_max: 35, style: 'prose', minutes: null, player_selectable: false },
  { key: 'novel', label: 'Tiểu thuyết mỏng', chapters_min: 30, chapters_max: 60, style: 'prose', minutes: null, player_selectable: false },
  // Truyện kịch bản audio có mức riêng, đo bằng phút nghe; `/setup` từ chối mức khác kiểu truyện.
  { key: 'audio_30', label: 'Audio ~30 phút', chapters_min: 3, chapters_max: 4, style: 'audio', minutes: 30, player_selectable: true },
  { key: 'audio_45', label: 'Audio ~45 phút', chapters_min: 5, chapters_max: 5, style: 'audio', minutes: 45, player_selectable: true },
  { key: 'audio_60', label: 'Audio ~1 tiếng', chapters_min: 6, chapters_max: 7, style: 'audio', minutes: 60, player_selectable: true },
];

export const MOCK_CONFIG: PublicConfig = {
  input: {
    custom_action_max_chars: 200,
    character_name_max_chars: 40,
    personality_max_chars: 300,
    backstory_max_chars: 600,
    narrator_question_max_chars: 300,
  },
  narrator_questions_per_chapter: 3,
  rewrite_per_scene: 1,
  cost_usd: { per_scene: 0.02, per_chapter: 0.08, per_story: 1 },
  story_lengths: MOCK_LENGTH_LEVELS.filter((l) => l.player_selectable).map(({ key, label, chapters_min, chapters_max, style, minutes }) => ({
    key,
    label,
    chapters_min,
    chapters_max,
    style,
    minutes,
  })),
  darkness_levels: [
    { key: 'light', label: 'Nhẹ' },
    { key: 'medium', label: 'Vừa' },
    { key: 'heavy', label: 'Đậm' },
  ],
  default_darkness_level: 'medium',
  writer_tier: { label: 'Tiêu chuẩn' },
  chapter_estimate_default_usd: 0.01,
};

export const SCENES: string[] = [
  [
    'Gió trên đèo Lạc Nhạn thổi ngược, mang theo mùi tuyết chưa kịp rơi. Kha Diệp kéo cao cổ áo, đếm từng bậc đá dẫn lên tháp chuông như mọi đêm trực.',
    'Chiếc chuông đồng treo giữa bốn cột gỗ lim, to bằng một gian nhà. Người ta bảo nó chỉ kêu khi có kẻ lạ vượt đèo.',
    'Đêm nay nó kêu ba tiếng, rồi im bặt.',
    '- Ngươi nghe thấy không? - Lão Tần gác cổng thò đầu ra khỏi chòi, tay còn cầm bát rượu. - Ba tiếng. Xưa nay chưa từng có ba tiếng.',
    '- Có lẽ gió, - Kha Diệp đáp, dù chính nàng cũng không tin.',
    'Dưới chân tháp, trên lớp băng mỏng, có một hàng dấu chân đi lên mà không có hàng nào đi xuống.',
  ].join('\n'),
  [
    'Trạm gác đèo có bảy người, kể cả con chó vàng tên Mốc. Sáng hôm sau chỉ còn sáu.',
    'Người mất tích là Đỗ Khiêm, kẻ giữ sổ thông hành. Bàn của hắn vẫn ngay ngắn, nghiên mực chưa khô, cây bút đặt chéo trên trang ghi dở.',
    'Kha Diệp cúi xuống đọc dòng cuối: "Giờ Tý, một người qua đèo, không mang thẻ, nói là đi tìm em gái."',
    '- Hắn bỏ đi theo khách lạ à? - Trưởng trạm Lương Phục hỏi, giọng khàn vì thức trắng.',
    '- Hắn không mang áo bông, - nàng nói. - Không ai đi theo ai giữa trời này mà không mang áo bông.',
    'Lương Phục nhìn nàng lâu hơn cần thiết, rồi gấp cuốn sổ lại.',
  ].join('\n'),
  [
    'Con đường mòn sau tháp chuông dẫn xuống khe Liễu, nơi mùa hè có suối, mùa đông chỉ còn đá.',
    'Mốc chạy trước, mũi dí sát mặt tuyết. Đến khúc quanh thứ ba, nó dừng lại và gầm gừ với một gốc thông đổ.',
    'Dưới gốc thông có một chiếc đèn lồng giấy, khung tre gãy, giấy đỏ đã bạc. Trên giấy viết hai chữ bằng mực tàu: "Về nhà".',
    '- Đây không phải đồ của trạm, - Kha Diệp lẩm bẩm.',
    'Nàng gói chiếc đèn vào khăn, nhét vào trong áo. Khi đứng dậy, nàng thấy phía bên kia khe có khói bếp, mỏng như một sợi chỉ.',
  ].join('\n'),
  [
    'Căn chòi bên kia khe thấp và tối, mái lợp vỏ cây. Một bà cụ ngồi bên bếp lửa, đang hơ đôi tay gầy.',
    '- Cháu đến vì tiếng chuông, - bà nói, không ngẩng lên. - Ai cũng đến vì tiếng chuông.',
    '- Bà đã thấy một người đàn ông đi qua đây không? Áo xám, không mang áo bông.',
    'Bà cụ đẩy một que củi vào lửa. Ngọn lửa bùng lên, soi rõ trên vách một hàng đèn lồng giấy đỏ, chiếc nào cũng viết hai chữ "Về nhà".',
    '- Đêm qua có hai người, - bà nói. - Một người đi lên. Một người đi xuống. Cháu muốn hỏi người nào?',
  ].join('\n'),
  [
    'Kha Diệp trở về trạm khi trời đã sẩm tối. Chiếc đèn lồng trong áo nàng nhẹ như không, nhưng nàng thấy nó ấm.',
    'Lương Phục đứng chờ ở cổng, tay cầm cây đuốc chưa thắp.',
    '- Ngươi đi đâu cả ngày?',
    '- Xuống khe Liễu tìm Đỗ Khiêm.',
    '- Và?',
    'Nàng chưa kịp trả lời thì trên đỉnh tháp, chiếc chuông đồng lại kêu. Một tiếng. Rồi hai.',
  ].join('\n'),
  [
    'Lần này không ai bảo đó là gió.',
    'Cả sáu người trong trạm cùng chạy lên tháp. Mốc sủa dữ dội, lông dựng đứng.',
    'Trên sàn gỗ dưới chiếc chuông, ai đó đã đặt cuốn sổ thông hành của Đỗ Khiêm, mở đúng trang ghi dở. Dưới dòng chữ cũ có thêm một dòng mới, nét mực còn ướt: "Giờ Tuất, một người qua đèo. Lần này là để về."',
    'Lão Tần đánh rơi bát rượu. Tiếng vỡ vang khắp tháp, lâu hơn cả tiếng chuông.',
  ].join('\n'),
];

/** Cảnh của truyện mẫu kiểu kịch bản audio: viết để đọc thành tiếng (người kể xưng tôi, câu ngắn,
 *  lời thoại có câu dẫn). */
export const AUDIO_SCENES: string[] = [
  [
    'Tôi là người trực đêm của đài phát thanh thị trấn Sông Lam.',
    'Đúng nửa đêm, tôi tắt nhạc. Tôi đọc bản tin cuối cùng. Rồi tôi ngồi chờ.',
    'Ngọn đèn đỏ trên bàn bỗng sáng. Có người gọi vào đường dây trực tiếp.',
    'Tôi nhấc máy. Một ông lão nói, giọng chậm và khàn: "Cô còn trực à? Tôi muốn xin một bài hát."',
    'Tôi hỏi ông: "Ông muốn tặng bài hát cho ai?"',
  ].join('\n'),
  [
    'Ông lão im lặng rất lâu. Tôi nghe thấy tiếng mưa ở đầu dây bên kia.',
    'Rồi ông đáp: "Tặng cho cô gái đã gọi vào đây đêm qua. Cô không nhớ sao?"',
    'Tôi không nhớ. Đêm qua, đài tắt máy phát vì mất điện.',
    'Tôi nói với ông: "Đêm qua không có ai trực cả, thưa ông."',
    'Ông lão cười khẽ. Ông nói: "Vậy thì người nghe máy đêm qua là ai?"',
  ].join('\n'),
  [
    'Sáng hôm sau, tôi mở sổ trực của đài.',
    'Trang của đêm mất điện không trống. Có một dòng chữ, nét mực xanh, giống hệt chữ của tôi.',
    'Dòng chữ viết: "Một cuộc gọi lúc nửa đêm. Một ông lão xin bài hát cho chính mình."',
    'Tôi gập sổ lại. Tay tôi lạnh ngắt.',
  ].join('\n'),
  [
    'Đêm đó, tôi đến đài sớm hơn thường lệ.',
    'Ông Sáu bảo vệ đứng ở cổng. Ông hỏi tôi: "Cô trực tiếp à? Hôm nay đâu phải ca của cô."',
    'Tôi đáp: "Tôi chỉ muốn nghe lại băng ghi âm đêm qua."',
    'Ông Sáu lắc đầu. Ông nói: "Đêm qua mất điện. Làm gì có băng nào."',
  ].join('\n'),
];

/** Cảnh kết của truyện mẫu (chương cuối của bản kế hoạch giả). */
export const END_SCENE = [
  'Sáng hôm sau, tuyết ngừng rơi. Kha Diệp treo chiếc đèn lồng giấy đỏ lên cột chuông và thắp nó giữa ban ngày.',
  'Từ khe Liễu, một bóng người áo xám chậm rãi đi lên, không mang áo bông, tay ôm cuốn sổ thông hành.',
  '- Ta về rồi, - Đỗ Khiêm nói, giọng khản đặc. - Người kia không về được nữa.',
  'Chiếc chuông đồng im lặng. Lần đầu tiên sau nhiều năm, nó không kêu khi có người vượt đèo.',
].join('\n');

let choiceSeq = 0;
function choiceId(): string {
  choiceSeq += 1;
  return `choice-${choiceSeq.toString(16).padStart(12, '0')}`;
}

const CHOICE_SETS: Omit<PlayerChoice, 'id'>[][] = [
  [
    { kind: 'action', kind_label: 'Hành động', tone: null, tone_label: null, text: 'Đi theo sợi khói bếp xuống khe Liễu lần nữa, một mình.' },
    { kind: 'dialogue', kind_label: 'Lời thoại', tone: 'truth', tone_label: 'nói thật', text: 'Kể cho Lương Phục về chiếc đèn lồng giấy đỏ.' },
    { kind: 'inner', kind_label: 'Nội tâm', tone: null, tone_label: null, text: 'Tự hỏi vì sao Lương Phục gấp cuốn sổ lại nhanh đến thế.' },
  ],
  [
    { kind: 'action', kind_label: 'Hành động', tone: null, tone_label: null, text: 'Lật cuốn sổ sang trang trước, tìm tên người khách lạ.' },
    { kind: 'dialogue', kind_label: 'Lời thoại', tone: 'lie', tone_label: 'nói dối', text: 'Nói với Lương Phục rằng nàng không tìm thấy gì ở khe Liễu.' },
    { kind: 'inner', kind_label: 'Nội tâm', tone: null, tone_label: null, text: 'Nhớ lại thật kỹ giọng nói của bà cụ bên bếp lửa.' },
  ],
  [
    { kind: 'action', kind_label: 'Hành động', tone: null, tone_label: null, text: 'Thắp chiếc đèn lồng giấy đỏ và treo nó lên cột chuông.' },
    { kind: 'dialogue', kind_label: 'Lời thoại', tone: 'silence', tone_label: 'im lặng', text: 'Không đáp khi lão Tần hỏi nàng giấu gì trong áo.' },
    { kind: 'inner', kind_label: 'Nội tâm', tone: null, tone_label: null, text: 'Tự nhủ rằng hàng dấu chân kia không phải của Đỗ Khiêm.' },
  ],
];

const AUDIO_CHOICES: Omit<PlayerChoice, 'id'>[] = [
  { kind: 'action', kind_label: 'Hành động', tone: null, tone_label: null, text: 'Tua lại cuộn băng trực của đêm mất điện.' },
  { kind: 'dialogue', kind_label: 'Lời thoại', tone: 'truth', tone_label: 'nói thật', text: 'Kể cho ông Sáu bảo vệ về cuộc gọi lúc nửa đêm.' },
  { kind: 'inner', kind_label: 'Nội tâm', tone: null, tone_label: null, text: 'Tự hỏi vì sao giọng ông lão nghe quen đến thế.' },
];

/** `style`: truyện kịch bản audio có bộ lựa chọn riêng, hợp với truyện của nó. */
export function makeChoices(chapter: number, style: StoryStyle = 'prose'): PlayerChoice[] {
  const set = style === 'audio' ? AUDIO_CHOICES : (CHOICE_SETS[(chapter - 1) % CHOICE_SETS.length] ?? CHOICE_SETS[0] ?? []);
  return set.map((c) => ({ ...c, id: choiceId() }));
}

export function notebookFor(chapter: number): NotebookOut {
  const all: NotebookOut['entries'] = [
    // Nhân vật chính có mục từ chương 0 (D-74): câu trích là dòng của thiết lập truyện.
    { ref: 'm1', kind: 'Character', text: 'Kha Diệp', aliases: [], since_chapter: 0, quote: 'Nhân vật chính: Kha Diệp', about: [], is_protagonist: true },
    { ref: 'm2', kind: 'Character', text: 'Lão Tần', aliases: ['lão gác cổng'], since_chapter: 1, quote: '- Ngươi nghe thấy không? - Lão Tần gác cổng thò đầu ra khỏi chòi, tay còn cầm bát rượu.', about: [], is_protagonist: false },
    { ref: 'm3', kind: 'Location', text: 'Đèo Lạc Nhạn', aliases: [], since_chapter: 1, quote: 'Gió trên đèo Lạc Nhạn thổi ngược, mang theo mùi tuyết chưa kịp rơi.', about: [], is_protagonist: false },
    { ref: 'm4', kind: 'Location', text: 'Tháp chuông', aliases: [], since_chapter: 1, quote: 'Kha Diệp kéo cao cổ áo, đếm từng bậc đá dẫn lên tháp chuông như mọi đêm trực.', about: [], is_protagonist: false },
    { ref: 'm5', kind: 'Item', text: 'Chuông đồng', aliases: ['chiếc chuông'], since_chapter: 1, quote: 'Chiếc chuông đồng treo giữa bốn cột gỗ lim, to bằng một gian nhà.', about: [], is_protagonist: false },
    { ref: 'm6', kind: 'Fact', text: 'Đêm ấy chuông kêu ba tiếng rồi im bặt', aliases: [], since_chapter: 1, quote: 'Đêm nay nó kêu ba tiếng, rồi im bặt.', about: ['m5'], is_protagonist: false },
    { ref: 'm7', kind: 'Character', text: 'Đỗ Khiêm', aliases: ['kẻ giữ sổ thông hành'], since_chapter: 1, quote: 'Người mất tích là Đỗ Khiêm, kẻ giữ sổ thông hành.', about: [], is_protagonist: false },
    { ref: 'm8', kind: 'Character', text: 'Lương Phục', aliases: ['trưởng trạm'], since_chapter: 1, quote: '- Hắn bỏ đi theo khách lạ à? - Trưởng trạm Lương Phục hỏi, giọng khàn vì thức trắng.', about: [], is_protagonist: false },
    { ref: 'm9', kind: 'Event', text: 'Đỗ Khiêm mất tích sau đêm chuông kêu', aliases: [], since_chapter: 1, quote: 'Trạm gác đèo có bảy người, kể cả con chó vàng tên Mốc. Sáng hôm sau chỉ còn sáu.', about: ['m7'], is_protagonist: false },
    { ref: 'm10', kind: 'Location', text: 'Khe Liễu', aliases: [], since_chapter: 2, quote: 'Con đường mòn sau tháp chuông dẫn xuống khe Liễu, nơi mùa hè có suối, mùa đông chỉ còn đá.', about: [], is_protagonist: false },
    { ref: 'm11', kind: 'Item', text: 'Đèn lồng giấy đỏ', aliases: ['chiếc đèn lồng'], since_chapter: 2, quote: 'Dưới gốc thông có một chiếc đèn lồng giấy, khung tre gãy, giấy đỏ đã bạc.', about: [], is_protagonist: false },
    { ref: 'm12', kind: 'Character', text: 'Bà cụ bên kia khe', aliases: [], since_chapter: 2, quote: 'Một bà cụ ngồi bên bếp lửa, đang hơ đôi tay gầy.', about: [], is_protagonist: false },
    { ref: 'm13', kind: 'Fact', text: 'Đêm qua có hai người qua khe: một người đi lên, một người đi xuống', aliases: [], since_chapter: 2, quote: '- Đêm qua có hai người, - bà nói. - Một người đi lên. Một người đi xuống. Cháu muốn hỏi người nào?', about: [], is_protagonist: false },
  ];
  const lies: NotebookOut['lies'] =
    chapter >= 3
      ? [{ content: 'Nàng không tìm thấy gì ở khe Liễu.', chapter: 3, told_to: ['Lương Phục'] }]
      : [];
  return { chapter, entries: all.filter((e) => e.since_chapter <= chapter), lies };
}

export const SETTINGS: SettingOption[] = [
  { title: 'Trạm gác đèo Lạc Nhạn', intro: 'Bảy người giữ một con đèo mà mùa đông nào cũng nuốt mất vài lữ khách. Trên tháp, một chiếc chuông đồng chỉ kêu khi có kẻ lạ vượt núi.' },
  { title: 'Chợ đêm bến Vạn Thuỷ', intro: 'Mỗi đêm rằm, bến sông mọc lên một phiên chợ bán những thứ người ta đánh mất. Ai mua được gì thì phải trả bằng một kỷ niệm.' },
  { title: 'Thư viện trên lưng rùa', intro: 'Một con rùa đá to như hòn đảo chở trên lưng tàng thư của cả một triều đại đã mất. Bạn là người chép sách trẻ nhất trên đó.' },
];

export const PLOTS: PlotOption[] = [
  { title: 'Tiếng chuông thứ ba', summary: 'Chuông kêu ba tiếng giữa đêm, và sáng hôm sau một người trong trạm biến mất.' },
  { title: 'Lá thư không người nhận', summary: 'Một lá thư đến trạm, đề tên bạn bằng nét chữ của người mẹ đã mất từ lâu.' },
  { title: 'Mùa tuyết không tan', summary: 'Tuyết năm nay không tan sau tiết lập xuân. Người già trong trạm bảo đó là điềm của một lời thề bị phá.' },
];

export const CHARACTERS: CharacterOption[] = [
  { name: 'Kha Diệp', personality: 'Ít nói, tinh mắt, ghét để người khác nợ mình.', backstory: 'Con gái một thợ đúc chuông dưới xuôi. Lên đèo làm lính gác năm mười sáu tuổi, sau khi cha mất trong một mùa lũ.' },
  { name: 'Đào Tịnh', personality: 'Hay cười, liều lĩnh, nhớ mặt người rất giỏi.', backstory: 'Từng dẫn đường cho các đoàn buôn muối. Bỏ nghề sau một chuyến đi mà chỉ mình anh trở về.' },
  { name: 'Mạc Uyên', personality: 'Điềm tĩnh, cẩn trọng, tin vào sổ sách hơn lời nói.', backstory: 'Người chép sổ ở trạm dưới chân núi, vừa được điều lên trạm đèo vào đầu mùa đông.' },
];

export const FINISHED_SCENES: string[] = [
  [
    'Ngõ Mười Ba có mười ba chiếc đèn lồng, và suốt mười ba năm chưa đêm nào chúng cùng tắt.',
    '- Cô đến muộn, - ông Sáu bán nước nói, đẩy sang một chén chè xanh. - Chiếc thứ bảy tắt từ chập tối.',
    'Hạnh nhìn dọc con ngõ. Chiếc đèn thứ bảy treo trước một cánh cửa đã đóng đinh chéo.',
  ].join('\n'),
  [
    'Hạnh đặt chiếc chìa khoá đồng lên bàn ông Sáu. Ông nhìn nó rất lâu rồi mới nhận.',
    '- Mười ba năm, - ông nói. - Tôi tưởng sẽ không ai trả lại.',
    'Hạnh thổi tắt ngọn đèn lồng cuối cùng trong ngõ. Lần đầu tiên sau mười ba năm, ngõ tối mà không ai sợ.',
  ].join('\n'),
];
