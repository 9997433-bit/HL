import assert from 'node:assert/strict'
import {
  OFFLINE_ASR,
  chooseTier,
  floatToPcm16,
  modeOfTier,
  packCacheName,
  parseManifest,
  resampleTo16k,
  sourceOfTier
} from '../src/utils/offlineAsr.js'
import {
  GRADES,
  LOUDNESS_SCORE_CAP,
  alignChars,
  companionReplyForResult,
  evaluate,
  gradeOf,
  normalizeTranscript,
  phonemeMarks,
  scoreFromLoudness,
  scoreFromSimilarity,
  similarity,
  similarityV2
} from '../src/utils/speechEval.js'

const tests = []
const test = (name, fn) => tests.push({ name, fn })

const REF = '床前明月光'

test('识别结果只留汉字，标点和英文都不参与判分', () => {
  assert.equal(normalizeTranscript('床前，明月光。'), REF)
  assert.equal(normalizeTranscript('床前 ok 明月光 123'), REF)
  assert.equal(normalizeTranscript(null), '')
})

test('念全对是满分', () => {
  assert.equal(similarity(REF, '床前明月光'), 1)
  assert.equal(scoreFromSimilarity(similarity(REF, '床前，明月光。')), 100)
})

test('漏字只扣漏掉的那几个字，后面的字不会被连坐', () => {
  // 漏了「前」，剩下四个字仍应判对
  const { chars, hits, total } = alignChars(REF, '床明月光')
  assert.equal(total, 5)
  assert.equal(hits, 4)
  assert.deepEqual(
    chars.map((c) => c.status),
    ['hit', 'miss', 'hit', 'hit', 'hit']
  )
})

test('多念出来的字只轻罚，不会把一遍好的跟读判成不及格', () => {
  const score = scoreFromSimilarity(similarity(REF, '床前明月光读完啦'))
  assert.ok(score >= 80, `多读三个字后得 ${score} 分，罚得太重`)
  assert.ok(score < 100, '多读了字还给满分，等于不看多读')
})

test('v3 转写代理能区分声调候选、近音候选和同音字', () => {
  const pinyin = new Map([
    ['妈', 'mā'],
    ['马', 'mǎ'],
    ['山', 'shān'],
    ['三', 'sān'],
    ['他', 'tā'],
    ['她', 'tā']
  ])
  const detail = phonemeMarks('妈山他', '马三她', (char) => pinyin.get(char))

  assert.deepEqual(detail.chars.map((item) => item.status), ['tone', 'near', 'hit'])
  assert.equal(detail.toneErrors, 1)
  assert.equal(detail.nearMisses, 1)
  assert.equal(detail.hits, 1)
  assert.equal(similarityV2('妈山他', '马三她', (char) => pinyin.get(char)), 1.75 / 3)
})

test('v3 转写代理对漏字和未知拼音保守判 miss，多读仍沿用轻罚', () => {
  const pinyin = new Map([
    ['妈', 'ma1'],
    ['马', 'ma3'],
    ['好', 'hao3']
  ])
  const lookup = (char) => pinyin.get(char)
  const detail = phonemeMarks('妈龘', '马大', lookup)

  assert.deepEqual(detail.chars.map((item) => item.status), ['tone', 'miss'])
  assert.equal(detail.misses, 1)
  assert.equal(similarityV2('妈妈', '妈妈好好', lookup), 0.8)
})

test('念的完全是别的内容判 0 分', () => {
  assert.equal(similarity(REF, '今天天气真好'), 0)
  assert.equal(scoreFromSimilarity(similarity(REF, '')), 0)
})

test('响度档封顶 85 分，不会给出它其实听不出来的满分', () => {
  const best = scoreFromLoudness({ voicedRatio: 1, durationRatio: 1.5, peak: 1 })
  assert.equal(best, LOUDNESS_SCORE_CAP)
})

test('响度档：没出声就是 0 分', () => {
  assert.equal(scoreFromLoudness({ voicedRatio: 0, durationRatio: 1, peak: 0 }), 0)
  assert.equal(scoreFromLoudness({ voicedRatio: 0.5, durationRatio: 1, peak: 0.01 }), 0)
  assert.equal(scoreFromLoudness(), 0)
})

