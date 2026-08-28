/**
 * ROUND13_H1 —— 跟读离线 ASR 的 RTF 基准（主机侧）。
 *
 * 卡住 available 的两件事，一件是冻结集没录（F4），另一件是**真机性能没测**（F7）：
 * 中端 Android 上句末到结果 P95 ≤2.5 秒、RTF ≤0.5、峰值新增内存 ≤300 MiB、
 * 主线程无 >100 ms 长任务。这四条只有真机说了算，而 VM 里没有真机。
 *
 * 那这个脚本量什么？量**同一套装法在这台主机上的实时因子、句末尾延迟、
 * 逐帧解码耗时和内存增量**，外加一段可在 Android WebView 里原样重跑的
 * CPU 标定回路。它给出的是三样东西：
 *
 *   1. **一条地板线。** 真机不可能比主机快。主机 RTF 都超 0.5 的话，
 *      根本不用等真机排期就知道这个量化档没戏，当场换档比等三周便宜。
 *   2. **一把尺子。** `calibration` 是一段纯 JS 的定长浮点回路，
 *      在 Android WebView 的 console 里跑同一段就能拿到 deviceLoopMs。
 *      真机 RTF ≈ hostRtfP95 × (deviceLoopMs / hostLoopMs)——
 *      这样真机那一趟只需要量一个数，就能先算出预期值再去对照实测。
 *   3. **一份可复现的记录。** 机型、核数、负载、每一趟的原始值都写进
 *      .agent_workspace/evidence/r13/asr-rtf/host-baseline.json，
 *      下一轮换模型/换量化档时能横比。
 *
 * 它**不给**的是结论。输出里的 projection.deviceVerdict 恒为 unmeasured，
 * onDevice 恒为 false；test-asr-eval-set.mjs 有一条断言专门守着
 * 「这些数不许流进性能层的实测列」。口径见
 * .agent_workspace/r13-asr-android-rtf-baseline.md。
 *
 * 用法：node scripts/bench-asr-rtf.mjs [--passes 5] [--json] [--out <path>]
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { bootEngine, readManifest, readWav } from './lib/asr-runtime.mjs'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = path.resolve(appRoot, '../..')
const argv = process.argv.slice(2)
const asJson = argv.includes('--json')
const flag = (name, fallback) => {
  const at = argv.indexOf(name)
  return at >= 0 && argv[at + 1] ? argv[at + 1] : fallback
}
const passes = Math.max(3, Number(flag('--passes', '5')))
const outPath = path.resolve(
  repoRoot,
  flag('--out', '.agent_workspace/evidence/r13/asr-rtf/host-baseline.json')
)

const FIXTURE = path.join(appRoot, 'scripts/fixtures/asr/upstream-zh-0.wav')

/**
 * 中端 Android 的 WebView 跑完一遍 calibrationLoop 大约要多久（毫秒）。
 *
 * 这是整份记录里**唯一的假设**，也是真机那一趟唯一需要替掉的数：
 * 500 ms 对应状态好的中端芯（近两年 2GHz 级大核、未热降频），
 * 1200 ms 对应千元机或降频之后。Android QA 在真机 WebView 里跑一遍
 * 同一段回路，把实测值填进来，推算就变成了半实测。
 *
 * 为什么锚在「设备跑这段回路要多久」而不是「设备比主机慢几倍」：
 * 这台 CI VM 是共用的，负载动辄十几二十，主机自己的绝对耗时随时在飘。
 * 而 rtfPerLoopMs（RTF ÷ 回路耗时）里两边的抖动会互相抵消，
 * 它才是能跨机器、跨时间横比的那个量。
 */
const ANDROID_LOOP_MS = Object.freeze({ min: 500, max: 1200, basis: 'assumed-webview-scalar-loop' })
/** 性能层写死的真机门槛，只用来算「离红线还有多远」，不用来判定。 */
const DEVICE_BUDGET = Object.freeze({ rtf: 0.5, tailMs: 2500, longTaskMs: 100, memoryMiB: 300 })

const quantile = (list, q) => {
  if (!list.length) return null
  const sorted = [...list].sort((a, b) => a - b)
  const at = Math.min(sorted.length - 1, Math.max(0, Math.ceil(q * sorted.length) - 1))
  return sorted[at]
}
const round = (value, digits = 3) =>
  value === null || value === undefined ? null : Number(Number(value).toFixed(digits))
