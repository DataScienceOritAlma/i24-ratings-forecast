import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#1E5DB8",
          dark: "#0A2540",
          light: "#4A90E2",
          // Accent is reserved for the security-event scenario and warnings.
          // Dark enough for white text (5.2:1).
          accent: "#C2410C",
          "accent-light": "#FDBA74",
        },
        ink: "#16202E",
        muted: "#55657A",
        canvas: "#F5F7FA",
        line: "#E1E7EF",
      },
      fontFamily: {
        sans: ["var(--font-heebo)", "Heebo", "Arial", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(10, 37, 64, 0.05), 0 1px 3px rgba(10, 37, 64, 0.04)",
        "card-hover": "0 8px 24px rgba(10, 37, 64, 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
