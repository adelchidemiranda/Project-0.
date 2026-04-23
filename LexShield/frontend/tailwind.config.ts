import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "#C9A84C", // Gold accent
          foreground: "#1a1f36",
        },
        navy: {
          DEFAULT: "#1a1f36",
          light: "#2d344d",
          dark: "#0f121d",
        }
      },
      fontFamily: {
        serif: ["var(--font-cormorant)"],
        sans: ["var(--font-inter)"],
      },
    },
  },
  plugins: [],
};
export default config;
