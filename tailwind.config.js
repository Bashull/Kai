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
        'kai-dark': '#111827',
        'kai-surface': '#1f2937',
        'kai-green': '#39ff14',
        'kai-primary': '#4f46e5',
        'border-color': '#374151',
        'text-primary': '#f3f4f6',
        'text-secondary': '#9ca3af',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        orbitron: ['Orbitron', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
        'text-glow': 'text-glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        'text-glow': {
          'from': { textShadow: '0 0 4px rgba(57, 255, 20, 0.5), 0 0 8px rgba(57, 255, 20, 0.4)' },
          'to': { textShadow: '0 0 8px rgba(57, 255, 20, 0.5), 0 0 16px rgba(79, 70, 229, 0.4)' }
        },
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms')
  ],
}