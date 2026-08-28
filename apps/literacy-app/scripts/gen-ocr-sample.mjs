/**
 * 画一张拍照识字的示例图，输出到 public/ocr/sample-photo.png。
 *
 * 为什么要入库一张图，而不是运行时用 canvas 现画？
 *   现画依赖设备上装了哪套中文字体，同一段代码在平板、Windows、无头 Chrome 上
 *   画出来的字形完全不同，识别结果也就跟着飘。入库一张图，孩子第一次点「试一张示例」
 *   看到的效果和 smoke 测试里断言的效果是同一个。
 *
 * 用法：node scripts/gen-ocr-sample.mjs（改了图才需要跑，不在构建链上）
 */

import { writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const OUT = fileURLToPath(new URL('../public/ocr/sample-photo.png', import.meta.url))
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'

// 四个字都在字表最前面的单元里：示例一定认得出，也一定讲得了
const PAGE = `<!doctype html><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0 }
  body {
    width: 640px; height: 400px;
    display: grid; place-items: center;
    background: radial-gradient(120% 120% at 30% 10%, #fbf6ec, #e9ded0);
    font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  }
  .card {
    padding: 40px 52px; border-radius: 10px; background: #fff;
    box-shadow: 0 10px 28px rgba(60, 44, 24, 0.22);
  }
  p { margin: 0; font-size: 96px; letter-spacing: 26px; color: #14110d }
</style><div class="card"><p>日月山水</p></div>`

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage']
})
try {
  const page = await browser.newPage()
  await page.setViewport({ width: 640, height: 400, deviceScaleFactor: 1 })
  await page.setContent(PAGE, { waitUntil: 'load' })
  const png = await page.screenshot({ type: 'png' })
  await writeFile(OUT, png)
  console.log(`[ocr] 示例图已生成：${(png.length / 1024).toFixed(0)} KB`)
} finally {
  await browser.close()
}
