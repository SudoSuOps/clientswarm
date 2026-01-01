/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // ClientSwarm medical palette
        client: {
          bg: {
            dark: '#0a0f1a',
            card: '#111827',
            elevated: '#1f2937',
          },
          text: {
            DEFAULT: '#f9fafb',
            dim: '#9ca3af',
            muted: '#6b7280',
          },
          blue: {
            DEFAULT: '#3b82f6',
            light: '#60a5fa',
            dark: '#2563eb',
          },
          teal: {
            DEFAULT: '#14b8a6',
            light: '#2dd4bf',
          },
          success: '#10b981',
          warning: '#f59e0b',
          error: '#ef4444',
          border: '#374151',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
