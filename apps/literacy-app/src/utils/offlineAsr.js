/**
 * 跟读 v3 · 离线 ASR（sherpa-onnx WASM + Worker）接线层。
 *
 * 路线与门槛见 .agent_workspace/r9-followread-asr-evaluation.md：
 * 这一层只负责「把设备内识别接进跟读链」，不负责音素诊断。它给出的仍然是
 * 汉字转写，评分沿用 utils/speechEval.js 的逐字对齐，绝不叫「音素准确率」。
 *
 * 四条硬约束，改这个文件之前先读一遍：
 *
 *   1. 同源自托管。模型、wasm、worklet 全部从 public/asr/ 取，运行时不回退到
 *      任何第三方 CDN；每个文件都要在清单里冻结 sha256，校验不过就整包作废。
 *   2. 家长点了才下。probe() 只读清单和缓存，install() 才会发起下载；
 *      下载走独立的版本化 Cache Storage，不污染首屏 precache。
 *   3. 失败只许往下降。引擎起不来、超时、校验失败——一律回到录音档，
 *      不得静默切到可能联网的浏览器 SpeechRecognition（见 chooseTier）。
 *   4. 音频不出设备。PCM 只在页面内存和 Worker 之间传递，不写盘、不上传。
 *
 * 纯函数（parseManifest / resampleTo16k / floatToPcm16 / chooseTier …）不碰
 * 浏览器 API，scripts/test-speech-eval.mjs 直接在 Node 里跑。
 */

/** 引擎与打包约定；模型本身不随仓库分发，见 public/asr/manifest.json。 */
export const OFFLINE_ASR = Object.freeze({
  engine: 'sherpa-onnx',
  runtime: 'wasm-worker',
  schema: 'literacy-asr-pack/1',
  manifest: 'manifest.json',
  worklet: 'pcm-capture.worklet.js',
  cachePrefix: 'literacy-app-asr-pack-',
  sampleRate: 16000,
  /** 评估文档 §5 资源层：可选评测包压缩下载目标 ≤ 60 MiB。 */
  maxPackBytes: 60 * 1024 * 1024,
  /** §5 可靠性层：五类故障都要在 2 秒内降档，这里留一点余量给低端机冷启动。 */
  initTimeoutMs: 2000,
  finalTimeoutMs: 2000
})

const HEX64 = /^[0-9a-f]{64}$/

/* --------------------------------------------------------------- 纯函数层 */

/** base 是 './'，用 baseURI 拼相对路径，子目录部署与 Android WebView 都能工作。 */
export function asrAssetUrl(file = '') {
  return new URL(`asr/${file}`, document.baseURI).href
}

/**
 * 清单校验。宁可整包不装，也不要装一份来路不明的模型。
 *
 * 通过校验只说明「这份清单可以拿去下载」，不代表文件已经在本机；
 * 是否装好由 probeOfflinePack() 查缓存决定。
 */
export function parseManifest(raw) {
  const data = typeof raw === 'string' ? JSON.parse(raw) : raw
  if (!data || typeof data !== 'object') throw new Error('离线评测包清单不是对象')
  if (data.schema !== OFFLINE_ASR.schema) throw new Error(`清单版本不认识：${data.schema}`)
  if (data.engine !== OFFLINE_ASR.engine) throw new Error(`引擎对不上：${data.engine}`)
  if (!data.modelId || !data.modelVersion) throw new Error('清单缺少 modelId / modelVersion')
  if (!data.license) throw new Error('清单缺少模型许可证，未经许可证核对不得分发')
  if (data.available !== true) throw new Error('这个版本还没有冻结离线评测包')

  const files = Array.isArray(data.files) ? data.files : []
  if (!files.length) throw new Error('清单里一个文件都没有')

  let bytes = 0
  for (const file of files) {
    const path = String(file?.path ?? '')
    if (!path || path.startsWith('/') || path.includes('..') || /^[a-z]+:/i.test(path)) {
      throw new Error(`文件路径必须是 public/asr/ 下的相对路径：${path || '(空)'}`)
    }
    if (!HEX64.test(String(file?.sha256 ?? ''))) {
      throw new Error(`${path} 没有冻结 sha256，拒绝下载`)
    }
    if (!Number.isInteger(file?.bytes) || file.bytes <= 0) {
      throw new Error(`${path} 缺少合法的 bytes`)
    }
    bytes += file.bytes
  }
  if (bytes > OFFLINE_ASR.maxPackBytes) {
    throw new Error(`整包 ${(bytes / 1048576).toFixed(1)} MiB，超过 60 MiB 预算`)
  }
  if (!files.some((file) => file.role === 'wasm-glue')) throw new Error('清单缺少 wasm 胶水脚本')
  if (!files.some((file) => file.role === 'wasm-binary')) throw new Error('清单缺少 wasm 二进制')

  return Object.freeze({
    schema: data.schema,
    engine: data.engine,
    modelId: String(data.modelId),
    modelVersion: String(data.modelVersion),
    license: String(data.license),
    bytes,
    files: Object.freeze(files.map((file) => Object.freeze({ ...file })))
  })
}