const stats = (list, digits = 3) => ({
  runs: list.length,
  min: round(Math.min(...list), digits),
  p50: round(quantile(list, 0.5), digits),
  p95: round(quantile(list, 0.95), digits),
  max: round(Math.max(...list), digits)
})

/**
 * CPU 标定回路：定长、纯标量、不分配内存，所以在 Node 与 WebView 里跑的是同一件事。
 * 别动这里的常数——改了它，历史记录就没法横比了。
 */
function calibrationLoop(iterations = 40_000_000) {
  let acc = 0
  for (let i = 1; i <= iterations; i += 1) acc += Math.sqrt(i) / (i + 1)
  return acc
}

function calibrate(runs = 5) {
  const samples = []
  for (let i = 0; i < runs; i += 1) {
    const started = performance.now()
    calibrationLoop()
    samples.push(performance.now() - started)
  }
  return { iterations: 40_000_000, ...stats(samples, 1) }
}

/* --------------------------------------------------------------- 跑一趟 */

const manifest = readManifest()
const files = Array.isArray(manifest.files) ? manifest.files : []
if (files.length === 0) {
  console.error('清单里没有落库文件，先跑 npm run gen:asr:pack')
  process.exit(1)
}

const loadBefore = os.loadavg()[0]
const rssBaseline = process.memoryUsage().rss

const bootStarted = performance.now()
const engine = await bootEngine(files)
const bootMs = performance.now() - bootStarted
const rssAfterBoot = process.memoryUsage().rss

const createStarted = performance.now()
const recognizer = engine.createOnlineRecognizer(engine.Module, undefined)
const createMs = performance.now() - createStarted

const { sampleRate, samples } = readWav(FIXTURE)
const audioSeconds = samples.length / sampleRate
/** 100 ms 一帧，与 pcm-capture.worklet.js 送上来的粒度一致。 */
const chunk = sampleRate / 10

const rtfs = []
const tails = []
const chunkMs = []
let rssPeak = rssBaseline
let text = ''

for (let pass = 0; pass < passes; pass += 1) {
  const stream = recognizer.createStream()
  const started = performance.now()
  for (let i = 0; i < samples.length; i += chunk) {
    const frameStarted = performance.now()
    stream.acceptWaveform(sampleRate, samples.subarray(i, Math.min(samples.length, i + chunk)))
    while (recognizer.isReady(stream)) recognizer.decode(stream)
    chunkMs.push(performance.now() - frameStarted)
  }
  // 句末：孩子读完最后一个字，到界面能给出结果之间的那段等待
  const tailStarted = performance.now()
  stream.inputFinished()
  while (recognizer.isReady(stream)) recognizer.decode(stream)
  text = recognizer.getResult(stream)?.text ?? ''
  const tailMs = performance.now() - tailStarted
  const totalMs = performance.now() - started

  rtfs.push(totalMs / 1000 / audioSeconds)
  tails.push(tailMs)
  rssPeak = Math.max(rssPeak, process.memoryUsage().rss)
  stream.free?.()
}

const rtf = stats(rtfs)
const calibration = calibrate()
/** 抵掉共用 VM 的负载抖动：这个比值才是能横比的量。 */
const rtfPerLoopMs = rtf.p50 / calibration.p50
const projectionBand = [
  round(rtfPerLoopMs * ANDROID_LOOP_MS.min),
  round(rtfPerLoopMs * ANDROID_LOOP_MS.max)
]
const contended = loadBefore / os.cpus().length > 1.5

