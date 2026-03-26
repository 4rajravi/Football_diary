/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // The World Monitor "Sharp" Palette
        night: {
          950: '#020617', // Deepest background
          900: '#0f172a', // Main surface (cards/sidebar)
          800: '#1e293b', // Hover states / active
          700: '#334155', // Borders (The "Sharp" line)
        },
        // High-tech accents
        accent: {
          cyan: '#22d3ee',   // Tech/Active
          emerald: '#10b981', // Success/Positive
          amber: '#f59e0b',   // Warning/Gold
          crimson: '#f43f5e', // Alert/Danger
        }
      },
      fontFamily: {
        // Inter for UI, JetBrains Mono for that "monitor/data" look
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'], 
      },
      borderWidth: {
        '0.5': '0.5px', // Ultra-sharp hairline borders
      }
    },
  },
  plugins: [],
}