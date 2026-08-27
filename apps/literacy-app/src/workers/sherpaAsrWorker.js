/**
 * 跟读 v3 · sherpa-onnx WASM Worker（spike）。
 *
 * 主线程只把 16 kHz Int16 PCM 丢进来，识别、解码全在这条 Worker 线程上跑：
 * 低端机上 wasm 推理动辄几百毫秒，放主线程会把跟读界面卡成幻灯片。
 *
 * 引擎文件全部从 utils/offlineAsr.js 装好的版本化 Cache Storage 里取，
 * 这里不发任何网络请求——缓存里没有就直接报错，让上层降回录音档。
 *
 * 协议（主线程 → Worker）：
 *   { type:'init', cacheName, sampleRate, files:[{ path, role, url }] }
 *   { type:'audio', pcm:Int16Array }   // transferable
 *   { type:'flush' } / { type:'dispose' }
 *
 * 协议（Worker → 主线程）：
 *   { type:'ready' } | { type:'partial', text }
 *   { type:'final', text, tokens, timings, confidence } | { type:'error', message }
 */

let recognizer = null
let stream = null
let sampleRate = 16000
let lastText = ''

const post = (message) => self.postMessage(message)

async function cachedBytes(cacheName, url) {
  const cache = await caches.open(cacheName)
  const hit = await cache.match(url)
  if (!hit) throw new Error(`离线评测包里少了 ${url.split('/').pop()}`)
  return hit.arrayBuffer()
}

/**
 * 装引擎。
 *
 * sherpa-onnx 的 wasm 产物是「胶水 JS + .wasm 二进制 + 模型/tokens」，
 * 胶水脚本导出一个 Emscripten 工厂函数；把 wasmBinary 直接喂给它，
 * 就不会再去按相对路径找 .wasm（Worker 里那条路径本来也不通）。
 */
async function boot({ cacheName, files }) {
  const glue = files.find((file) => file.role === 'wasm-glue')
  const binary = files.find((file) => file.role === 'wasm-binary')
  if (!glue || !binary) throw new Error('清单里没有 wasm 胶水脚本或二进制')

  const [glueSource, wasmBinary] = await Promise.all([
    cachedBytes(cacheName, glue.url),
    cachedBytes(cacheName, binary.url)
  ])

  const blobUrl = URL.createObjectURL(
    new Blob([glueSource], { type: 'text/javascript' })
  )
  let factoryModule
  try {
    factoryModule = await import(/* @vite-ignore */ blobUrl)
  } finally {
    URL.revokeObjectURL(blobUrl)
  }

  const createModule = factoryModule.default ?? factoryModule.createSherpaOnnxModule
  if (typeof createModule !== 'function') {
    throw new Error('wasm 胶水脚本没有导出 Emscripten 工厂函数')
  }

  const runtime = await createModule({
    wasmBinary,
    // 模型、tokens 也走缓存：locateFile 再去猜路径就会打到网络上。
    locateFile: (name) => files.find((file) => file.path.endsWith(name))?.url ?? name
  })

  const create = runtime.createOnlineRecognizer ?? factoryModule.createOnlineRecognizer
  if (typeof create !== 'function') {
    throw new Error('引擎没有暴露 createOnlineRecognizer')
  }

  recognizer = create(runtime, {
    featConfig: { sampleRate, featureDim: 80 },
    decodingMethod: 'greedy_search',
    enableEndpoint: false
  })
  stream = recognizer.createStream()
}

function feed(pcm) {
  if (!recognizer || !stream) return
  // 引擎吃 Float32；Int16 是主线程为了少传一半字节做的压缩
  const float = new Float32Array(pcm.length)
  for (let i = 0; i < pcm.length; i += 1) float[i] = pcm[i] / 32768
  stream.acceptWaveform(sampleRate, float)
  while (recognizer.isReady(stream)) recognizer.decode(stream)
  const text = recognizer.getResult(stream)?.text ?? ''
  if (text && text !== lastText) {
    lastText = text
    post({ type: 'partial', text })
  }
}

function flush() {
  if (!recognizer || !stream) {
    post({ type: 'final', text: lastText, tokens: [], timings: [], confidence: null })
    return
  }
  stream.inputFinished?.()
  while (recognizer.isReady(stream)) recognizer.decode(stream)
  const result = recognizer.getResult(stream) ?? {}
  post({
    type: 'final',
    text: result.text ?? lastText,
    tokens: result.tokens ?? [],
    timings: result.timestamps ?? [],
    // 引擎不给逐句置信度时宁可交 null，也不要编一个数字出来当依据
    confidence: Number.isFinite(result.confidence) ? result.confidence : null
  })
}

function dispose() {
  try {
    stream?.free?.()
    recognizer?.free?.()
  } catch {
    /* 引擎已经塌了，没什么可回收的 */
  }
  stream = null
  recognizer = null
}

self.onmessage = async (event) => {
  const data = event.data ?? {}
  try {
    if (data.type === 'init') {
      sampleRate = data.sampleRate ?? sampleRate
      await boot(data)
      post({ type: 'ready' })
    } else if (data.type === 'audio') {
      feed(data.pcm)
    } else if (data.type === 'flush') {
      flush()
    } else if (data.type === 'dispose') {
      dispose()
      self.close()
    }
  } catch (error) {
    dispose()
    post({ type: 'error', message: error?.message ?? String(error) })
  }
}
