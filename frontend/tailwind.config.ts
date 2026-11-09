import type { Config } from "tailwindcss";

/**
 * Design tokens — fixed by the project visual rules. Do not improvise colors.
 * primary deep green, accent red (alerts/blocked/header accent line only).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#0B5D3B", dark: "#084A30", light: "#EAF3EE" },
        accent: "#C1272D",
        background: "#F7F8F6",
        stroke: "#E3E7E2",
        ink: { DEFAULT: "#14201A", secondary: "#5B6B62" },
        success: "#2E7D32",
        warning: "#B7791F",
        danger: "#C1272D",
        info: "#1F5F8B",
      },
      maxWidth: {
        page: "1200px",
      },
    },
  },
  plugins: [],
};

export default config;
