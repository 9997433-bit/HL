/**
 * ROUND12_H1 —— 落库的那 35 MiB 到底能不能跑。
 *
 * 清单里写着 sha256、体积、角色，那些只证明「文件是我们放进去的那一份」。
 * 这个脚本证明另一件事：**把它们按 Worker 那套装法装起来，引擎真的会说中文**。
 * 装法和 src/workers/sherpaAsrWorker.js 的 boot() 一模一样——
 * 非模块胶水用 new Function 递 Module、空包 getPreloadedPackage、
 * 模型运行时写进 MEMFS、createOnlineRecognizer 从 asr-api 那份 JS 里取。
 * 两边哪天走岔了，这里会先红。
 *
 * 音频是上游模型仓库自带的示例（成人普通话，Apache-2.0，见 manifest.source.engineFixture）。
 * **它不是儿童冻结集**：这里量的是「引擎跑不跑得动、解码对不对、桌面 RTF 多少」，
 * 不是「这个模型对孩子好不好用」。后者要等 F4 的 300 条实录，谁都别拿这条充数。
 *
 * 用法：node scripts/test-asr-engine.mjs [--json]
 */

import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { PACK_ROLES, parseManifest } from '../src/utils/offlineAsr.js'
import { alignChars, normalizeTranscript } from '../src/utils/speechEval.js'
import { bootEngine, bytesOf, readManifest, readWav } from './lib/asr-runtime.mjs'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const asJson = process.argv.includes('--json')
const manifest = readManifest()

/** 上游给这条示例音频公布的参考转写；逐字对齐用它当分母。 */
const FIXTURE = {
  wav: path.join(appRoot, 'scripts/fixtures/asr/upstream-zh-0.wav'),
  reference: '对我做了介绍那么我想说的是大家如果对我的研究感兴趣'
}
/** 桌面 VM 上的实时因子红线。真机门槛（≤0.5）另算，见清单 goNoGo 性能层。 */
const DESKTOP_RTF_BUDGET = 0.35

const tests = []
const test = (name, fn) => tests.push({ name, fn })
const sha256 = (buffer) => createHash('sha256').update(buffer).digest('hex')

/* ------------------------------------------------------------ 1. 落库核对 */

const files = Array.isArray(manifest.files) ? manifest.files : []

test('清单里的每个文件都真在 public/ 下发得出去，bytes 与 sha256 逐项对得上', () => {
  assert.ok(files.length >= PACK_ROLES.length, `清单只有 ${files.length} 个文件`)
  for (const file of files) {
    const body = bytesOf(file.path)
    assert.equal(body.length, file.bytes, `${file.path} 实际 ${body.length} 字节，清单写 ${file.bytes}`)
    assert.equal(sha256(body), file.sha256, `${file.path} 指纹对不上，落库的不是清单里那一份`)
  }
})

test('七个角色一个不少，整包不超 60 MiB', () => {
  const roles = new Set(files.map((f) => f.role))
  const missing = PACK_ROLES.filter((role) => !roles.has(role))
  assert.equal(missing.length, 0, `缺角色：${missing.join('、')}`)
  const total = files.reduce((n, f) => n + f.bytes, 0)
  assert.ok(total <= 60 * 1048576, `整包 ${(total / 1048576).toFixed(2)} MiB 超预算`)
})

test('每个文件都写明了出处、上游 sha256 与许可证——落库不许来路不明', () => {
  const sources = manifest.source?.files ?? []
  for (const file of files) {
    const source = sources.find((s) => s.path === file.path)
    assert.ok(source, `${file.path} 没有出处记录`)
    assert.ok(/^(hf:|k2-fsa\/)/.test(source.from), `${file.path} 的出处写得不可复现：${source.from}`)
    assert.match(source.upstreamSha256 ?? '', /^[a-f0-9]{64}$/, `${file.path} 没记上游 sha256`)
    assert.ok(source.license, `${file.path} 没记许可证`)
  }
})