test('响度档：读得越久越响分越高', () => {
  const quiet = scoreFromLoudness({ voicedRatio: 0.2, durationRatio: 0.3, peak: 0.1 })
  const loud = scoreFromLoudness({ voicedRatio: 0.8, durationRatio: 0.9, peak: 0.4 })
  assert.ok(loud > quiet, `认真读完 ${loud} 分没有高过敷衍 ${quiet} 分`)
})

test('分档阈值单调，且 0 分也有一句话可说', () => {
  assert.equal(gradeOf(100).id, 'gold')
  assert.equal(gradeOf(85).id, 'gold')
  assert.equal(gradeOf(84).id, 'silver')
  assert.equal(gradeOf(70).id, 'silver')
  assert.equal(gradeOf(50).id, 'bronze')
  assert.equal(gradeOf(0).id, 'again')
  for (const grade of GRADES) assert.ok(grade.label && grade.tip, `${grade.id} 缺少文案`)
})

test('evaluate：识别档给出逐字标记，响度档如实说明分数怎么来的', () => {
  const heard = evaluate({ mode: 'recognition', reference: REF, heard: '床前明月光' })
  assert.equal(heard.score, 100)
  assert.equal(heard.chars.length, 5)
  assert.ok(heard.chars.every((c) => c.status === 'hit'))

  const loud = evaluate({
    mode: 'loudness',
    reference: REF,
    sample: { voicedRatio: 0.7, durationRatio: 0.9, peak: 0.35 }
  })
  assert.ok(loud.score > 0 && loud.score <= LOUDNESS_SCORE_CAP)
  assert.ok(loud.chars.every((c) => c.status === 'unknown'), '响度档不该假装知道哪个字念对了')
  assert.ok(loud.note.includes('大声读完'), '响度档没有说明这一分是怎么来的')
})

test('v2 三档名称稳定，旧 loudness 调用会归一到 recording', () => {
  const sample = { voicedRatio: 0.7, durationRatio: 0.9, peak: 0.35 }
  assert.equal(evaluate({ mode: 'recording', reference: REF, sample }).mode, 'recording')
  assert.equal(evaluate({ mode: 'loudness', reference: REF, sample }).mode, 'recording')
})

test('离线学伴按档位和漏字给出短回复', () => {
  const missed = evaluate({ mode: 'recognition', reference: REF, heard: '床明月光' })
  assert.match(companionReplyForResult(missed), /前/)
  assert.match(
    companionReplyForResult({
      mode: 'listen-only',
      score: null,
      grade: { id: 'okay' },
      chars: []
    }),
    /范读/
  )
  assert.match(
    companionReplyForResult({
      mode: 'recording',
      score: 75,
      grade: { id: 'silver' },
      chars: []
    }),
    /回放/
  )
})

/* ------------------------------------------- v3 离线 ASR 接线层（ROUND10_H1） */

/**
 * ROUND12_H1：整包从「胶水 + 二进制」两件长到七件——JS API 层和
 * encoder/decoder/joiner/tokens 缺任何一件，Worker 都装不起来，
 * 所以 parseManifest 现在逐个角色查。这份夹具跟着长。
 */
const PACK_FIXTURE = [
  ['asr/models/glue.js', 'wasm-glue', 1024],
  ['asr/models/engine.wasm', 'wasm-binary', 2048],
  ['asr/models/api.js', 'asr-api', 512],
  ['asr/models/encoder.int8.onnx', 'model-encoder', 4096],
  ['asr/models/decoder.int8.onnx', 'model-decoder', 1024],
  ['asr/models/joiner.int8.onnx', 'model-joiner', 1024],
  ['asr/models/tokens.txt', 'tokens', 256]
]

const goodManifest = () => ({
  schema: OFFLINE_ASR.schema,
  engine: 'sherpa-onnx',
  available: true,
  modelId: 'streaming-zipformer-zh',
  modelVersion: '2026-01-01',
  license: 'Apache-2.0',
  files: PACK_FIXTURE.map(([path, role, bytes], index) => ({
    path,
    role,
    bytes,
    sha256: index.toString(16).repeat(64)
  }))
})

