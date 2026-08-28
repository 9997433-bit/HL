/**
 * ROUND14_H2 —— App 侧（WebView）拍照识字的实测矩阵。
 *
 * scripts/test-ocr-accuracy.mjs 把十张真实样张的**原图**直接喂给引擎，跑出 40/41。
 * 可孩子在 App 里按下的那条链多一段：照片先过 utils/ocr.js 的 preprocess()，
 * 再进引擎。R13 收线时这两个数第一次被分开量，差距大得不像话——App 侧只有 33/41。
 * 七个字丢在预处理里，而 Node 基准一分都看不见它：那个脚本压根不经过 preprocess()。
 *
 * 这个脚本补的就是这段盲区：
 *
 *   1. 在真的 Chromium 里跑真的 preprocess()。canvas 的缩放插值、getImageData 的
 *      色彩空间这些东西没法在 Node 里拿替身模拟——test-ocr-accuracy 的 canvas 替身
 *      验的是算术，验不了「浏览器把 320×81 放大到 1280×324 之后笔画还剩多少」。
 *      所以这里起一个 headless Chrome，UA 换成 android-sim 那套 WebView UA，
 *      直接把 src/utils/ocr.js 的源码注进页面执行。
 *   2. 预处理后的画布存成 PNG，再用与 App 完全一致的引擎配置（LSTM_ONLY +
 *      同一份 chi_sim 语言包）认一遍，逐张记召回、置信度和 photoStats。
 *   3. 落一份 .agent_workspace/evidence/r14/ocr/app-webview-matrix.json：
 *      门禁 check-round14 的 H2 读它的 passCount / total，判 App 侧是不是 ≥40/41。
 *
 * simulated:true —— 这是 VM 上的 headless Chrome，不是 Android 真机。它证得了
 * 「预处理没有把字吃掉」，证不了 WebView 上的内存、SW 缓存与相机链路，那些是
 * test-ocr-device.mjs B 段的活，两份证据分目录放，谁都不许冒充谁。
 *
 * 用法：
 *   node scripts/test-ocr-app-matrix.mjs          跑分 + 落证据
 *   node scripts/test-ocr-app-matrix.mjs --json   机读汇总
 */

import assert from 'node:assert/strict'
import { existsSync, mkdirSync, mkdtempSync, readdirSync, writeFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import puppeteer from 'puppeteer-core'

import { extractHanzi, OCR_PACK } from '../src/utils/ocr.js'

const asJson = process.argv.includes('--json')
const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = path.resolve(appDir, '..', '..')
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'

/** 与 scripts/android-sim.mjs 同一串：证据里写清这是哪一种 WebView 的模拟。 */
const WEBVIEW_UA =
  'Mozilla/5.0 (Linux; Android 13; Pixel 7 Build/TQ3A.230805.001; wv) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Mobile Safari/537.36'

/**
 * App 侧的及格线：十张真实样张 41 个字，只准丢一个。
 *
 * 那一个是喷漆「小心地滑」的「滑」——镂空模板把笔画断开，Node 基准也认不出，
 * 这是引擎自己的边界（见 test-ocr-accuracy.mjs 那张图的注释）。除它之外
 * App 侧丢的每一个字都是预处理丢的，一个都不放过。
 */
const MIN_RECALL = 40

const evidenceDir = path.join(repoDir, '.agent_workspace/evidence/r14/ocr')
const evidenceFile = path.join(evidenceDir, 'app-webview-matrix.json')

const realSamples = JSON.parse(
  await readFile(path.join(appDir, 'scripts/fixtures/ocr/real-samples.json'), 'utf8')
)

/**
 * 把 src/utils/ocr.js 塞进页面。
 *
 * 不是抄一份 preprocess 过来——抄的那份会和线上那份慢慢分岔，量出来的分数就成了
 * 自说自话。这里读的是同一个文件，只摘掉 import / export 两个模块关键字
 * （字库那条 import 是 splitByLibrary 用的，预处理一行都用不着）。
 */
const moduleSource = await readFile(path.join(appDir, 'src/utils/ocr.js'), 'utf8')
const browserSource = moduleSource
  .replace(/^import[\s\S]*?from\s+'[^']+'\n/gm, '')
  .replace(/^export /gm, '')

/** 基准集里全部二十张图：真实样张跑分，其余只量 photoStats 供阈值对账。 */
const fixtureDir = path.join(appDir, 'scripts/fixtures/ocr')
const allImages = [
  { name: '示例字卡', file: path.join(appDir, `public/ocr/${OCR_PACK.sample}`) },
  ...readdirSync(fixtureDir)
    .filter((f) => f.endsWith('.png'))
    .sort()
    .map((f) => ({ name: f.replace(/\.png$/, ''), file: path.join(fixtureDir, f) }))
]

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage']
})

const measured = []
let chromeVersion = ''
try {
  chromeVersion = await browser.version()
  const page = await browser.newPage()
  await page.setUserAgent(WEBVIEW_UA)
  await page.setContent('<!doctype html><meta charset="utf-8"><title>ocr-app-matrix</title>')
  await page.evaluate(`${browserSource}\n;window.preprocess = preprocess;`)
  assert.equal(
    await page.evaluate('typeof window.preprocess'),
    'function',
    'src/utils/ocr.js 注进页面之后没有 preprocess()——文件结构变了，改这里的剥壳规则'
  )

  for (const image of allImages) {
    const png = await readFile(image.file)
    const out = await page.evaluate(async (dataUrl) => {
      const img = new Image()
      img.src = dataUrl
      await img.decode()
      const canvas = window.preprocess(img)
      return {
        png: canvas.toDataURL('image/png'),
        from: [img.naturalWidth, img.naturalHeight],
        to: [canvas.width, canvas.height],
        photo: canvas.photoStats
      }
    }, `data:image/png;base64,${png.toString('base64')}`)
    measured.push({ ...image, ...out })
  }
} finally {
  await browser.close()
}

