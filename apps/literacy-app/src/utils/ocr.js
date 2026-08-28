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

/**
 * 灰阶跨度宽到这个数以上就不拉了（ROUND14_H2）。
 *
 * 拉伸的收益是 255/span 这个增益；跨度本来就有两百多的照片，增益只剩 1.2 倍，
 * 拉了等于没拉，却要为它把三通道压成灰度——而颜色是引擎自己二值化时用得上的信息。
 * 喷漆「小心地滑」那张的「心」就是这么丢的：灰度化之后字面和水泥墙一个亮度。
 * 线放在 180（增益 1.4 倍），二十张基准图里被拉的是暖光、失焦、低光、
 * 警示锥、小票、店招这几张真正挤在一小段灰度里的。
 */
const STRETCH_SPAN = 180

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
 * 认不出的时候界面要说得出「为什么」（ROUND12_H2）。
 *
 * 「没认出来」只有一句话可说的时候，孩子只会以为是自己拍得不好；可现场真正改得动的
 * 三件事——补光、端稳、换个取景——对应的是三种完全不同的失败。区分它们不需要再跑一遍
 * 模型，preprocess() 本来就要把每个像素过一遍，顺手就能量出来：
 *
 *   luma       拉伸**之前**的平均灰度。这是曝光，跟「暗不暗」直接对应。
 *              必须在拉伸前取——拉满之后每张图的均值都被推向 128，暗照片会消失。
 *   span       拉伸前的灰阶跨度。窄说明整张图挤在一小段灰度里。
 *              判「暗」要 luma 和 span 一起看：黑板照片的 luma 只有三十几，
 *              可白粉笔字把 span 拉到两百以上——画面是暗的，笔画不是。
 *   sharpness  拉伸**之后**横向梯度的 99 分位数（0–255）。
 *
 * 锐度为什么取分位数而不是平均值：一张字卡的绝大部分面积是空白，
 * 平均梯度基本等于「空白占了多大比例」，跟糊不糊没多大关系——实测二十张基准图
 * 的平均梯度全落在 0.4–3.9 这个窄带里，拍糊的便签(0.4)和干净的绘本内页(1.3)
 * 分不开。分位数只看最陡的那百分之一像素，也就是笔画的边：边缘被模糊摊开时，
 * 峰值梯度会实实在在地塌下去。
 *
 * 门槛写在 CameraOcrView 里而不是这里：这里只管量，怎么解读是界面的事。
 */
function measure(gray, width, height, stretch) {
  let sum = 0
  let min = 255
  let max = 0
  for (let i = 0; i < gray.length; i += 1) {
    sum += gray[i]
    if (gray[i] < min) min = gray[i]
    if (gray[i] > max) max = gray[i]
  }
  // 梯度直方图：256 个整数桶，一趟扫完，不用为了求分位数把上百万个数排序
  const bins = new Uint32Array(256)
  let pairs = 0
  for (let y = 0; y < height; y += 1) {
    const row = y * width
    for (let x = 1; x < width; x += 1) {
      const d = Math.abs(stretch(gray[row + x]) - stretch(gray[row + x - 1]))
      bins[Math.min(255, Math.round(d))] += 1
      pairs += 1
    }
  }
  let seen = 0
  let sharpness = 0
  const cut = pairs * 0.99
  for (let i = 0; i < 256; i += 1) {
    seen += bins[i]
    if (seen >= cut) {
      sharpness = i
      break
    }
  }
  return {
    luma: Math.round(sum / Math.max(1, gray.length)),
    span: max - min,
    sharpness
  }
}

/**
 * 缩放 + 去色 + 拉对比度。
 *
 * 家里随手拍的照片通常是暖光下的书页：整体偏黄、明暗不匀。
 * 先转灰度再把实际用到的灰阶拉满 0–255，比直接丢给 Tesseract 稳得多，
 * 而且这点计算量在主线程上跑一帧就完了，不值得再开一个 worker。
 *
 * 只降不升（ROUND14_H2）。这里原先还会把短边不足 640 的照片放大回去，理由是
 * 「太小的照片笔画会糊成一团」——听起来对，实测反过来：放大用的是双线性插值，
 * 一个字节的新信息都没有，只把笔画边缘摊平；而引擎的 LSTM 行识别本来就要把每一行
 * 归一化到固定高度，放大之后等于连着重采样两次。十张真实样张全是三百像素以内的裁图，
 * 被 4 倍放大之后 App 侧只认得出 33/41，去掉这一步立刻回到 39/41
 * （对账见 .agent_workspace/evidence/r14/ocr/app-webview-matrix.json）。
 *
 * 量出来的曝光/锐度挂在返回的 canvas 上（`photoStats`）。挂在对象上而不是改返回值，
 * 是为了不动 preprocess() 这个签名——它已经有三处调用方和一整套单元测试。
 */
export function preprocess(source, { maxSide = MAX_SIDE } = {}) {
  const width = source.naturalWidth || source.width
  const height = source.naturalHeight || source.height
  const longest = Math.max(width, height)
  const shortest = Math.min(width, height)
  if (!longest || !shortest) throw new Error('照片是空的')

  const scale = Math.min(1, maxSide / longest)
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
  // 近乎纯色的照片拉了只会把噪点放大成假笔画，跨度本来就宽的拉了等于没拉：
  // 两头都不动，中间那一段才真的需要把灰阶摊开。
  const stretchable = span > 8 && span < STRETCH_SPAN
  const stretch = (value) => (stretchable ? ((value - min) * 255) / span : value)
  if (stretchable) {
    for (let i = 0, g = 0; i < pixels.length; i += 4, g += 1) {
      const value = stretch(gray[g])
      pixels[i] = value
      pixels[i + 1] = value
      pixels[i + 2] = value
      pixels[i + 3] = 255
    }
    ctx.putImageData(image, 0, 0)
  }
  canvas.photoStats = measure(gray, canvas.width, canvas.height, stretch)
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
    // 认不出时界面靠这三个数分辨「暗」「糊」和「没字」，见 CameraOcrView 的 reason
    photo: canvas.photoStats ?? null,
    ms: Date.now() - started
  }
}
