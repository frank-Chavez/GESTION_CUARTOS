/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './modules/**/templates/**/*.html',
    './static/**/*.js',
    './node_modules/flowbite/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
      },
      colors: {
        'dark-bg': '#1a1410',
        'dark-card': '#261d17',
        'dark-border': '#3d2a1f',
        'dark-text': '#e5e5e5',
        'dark-muted': '#a0a0a0',
        'dark-accent': '#ef893f',
      },
    },
  },
  plugins: [require('flowbite/plugin')],
};
