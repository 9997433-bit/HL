import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { inlineEntryCss } from '../../scripts/vite-critical-css-plugin.mjs'
import { offlinePrecache } from '../../scripts/vite-offline-plugin.mjs'

export default defineConfig({
  base: './',
  plugins: [
    vue(),
    inlineEntryCss(),
    /**
     * 拍照识字的 wasm 内核 + 语言包近 6 MB。放进预缓存等于每个访客一进门就下载
     * 一个多半用不上的大件，所以这三个文件留给 sw.js 里的按需缓存：
     * 第一次真的去认字才下载，下载完照样离线可用。
     *
     * 跟读的离线评测包（asr/models/）同理，而且更严：它由家长点「下载」才取，
     * 逐文件校验 sha256 后存进 utils/offlineAsr.js 自己的版本化缓存，
     * 混进 precache 会让每个访客都替一个可选功能买单。
     */
    offlinePrecache({
      exclude: [/^ocr\/(?:worker\.min|tesseract-core|chi_sim)/, /^asr\/models\//]
    })
  ],
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
         *
         * 玩步的手写剧本同理（play-rich-u7.js）：玩到这一单元才下载那一片。
         * 起名字不只是好看——scripts/check-bundle.mjs 靠这两组名字在 dist 上验
         * 「课文包 / 手写剧本没有被同步拉进首屏或单字详情」。
         */
        manualChunks(id) {
          const unit = id.match(/src[\\/]data[\\/]chars[\\/](u\d+)\.js$/)
          if (unit) return `chars-${unit[1]}`
          const play = id.match(/src[\\/]data[\\/]play-rich[\\/](u\d+)\.js$/)
          return play ? `play-rich-${play[1]}` : null
        }
      }
    }
  },
  server: {
    host: true,
    port: 5173
  }
})
