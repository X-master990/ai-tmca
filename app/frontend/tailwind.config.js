/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy:  '#0F3057',
        teal:  '#008891',
        cyan:  '#E0F0F2',
        cream: '#FDF4E3',
        gold:  '#C5832B',
        ok:    '#27ae60',
        warn:  '#C0392B',
        ink:   '#1A1A2E',
        soft:  '#3D3D52',
      },
      fontFamily: {
        sans: ['"Noto Sans TC"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
