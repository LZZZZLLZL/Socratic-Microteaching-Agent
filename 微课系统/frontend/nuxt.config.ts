// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@element-plus/nuxt'],

  elementPlus: {
    importStyle: 'css',
  },

  routeRules: {
    '/api/**': { proxy: 'http://127.0.0.1:8000/**' },
  },

  css: ['~/assets/styles/main.css'],
})
