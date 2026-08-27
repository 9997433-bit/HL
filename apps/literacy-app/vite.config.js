import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { inlineEntryCss } from '../../scripts/vite-critical-css-plugin.mjs'
import { offlinePrecache } from '../../scripts/vite-offline-plugin.mjs'

export default defineConfig({
  base: './',
  plugins: [vue(), inlineEntryCss(), offlinePrecache()],
  resolve: {
    alias: {
      '@shared': fileURLToPath(new URL('../../shared', import.meta.url)),
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        /**
         * 每个单元的课文单独成块（chars-u7.js 这样），文件名一眼能看出是哪一单元，
         * 也保证主包里只有字表索引，不会把上千个字的释义例句一次性背上。
         */
        manualChunks(id) {
          const unit = id.match(/src[\\/]data[\\/]chars[\\/](u\d+)\.js$/)
          return unit ? `chars-${unit[1]}` : null
        }
      }
    }
  },
  server: {
    host: true,
    port: 5173
  }
})
