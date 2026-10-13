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
        space: {
          950: 'rgb(var(--space-950, 6 9 17) / <alpha-value>)',
          900: 'rgb(var(--space-900, 11 15 25) / <alpha-value>)',
          850: 'rgb(var(--space-850, 16 22 38) / <alpha-value>)',
          800: 'rgb(var(--space-800, 21 30 51) / <alpha-value>)',
          700: 'rgb(var(--space-700, 30 41 59) / <alpha-value>)',
          600: 'rgb(var(--space-600, 51 65 85) / <alpha-value>)',
        },
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
        },
        brand: {
          blue: '#3b82f6',
          purple: '#8b5cf6',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