/** 一个模型版本一个缓存，换模型等于换评分规则，旧缓存不复用。 */
export function packCacheName(manifest) {
  return `${OFFLINE_ASR.cachePrefix}${manifest.modelId}-${manifest.modelVersion}`
}

/**
 * 降级阶梯（v3 四档）。对外仍然只有三个 mode，第一档是 recognition 的内部实现。
 *
 *   offline-asr  本地模型装好且 Worker 起得来 → 设备内逐字识别，不联网
 *   recognition  家长显式打开浏览器识别 → 可能走厂商在线服务
 *   recording    只有麦克风 → 按响度和时长给分，封顶 85，可回放
 *   listen-only  没有麦克风 → 不打分，孩子自评
 *
 * offlineFault 是本轮会话里「本地引擎已经证明起不来」。这时候必须落到录音档：
 * 悄悄改用可能联网的浏览器识别，等于替家长做了隐私决定。
 *
 * 没有麦克风（设备缺失或家长拒绝）先于一切：识别档再高也要有音频才成立，
 * 离线包已经装好也不例外——否则孩子会拿到一个「什么都没听见」的 0 分。
 */
export function chooseTier({
  offlineReady = false,
  offlineFault = false,
  canRecognize = false,
  allowRecognition = false,
  canRecord = false,
  micDenied = false
} = {}) {
  const fallback = canRecord && !micDenied ? 'recording' : 'listen-only'
  if (fallback === 'listen-only') return fallback
  if (offlineFault) return fallback
  if (offlineReady) return 'offline-asr'
  if (canRecognize && allowRecognition) return 'recognition'
  return fallback
}

/** 四档 → 对外三档：进度数据和界面不因为换了识别内核而分叉。 */
export function modeOfTier(tier) {
  return tier === 'offline-asr' ? 'recognition' : tier
}

/** 这一分是谁给的；写进结果对象，家长中心和回归测试都能看见。 */
export function sourceOfTier(tier) {
  if (tier === 'offline-asr') return 'offline-sherpa'
  if (tier === 'recognition') return 'web-speech'
  if (tier === 'recording') return 'loudness'
  return 'self'
}

/**
 * 线性重采样到 16 kHz。
 * AudioContext 给什么采样率由设备定（常见 44.1k / 48k），模型只吃 16k 单声道。
 */
export function resampleTo16k(input, inputRate, targetRate = OFFLINE_ASR.sampleRate) {
  const source = input instanceof Float32Array ? input : Float32Array.from(input ?? [])
  if (!source.length || !inputRate || inputRate === targetRate) return source
  const ratio = inputRate / targetRate
  const length = Math.max(1, Math.floor(source.length / ratio))
  const out = new Float32Array(length)
  for (let i = 0; i < length; i += 1) {
    const at = i * ratio
    const left = Math.floor(at)
    const right = Math.min(source.length - 1, left + 1)
    const frac = at - left
    out[i] = source[left] * (1 - frac) + source[right] * frac
  }
  return out
}

