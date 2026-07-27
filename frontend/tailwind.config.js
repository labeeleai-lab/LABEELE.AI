/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'royal-blue': {
          50: '#f0f4f9',
          100: '#e1eaf3',
          200: '#c3d5e8',
          300: '#a5bfdd',
          400: '#875ad2',
          500: '#1F3A93',
          600: '#1a3080',
          700: '#15266d',
          800: '#0f1c4d',
          900: '#0a1230',
        },
        'gold': {
          50: '#fffdf5',
          100: '#fffae6',
          200: '#fff4cc',
          300: '#fff0b3',
          400: '#ffe699',
          500: '#D4AF37',
          600: '#c9a82e',
          700: '#b39a27',
          800: '#9d8a1f',
          900: '#8a7618',
        },
        'labeele-gold': '#D4AF37',
        'labeele-dark': '#0F1C4D',
        'labeele-blue': '#1F3A93',
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '12px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Monaco', 'Courier New', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}