/** 预处理后的画布存成 PNG 再认：引擎吃到的就是 App 里那张图，一个像素不差。 */
const workDir = mkdtempSync(path.join(os.tmpdir(), 'ocr-app-matrix-'))
for (const row of measured) {
  row.processed = path.join(workDir, `${row.name}.png`)
  writeFileSync(row.processed, Buffer.from(row.png.split(',')[1], 'base64'))
  delete row.png
}

const { createWorker, OEM } = await import('tesseract.js').catch(() => {
  throw new Error('tesseract.js 没装上，先跑 npm install')
})
// 与 utils/ocr.js 的 getWorker() 一致：只用 LSTM，语言包读同一份 public/ocr/。
const worker = await createWorker(OCR_PACK.lang, OEM.LSTM_ONLY, {
  langPath: path.join(appDir, 'public/ocr'),
  gzip: true,
  cacheMethod: 'none',
  logger: () => {}
})

const rows = []
try {
  for (const sample of realSamples.samples) {
    const row = measured.find((m) => m.name === sample.name)
    assert.ok(row, `真实样张 ${sample.name}.png 没跑到预处理`)
    const started = Date.now()
    const { data } = await worker.recognize(row.processed)
    const chars = extractHanzi(data.text)
    const wanted = [...new Set(sample.text)]
    const hit = wanted.filter((c) => chars.includes(c))
    rows.push({
      name: sample.name,
      tier: sample.tier,
      expect: sample.text,
      hit: hit.length,
      total: wanted.length,
      missed: wanted.filter((c) => !chars.includes(c)).join(''),
      noise: chars.filter((c) => !wanted.includes(c)).join(''),
      confidence: Math.round(data.confidence ?? 0),
      ms: Date.now() - started,
      canvas: { from: row.from.join('×'), to: row.to.join('×') },
      photo: row.photo
    })
  }
} finally {
  await worker.terminate()
}

const passCount = rows.reduce((n, r) => n + r.hit, 0)
const total = rows.reduce((n, r) => n + r.total, 0)

mkdirSync(evidenceDir, { recursive: true })
writeFileSync(
  evidenceFile,
  `${JSON.stringify(
    {
      marker: 'ROUND14_H2',
      capturedAt: new Date().toISOString(),
      // VM 上的 headless Chrome，不是设备。真机那一段在 evidence/r14/android/。
      simulated: true,
      onDevice: false,
      surface: { chrome: chromeVersion, userAgent: WEBVIEW_UA, headless: true },
      pipeline: 'src/utils/ocr.js preprocess() → tesseract.js chi_sim LSTM_ONLY',
      floor: MIN_RECALL,
      passCount,
      total,
      recall: Number((total ? passCount / total : 0).toFixed(4)),
      samples: rows,
      // 二十张图的曝光/锐度：CameraOcrView 那三条判暗判糊的线要压在它们之外，
      // test-ocr-accuracy.mjs 的 MEASURED 表就是从这里回填的。
      stats: Object.fromEntries(measured.map((m) => [m.name, m.photo]))
    },
    null,
    2
  )}\n`
)

const failures = []
if (total !== 41) failures.push(`真实样张一共 ${total} 个字，基准是 41——样张清单被动过`)
if (passCount < MIN_RECALL) {
  failures.push(
    `App 侧召回 ${passCount}/${total}（下限 ${MIN_RECALL}）：` +
      `预处理把字吃掉了，逐张看 ${path.relative(repoDir, evidenceFile)}`
  )
}
if (!existsSync(evidenceFile)) failures.push('证据 JSON 没落盘')

if (asJson) {
  console.log(
    JSON.stringify(
      { marker: 'ROUND14_H2', passCount, total, floor: MIN_RECALL, failures, samples: rows },
      null,
      2
    )
  )
} else {
  for (const r of rows) {
    console.log(
      // 满分打勾，缺字打半月：喷漆那张的「滑」是引擎边界，不是这一段的失败，
      // 真正的红灯由下面 failures 那几行给。
      `  ${r.hit === r.total ? '✓' : '◐'} ${r.name}：${r.hit}/${r.total}` +
        ` · 把握 ${r.confidence} · ${r.canvas.from} → ${r.canvas.to}` +
        ` · 曝光 ${r.photo.luma} / 跨度 ${r.photo.span} / 锐度 ${r.photo.sharpness}` +
        `${r.missed ? ` · 丢字「${r.missed}」` : ''}${r.noise ? ` · 误检「${r.noise}」` : ''}`
    )
  }
  for (const f of failures) console.log(`  ✗ ${f}`)
  console.log(
    `\n拍照识字 App 侧矩阵 [ROUND14_H2]：${rows.length} 张真实样张，` +
      `召回 ${passCount}/${total}（下限 ${MIN_RECALL}）；` +
      `证据 ${path.relative(repoDir, evidenceFile)}（simulated:true，非真机）。`
  )
}

process.exit(failures.length ? 1 : 0)
