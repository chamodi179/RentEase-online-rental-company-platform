import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12203A",       // deep navy — headers, primary text, trust
        "ink-soft": "#3C4B66",
        paper: "#F7F6F2",     // warm off-white background
        amber: "#E7A93C",     // booking / CTA accent
        "amber-dark": "#C68B27",
        available: "#2F8F6E", // status: available/confirmed
        pending: "#C68B27",
        danger: "#B5493D",
        line: "#E1DED4",
      },
      fontFamily: {
        display: ["ui-sans-serif", "system-ui", "sans-serif"],
        body: ["ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: { card: "10px" },
    },
  },
  plugins: [],
};
export default config;
