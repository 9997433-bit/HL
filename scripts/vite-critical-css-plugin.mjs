/**
 * Inline the entry stylesheet so the first useful paint does not wait for a
 * second request. Route-level styles remain separate lazy chunks.
 */
export function inlineEntryCss() {
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
          },
        )
        output.source = html
      }
    },
  }
}
