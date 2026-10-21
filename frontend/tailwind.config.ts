import type { Config } from 'tailwindcss';
// Theme từ bàn giao thiết kế (tokens/tailwind-theme.js), giá trị thật là biến CSS trong tokens.css.
import theme from './src/styles/tailwind-theme.cjs';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: theme as Config['theme'],
  plugins: [],
} satisfies Config;
