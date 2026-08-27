/**
 * 画一组拍照识字的基准图，输出到 scripts/fixtures/ocr/。
 *
 * 为什么不直接拿用户的照片当基准：一是没有可公开的授权照片，二是基准图必须
 * 一个字节都不变，否则今天 4/4、明天 3/4 分不清是引擎退化还是图换了。
 * 这里把八种「家里最常拍到」的版面固化下来，连同 public/ocr/sample-photo.png
 * 一起组成 scripts/test-ocr-accuracy.mjs 的基准集。
 *
 * 印刷体（ROUND8_H4 起）：
 *
 *   - book-page   绘本内页：小字、两行、纸色底，考的是小字号下的召回；
 *   - warm-light  暖光台灯下的字卡：偏黄、低对比、轻微倾斜，考的是预处理该救回来的那一类；
 *   - blackboard  黑板/夜间模式：深底白字，考的是反色版面不会整页丢字；
 *   - blurry-note 手抖拍糊的便签：小字 + 失焦，印刷体里最难的一张。
 *
 * 扩样（ROUND9_H2）：前四张全是「摆好了拍」，可孩子举着手机的时候不是这样。
 * 这四张各补一类真实退化，也是 test-ocr-accuracy.mjs 里的四个 tier：
 *
 *   - handwriting  手写 tier：作业本上一笔一画写的字。没有可用的手写中文字体，
 *                  这里用逐字的旋转/位移/缩放/斜切抖动去逼近「手写不齐」，
 *                  抖动量写死在 JITTER 里——基准图必须每次画出来都一样；
 *   - low-light    低光 tier：夜里没开够灯，深底 + 暗字 + 传感器噪点，
 *                  考的是对比度拉伸能不能把字从噪点里拽出来；
 *   - busy-bg      复杂背景 tier：花桌布上摆着的字卡，画面里全是跟笔画抢注意力的
 *                  格纹和圆点，考的是引擎会不会把背景纹理认成字；
 *   - angled-card  斜拍 tier：孩子斜着举手机，字卡带透视变形 + 半边手影，
 *                  考的是非正视角下的召回。
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

/**
 * 手写 tier 的抖动表：[旋转度数, 纵向位移 px, 缩放, 斜切度数]。
 * 写死而不是随机，是因为基准图一个字节都不能变——random 一次一个样，
 * 分数掉了就分不清是引擎退化还是图重画了。
 */
const JITTER = [
  [-5.5, 7, 1.07, -5],
  [4.5, -8, 0.92, 4],
  [-2.8, 10, 1.03, -6],
  [6, -5, 0.95, 3.5]
]

/** 一行「手写」字：逐字套 JITTER，写不齐才像作业本上的字。 */
const handwritten = (text) =>
  [...text]
    .map((char, i) => {
      const [rotate, dy, scale, skew] = JITTER[i % JITTER.length]
      return (
        `<span style="display:inline-block;transform:rotate(${rotate}deg) ` +
        `translateY(${dy}px) scale(${scale}) skewX(${skew}deg)">${char}</span>`
      )
    })
    .join('')

