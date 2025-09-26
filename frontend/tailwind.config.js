/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "node_modules/flowbite-react/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          DEFAULT: "#111827", // Dark blue
          light: "#1F2937",
          dark: "#0F172A",
        },
        accent: {
          DEFAULT: "#40C0FF", // Light blue accent
          dark: "#0EA5E9",
          light: "#7DD3FC",
        },
        // Neutral grays
        sidebar: "#374151", // Gray for sidebar
        chat: "#4B5563", // Gray for chat areas
        backgroundColor: "",
      },
    },
  },
  plugins: [require("flowbite/plugin")],
  // corePlugins: {
  //   preflight: false,
  // },
};
