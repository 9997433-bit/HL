/**
 * 把 Tesseract.js 的 worker 脚本与 wasm 内核从 node_modules 复制到 public/ocr/。
 *
 * Tesseract.js 默认会去 jsDelivr 取 worker 和内核，这条路在断网的平板上直接断掉，
 * 所以拍照识字用的每一个文件都要落到同源目录下，由 Service Worker 兜底缓存。
 *
 * 内核只带 SIMD + LSTM 这一个变体：
 *   - LSTM 是 Tesseract.js 的默认识别引擎（OEM.LSTM_ONLY），传统引擎用不上；
 *   - SIMD 从 Chrome 91 / Firefox 89 / Safari 16.4 起就是标配，
 *     每多带一个变体就多 3.9 MB，不值得为极老的浏览器把包翻倍。
 *   因此 utils/ocr.js 里的 corePath 直接指到这一个文件（指到目录的话
 *   Tesseract.js 会按特性探测去猜文件名，猜出 relaxedsimd 就 404 了）。
 *
 * 语言包 chi_sim.traineddata.gz 不在 node_modules 里，它是入库的二进制，
 * 见 THIRD_PARTY_NOTICES.md；这里只核对它在不在。
 *
 * 用法：node scripts/gen-ocr-assets.mjs
 * 已挂在 package.json 的 prebuild / predev 钩子上，无需手动执行。
 */

import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'

const require = createRequire(import.meta.url)
const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const outDir = path.join(appDir, 'public', 'ocr')

/** 三个文件名与 src/utils/ocr.js 里的 OCR_PACK 一一对应，改名要一起改。 */
const LANG_FILE = 'chi_sim.traineddata.gz'
const CORE_FILE = 'tesseract-core-simd-lstm.wasm.js'
const WORKER_FILE = 'worker.min.js'

function packageDir(id) {
  return path.dirname(require.resolve(`${id}/package.json`))
}

function version(id) {
  return JSON.parse(fs.readFileSync(path.join(packageDir(id), 'package.json'), 'utf8')).version
}

function main() {
  let tesseractDir
  let coreDir
  try {
    tesseractDir = packageDir('tesseract.js')
    coreDir = packageDir('tesseract.js-core')
  } catch {
    console.warn(
      '[ocr] 未找到 tesseract.js，跳过 OCR 资源生成。\n' +
        '      拍照识字会显示「识字包没装上」，其余功能不受影响。'
    )
    return
  }

  fs.mkdirSync(outDir, { recursive: true })

  const copies = [
    { from: path.join(tesseractDir, 'dist', WORKER_FILE), to: WORKER_FILE },
    { from: path.join(coreDir, CORE_FILE), to: CORE_FILE }
  ]

  const files = []
  for (const { from, to } of copies) {
    if (!fs.existsSync(from)) {
      console.error(`[ocr] 上游包里找不到 ${path.relative(appDir, from)}，请核对 tesseract.js 版本。`)
      process.exitCode = 1
      return
    }
    fs.copyFileSync(from, path.join(outDir, to))
    files.push({ name: to, bytes: fs.statSync(from).size })
  }

  const langPath = path.join(outDir, LANG_FILE)
  if (!fs.existsSync(langPath)) {
    console.error(
      `[ocr] 缺少语言包 public/ocr/${LANG_FILE}。它是入库文件，请从 git 恢复，\n` +
        '      或从 https://tessdata.projectnaptha.com/4.0.0_fast/ 重新下载。'
    )
    process.exitCode = 1
    return
  }
  files.push({ name: LANG_FILE, bytes: fs.statSync(langPath).size })

  // 运行时先读这份清单：装没装上、要下多少流量，都不必等 wasm 真的开始下载。
  // 刻意不写生成时间，否则每次构建都会把工作区弄脏。
  const manifest = {
    lang: 'chi_sim',
    core: CORE_FILE,
    worker: WORKER_FILE,
    tesseract: version('tesseract.js'),
    tesseractCore: version('tesseract.js-core'),
    files: files.sort((a, b) => a.name.localeCompare(b.name))
  }
  fs.writeFileSync(path.join(outDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)

  const mb = (files.reduce((n, f) => n + f.bytes, 0) / 1024 / 1024).toFixed(1)
  console.log(
    `[ocr] 已备好离线识字包：tesseract.js ${manifest.tesseract} + ` +
      `内核 ${manifest.tesseractCore} + chi_sim 语言包，共约 ${mb} MB。`
  )
}

main()
