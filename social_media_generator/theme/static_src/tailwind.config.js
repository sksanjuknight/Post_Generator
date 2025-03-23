// social_media_generator/theme/static_src/tailwind.config.js

module.exports = {
    content: [
      // Templates in project
      '../templates/**/*.html',
      '../../templates/**/*.html',
      '../../**/templates/**/*.html',
      
      // Templates in apps
      '../../**/templates/**/*.html',
      '../../**/forms.py',
      
      // JavaScript files
      '../../**/static/js/**/*.js',
    ],
    theme: {
      extend: {
        colors: {
          primary: {
            50: '#f0f9ff',
            100: '#e0f2fe',
            200: '#bae6fd',
            300: '#7dd3fc',
            400: '#38bdf8',
            500: '#0ea5e9',
            600: '#0284c7',
            700: '#0369a1',
            800: '#075985',
            900: '#0c4a6e',
          },
          secondary: {
            50: '#f5f3ff',
            100: '#ede9fe',
            200: '#ddd6fe',
            300: '#c4b5fd',
            400: '#a78bfa',
            500: '#8b5cf6',
            600: '#7c3aed',
            700: '#6d28d9',
            800: '#5b21b6',
            900: '#4c1d95',
          },
        },
        spacing: {
          '72': '18rem',
          '84': '21rem',
          '96': '24rem',
        },
        fontFamily: {
          sans: ['Inter', 'system-ui', 'sans-serif'],
          serif: ['Georgia', 'serif'],
        },
      },
    },
    plugins: [
      require('@tailwindcss/forms'),
    ],
  }