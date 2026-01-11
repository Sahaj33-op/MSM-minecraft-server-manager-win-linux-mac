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
        // Modern deep black theme
        background: '#0a0a0f',
        'background-secondary': '#111118',
        'background-tertiary': '#06060a',
        foreground: '#f0f0f5',
        'foreground-muted': '#6b6b7a',

        // Primary green
        primary: {
          DEFAULT: '#22c55e',
          hover: '#16a34a',
          dark: '#166534',
          foreground: '#000000',
          glow: 'rgba(34, 197, 94, 0.4)',
        },

        // Secondary
        secondary: {
          DEFAULT: '#1a1a24',
          hover: '#252532',
          foreground: '#f0f0f5',
        },

        // Accent (orange for warnings/actions)
        accent: {
          DEFAULT: '#f59e0b',
          hover: '#d97706',
          foreground: '#000000',
        },

        // Destructive (red)
        destructive: {
          DEFAULT: '#ef4444',
          hover: '#dc2626',
          foreground: '#ffffff',
        },

        // Card backgrounds
        card: {
          DEFAULT: '#12121a',
          hover: '#1a1a26',
          border: '#2a2a38',
        },

        // Console
        console: {
          bg: '#08080c',
          text: '#b8c0cc',
          border: '#1e1e28',
        },

        // Status colors
        online: '#22c55e',
        offline: '#52525b',
        starting: '#f59e0b',
        stopping: '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'glow': '0 0 32px rgba(34, 197, 94, 0.4)',
        'glow-sm': '0 0 16px rgba(34, 197, 94, 0.3)',
        'glow-lg': '0 0 48px rgba(34, 197, 94, 0.5)',
        'card': '0 8px 32px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 12px 48px rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        'slide-down': 'slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        'shimmer': 'shimmer 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(20px) scale(0.95)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
