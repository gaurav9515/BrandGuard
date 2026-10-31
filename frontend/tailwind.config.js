/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-alt': 'var(--surface-alt)',
        border: 'var(--border)',
        text: 'var(--text)',
        'text-muted': 'var(--text-muted)',
        primary: 'var(--primary)',
        'primary-hover': 'var(--primary-hover)',
        accent: 'var(--accent)',
        bark: 'var(--bark)',
        blocker: 'var(--blocker)',
        'blocker-tint': 'var(--blocker-tint)',
        'warning-text': 'var(--warning-text)',
        'warning-tint': 'var(--warning-tint)',
        cleared: 'var(--cleared)',
        'cleared-tint': 'var(--cleared-tint)',
        info: 'var(--info)',
        'info-tint': 'var(--info-tint)',
        forest: {
          50: '#EAF5EE',
          100: '#CBE7D4',
          200: '#A3D9B5',
          700: '#13653F',
          800: '#0F5132',
          900: '#0B4226',
          950: '#0A3423',
        },
        brand: {
          50: '#EAF5EE',
          100: '#CBE7D4',
          500: '#10b981',
          700: '#065F46',
          800: '#0F5132',
          900: '#0F5132',
          950: '#0A3423',
        }
      },
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      }
    },
  },
  plugins: [],
}
