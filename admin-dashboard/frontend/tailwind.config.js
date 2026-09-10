/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Vaporwave Cyberpunk Theme
        neon: {
          pink: '#ff006e',
          cyan: '#00f5ff',
          purple: '#b026ff',
          blue: '#00d4ff',
          green: '#00ff9f',
        },
        dark: {
          900: '#0a0a0f',
          800: '#12121a',
          700: '#1a1a2e',
          600: '#252538',
          500: '#2e2e48',
        }
      },
      boxShadow: {
        'neon-pink': '0 0 20px rgba(255, 0, 110, 0.5), 0 0 40px rgba(255, 0, 110, 0.3)',
        'neon-cyan': '0 0 20px rgba(0, 245, 255, 0.5), 0 0 40px rgba(0, 245, 255, 0.3)',
        'neon-purple': '0 0 20px rgba(176, 38, 255, 0.5), 0 0 40px rgba(176, 38, 255, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 8s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(255, 0, 110, 0.5)' },
          '100%': { boxShadow: '0 0 40px rgba(0, 245, 255, 0.8)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        }
      },
      fontFamily: {
        'cyber': ['Orbitron', 'sans-serif'],
        'mono': ['Space Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
