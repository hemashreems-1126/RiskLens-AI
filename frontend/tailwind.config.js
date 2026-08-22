/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          low: "#16a34a",
          medium: "#d97706",
          high: "#ea580c",
          critical: "#dc2626",
        },
        brand: {
          900: "#0f172a",
          800: "#1e293b",
          700: "#334155",
          600: "#475569",
          50: "#f8fafc",
        },
      },
    },
  },
  plugins: [],
}
