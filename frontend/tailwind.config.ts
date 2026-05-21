import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#1E5DB8",
          dark: "#0A2540",
          light: "#4A90E2",
          accent: "#FF6B35",
          "accent-light": "#FFA570",
        },
        ink: "#1A202C",
        muted: "#5A6B7B",
      },
      fontFamily: {
        sans: ["Heebo", "Arial", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 16px rgba(10, 37, 64, 0.08)",
        "card-hover": "0 20px 50px rgba(10, 37, 64, 0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
