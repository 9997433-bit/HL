/**
 * ROUND14_H1 —— 落库管线的**空载走查**（pilot），用合成 wav 把整条路跑通。
 *
 * 这个脚本存在的理由，和它明确**不**做的事一样重要。
 *
 * R14-1 交了两样东西：批次 1 的 100 个槽位（派工单）和 `ingest-asr-freeze-batch.mjs`
 * 的 14 条拒收闸（收货台）。两样都只被自检撞过——自检用的是内存里编出来的假交付，
 * 磁盘上一个音频文件都没有。于是这条路上有一整段代码从来没被执行过：
 * **`--verify-audio`**（音频真的在不在、sha256 对不对得上），
 * 也正是 `r14-asr-recording-batch1.md` §8 记下的那条债：「CI 上跑不了」。
 *
 * 这一轮补的就是那一段。做法是**在临时目录里生成真的 wav 文件**——
 * 真的 RIFF 头、真的 16 kHz 16-bit PCM 采样、真的时长、真的 sha256——
 * 然后拿它们走一遍完整的落库流程：构造交付清单 → 过 14 条闸 → 核对磁盘音频 →
 * 落库进一份**沙箱副本**。走完之后再把其中一个文件改一个字节，
 * 确认指纹核对当场报错：这条闸不是摆设。
 *
 * ## 它不是什么
 *
 *   - **不是儿童实录。** 生成的是整数三角波加噪声，不是任何人的声音。
 *     一段合成音里没有孩子的语速、共发音、气声，也没有任何隐私。
 *     报表里 `childRecorded: false` 是这份数据的第一属性，不是免责声明。
 *   - **不是评测数据。** 标注（`labels`）是照着槽位的设计意图**声明**出来的，
 *     不是听着音频转写出来的。拿它算字符召回只会算出一个恒等于 1 的数。
 *   - **不进生产评测集。** 落库落的是 `structuredClone` 出来的沙箱副本，
 *     冻结集 id 换成 `FS-PILOT-B1-DRYRUN`。
 *     `scripts/data/asr-eval-set.json` 一个字节都不会被这个脚本写过。
 *   - **不碰 `available`。** 和落库闸一样：放行只有 Go/No-Go 一个入口。
 *
 * ## 为什么条数卡在 20
 *
 * 走查要证明的是「这条路通不通」，不是「录了多少」。十来条足够把八个类别、
 * 仲裁、类别漂移、指纹核对各演一遍；再多就只是把同一段合成音复制粘贴，
 * 除了让 `recorded` 这个数字变好看以外没有任何信息量——而那个数字正是
 * H1 的放行门槛之一（≥300）。所以这里硬性卡 20 条（`PILOT.cap`），
 * 超了直接抛错，`test-asr-eval-set.mjs` 另有一条断言守着同一个上限。
 *
 * ## 可复现
 *
 * 波形是整数运算生成的（xorshift + 三角波，不用 Math.sin 这类由实现决定的函数），
 * 所以同一个槽位在任何机器上都生成出同一份字节、同一个 sha256。
 * harness 因此可以**重跑一遍再和落盘的报表逐字段比对**——报表改不了，
 * 改了就和重跑的结果对不上。
 *
 * ## 用法
 *
 *   node scripts/pilot-asr-ingest.mjs                 # 跑一遍，打印结果，不写文件
 *   node scripts/pilot-asr-ingest.mjs --write         # 顺带写 evidence 报表
 *   node scripts/pilot-asr-ingest.mjs --count 8       # 少跑几条（上限 20）
 *   node scripts/pilot-asr-ingest.mjs --root /tmp/x --keep   # 指定目录并保留 wav
 *
 * 口径见 .agent_workspace/r14-followread-release.md §4。
 */

import { createHash } from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { POEM_MAP } from '../src/data/poems.js'
import {
  DELIVERY_SCHEMA,
  REJECT_CODES,
  applyDelivery,
  pointsIntoRepo,
  validateDelivery,
  verifyAudio
} from './ingest-asr-freeze-batch.mjs'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = path.resolve(appRoot, '../..')
const evalSetPath = path.join(appRoot, 'scripts/data/asr-eval-set.json')

