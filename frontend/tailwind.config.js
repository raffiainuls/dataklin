/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vsbg: '#1e1e1e', // vscode like background
        vssid: '#252526', // vscode sidebar/panels
        vshl: '#37373d', // vscode highlight/borders
        vsblue: '#007acc', // vscode blue
        vstext: '#cccccc', // vscode text
        vsgreen: '#4ec9b0', // vscode green
        vsorange: '#ce9178', // vscode orange
      }
    },
  },
  plugins: [],
}
