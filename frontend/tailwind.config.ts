import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff", 100: "#e0e7ff", 200: "#c7d2fe", 300: "#a5b4fc",
          400: "#818cf8", 500: "#6366f1", 600: "#4f46e5", 700: "#4338ca",
          800: "#3730a3", 900: "#312e81", 950: "#1e1b4b",
        },
        accent: {
          400: "#c084fc", 500: "#a855f7", 600: "#9333ea", 700: "#7e22ce",
        },
      },
      boxShadow: {
        glow: "0 20px 60px -15px rgba(99,102,241,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