test('离线评测包清单必须冻结哈希、许可证和可用标记，否则整包不装', () => {
  const ok = parseManifest(goodManifest())
  assert.equal(ok.bytes, PACK_FIXTURE.reduce((n, [, , bytes]) => n + bytes, 0))
  assert.equal(packCacheName(ok), `${OFFLINE_ASR.cachePrefix}streaming-zipformer-zh-2026-01-01`)

  const reject = (mutate, hint) => {
    const draft = goodManifest()
    mutate(draft)
    assert.throws(() => parseManifest(draft), new RegExp(hint), `${hint} 应当被拒绝`)
  }
  reject((m) => (m.available = false), '还没有冻结')
  reject((m) => (m.license = ''), '许可证')
  reject((m) => (m.files[0].sha256 = 'not-a-hash'), 'sha256')
  reject((m) => (m.files[0].path = 'https://cdn.example.com/glue.js'), '站点相对路径')
  reject((m) => (m.files[0].path = 'asr/../../secret.js'), '站点相对路径')
  reject((m) => (m.files[0].path = 'ocr/chi_sim.traineddata.gz'), '站点相对路径')
  reject((m) => (m.files = m.files.slice(1)), 'wasm-glue')
  reject((m) => (m.files = m.files.slice(0, -1)), 'tokens')
  reject((m) => m.files.splice(3, 1), 'model-encoder')
  reject((m) => (m.files[1].bytes = OFFLINE_ASR.maxPackBytes), '60 MiB')
})

test('四档降级：离线优先，引擎失败只降到录音档，绝不改用可能联网的浏览器识别', () => {
  const base = { canRecognize: true, allowRecognition: true, canRecord: true }
  assert.equal(chooseTier({ ...base, offlineReady: true }), 'offline-asr')
  assert.equal(chooseTier({ ...base, offlineReady: false }), 'recognition')
  assert.equal(chooseTier({ ...base, allowRecognition: false }), 'recording')
  assert.equal(chooseTier({ ...base, offlineReady: true, offlineFault: true }), 'recording')
  // 没有麦克风就没有音频：离线包装好了也一样只能自评（ROUND11_H1 演练 D4）
  assert.equal(chooseTier({ ...base, offlineReady: true, micDenied: true }), 'listen-only')
  assert.equal(
    chooseTier({ ...base, offlineReady: true, offlineFault: true, micDenied: true }),
    'listen-only'
  )
  assert.equal(chooseTier({ canRecord: false }), 'listen-only')
})

test('四档映射回三档 mode，并各自记下这一分是谁给的', () => {
  assert.equal(modeOfTier('offline-asr'), 'recognition')
  for (const tier of ['recognition', 'recording', 'listen-only']) {
    assert.equal(modeOfTier(tier), tier, `${tier} 的对外 mode 不该被改写`)
  }
  assert.equal(sourceOfTier('offline-asr'), 'offline-sherpa')
  assert.equal(sourceOfTier('recognition'), 'web-speech')
  assert.equal(sourceOfTier('recording'), 'loudness')
  assert.equal(sourceOfTier('listen-only'), 'self')
})

test('采音管线：重采样到 16k 且 Int16 不溢出', () => {
  const input = Float32Array.from({ length: 480 }, (_, i) => Math.sin(i / 8))
  const out = resampleTo16k(input, 48000)
  assert.equal(out.length, 160)
  assert.equal(resampleTo16k(input, 16000).length, 480)
  assert.ok(Math.abs(out[0] - input[0]) < 1e-6, '首采样点应当对齐')

  const pcm = floatToPcm16(Float32Array.from([0, 1, -1, 2, -2, 0.5]))
  assert.deepEqual([...pcm], [0, 32767, -32768, 32767, -32768, 16384])
})

let passed = 0
for (const { name, fn } of tests) {
  try {
    await fn()
    passed += 1
    console.log(`  ✓ ${name}`)
  } catch (error) {
    console.error(`  ✗ ${name}`)
    throw error
  }
}

console.log(`跟读评测单元测试：${passed}/${tests.length} 通过。`)