const report = {
  marker: 'ROUND13_H1',
  schema: 'literacy-asr-rtf-baseline/1',
  /** 这台机器不是 Android 真机。整份记录的意义全系在这个字段上。 */
  onDevice: false,
  measuredAt: new Date().toISOString(),
  host: {
    kind: 'ci-vm',
    cpu: os.cpus()[0]?.model?.replace(/\s+/g, ' ').trim() ?? 'unknown',
    cores: os.cpus().length,
    totalMemGiB: round(os.totalmem() / 1073741824, 1),
    platform: `${os.platform()} ${os.release()}`,
    node: process.version,
    load1Before: round(loadBefore, 2),
    load1After: round(os.loadavg()[0], 2),
    shared: true,
    /** 共用 VM 上别人也在跑：绝对耗时会被拉长，rtfPerLoopMs 不受影响。 */
    contended
  },
  pack: {
    modelId: manifest.modelId,
    modelVersion: manifest.modelVersion,
    bytes: files.reduce((n, f) => n + (f.bytes ?? 0), 0)
  },
  calibration,
  engine: { bootMs: round(bootMs, 1), createRecognizerMs: round(createMs, 1) },
  fixture: {
    path: 'apps/literacy-app/scripts/fixtures/asr/upstream-zh-0.wav',
    audioSeconds: round(audioSeconds, 2),
    frameMs: 100,
    speaker: 'adult',
    note: '上游模型仓库自带的成人普通话示例。儿童语速与共发音另计，见 F4 冻结集。'
  },
  decode: { passes, rtf, rtfPerLoopMs: round(rtfPerLoopMs, 6), text },
  tailMs: stats(tails, 1),
  chunkMs: stats(chunkMs, 1),
  memory: {
    rssBaselineMiB: round(rssBaseline / 1048576, 1),
    rssAfterBootMiB: round(rssAfterBoot / 1048576, 1),
    rssPeakMiB: round(rssPeak / 1048576, 1),
    peakRssDeltaMiB: round((rssPeak - rssBaseline) / 1048576, 1),
    note:
      'Node 进程的 RSS 增量，含 wasm 线性内存与 onnx 权重，且 Node 不急着回收——' +
      '这是上界，不是 WebView 里的实际占用。真机口径由 F7 单独测。'
  },
  projection: {
    method:
      'deviceRtf ≈ rtfPerLoopMs × deviceLoopMs；deviceLoopMs 由同一段 calibrationLoop 在 Android WebView 里跑出，' +
      '除以主机耗时的做法可抵掉共用 VM 的负载抖动',
    deviceLoopMsAssumption: ANDROID_LOOP_MS,
    androidRtfBand: projectionBand,
    budget: DEVICE_BUDGET,
    /** 恒为 unmeasured：推算不是实测，这里不替真机签字。 */
    deviceVerdict: 'unmeasured',
    owner: 'SKIP owner: Android QA',
    blocks: 'freezeChecklist F7 → available=true'
  }
}

fs.mkdirSync(path.dirname(outPath), { recursive: true })
fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`)

if (asJson) {
  console.log(JSON.stringify(report, null, 2))
} else {
  console.log(
    `  主机：${report.host.cpu} × ${report.host.cores}，负载 ${report.host.load1Before} → ` +
      `${report.host.load1After}${contended ? '（共用 VM 有争抢，绝对耗时偏大）' : ''}`
  )
  console.log(`  标定回路：${report.calibration.iterations.toLocaleString('en-US')} 次，p50 ${report.calibration.p50} ms`)
  console.log(`  启动 ${report.engine.bootMs} ms + 建识别器 ${report.engine.createRecognizerMs} ms`)
  console.log(
    `  解码 ${passes} 趟 ${report.fixture.audioSeconds} s 音频：` +
      `RTF min ${rtf.min} · p50 ${rtf.p50} · p95 ${rtf.p95} · max ${rtf.max}` +
      ` · 归一化 ${report.decode.rtfPerLoopMs} RTF/回路 ms`
  )
  console.log(`  句末到结果：p50 ${report.tailMs.p50} ms · p95 ${report.tailMs.p95} ms（真机预算 ${DEVICE_BUDGET.tailMs} ms）`)
  console.log(`  逐帧解码：p95 ${report.chunkMs.p95} ms · max ${report.chunkMs.max} ms（长任务红线 ${DEVICE_BUDGET.longTaskMs} ms，Worker 内不算主线程）`)
  console.log(`  内存增量：峰值 +${report.memory.peakRssDeltaMiB} MiB 上界（真机预算 ${DEVICE_BUDGET.memoryMiB} MiB）`)
  console.log(`  识别「${text}」`)
  console.log('')
  console.log(
    `  推算中端 Android RTF ${projectionBand[0]}–${projectionBand[1]}` +
      `（假设回路 ${ANDROID_LOOP_MS.min}–${ANDROID_LOOP_MS.max} ms，门槛 ${DEVICE_BUDGET.rtf}）` +
      ` —— ${report.projection.deviceVerdict}，${report.projection.owner}`
  )
  console.log(`  写入 ${path.relative(repoRoot, outPath)}`)
  console.log('\n提醒：这台机器不是 Android 真机，这份记录不构成 F7 的验收证据。')
}