export const PILOT = Object.freeze({
  schema: 'literacy-asr-pilot-ingest/1',
  marker: 'ROUND14_H1',
  /** 走查的硬上限。它不是配置，是一条「别把走查数据当录音进度用」的闸。 */
  cap: 20,
  defaultCount: 12,
  batchId: 'B1',
  sandboxFreezeSetId: 'FS-PILOT-B1-DRYRUN',
  report: '.agent_workspace/evidence/r14/asr/pilot-ingest.json',
  releaseDoc: '.agent_workspace/r14-followread-release.md',
  sampleRate: 16000,
  bitDepth: 16,
  /** 八个类别各演一遍，剩下的名额按槽位号顺延。 */
  categoryOrder: ['normal', 'miss', 'extra', 'repeat', 'silence', 'bystander', 'tone', 'initial']
})

/* --------------------------------------------------------- 合成 wav */

/**
 * 整数三角波 + xorshift 噪声。
 *
 * 刻意不用 Math.sin：ECMAScript 不保证超越函数在不同引擎/版本上给出同一个 bit，
 * 而这份波形的 sha256 是要被 harness 拿去逐字节比对的。整数运算与 IEEE754
 * 的加减乘除除外——它们处处一致。
 */
function synthesizePcm({ frames, seed, silent }) {
  const data = Buffer.alloc(frames * 2)
  let state = (seed >>> 0) || 0x9e3779b9
  const rnd = () => {
    state ^= (state << 13) >>> 0
    state >>>= 0
    state ^= state >>> 17
    state ^= (state << 5) >>> 0
    state >>>= 0
    return state
  }
  const period = 91
  const half = period >> 1
  const amp = silent ? 24 : 7000
  for (let i = 0; i < frames; i += 1) {
    const phase = i % period
    const ramp =
      phase < half
        ? Math.floor((phase * amp * 2) / half) - amp
        : amp - Math.floor(((phase - half) * amp * 2) / (period - half))
    const noise = silent ? (rnd() % 33) - 16 : (rnd() % 257) - 128
    const value = Math.max(-32768, Math.min(32767, ramp + noise))
    data.writeInt16LE(value, i * 2)
  }
  return data
}

/** 44 字节 RIFF/WAVE 头 + PCM 数据。写的是真文件，不是「假装有个音频」。 */
function wavBuffer({ seconds, sampleRate, seed, silent }) {
  const frames = Math.round(seconds * sampleRate)
  const pcm = synthesizePcm({ frames, seed, silent })
  const header = Buffer.alloc(44)
  header.write('RIFF', 0, 'ascii')
  header.writeUInt32LE(36 + pcm.length, 4)
  header.write('WAVE', 8, 'ascii')
  header.write('fmt ', 12, 'ascii')
  header.writeUInt32LE(16, 16)
  header.writeUInt16LE(1, 20)
  header.writeUInt16LE(1, 22)
  header.writeUInt32LE(sampleRate, 24)
  header.writeUInt32LE(sampleRate * 2, 28)
  header.writeUInt16LE(2, 32)
  header.writeUInt16LE(16, 34)
  header.write('data', 36, 'ascii')
  header.writeUInt32LE(pcm.length, 40)
  return Buffer.concat([header, pcm])
}

/** 从磁盘上的 wav 头把时长与采样率读回来——交付清单里的数不许是「写上去的」。 */
export function readWavMeta(absPath) {
  const body = fs.readFileSync(absPath)
  if (body.length < 44 || body.toString('ascii', 0, 4) !== 'RIFF') {
    throw new Error(`${absPath} 不是 RIFF/WAVE 文件`)
  }
  const sampleRate = body.readUInt32LE(24)
  const channels = body.readUInt16LE(22)
  const bitDepth = body.readUInt16LE(34)
  const dataBytes = body.readUInt32LE(40)
  const seconds = Number(
    (dataBytes / (sampleRate * channels * (bitDepth / 8))).toFixed(3)
  )
  return {
    sampleRate,
    channels,
    bitDepth,
    bytes: body.length,
    seconds,
    sha256: createHash('sha256').update(body).digest('hex')
  }
}