/** Float32 [-1,1] → Int16 PCM。越界要夹住，不然溢出会变成刺耳的爆音。 */
export function floatToPcm16(input) {
  const source = input instanceof Float32Array ? input : Float32Array.from(input ?? [])
  const out = new Int16Array(source.length)
  for (let i = 0; i < source.length; i += 1) {
    const v = Math.max(-1, Math.min(1, source[i]))
    out[i] = Math.round(v < 0 ? v * 0x8000 : v * 0x7fff)
  }
  return out
}

const STEP_TEXT = {
  probing: '正在看看这台设备装没装离线评测包',
  downloading: '正在下载离线评测包',
  verifying: '正在核对文件指纹',
  booting: '正在启动离线评测引擎',
  ready: '离线评测包可以用了',
  removed: '离线评测包已经删掉了'
}

export function describeAsrStep(step) {
  return STEP_TEXT[step] ?? '正在准备'
}

/* ------------------------------------------------------------- 浏览器实现层 */

const hex = (buffer) =>
  [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('')

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  return hex(digest)
}

function cachesAvailable() {
  return typeof caches !== 'undefined' && typeof crypto?.subtle?.digest === 'function'
}

async function readManifest() {
  const response = await fetch(asrAssetUrl(OFFLINE_ASR.manifest), { cache: 'no-cache' })
  if (!response.ok) throw new Error(`读不到离线评测包清单（HTTP ${response.status}）`)
  return parseManifest(await response.text())
}

/**
 * 只读探测：这台设备现在能不能用离线档。
 *
 * @returns {Promise<{status:'ready'|'available'|'unavailable', manifest:object|null, note:string}>}
 */
export async function probeOfflinePack() {
  if (!cachesAvailable()) {
    return { status: 'unavailable', manifest: null, note: '这台设备不支持离线评测包，用录音档。' }
  }
  let manifest
  try {
    manifest = await readManifest()
  } catch (error) {
    return { status: 'unavailable', manifest: null, note: error.message }
  }

  try {
    const cache = await caches.open(packCacheName(manifest))
    for (const file of manifest.files) {
      if (!(await cache.match(asrAssetUrl(file.path)))) {
        return {
          status: 'available',
          manifest,
          note: `离线评测包还没下载（约 ${(manifest.bytes / 1048576).toFixed(0)} MB）。`
        }
      }
    }
    return { status: 'ready', manifest, note: '离线评测包已就绪，识别只在这台设备上进行。' }
  } catch (error) {
    return { status: 'unavailable', manifest: null, note: `缓存读不了：${error.message}` }
  }
}

/**
 * 下载并校验整包。任一文件哈希对不上就把这一版缓存整个删掉——
 * 半截的模型比没有模型更糟：它会在孩子读到一半的时候崩。
 */
export async function installOfflinePack({ onProgress, signal } = {}) {
  if (!cachesAvailable()) throw new Error('这台设备不支持离线评测包')
  const manifest = await readManifest()
  const cacheName = packCacheName(manifest)
  const cache = await caches.open(cacheName)
  let done = 0

  try {
    for (const file of manifest.files) {
      if (signal?.aborted) throw new Error('已取消下载')
      const url = asrAssetUrl(file.path)
      onProgress?.({ step: 'downloading', file: file.path, done, total: manifest.bytes })

      const response = await fetch(url, { cache: 'no-store', signal })
      if (!response.ok) throw new Error(`${file.path} 下载失败（HTTP ${response.status}）`)
      const buffer = await response.arrayBuffer()

      onProgress?.({ step: 'verifying', file: file.path, done, total: manifest.bytes })
      const digest = await sha256Hex(buffer)
      if (digest !== file.sha256) throw new Error(`${file.path} 指纹对不上，整包作废`)

      await cache.put(
        url,
        new Response(buffer, { headers: { 'content-type': file.type ?? 'application/octet-stream' } })
      )
      done += buffer.byteLength
      onProgress?.({ step: 'downloading', file: file.path, done, total: manifest.bytes })
    }
  } catch (error) {
    await caches.delete(cacheName).catch(() => {})
    throw error
  }

  onProgress?.({ step: 'ready', done, total: manifest.bytes })
  return manifest
}

