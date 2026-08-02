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
        paper: "hsl(var(--background))",
        ink: "hsl(var(--foreground))",
        warn: {
          amber: "#b8860b",
          red: "#b3261e",
        },
        border: "hsl(var(--border))",
        ring: "#177a99",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        muted: "hsl(var(--muted))",
        // Vitals-monitor dark palette for the analytics dashboard: near-black
        // teal (like a dimmed instrument screen) with a single mint "pulse"
        // accent that traces charts and sparklines, evoking an ECG readout
        // rather than a generic dark SaaS dashboard.
        vitals: {
          bg: "#071a20",
          surface: "#0e2830",
          line: "#1c3a42",
          pulse: "#35e0c0",
          "pulse-dim": "#1f8a76",
          warn: "#ff8a65",
          ink: "#eaf6f4",
          "ink-muted": "#7fa8a8",
        },
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
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
