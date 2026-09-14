/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // QODEKRAFT brand palette
        brand: {
          50:  '#e8f0fe',
          100: '#c5d8fc',
          200: '#9ab8f9',
          300: '#6f97f6',
          400: '#3d6df0',
          500: '#2563EB', // primary blue
          600: '#1d55cc',
          700: '#1645ab',
          800: '#0e348a',
          900: '#0a2566',
        },
        dark: {
          900: '#080E1E', // deepest background
          800: '#0F1729', // main background
          700: '#1A2540', // card background
          600: '#243054', // elevated card
          500: '#2E3D68', // borders/dividers
          400: '#3D4F7A', // subtle elements
        },
        accent: {
          blue:   '#2563EB',
          indigo: '#4F46E5',
          sky:    '#0EA5E9',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
        'card':  '0 4px 24px rgba(0, 0, 0, 0.25)',
        'glow':  '0 0 20px rgba(37, 99, 235, 0.4)',
        'glow-sm': '0 0 10px rgba(37, 99, 235, 0.25)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-brand': 'linear-gradient(135deg, #1A2540 0%, #0F1729 50%, #080E1E 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(26, 37, 64, 0.8), rgba(15, 23, 41, 0.95))',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(16px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        slideInRight: { from: { opacity: '0', transform: 'translateX(16px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        pulseGlow: { '0%, 100%': { boxShadow: '0 0 10px rgba(37, 99, 235, 0.3)' }, '50%': { boxShadow: '0 0 25px rgba(37, 99, 235, 0.6)' } },
      },
      borderRadius: {
        'xl2': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
