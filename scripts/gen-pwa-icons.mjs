/**
 * 从各 App 的 favicon.svg 生成 PWA / Android 所需的 PNG 图标。
 * 依赖 puppeteer-core（与 axe 门禁共用），无需额外图像库。
 */

import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const APPS = [
  { id: 'literacy-app', svg: 'apps/literacy-app/public/favicon.svg' },
  { id: 'math-app', svg: 'apps/math-app/public/favicon.svg' }
]

const SIZES = [
  { name: 'icon-192.png', size: 192, maskable: false },
  { name: 'icon-512.png', size: 512, maskable: false },
  { name: 'icon-maskable-512.png', size: 512, maskable: true }
]

function chromePath() {
  for (const candidate of [
    process.env.CHROME_PATH,
    '/usr/bin/google-chrome-stable',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium'
  ]) {
    if (candidate) return candidate
  }
  return '/usr/bin/chromium'
}

async function renderSvg(page, svg, size, maskable) {
  const padding = maskable ? Math.round(size * 0.1) : 0
  const inner = size - padding * 2
  const html = `<!doctype html><html><body style="margin:0;background:transparent">
    <div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center">
      <div style="width:${inner}px;height:${inner}px">${svg}</div>
    </div>
  </body></html>`
  await page.setViewport({ width: size, height: size, deviceScaleFactor: 1 })
  await page.setContent(html, { waitUntil: 'domcontentloaded', timeout: 10000 })
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))))
  return page.screenshot({ type: 'png', omitBackground: !maskable })
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: chromePath(),
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })

  try {
    const page = await browser.newPage()
    for (const app of APPS) {
      const svgPath = path.join(root, app.svg)
      const svg = await fs.readFile(svgPath, 'utf8')
      const outDir = path.join(root, 'apps', app.id, 'public', 'icons')
      await fs.mkdir(outDir, { recursive: true })
      for (const spec of SIZES) {
        const png = await renderSvg(page, svg, spec.size, spec.maskable)
        await fs.writeFile(path.join(outDir, spec.name), png)
        console.log(`[icons] ${app.id}/${spec.name}`)
      }
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error('gen-pwa-icons:', error.message)
  process.exit(1)
})