/** 传感器噪点：feTurbulence 铺一层，低光那张才不是一块干净的暗色。 */
const NOISE = encodeURI(
  "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>" +
    "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' " +
    "numOctaves='3' seed='7' stitchTiles='stitch'/></filter>" +
    "<rect width='160' height='160' filter='url(%23n)'/></svg>"
).replace(/#/g, '%23')

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
  },
  {
    name: 'handwriting',
    // 作业本上一笔一画写出来的字：蓝墨水、横格纸、每个字都写不齐。
    // 印刷体字卡全认得出不代表这一类也行，手写 tier 的召回率单独定线。
    body: `
      body {
        background:
          repeating-linear-gradient(180deg, transparent 0 74px, #c3d4e8 74px 76px),
          #fbfaf4;
        font-family: ${HEI};
      }
      .sheet { width: 540px; padding: 26px 30px }
      p {
        margin: 0; font-size: 76px; letter-spacing: 24px; color: #1f3a93;
        -webkit-text-stroke: 0.6px #1f3a93;
      }
    `,
    html: `<div class="sheet"><p>${handwritten('春夏秋冬')}</p></div>`
  },
  {
    name: 'low-light',
    // 天黑了只开一盏小灯：整张压暗、字几乎融进背景，还盖着一层传感器噪点。
    //
    // 88px 不是随手挑的字号。深底浅字这一类，tesseract 认反色版面有个字块大小的
    // 下限：同一张图把字缩到 82px 就整页零召回（实测 0/4，不是「少认几个」）。
    // 改这张之前先跑一遍 --json，别看着「眼睛读得出来」就下结论。
    body: `
      body { background: #14161b; font-family: ${HEI} }
      body::after {
        content: ''; position: fixed; inset: 0; opacity: 0.2;
        background-image: url("${NOISE}");
      }
      .dim {
        padding: 40px 58px; border-radius: 10px;
        background: radial-gradient(85% 95% at 38% 26%, #363b43 0%, #23262c 100%);
      }
      p { margin: 0; font-size: 88px; letter-spacing: 20px; color: #9aa1ab }
    `,
    html: '<div class="dim"><p>风雨雷电</p></div>'
  },
  {
    name: 'busy-bg',
    // 花桌布上摆着的字卡：格纹、圆点、几支蜡笔一起往镜头里挤。
    // 认错背景纹理的引擎会在这张上冒出一串图上根本没有的字（MAX_NOISE 守着）。
    body: `
      body {
        background:
          repeating-linear-gradient(45deg, #f3c6c0 0 26px, #e9a9a1 26px 52px),
          #e9a9a1;
        font-family: ${FALLBACK};
      }
      .dots {
        position: fixed; inset: 0;
        background-image: radial-gradient(#7fa8d4 9px, transparent 10px);
        background-size: 64px 64px; opacity: 0.75;
      }
      .crayon {
        position: fixed; width: 168px; height: 30px; border-radius: 15px;
        box-shadow: 0 4px 10px rgba(60, 30, 20, 0.35);
      }
      .c1 { background: #4f9d5a; left: -34px; top: 40px; transform: rotate(24deg) }
      .c2 { background: #f2b53a; right: -40px; bottom: 54px; transform: rotate(-18deg) }
      .card {
        position: relative; transform: rotate(2.2deg);
        padding: 32px 46px; border-radius: 10px; background: #fdfcf7;
        box-shadow: 0 12px 26px rgba(50, 25, 20, 0.32);
      }
      p { margin: 0; font-size: 74px; letter-spacing: 18px; color: #211d18 }
    `,
    html:
      '<div class="dots"></div><i class="crayon c1"></i><i class="crayon c2"></i>' +
      '<div class="card"><p>红黄蓝绿</p></div>'
  },
  {
    name: 'angled-card',
    // 孩子斜着举手机拍的字卡：透视一压，右半边还盖着自己的手影。
    // 正视角下的高分不代表这一类也稳，斜拍 tier 的下限比印刷体低一档。
    body: `
      body { background: #ded6c8; font-family: ${HEI}; perspective: 900px }
      .card {
        position: relative;
        transform: rotateY(-26deg) rotateX(9deg) rotate(-2.4deg);
        padding: 40px 54px; border-radius: 10px; background: #fbf7ee;
        box-shadow: 0 18px 34px rgba(60, 48, 30, 0.35);
      }
      .card::after {
        content: ''; position: absolute; inset: 0; border-radius: 10px;
        background: linear-gradient(100deg, rgba(0, 0, 0, 0) 46%, rgba(28, 22, 12, 0.42) 100%);
      }
      p { margin: 0; font-size: 82px; letter-spacing: 20px; color: #262019 }
    `,
    html: '<div class="card"><p>手口耳目</p></div>'
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
