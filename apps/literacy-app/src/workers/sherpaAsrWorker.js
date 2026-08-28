/**
 * 跟读 v3 · sherpa-onnx WASM Worker（spike）。
 *
 * 主线程只把 16 kHz Int16 PCM 丢进来，识别、解码全在这条 Worker 线程上跑：
 * 低端机上 wasm 推理动辄几百毫秒，放主线程会把跟读界面卡成幻灯片。
 *
 * 引擎文件全部从 utils/offlineAsr.js 装好的版本化 Cache Storage 里取，
 * 这里不发任何网络请求——缓存里没有就直接报错，让上层降回录音档。
 *
 * ROUND12_H1：模型落库之后，这里对上的是**真实的 sherpa-onnx WASM 产物形状**——
 * 官方胶水是非 MODULARIZE 的普通脚本（不导出工厂函数），模型也不再走 --preload-file
 * 的 .data，而是由 gen-asr-pack.mjs 逐文件自托管、由这里在运行时写进 MEMFS。
 * 七个角色少一个都起不来，见 boot()。
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

/** Emscripten MEMFS 里模型的落点；createOnlineRecognizer 按相对路径去开这几个文件。 */
const FS_NAMES = {
  'model-encoder': 'encoder.onnx',
  'model-decoder': 'decoder.onnx',
  'model-joiner': 'joiner.onnx',
  tokens: 'tokens.txt'
}

/**
 * 跟读只认中文流式 transducer：整份配置在这里写死，不从清单里读。
 * 清单能决定「装哪个模型」，不能决定「按什么规矩打分」——后者一变，
 * 冻结集跑出来的分数就不能和上一版横比了（清单 F10）。
 */
function recognizerConfig(rate) {
  return {
    featConfig: { sampleRate: rate, featureDim: 80 },
    modelConfig: {
      transducer: { encoder: './encoder.onnx', decoder: './decoder.onnx', joiner: './joiner.onnx' },
      paraformer: { encoder: '', decoder: '' },
      zipformer2Ctc: { model: '' },
      nemoCtc: { model: '' },
      toneCtc: { model: '' },
      tokens: './tokens.txt',
      numThreads: 1,
      provider: 'cpu',
      debug: 0,
      modelType: 'zipformer',
      modelingUnit: 'cjkchar',
      bpeVocab: ''
    },
    decodingMethod: 'greedy_search',
    maxActivePaths: 4,
    // 断句由跟读界面控制（孩子读完一句才收尾），引擎自己别插手
    enableEndpoint: 0,
    rule1MinTrailingSilence: 2.4,
    rule2MinTrailingSilence: 1.2,
    rule3MinUtteranceLength: 20,
    hotwordsFile: '',
    hotwordsScore: 1.5,
    ctcFstDecoderConfig: { graph: '', maxActive: 3000 },
    ruleFsts: '',
    ruleFars: ''
  }
}

/**
 * 装引擎。
 *
 * 上游 WASM 产物的真实形状（v1.12.15 实查）：
 *   - 胶水是**非 MODULARIZE** 的普通脚本，跑起来就地改一个叫 Module 的对象，
 *     不导出工厂函数——所以用 new Function 把我们自己的 Module 传进去，
 *     再等 onRuntimeInitialized；
 *   - 胶水里 loadPackage() 的元数据已被 gen-asr-pack.mjs 改成空包，
 *     配上 getPreloadedPackage 返回空 buffer，启动过程一个网络请求都不会发；
 *   - 模型/tokens 由我们在运行时写进 MEMFS，路径与 recognizerConfig 一一对应；
 *   - createOnlineRecognizer 在另一份 JS API 里（asr-api 角色），也从缓存取。
 */
async function boot({ cacheName, files }) {
  const pick = (role) => {
    const file = files.find((item) => item.role === role)
    if (!file) throw new Error(`离线评测包缺少 ${role}`)
    return file
  }
  const roles = ['wasm-glue', 'wasm-binary', 'asr-api', ...Object.keys(FS_NAMES)]
  const loaded = Object.fromEntries(
    await Promise.all(
      roles.map(async (role) => [role, await cachedBytes(cacheName, pick(role).url)])
    )
  )

  const decoder = new TextDecoder()
  const Module = {
    wasmBinary: loaded['wasm-binary'],
    // 空包：模型不走 --preload-file，locateFile 也就没有第二个去处
    getPreloadedPackage: () => new ArrayBuffer(0),
    locateFile: (name) => files.find((file) => file.path.endsWith(name))?.url ?? name,
    print: () => {},
    printErr: () => {}
  }
  const started = new Promise((resolve, reject) => {
    Module.onRuntimeInitialized = resolve
    Module.onAbort = (reason) => reject(new Error(`wasm 起不来：${reason}`))
  })
  // eslint-disable-next-line no-new-func -- 上游胶水是非模块脚本，只能这样把 Module 递进去
  new Function('Module', decoder.decode(loaded['wasm-glue']))(Module)
  await started

  for (const [role, name] of Object.entries(FS_NAMES)) {
    Module.FS_createDataFile('/', name, new Uint8Array(loaded[role]), true, true, true)
  }

  // eslint-disable-next-line no-new-func -- 同上；给一个 module 壳，免得它走 node 分支
  const api = new Function(
    'module',
    `${decoder.decode(loaded['asr-api'])}\n;return createOnlineRecognizer;`
  )({ exports: {} })
  if (typeof api !== 'function') throw new Error('引擎没有暴露 createOnlineRecognizer')

  recognizer = api(Module, recognizerConfig(sampleRate))
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
