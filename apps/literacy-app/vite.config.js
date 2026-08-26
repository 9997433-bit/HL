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
        manualChunks(id) {
          // characters.js imports this tiny catalogue too; keep the catalogue
          // with the shell instead of letting Rollup pull it into the rich-data
          // chunk and preload that chunk on the home page.
          if (id.endsWith('/src/data/character-index.js')) return 'character-index'
          if (id.endsWith('/src/data/characters.js')) return 'characters'
        }
      }
    }
  },
  server: {
    host: true,
    port: 5173
  }
})
