/**
 * ROUND10_H2 —— 把公开授权的真实照片切成基准图，输出到 scripts/fixtures/ocr/real-*.png。
 *
 * gen-ocr-benchmark.mjs 画的十张图全是浏览器渲染出来的：字形干净、笔画完整、
 * 噪点是我们自己撒上去的。它们能守住引擎侧退化，但守不住一件事——
 * 真实世界里的字长什么样。R9 那套合成图跑到总召回 100%，孩子举着手机拍小区
 * 告示牌却可能一个字都对不上，这中间的差距在合成图上是看不见的。
 *
 * 这个脚本补的就是那一段：从 Wikimedia Commons 取三张**真人用手机拍的**照片，
 * 只做三件事——裁剪、等比缩放、存成 PNG，一点增强都不加，让引擎看见真实的
 * 反光、断笔、树影和镜头畸变。
 *
 * 为什么只裁不修：
 *   - 裁剪对应孩子「把镜头对准那几个字」的动作，是识字 App 里真实发生的取景；
 *   - 缩放是必要的，原图 4000 px 宽送进 tesseract 又慢又不见得更准（实测见下）；
 *   - 灰度、对比度拉伸这些交给 utils/ocr.js 的 preprocess()，那是运行时的活，
 *     烘进基准图就等于把被测对象和测试数据混在一起了。
 *
 * 素材与授权（清单 fixtures/ocr/real-samples.json，署名同步进 THIRD_PARTY_NOTICES.md）：
 * 三张都是 CC BY-SA，裁剪后的 PNG 属于演绎作品，按同一许可再分发；
 * sha256 钉住原图，上游哪天换了文件当场报错，而不是悄悄换一张图重画基准。
 *
 * 裁剪框怎么定的（写死在清单里，不是随手截的）：
 *   - 只框住目标那一行字。「爱护花草／禁止踩踏」这种两行牌子只取第一行，
 *     因为「禁、止、踩、踏」四个字不在本应用字表里，留在画面里就会变成误检；
 *   - 边框要裁掉。当心类标牌外面那圈黑色矩形会被 tesseract 当成版面框，
 *     实测把边框留在画面里，同一张图的召回从 4/4 掉到 0/4（原文只剩「[ED」）；
 *   - 输出宽度按「字高落在 40–100 px」挑，每张单独实测过。同一张图放到 640 px
 *     反而比 320 px 差（爱护花草：320 px 4/4 conf 90，640 px 掉到 2/4），
 *     换清单里的 width 之前先跑 test-ocr-accuracy.mjs --json 看数。
 *
 * 用法：node scripts/gen-ocr-real-samples.mjs（要联网；改了清单才需要跑，不在构建链上）
 *      --keep-src 保留 .cache/ocr-src/ 下的原图，方便反复试裁剪框
 * 跑完记得重新跑 npm run test:ocr:accuracy 回填阈值。
 */

import { createHash } from 'node:crypto'
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const OUT_DIR = new URL('./fixtures/ocr/', import.meta.url)
const CACHE_DIR = new URL('../.cache/ocr-src/', import.meta.url)
const MANIFEST = new URL('./fixtures/ocr/real-samples.json', import.meta.url)
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'
const keepSrc = process.argv.includes('--keep-src')

/** Commons 要求带上能联系到人的 UA，匿名请求会被 403 挡掉。 */
const UA =
  'hongen-edu-apps/1.0 (https://github.com/; OCR benchmark fixture builder) node-fetch'

const { samples } = JSON.parse(await readFile(MANIFEST, 'utf8'))

/** 原图缓存在 .cache/ 下（已被 .gitignore 排除），重跑时不必反复拉 2 MB 的大图。 */
async function source(sample) {
  await mkdir(CACHE_DIR, { recursive: true })
  const cached = fileURLToPath(new URL(`${sample.name}.bin`, CACHE_DIR))
  if (!existsSync(cached)) {
    const res = await fetch(sample.file, { headers: { 'User-Agent': UA } })
    if (!res.ok) throw new Error(`${sample.name}：原图下载失败 HTTP ${res.status}`)
    await writeFile(cached, Buffer.from(await res.arrayBuffer()))
  }
  const buf = await readFile(cached)
  const sha = createHash('sha256').update(buf).digest('hex')
  if (sha !== sample.sha256) {
    throw new Error(
      `${sample.name}：原图 sha256 对不上——清单记的是 ${sample.sha256}，拿到的是 ${sha}。` +
        '上游换图了就核对授权、重定裁剪框，再把新的哈希写回清单。'
    )
  }
  return buf
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage']
})
try {
  const page = await browser.newPage()
  await page.goto('about:blank')
  for (const sample of samples) {
    const buf = await source(sample)
    const dataUrl = await page.evaluate(
      async (job, base64) => {
        const img = new Image()
        img.src = `data:image/jpeg;base64,${base64}`
        await img.decode()
        const [x0, y0, x1, y1] = job.crop
        const sx = Math.round(x0 * img.naturalWidth)
        const sy = Math.round(y0 * img.naturalHeight)
        const sw = Math.round((x1 - x0) * img.naturalWidth)
        const sh = Math.round((y1 - y0) * img.naturalHeight)
        const canvas = document.createElement('canvas')
        canvas.width = job.width
        canvas.height = Math.round((sh / sw) * job.width)
        const ctx = canvas.getContext('2d')
        ctx.imageSmoothingQuality = 'high'
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
        return canvas.toDataURL('image/png')
      },
      sample,
      buf.toString('base64')
    )
    const png = Buffer.from(dataUrl.split(',')[1], 'base64')
    await writeFile(fileURLToPath(new URL(`${sample.name}.png`, OUT_DIR)), png)
    console.log(
      `[ocr] 真实样张 ${sample.name}.png（${sample.text}）：` +
        `${(png.length / 1024).toFixed(0)} KB · ${sample.license} · ${sample.author}`
    )
  }
} finally {
  await browser.close()
  if (!keepSrc) await rm(CACHE_DIR, { recursive: true, force: true })
}
