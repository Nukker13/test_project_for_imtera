import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Бэкенд проксируется, а не вызывается напрямую по своему адресу. Это не
// украшательство: Sanctum в SPA-режиме аутентифицирует по сессионной куке, и
// когда фронт и API для браузера живут на одном origin, куки работают сами
// собой — без настройки CORS, SameSite и списка stateful-доменов.
const backend = process.env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/sanctum': { target: backend, changeOrigin: true },
    },
  },
})
