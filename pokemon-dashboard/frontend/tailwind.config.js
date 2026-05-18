/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        pokemon: {
          red: "#CC0000",
          blue: "#003A70",
          yellow: "#FFCB05",
          dark: "#1a1a2e",
          card: "#16213e",
          border: "#0f3460",
        },
      },
    },
  },
  plugins: [],
};