/** 家长要删就真删：这一版的整个缓存都清掉，下次回到录音档。 */
export async function removeOfflinePack() {
  if (typeof caches === 'undefined') return false
  const names = await caches.keys()
  const mine = names.filter((name) => name.startsWith(OFFLINE_ASR.cachePrefix))
  await Promise.all(mine.map((name) => caches.delete(name)))
  return mine.length > 0
}

/**
 * 起一个 Worker 跑 sherpa-onnx。
 *
 * 主线程只收进度、partial/final 和引擎自报的置信度；初始化和收尾都有超时，
 * 超时即视为这一档不可用，由调用方降到录音档。
 */
export function createOfflineRecognizer(manifest, { timeoutMs = OFFLINE_ASR.initTimeoutMs } = {}) {
  const worker = new Worker(new URL('../workers/sherpaAsrWorker.js', import.meta.url), {
    type: 'module',
    name: 'sherpa-asr'
  })

  let partialText = ''
  let settleFinal = null
  let disposed = false
  const waiters = { ready: null }

  const fail = (message) => {
    waiters.ready?.reject(new Error(message))
    waiters.ready = null
    settleFinal?.({ text: partialText, confidence: 0, degraded: true })
    settleFinal = null
  }

  worker.onerror = (event) => fail(event.message || '离线评测引擎崩了')
  worker.onmessageerror = () => fail('离线评测引擎发回了读不懂的消息')
  worker.onmessage = (event) => {
    const data = event.data ?? {}
    if (data.type === 'ready') {
      waiters.ready?.resolve(true)
      waiters.ready = null
    } else if (data.type === 'partial') {
      partialText = data.text ?? partialText
    } else if (data.type === 'final') {
      settleFinal?.({
        text: data.text ?? partialText,
        tokens: data.tokens ?? [],
        timings: data.timings ?? [],
        confidence: Number.isFinite(data.confidence) ? data.confidence : null,
        degraded: false
      })
      settleFinal = null
    } else if (data.type === 'error') {
      fail(data.message ?? '离线评测引擎起不来')
    }
  }

  const withTimeout = (promise, ms, message) =>
    Promise.race([
      promise,
      new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms))
    ])

  const ready = withTimeout(
    new Promise((resolve, reject) => {
      waiters.ready = { resolve, reject }
      worker.postMessage({
        type: 'init',
        cacheName: packCacheName(manifest),
        sampleRate: OFFLINE_ASR.sampleRate,
        files: manifest.files.map((file) => ({ ...file, url: asrAssetUrl(file.path) }))
      })
    }),
    timeoutMs,
    `离线评测引擎 ${timeoutMs} 毫秒内没起来`
  )

  return {
    modelVersion: manifest.modelVersion,
    modelId: manifest.modelId,
    ready,
    /** @param {Int16Array} pcm 16 kHz 单声道 */
    accept(pcm) {
      if (disposed || !pcm?.length) return
      const copy = pcm.slice()
      worker.postMessage({ type: 'audio', pcm: copy }, [copy.buffer])
    },
    /** 收尾：拿最后一段 final，超时就把已有的 partial 交出去并标记降级。 */
    finish(ms = OFFLINE_ASR.finalTimeoutMs) {
      if (disposed) return Promise.resolve({ text: partialText, confidence: 0, degraded: true })
      return withTimeout(
        new Promise((resolve) => {
          settleFinal = resolve
          worker.postMessage({ type: 'flush' })
        }),
        ms,
        '离线评测收尾超时'
      ).catch(() => ({ text: partialText, confidence: 0, degraded: true }))
    },
    dispose() {
      if (disposed) return
      disposed = true
      settleFinal = null
      try {
        worker.postMessage({ type: 'dispose' })
      } catch {
        /* 已经没了 */
      }
      worker.terminate()
    }
  }
}
