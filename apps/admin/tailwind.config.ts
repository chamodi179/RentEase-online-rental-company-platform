import type { Config } from "tailwindcss";

// Deliberately distinct from the customer app's palette: denser, cooler,
// built for tables and data — not a marketing surface (architecture doc §6).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#0F1720",        // sidebar / login screen chrome
        surface: "#FFFFFF",       // cards, panels, table backgrounds
        graphite: "#1C2733",      // primary text
        "graphite-soft": "#5B6B7C", // secondary/muted text
        line: "#DFE4E9",
        action: "#2563EB",        // admin actions — distinct from customer amber
        "action-dark": "#1D4ED8",
        ok: "#15803D",
        warn: "#B45309",
        danger: "#B91C1C",
      },
      borderRadius: { card: "8px" },
    },
  },
  plugins: [],
};
export default config;
