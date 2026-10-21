// WriTory — phần theme cho Tailwind (dạng config v3; với Tailwind v4 chuyển sang khối @theme
// trỏ vào cùng các biến trong tokens.css). Giá trị thật nằm ở tokens.css.
/** @type {import('tailwindcss').Config['theme']} */
module.exports = {
  extend: {
    colors: {
      ink: {
        950: 'var(--ink-950)', 900: 'var(--ink-900)', 850: 'var(--ink-850)', 800: 'var(--ink-800)',
        750: 'var(--ink-750)', 700: 'var(--ink-700)', 600: 'var(--ink-600)', 500: 'var(--ink-500)',
        400: 'var(--ink-400)', 200: 'var(--ink-200)', 100: 'var(--ink-100)', 50: 'var(--ink-50)',
      },
      paper: {
        50: 'var(--paper-50)', 100: 'var(--paper-100)', 200: 'var(--paper-200)', 400: 'var(--paper-400)',
        500: 'var(--paper-500)', 700: 'var(--paper-700)', 800: 'var(--paper-800)', 950: 'var(--paper-950)',
      },
      cinnabar: {
        700: 'var(--cinnabar-700)', 600: 'var(--cinnabar-600)', 400: 'var(--cinnabar-400)',
        200: 'var(--cinnabar-200)', 100: 'var(--cinnabar-100)',
      },
      jade: { 400: 'var(--jade-400)', 200: 'var(--jade-200)' },
      'on-cinnabar': 'var(--on-cinnabar)',
    },
    fontFamily: {
      display: ['Cormorant Garamond', 'Times New Roman', 'serif'],
      reading: ['Literata', 'Georgia', 'serif'],
      ui: ['Be Vietnam Pro', 'Segoe UI', 'system-ui', 'sans-serif'],
    },
    maxWidth: { reading: '760px', page: '1240px' },
    minHeight: { tap: '44px' },
    minWidth: { tap: '44px' },
    borderRadius: { sm: '8px', md: '12px', lg: '16px', xl: '20px' },
    transitionTimingFunction: { out: 'cubic-bezier(.2,.8,.2,1)' },
  },
};
