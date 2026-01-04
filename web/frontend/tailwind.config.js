/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Particle News inspired dark theme
        dark: {
          900: '#0a0a0b',
          800: '#111113',
          700: '#1a1a1d',
          600: '#242428',
          500: '#2d2d32',
        },
        accent: {
          orange: '#e07c4a',
          blue: '#4a90d9',
          coral: '#e05a5a',
          gold: '#d4a44a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
