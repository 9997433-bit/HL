/**
 * 拍照识字的 OCR 流水线：一张照片 → 汉字 → 字库里的讲解。
 *
 * 三条约束决定了这里的写法：
 *
 *   1. 离线。Tesseract.js 默认从 jsDelivr 取 worker / wasm / 语言包，断网即废。
 *      所有资源改指 public/ocr/（由 scripts/gen-ocr-assets.mjs 备好），
 *      Service Worker 在第一次用到时把它们收进 literacy-app-ocr-pack 缓存。
 *   2. 懒加载。整包近 6 MB，只有孩子真的按下「开始认字」才 import()，
 *      首屏一个字节都不为它买单；worker 建好之后常驻，第二张照片就不用再等。
 *   3. 只讲字库里的字。识别结果先过一遍 CHARACTER_MAP：认得的字直接跳到单字页
 *      看拼音、释义、笔顺，认不得的字如实说「这个字还没进字库」，不瞎编释义。
 *
 * extractHanzi / splitByLibrary 是纯函数，scripts/test-ocr.mjs 直接在 Node 里跑。
 */

import { CHARACTER_MAP } from '../data/characters.js'

/** 与 scripts/gen-ocr-assets.mjs 生成的文件一一对应。 */
export const OCR_PACK = Object.freeze({
  lang: 'chi_sim',
  worker: 'worker.min.js',
  core: 'tesseract-core-simd-lstm.wasm.js',
  manifest: 'manifest.json',
  sample: 'sample-photo.png'
})

/** 长边缩到这个像素数再识别：再大只是让 wasm 多算几秒，认字率并不会更高。 */
const MAX_SIDE = 1280

/** 太小的照片先放大，不然笔画会糊成一团。 */
const MIN_SIDE = 640

const HANZI = /[\u4e00-\u9fff]/

/** base 是 './'，用 baseURI 拼相对路径，子目录部署与 Android WebView 都能工作。 */
export function ocrAssetUrl(file = '') {
  return new URL(`ocr/${file}`, document.baseURI).href
}

/**
 * 识别结果里挑出汉字，按出现顺序去重。
 * OCR 免不了夹带标点、拼音和噪声字符，这一步把它们全部丢掉。
 */
export function extractHanzi(text, { limit = 24 } = {}) {
  const seen = new Set()
  const chars = []
  for (const ch of String(text ?? '')) {
    if (!HANZI.test(ch) || seen.has(ch)) continue
    seen.add(ch)
    chars.push(ch)
    if (chars.length >= limit) break
  }
  return chars
}

/** 按「字库里有没有」分成两堆；认得的那堆才有讲解可讲。 */
export function splitByLibrary(chars) {
  const known = []
  const unknown = []
  for (const ch of chars) (CHARACTER_MAP.has(ch) ? known : unknown).push(ch)
  return { known, unknown }
}

/**
 * 把 Tesseract 的进度回调翻译成一句孩子看得懂的话。
 * status 是英文常量，直接播报出去读屏会念一串英文。
 */
const STEP_TEXT = {
  'loading tesseract core': '正在装认字引擎',
  'initializing tesseract': '正在装认字引擎',
  'loading language traineddata': '正在翻汉字词典',
  'initializing api': '马上就好',
  'recognizing text': '正在看照片里的字'
}

export function describeStep(status) {
  return STEP_TEXT[status] ?? '正在准备'
}

/* ------------------------------------------------------------------ 图片预处理 */

/**
 * 缩放 + 去色 + 拉对比度。
 *
 * 家里随手拍的照片通常是暖光下的书页：整体偏黄、明暗不匀。
 * 先转灰度再把实际用到的灰阶拉满 0–255，比直接丢给 Tesseract 稳得多，
 * 而且这点计算量在主线程上跑一帧就完了，不值得再开一个 worker。
 */