/** 每个槽位一个固定种子：同一条 clip 在任何机器上生成同一份字节。 */
const seedOf = (clipId) => {
  let hash = 0x811c9dc5
  for (const ch of String(clipId)) {
    hash ^= ch.charCodeAt(0)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return hash
}

/* ------------------------------------------------------------- 选样 */

/**
 * 挑走查用的槽位：八个类别先各占一格，剩下的按槽位号顺延。
 * 顺序固定，所以两次跑出来挑中的是同一批——报表才可复现。
 */
export function selectSlots(evalSet, { count, batchId }) {
  const pool = evalSet.clips
    .filter((c) => c.batch === batchId && c.status !== 'recorded')
    .sort((a, b) => (a.id < b.id ? -1 : 1))
  const picked = []
  const taken = new Set()
  for (const category of PILOT.categoryOrder) {
    if (picked.length >= count) break
    const hit = pool.find((c) => c.category === category && !taken.has(c.id))
    if (hit) {
      taken.add(hit.id)
      picked.push(hit)
    }
  }
  for (const clip of pool) {
    if (picked.length >= count) break
    if (taken.has(clip.id)) continue
    taken.add(clip.id)
    picked.push(clip)
  }
  return picked.sort((a, b) => (a.id < b.id ? -1 : 1))
}

const referenceOf = (clip) => POEM_MAP.get(clip.poem)?.lines?.[clip.line]?.text ?? ''

/* ---------------------------------------------------------- 走查主体 */

/**
 * 跑一遍走查。纯粹到只有两处副作用：往 `root` 里写 wav、（调用方要求时）删掉它们。
 * 返回的报表对象就是落盘的那一份，除了 `generatedAt` 与 `audio.root` 两个易变字段。
 */
export function runPilot({ root, count = PILOT.defaultCount, keep = true } = {}) {
  if (!Number.isInteger(count) || count < 1) throw new Error(`--count 要是正整数，收到 ${count}`)
  if (count > PILOT.cap) {
    throw new Error(
      `走查条数 ${count} 超过上限 ${PILOT.cap}——走查证明的是路通不通，不是录了多少条`
    )
  }
  const audioRoot = root ?? fs.mkdtempSync(path.join(os.tmpdir(), 'asr-pilot-'))
  fs.mkdirSync(audioRoot, { recursive: true })

  const production = JSON.parse(fs.readFileSync(evalSetPath, 'utf8'))
  const manifest = JSON.parse(
    fs.readFileSync(path.join(appRoot, 'public/asr/manifest.json'), 'utf8')
  )

  /* 沙箱：换掉冻结集 id，标上 pilot，从此它和生产那份就不是同一批数据了。 */
  const sandbox = structuredClone(production)
  sandbox.pilot = true
  sandbox.freezeSet.id = PILOT.sandboxFreezeSetId
  sandbox.freezeSet.derivedFrom = production.freezeSet.id

  const slots = selectSlots(sandbox, { count, batchId: PILOT.batchId })
  if (slots.length < count) {
    throw new Error(`批次 ${PILOT.batchId} 里只挑得出 ${slots.length} 个可用槽位`)
  }

  /* 1. 生成 wav，并把时长/采样率/指纹从磁盘读回来 */
  const files = []
  let audioBytes = 0
  for (const slot of slots) {
    const silent = slot.category === 'silence' || slot.category === 'bystander'
    const rel = `${PILOT.batchId}/${slot.speaker}/${slot.id}.wav`
    const abs = path.join(audioRoot, rel)
    fs.mkdirSync(path.dirname(abs), { recursive: true })
    fs.writeFileSync(
      abs,
      wavBuffer({
        seconds: slot.seconds,
        sampleRate: PILOT.sampleRate,
        seed: seedOf(slot.id),
        silent
      })
    )
    const meta = readWavMeta(abs)
    audioBytes += meta.bytes
    files.push({ slot, rel, meta, silent })
  }

  /* 2. 交付清单。标注是「照槽位声明」的，不是听出来的——报表里写死这一点。 */
  const speakers = [...new Set(slots.map((c) => c.speaker))].sort()
  const consent = speakers.map((id) => ({
    speaker: id,
    state: 'signed',
    formRef: `pilot-consent/${id}-synthetic.md`
  }))

  /** 演一遍仲裁：第一条读全对的样本让两位标注员写出分歧，仲裁挑 A 那一版。 */
  const arbitrationAt = files.findIndex((f) => f.slot.category === 'normal')
  /** 演一遍类别漂移：另一条排的是 normal，"录出来" 漏了字，交付里改报 miss。 */
  const driftAt = files.findIndex((f, i) => f.slot.category === 'normal' && i !== arbitrationAt)

  const clips = files.map((file, index) => {
    const { slot, rel, meta } = file
    const entry = {
      clipId: slot.id,
      speaker: slot.speaker,
      audio: rel,
      sha256: meta.sha256,
      seconds: meta.seconds,
      sampleRate: meta.sampleRate,
      labels: { a: slot.spoken, b: slot.spoken }
    }
    if (index === arbitrationAt) {
      entry.labels = { a: slot.spoken, b: [...slot.spoken].slice(0, -1).join(''), arbiter: slot.spoken }
    }
    if (index === driftAt) {
      const shorter = [...slot.spoken].slice(0, -1).join('')
      entry.category = 'miss'
      entry.labels = { a: shorter, b: shorter }
    }
    return entry
  })

  const delivery = {
    schema: DELIVERY_SCHEMA,
    freezeSetId: PILOT.sandboxFreezeSetId,
    batch: PILOT.batchId,
    deliveredAt: '2026-08-28',
    note: 'pilot：合成音频的空载走查，不是儿童实录',
    consent,
    clips
  }

  /* 3. 过闸 */
  const result = validateDelivery({ evalSet: sandbox, delivery, referenceOf })
  if (result.errors.length || result.rejected.length) {
    throw new Error(
      `走查交付被自己的闸拦下了：${[
        ...result.errors,
        ...result.rejected.map((r) => `${r.clipId} ${r.code}`)
      ].join('；')}`
    )
  }

  /* 4. 核对磁盘音频（这一段以前在 CI 上从没被执行过），再故意改一个字节看它红不红 */
  const problems = verifyAudio(audioRoot, result.accepted)
  const victim = files[0]
  const victimAbs = path.join(audioRoot, victim.rel)
  const original = fs.readFileSync(victimAbs)
  const tampered = Buffer.from(original)
  tampered[44] = tampered[44] ^ 0xff
  fs.writeFileSync(victimAbs, tampered)
  const tamperProblems = verifyAudio(audioRoot, result.accepted)
  fs.writeFileSync(victimAbs, original)

  /* 5. 落库——落进沙箱副本 */
  const applied = applyDelivery({ evalSet: sandbox, accepted: result.accepted, batchId: PILOT.batchId })
  const appliedRecorded = applied.clips.filter((c) => c.status === 'recorded')

  /* 6. 负向演示：每条闸都该拦得住的那几种偷懒，这里用真文件再撞一次 */
  const negative = negativeDemo({ sandbox, delivery, files, audioRoot })

  if (!keep) fs.rmSync(audioRoot, { recursive: true, force: true })

  const report = {
    schema: PILOT.schema,
    marker: PILOT.marker,
    pilot: true,
    childRecorded: false,
    countsTowardFreezeSet: false,
    generatedAt: new Date().toISOString(),
    disclaimer:
      'pilot 走查数据：音频是整数三角波加噪声合成的，不是任何儿童的录音；' +
      '标注是照槽位设计意图声明的，不是听音转写；同意书是合成凭据，没有任何家庭参与。' +
      '它只回答「落库这条路通不通」，不参与任何评测指标，也不计入冻结集的 300 条。',
    cap: PILOT.cap,
    count: slots.length,
    generator: 'apps/literacy-app/scripts/pilot-asr-ingest.mjs',
    reproducible: {
      waveform: 'integer-triangle+xorshift',
      note: '同一槽位在任何机器上生成同一份字节；harness 重跑一遍即可逐字段核对这份报表'
    },
    audio: {
      kind: 'synthetic-tone',
      speech: false,
      sampleRate: PILOT.sampleRate,
      bitDepth: PILOT.bitDepth,
      channels: 1,
      files: files.length,
      bytes: audioBytes,
      inRepo: files.some((f) => pointsIntoRepo(f.rel)),
      rootKind: 'out-of-repo temp dir',
      root: audioRoot
    },
    annotations: {
      source: 'declared-from-slot',
      humanListened: false,
      note: '双标注与仲裁走的是真流程，写进去的文本却是槽位的设计意图——它证明闸在，不证明标注对'
    },
    consent: {
      kind: 'synthetic-voucher',
      realFamilies: 0,
      note: '合成凭据只为让 consent-missing 那条闸有东西可放行；真交付必须是家长签回的同意书'
    },
    sandbox: {
      freezeSetId: PILOT.sandboxFreezeSetId,
      derivedFrom: production.freezeSet.id,
      writesProductionEvalSet: false,
      stageAfter: applied.freezeSet.stage,
      batchStageAfter: applied.freezeSet.batchPlan.batches.find((b) => b.id === PILOT.batchId).stage,
      recordedAfter: appliedRecorded.length,
      recordedFloor: applied.freezeSet.recordedFloor
    },
    gate: {
      tool: 'apps/literacy-app/scripts/ingest-asr-freeze-batch.mjs',
      accepted: result.accepted.length,
      rejected: result.rejected.length,
      arbitrated: result.accepted.filter((a) => a.labels.arbiter !== null).length,
      categoryChanged: result.accepted.filter((a) => a.categoryChanged).length,
      drift: result.summary.drift
    },
    verifyAudio: {
      checked: result.accepted.length,
      problems: problems.length,
      tamperDetected: tamperProblems.length > 0,
      note: 'r14-asr-recording-batch1.md §8 记的「--verify-audio 在 CI 上跑不了」这条债到此为止'
    },
    negativeDemo: negative,
    clips: result.accepted.map((a) => ({
      clipId: a.clipId,
      speaker: a.speaker,
      category: a.category,
      categoryChanged: a.categoryChanged,
      seconds: a.seconds,
      sampleRate: a.sampleRate,
      audio: a.audio,
      sha256: a.sha256
    })),
    production: {
      evalSet: 'apps/literacy-app/scripts/data/asr-eval-set.json',
      recorded: production.clips.filter((c) => c.status === 'recorded').length,
      recordedFloor: production.freezeSet.recordedFloor,
      stage: production.freezeSet.stage,
      available: manifest.available,
      untouched: true
    }
  }
  return report
}

/**
 * 负向演示：拿真文件再撞几条闸。
 *
 * 自检里已经每条闸各撞过一次，那里用的是内存里编的交付。这里换成磁盘上真存在的
 * wav——8 kHz 的那条、12 秒的那条都是真生成出来的文件，闸拦下它们靠的是
 * 文件本身的元数据，不是清单里写了什么。
 */
function negativeDemo({ sandbox, delivery, files, audioRoot }) {
  const cases = []
  const base = files[0]
  const run = (label, mutate) => {
    const broken = structuredClone(delivery)
    mutate(broken)
    const outcome = validateDelivery({ evalSet: sandbox, delivery: broken, referenceOf })
    const hit = outcome.rejected[0] ?? null
    cases.push({
      label,
      code: hit?.code ?? null,
      rejected: outcome.rejected.length,
      reason: hit?.reason ?? '（没被拦下——这条闸出问题了）'
    })
  }

  const oddRate = path.join(audioRoot, 'negative/low-rate.wav')
  fs.mkdirSync(path.dirname(oddRate), { recursive: true })
  fs.writeFileSync(oddRate, wavBuffer({ seconds: 4, sampleRate: 8000, seed: 1, silent: false }))
  const lowMeta = readWavMeta(oddRate)

  const tooLong = path.join(audioRoot, 'negative/too-long.wav')
  fs.writeFileSync(
    tooLong,
    wavBuffer({ seconds: 12.5, sampleRate: PILOT.sampleRate, seed: 2, silent: false })
  )
  const longMeta = readWavMeta(tooLong)

  run('8 kHz 采样率的真文件', (d) => {
    d.clips = [
      {
        ...d.clips[0],
        audio: 'negative/low-rate.wav',
        sha256: lowMeta.sha256,
        seconds: lowMeta.seconds,
        sampleRate: lowMeta.sampleRate
      }
    ]
  })
  run('12.5 秒的真文件', (d) => {
    d.clips = [
      {
        ...d.clips[0],
        audio: 'negative/too-long.wav',
        sha256: longMeta.sha256,
        seconds: longMeta.seconds,
        sampleRate: longMeta.sampleRate
      }
    ]
  })
  run('音频指针指进仓库', (d) => {
    d.clips = [{ ...d.clips[0], audio: `apps/literacy-app/public/asr/${base.slot.id}.wav` }]
  })
  run('只有一位标注员', (d) => {
    d.clips = [{ ...d.clips[0], labels: { a: base.slot.spoken } }]
  })
  run('仲裁凭空写了第三版', (d) => {
    d.clips = [
      {
        ...d.clips[0],
        labels: {
          a: base.slot.spoken,
          b: [...base.slot.spoken].slice(0, -1).join(''),
          arbiter: '另起一版'
        }
      }
    ]
  })
  run('同意书没签回', (d) => {
    d.consent = d.consent.filter((c) => c.speaker !== d.clips[0].speaker)
  })
  return cases
}

/** 这一批负向演示至少要覆盖到的拒收码；少一条就说明演示缩水了。 */
export const NEGATIVE_CODES = Object.freeze([
  REJECT_CODES.SAMPLE_RATE,
  REJECT_CODES.DURATION,
  REJECT_CODES.AUDIO_IN_REPO,
  REJECT_CODES.SINGLE_ANNOTATION,
  REJECT_CODES.ARBITER_INVENTED,
  REJECT_CODES.CONSENT_MISSING
])

/** 落盘报表时抹掉两个易变字段，好让 harness 逐字段比对重跑的结果。 */
export const stableReport = (report) => {
  const copy = structuredClone(report)
  delete copy.generatedAt
  delete copy.audio.root
  return copy
}

/* ---------------------------------------------------------------- CLI */

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
if (isMain) {
  const argv = process.argv.slice(2)
  const flag = (name) => argv.includes(name)
  const value = (name) => {
    const at = argv.indexOf(name)
    return at >= 0 ? argv[at + 1] : null
  }
  const count = Number(value('--count') ?? PILOT.defaultCount)
  const root = value('--root')
  const keep = flag('--keep')
  const report = runPilot({ root, count, keep })

  if (flag('--write')) {
    // 落盘的是「可复现的那一份」：抹掉临时目录路径，只留时间戳。
    // harness 重跑一遍走查，把新结果和这份逐字段比对——报表改不了。
    const target = path.join(repoRoot, PILOT.report)
    const stable = { ...stableReport(report), generatedAt: report.generatedAt }
    fs.mkdirSync(path.dirname(target), { recursive: true })
    fs.writeFileSync(target, `${JSON.stringify(stable, null, 2)}\n`)
  }

  if (flag('--json')) {
    console.log(JSON.stringify(report, null, 2))
  } else {
    console.log(`  走查 ${report.count} 条（上限 ${report.cap}）· 合成音频 ${report.audio.files} 个文件 · ` +
      `${(report.audio.bytes / 1024).toFixed(0)} KiB`)
    console.log(
      `  过闸：收 ${report.gate.accepted} / 拒 ${report.gate.rejected} · ` +
        `仲裁 ${report.gate.arbitrated} 条 · 类别漂移 ${report.gate.categoryChanged} 条`
    )
    console.log(
      `  指纹核对：${report.verifyAudio.checked} 条无异常；改一个字节后 ` +
        `${report.verifyAudio.tamperDetected ? '当场报错 ✓' : '居然没发现 ✗'}`
    )
    console.log(
      `  沙箱落库：${report.sandbox.freezeSetId} 实录 ${report.sandbox.recordedAfter}/` +
        `${report.sandbox.recordedFloor}（stage ${report.sandbox.stageAfter}）`
    )
    for (const item of report.negativeDemo) {
      console.log(`  [负向] ${item.label} → ${item.code ?? '未拦下'}`)
    }
    console.log(
      `\n  生产评测集未改动：实录 ${report.production.recorded}/${report.production.recordedFloor}，` +
        `available=${report.production.available}。走查数据不计入冻结集，也不是儿童实录。`
    )
    if (keep || root) console.log(`  合成音频留在 ${report.audio.root}（仓库外）`)
  }
  process.exit(
    report.gate.rejected === 0 &&
      report.verifyAudio.problems === 0 &&
      report.verifyAudio.tamperDetected &&
      report.production.recorded === 0
      ? 0
      : 1
  )
}
