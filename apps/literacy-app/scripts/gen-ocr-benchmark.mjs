/**
 * 画一组拍照识字的基准图，输出到 scripts/fixtures/ocr/。
 *
 * 为什么不直接拿用户的照片当基准：一是没有可公开的授权照片，二是基准图必须
 * 一个字节都不变，否则今天 4/4、明天 3/4 分不清是引擎退化还是图换了。
 * 这里把三种「家里最常拍到」的版面固化下来，连同 public/ocr/sample-photo.png
 * 一起组成 scripts/test-ocr-accuracy.mjs 的基准集：
 *
 *   - book-page   绘本内页：小字、两行、纸色底，考的是小字号下的召回；
 *   - warm-light  暖光台灯下的字卡：偏黄、低对比、轻微倾斜，考的是预处理该救回来的那一类；
 *   - blackboard  黑板/夜间模式：深底白字，考的是反色版面不会整页丢字；
 *   - blurry-note 手抖拍糊的便签：小字 + 失焦，基准集里最难的一张，
 *                 它的召回率就是「孩子随手一拍」的下限。
 *
 * 基准图刻意不放进 public/：它们只在测试里用，进了 public/ 就要跟着构建产物
 * 发给每个孩子，还会被 Service Worker 预缓存，白占离线包的额度。
 *
 * 用法：node scripts/gen-ocr-benchmark.mjs（改了图才需要跑，不在构建链上）
 * 跑完记得重新跑 npm run test:ocr:accuracy 回填阈值。
 */

import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const OUT_DIR = new URL('./fixtures/ocr/', import.meta.url)
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'

const WIDTH = 640
const HEIGHT = 400

/** 两种中文字体轮着用：同一套字形上的高分说明不了引擎认不认得别家的字形。 */
const HEI = '"WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif'
const FALLBACK = '"Droid Sans Fallback", "WenQuanYi Micro Hei", sans-serif'

const SHEETS = [
  {
    name: 'book-page',
    body: `
      body {
        background: linear-gradient(160deg, #fdf8ee 0%, #f3e9d6 100%);
        font-family: ${FALLBACK};
      }
      .page {
        width: 520px; padding: 44px 36px; border-radius: 6px; background: #fffdf7;
        box-shadow: 0 8px 22px rgba(70, 52, 30, 0.18);
      }
      p { margin: 0; font-size: 52px; line-height: 1.5; letter-spacing: 10px; color: #1b1712 }
    `,
    html: '<div class="page"><p>白云青山绿水</p><p>花草鱼鸟人家</p></div>'
  },
  {
    name: 'warm-light',
    // 台灯下的字卡：整张偏黄、明暗不匀、拿歪了一点，正是 utils/ocr.js 里
    // 灰度 + 对比度拉伸要处理的那种照片
    body: `
      body {
        background: radial-gradient(90% 70% at 22% 18%, #f6e2b6 0%, #d8bd8b 62%, #b99f70 100%);
        font-family: ${HEI};
      }
      .card {
        transform: rotate(-1.6deg);
        padding: 38px 56px; border-radius: 12px;
        background: linear-gradient(120deg, #efe0c2, #e2cfa8);
        box-shadow: 0 14px 30px rgba(90, 66, 30, 0.28);
      }
      p { margin: 0; font-size: 80px; letter-spacing: 22px; color: #4a3a22 }
    `,
    html: '<div class="card"><p>上下左右</p></div>'
  },
  {
    name: 'blackboard',
    // 黑板与夜间模式都是深底白字：预处理只拉对比度、不反色，
    // 这张图守住「反色版面也不能整页丢字」
    body: `
      body { background: #1f2a24; font-family: ${HEI} }
      .board {
        padding: 40px 60px; border: 6px solid #6b5a3c; border-radius: 8px;
        background: #24302a;
      }
      p { margin: 0; font-size: 84px; letter-spacing: 24px; color: #f2f6f0 }
    `,
    html: '<div class="board"><p>天地人和</p></div>'
  },
  {
    name: 'blurry-note',
    // 手没端稳：整张失焦、字又小。这张不指望全认出来，但也不许一个字都不剩
    body: `
      body { background: #f0eee9; font-family: ${FALLBACK} }
      .note {
        filter: blur(2px) contrast(0.8);
        width: 470px; padding: 30px 34px; border-radius: 4px; background: #fbfaf6;
        box-shadow: 0 6px 18px rgba(40, 40, 40, 0.16);
      }
      p { margin: 0; font-size: 34px; line-height: 1.6; letter-spacing: 4px; color: #2b2b2b }
    `,
    html: '<div class="note"><p>今天我们一起</p><p>读书写字画画</p></div>'
  }
]

const pageHtml = (sheet) => `<!doctype html><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0 }
  body { width: ${WIDTH}px; height: ${HEIGHT}px; display: grid; place-items: center }
  ${sheet.body}
</style>${sheet.html}`

await mkdir(OUT_DIR, { recursive: true })

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage']
})
try {
  const page = await browser.newPage()
  await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 1 })
  for (const sheet of SHEETS) {
    await page.setContent(pageHtml(sheet), { waitUntil: 'load' })
    const png = await page.screenshot({ type: 'png' })
    await writeFile(fileURLToPath(new URL(`${sheet.name}.png`, OUT_DIR)), png)
    console.log(`[ocr] 基准图 ${sheet.name}.png：${(png.length / 1024).toFixed(0)} KB`)
  }
} finally {
  await browser.close()
}