export function preprocess(source, { maxSide = MAX_SIDE, minSide = MIN_SIDE } = {}) {
  const width = source.naturalWidth || source.width
  const height = source.naturalHeight || source.height
  const longest = Math.max(width, height)
  const shortest = Math.min(width, height)
  if (!longest || !shortest) throw new Error('照片是空的')

  const scale = Math.min(maxSide / longest, Math.max(1, minSide / shortest))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(width * scale))
  canvas.height = Math.max(1, Math.round(height * scale))

  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)

  const image = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const pixels = image.data
  const gray = new Uint8ClampedArray(pixels.length / 4)
  let min = 255
  let max = 0
  for (let i = 0, g = 0; i < pixels.length; i += 4, g += 1) {
    // Rec. 601 亮度权重：绿色对人眼最亮，也最接近墨迹的对比度
    const value = (pixels[i] * 299 + pixels[i + 1] * 587 + pixels[i + 2] * 114) / 1000
    gray[g] = value
    if (value < min) min = value
    if (value > max) max = value
  }

  const span = max - min
  for (let i = 0, g = 0; i < pixels.length; i += 4, g += 1) {
    const value = span > 8 ? ((gray[g] - min) * 255) / span : gray[g]
    pixels[i] = value
    pixels[i + 1] = value
    pixels[i + 2] = value
    pixels[i + 3] = 255
  }
  ctx.putImageData(image, 0, 0)
  return canvas
}

/** File / Blob / URL 都收，统一变成解好码的 <img>。 */
export function loadImage(source) {
  if (source instanceof HTMLImageElement) return Promise.resolve(source)
  const url = typeof source === 'string' ? source : URL.createObjectURL(source)
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.decoding = 'async'
    img.onload = () => {
      if (url !== source) URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      if (url !== source) URL.revokeObjectURL(url)
      reject(new Error('这张图片打不开'))
    }
    img.src = url
  })
}

/* ---------------------------------------------------------------------- 引擎 */

let workerPromise = null

/** 识字包在不在。装不上的时候界面要说人话，而不是抛一串 404。 */
export async function readPack() {
  try {
    const res = await fetch(ocrAssetUrl(OCR_PACK.manifest), { cache: 'force-cache' })
    if (!res.ok) return { ready: false, bytes: 0 }
    const manifest = await res.json()
    const bytes = (manifest.files ?? []).reduce((n, f) => n + (f.bytes ?? 0), 0)
    return { ready: true, bytes, version: manifest.tesseract ?? '' }
  } catch {
    return { ready: false, bytes: 0 }
  }
}

/**
 * 建 worker。第一次要下近 6 MB，之后常驻在内存里，换张照片立刻就能认。
 *
 * workerBlobURL 关掉：worker 直接用同源 URL 起，Service Worker 才能接管它
 * 内部的 importScripts / fetch，断网时才拿得到已经缓存下来的 wasm。
 */
async function getWorker(onStep) {
  if (!workerPromise) {
    workerPromise = (async () => {
      const { createWorker, OEM } = await import('tesseract.js')
      return createWorker(OCR_PACK.lang, OEM.LSTM_ONLY, {
        workerPath: ocrAssetUrl(OCR_PACK.worker),
        corePath: ocrAssetUrl(OCR_PACK.core),
        langPath: ocrAssetUrl(''),
        workerBlobURL: false,
        gzip: true,
        // 语言包已经由 Service Worker 缓存，再往 IndexedDB 抄一份纯属占地方
        cacheMethod: 'none',
        logger: (m) => onStep?.(m)
      })
    })().catch((err) => {
      workerPromise = null
      throw err
    })
  }
  return workerPromise
}

export async function releaseOcr() {
  const pending = workerPromise
  workerPromise = null
  if (!pending) return
  await pending.then((worker) => worker.terminate()).catch(() => {})
}

/**
 * 认一张照片。
 *
 * @param source File / Blob / 图片 URL / 已解码的 <img>
 * @param onStep Tesseract 的进度回调（{ status, progress }）
 */
export async function recognizePhoto(source, { onStep } = {}) {
  const started = Date.now()
  const image = await loadImage(source)
  const canvas = preprocess(image)
  const worker = await getWorker(onStep)
  const { data } = await worker.recognize(canvas)

  const chars = extractHanzi(data.text)
  const { known, unknown } = splitByLibrary(chars)
  return {
    text: (data.text ?? '').replace(/\s+/g, ''),
    confidence: Math.round(data.confidence ?? 0),
    known,
    unknown,
    ms: Date.now() - started
  }
}
