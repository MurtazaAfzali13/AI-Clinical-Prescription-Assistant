import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1280px" } },
    extend: {
      colors: {
        // Design tokens derived from the Watan Hospital letterhead:
        // deep clinical teal as the anchor, a lighter aqua for accents,
        // warm off-white paper background to echo the printed prescription.
        clinic: {
          950: "#0b3441",
          900: "#0e4a5c",
          800: "#12607a",
          700: "#177a99",
          600: "#1f96ba",
          500: "#2eb0d6",
          100: "#e3f3f7",
          50: "#f5fafb",
        },
        paper: "#fbfaf7",
        ink: "#1c2b2f",
        warn: {
          amber: "#b8860b",
          red: "#b3261e",
        },
        border: "hsl(200 20% 88%)",
        ring: "#177a99",
        background: "#fbfaf7",
        foreground: "#1c2b2f",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.25rem",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
