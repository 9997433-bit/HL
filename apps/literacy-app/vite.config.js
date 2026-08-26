import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { offlinePrecache } from '../../scripts/vite-offline-plugin.mjs'

export default defineConfig({
  base: './',
  plugins: [vue(), offlinePrecache()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: true,
    port: 5173
  }
})