test('胶水只被改了一处：除 loadPackage 元数据外与上游逐字节相同', () => {
  const glue = files.find((f) => f.role === 'wasm-glue')
  const source = manifest.source.files.find((s) => s.path === glue.path)
  const text = bytesOf(glue.path).toString('utf8')
  assert.match(text, /loadPackage\(\{"files":\[\],"remote_package_size":0\}\)/, '空包元数据不见了')
  assert.equal(
    text.match(/loadPackage\(\{/g).length,
    1,
    '胶水里出现了第二处 loadPackage——改动范围失控'
  )
  assert.notEqual(sha256(bytesOf(glue.path)), source.upstreamSha256, '胶水没改过，那空包是哪来的')
})

/* --------------------------------------------------- 2. 按 Worker 的装法启动 */

/** 装法本身在 scripts/lib/asr-runtime.mjs，与 bench-asr-rtf.mjs 共用同一份。 */

const run = { bootMs: null, createMs: null, decodeMs: null, seconds: null, rtf: null, text: '' }

test('引擎按 Worker 的装法起得来，且启动全程零网络请求', async () => {
  const guard = () => {
    throw new Error('装引擎过程中发起了网络请求——离线档不许触网')
  }
  const savedFetch = globalThis.fetch
  globalThis.fetch = guard
  const t0 = Date.now()
  try {
    const engine = await bootEngine(files)
    run.bootMs = Date.now() - t0
    const t1 = Date.now()
    run.recognizer = engine.createOnlineRecognizer(engine.Module, undefined)
    run.createMs = Date.now() - t1
  } finally {
    globalThis.fetch = savedFetch
  }
  assert.ok(run.recognizer, '引擎没起来')
})

test('喂一段真实中文语音，解码出来的是中文，不是空串也不是乱码', () => {
  const { sampleRate, samples } = readWav(FIXTURE.wav)
  const stream = run.recognizer.createStream()
  const t0 = Date.now()
  // 100 ms 一帧，和 pcm-capture.worklet.js 送上来的粒度一致
  const chunk = sampleRate / 10
  for (let i = 0; i < samples.length; i += chunk) {
    stream.acceptWaveform(sampleRate, samples.subarray(i, Math.min(samples.length, i + chunk)))
    while (run.recognizer.isReady(stream)) run.recognizer.decode(stream)
  }
  stream.inputFinished()
  while (run.recognizer.isReady(stream)) run.recognizer.decode(stream)
  run.decodeMs = Date.now() - t0
  run.seconds = samples.length / sampleRate
  run.rtf = run.decodeMs / 1000 / run.seconds
  run.text = run.recognizer.getResult(stream)?.text ?? ''
  assert.ok(run.text.length >= 10, `只解出「${run.text}」`)
  assert.match(run.text, /^[\u4e00-\u9fa5]+$/, `解码结果不是纯中文：${run.text}`)
})

test('逐字对齐字符召回 ≥90%——引擎与 speechEval 这条路是通的', () => {
  const reference = normalizeTranscript(FIXTURE.reference)
  const { hits, total } = alignChars(reference, normalizeTranscript(run.text))
  run.recall = hits / total
  run.hits = hits
  run.total = total
  assert.ok(
    run.recall >= 0.9,
    `字符召回 ${(run.recall * 100).toFixed(1)}%（${hits}/${total}）：「${run.text}」`
  )
})

test(`桌面实时因子 ≤ ${DESKTOP_RTF_BUDGET}——中端 Android 的门槛（0.5）另由真机测`, () => {
  assert.ok(run.rtf <= DESKTOP_RTF_BUDGET, `RTF ${run.rtf.toFixed(3)} 超过桌面红线`)
})

/* ------------------------------------------------------------------ 跑与出 */

let failed = 0
const failures = []
for (const { name, fn } of tests) {
  try {
    await fn()
    if (!asJson) console.log(`  ✓ ${name}`)
  } catch (error) {
    failed += 1
    failures.push(`${name}：${error.message}`)
    if (!asJson) console.log(`  ✗ ${name}\n      ${error.message}`)
  }
}

let packBytes = files.reduce((n, f) => n + f.bytes, 0)
let parsed = null
try {
  parsed = parseManifest({ ...manifest, available: true })
  packBytes = parsed.bytes
} catch {
  /* available 仍是 false 时这里只是拿不到解析结果，不影响判定 */
}

if (asJson) {
  console.log(
    JSON.stringify(
      {
        marker: 'ROUND12_H1',
        modelId: manifest.modelId,
        modelVersion: manifest.modelVersion,
        available: manifest.available,
        packBytes,
        packMiB: Number((packBytes / 1048576).toFixed(2)),
        engine: {
          bootMs: run.bootMs,
          createMs: run.createMs,
          decodeMs: run.decodeMs,
          audioSeconds: run.seconds,
          rtf: run.rtf === null ? null : Number(run.rtf.toFixed(3)),
          text: run.text,
          charRecall: run.recall === undefined ? null : Number(run.recall.toFixed(3)),
          reference: FIXTURE.reference
        },
        passed: tests.length - failed,
        tests: tests.length,
        failures
      },
      null,
      2
    )
  )
} else {
  console.log('')
  console.log(`  整包 ${(packBytes / 1048576).toFixed(2)} MiB · ${manifest.modelId}@${manifest.modelVersion} · available=${manifest.available}`)
  console.log(`  引擎启动 ${run.bootMs} ms（含 wasm 编译）+ 建识别器 ${run.createMs} ms`)
  console.log(`  解码 ${run.seconds?.toFixed(2)} s 音频用 ${run.decodeMs} ms，桌面 RTF ${run.rtf?.toFixed(3)}`)
  console.log(`  参考「${FIXTURE.reference}」`)
  console.log(`  识别「${run.text}」→ 字符召回 ${run.hits}/${run.total}`)
  console.log('  提醒：这是上游成人示例音频，只证明引擎跑得动；儿童冻结集另测（F4）。')
  console.log(`\n离线 ASR 落库回归（ROUND12_H1）：${tests.length - failed} / ${tests.length} 项通过。`)
}

process.exit(failed ? 1 : 0)
