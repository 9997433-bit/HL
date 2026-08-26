import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { offlinePrecache } from '../../scripts/vite-offline-plugin.mjs'

/**
 * The app shell stylesheet is required before Vue can paint anything useful.
 * Vite normally emits it as a blocking <link>; putting that small critical
 * asset directly in index.html removes a network round-trip while route CSS
 * remains split and lazy.
 */
function inlineEntryCss() {
  return {
    name: 'inline-entry-css',
    apply: 'build',
    enforce: 'post',
    generateBundle(_options, bundle) {
      for (const output of Object.values(bundle)) {
        if (output.type !== 'asset' || !output.fileName.endsWith('.html')) continue

        let html = String(output.source)
        html = html.replace(
          /<link rel="stylesheet" crossorigin href="([^"]+\.css)">/g,
          (link, href) => {
            const fileName = href.replace(/^\.?\//, '')
            const stylesheet = bundle[fileName]
            if (stylesheet?.type !== 'asset') return link

            const css = String(stylesheet.source).replace(/<\/style/gi, '<\\/style')
            delete bundle[fileName]
            return `<style data-critical>${css}</style>`
          }
        )
        output.source = html
      }
    }
  }
}

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
         * 也保证主包里只有字表索引，不会把 500 个字的释义例句一次性背上。
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
