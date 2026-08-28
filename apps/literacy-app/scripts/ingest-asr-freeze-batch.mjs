/**
 * ROUND14_H1 —— 冻结集录音批次的落库闸门。
 *
 * R13 把 300 条冻结集的**格子**排好了（`scripts/data/asr-eval-set.json` 的 `freezeSet`），
 * R14 批次 1 把其中 100 个格子编成了可以派工的槽位。这个脚本管的是下一步：
 * **录音回来了，凭什么让它进 clips[]。**
 *
 * 它存在的理由只有一个：把「录了 100 条」这句话从口头承诺变成可核对的事实。
 * 中间任何一步偷懒——单人标注当双标注、仲裁自己另写一版、音频顺手拷进仓库、
 * 孩子的同意书还没签回来就先录了——都要在这里当场被拦下，而不是等到
 * 半年后横比分数时才发现某一批数据来路不明。
 *
 * ## 三种用法
 *
 *   node scripts/ingest-asr-freeze-batch.mjs --plan
 *       只读。对着 clips[] 现算批次 1 还差哪些格子、每类缺几条、哪些孩子还没签同意书。
 *
 *   node scripts/ingest-asr-freeze-batch.mjs --batch <delivery.json> [--verify-audio <root>]
 *       演练落库。逐条过闸，打印哪些能进、哪些被挡在哪一条上；**一个字节都不写**。
 *       带 --verify-audio 时额外在本机核对音频文件确实存在、时长与 sha256 对得上——
 *       这一步只有拿着受控目录的那台机器跑得动，CI 上跑的是元数据那一半。
 *
 *   node scripts/ingest-asr-freeze-batch.mjs --batch <delivery.json> --apply
 *       真落库。把通过的条目写回 asr-eval-set.json：status 改 recorded、
 *       挂上仓库外的音频指针与 sha256、补 labels 双标注与仲裁、**删掉 mock**。
 *
 *   node scripts/ingest-asr-freeze-batch.mjs --self-test
 *       用内置样例把每一条闸都撞一遍（harness 每次跑都会调这一段）。
 *
 * ## 这个脚本永远不做的三件事
 *
 *   1. **不碰 `available`。** 放行只有 Go/No-Go 一个入口（见 test-asr-eval-set.mjs 的
 *      「available 只能由 Go/No-Go 说了算」）。落库最多把 stage 从 skeleton 推到 recording。
 *   2. **不把音频写进仓库。** `clip.audio` 存的是受控目录里的相对路径 + sha256，
 *      仓库里永远只有指针。指向仓库内部的交付一律拒收。
 *   3. **不替仲裁做决定。** 两位标注员不一致时，仲裁必须在两版里挑一版；
 *      凭空写第三版会被当成「事后编答案」拒收。
 *
 * 口径见 .agent_workspace/r14-asr-recording-batch1.md。
 */

import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const evalSetPath = path.join(appRoot, 'scripts/data/asr-eval-set.json')

export const DELIVERY_SCHEMA = 'literacy-asr-freeze-delivery/1'
export const MARKER = 'ROUND14_H1'

/** 3–10 秒，与评测集 harness 的 CLIP_SECONDS 是同一条线。 */
export const CLIP_SECONDS = [3, 10]
/** 低于 16 kHz 的录音喂不进 16 kHz 的流式模型，重采样只会把高频伪影当特征。 */
export const MIN_SAMPLE_RATE = 16000

/** 孩子没读的两类：仲裁转写必须是空的。 */
const SILENT_CATEGORIES = ['silence', 'bystander']

/**
 * 每一条闸对应一种「看上去像录完了、其实不算数」的情形。
 * 拒收码是稳定的：报表、文档、自检样例三处都按它对账。
 */
export const REJECT_CODES = Object.freeze({
  DUPLICATE: 'duplicate-in-delivery',
  UNKNOWN_SLOT: 'unknown-slot',
  WRONG_BATCH: 'wrong-batch',
  ALREADY_RECORDED: 'already-recorded',
  SPEAKER_MISMATCH: 'speaker-mismatch',
  CONSENT_MISSING: 'consent-missing',
  AUDIO_IN_REPO: 'audio-in-repo',
  AUDIO_FINGERPRINT: 'audio-fingerprint',
  DURATION: 'duration-out-of-range',
  SAMPLE_RATE: 'sample-rate-too-low',
  SINGLE_ANNOTATION: 'single-annotation',
  ARBITER_INVENTED: 'arbiter-not-a-choice',
  CATEGORY_MISMATCH: 'category-mismatch',
  SPEAKER_OVER_CAP: 'speaker-over-cap'
})

/* ------------------------------------------------------------------ 工具 */

const isHex64 = (value) => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value)

/** 只留汉字，和 speechEval.normalizeTranscript 同一套洗法（这里不引 Vue 侧模块，保持可独立运行）。 */
const CJK = /[\u3400-\u4dbf\u4e00-\u9fff]/
export const normalize = (text) => [...String(text ?? '')].filter((ch) => CJK.test(ch)).join('')

/**
 * 音频指针必须落在仓库外。
 * 判的是「写法上就指着仓库」——绝对路径、apps/ public/ 开头、以及用 ../ 往回爬的。
 */
export const pointsIntoRepo = (audio) => {
  const value = String(audio ?? '')
  if (!value) return true
  if (value.startsWith('/') || /^[a-zA-Z]:[\\/]/.test(value)) return true
  if (value.includes('..')) return true
  return /^(apps|public|src|scripts|dist|node_modules)\//.test(value)
}

/** 仲裁定稿：两位一致就是它，不一致时以仲裁为准。 */
export const arbitrated = (labels) => {
  const a = normalize(labels?.a)
  const b = normalize(labels?.b)
  if (a === b) return a
  return normalize(labels?.arbiter)
}

/**
 * 定稿转写与这一条声称的类别对不对得上。
 * 这条闸挡的是最难查的一种错：类别标签和录音内容说的不是一回事，
 * 到了算分那一步，漏字检出的分母里混进了几条读全对的样本，谁也看不出来。
 */
export function categoryFits(category, reference, spoken) {
  const ref = normalize(reference)
  const said = normalize(spoken)
  if (SILENT_CATEGORIES.includes(category)) return said === ''
  if (said === '') return false
  if (category === 'normal') return said === ref
  if (category === 'miss') return said.length < ref.length
  if (category === 'extra' || category === 'repeat') return said.length > ref.length
  if (category === 'tone' || category === 'initial') return said === ref
  return false
}

/* -------------------------------------------------------------- 校验主体 */

/**
 * 纯函数：给一份评测集和一份交付清单，算出哪些条目能进、哪些被哪条闸挡下。
 *
 * `referenceOf(clip)` 由调用方注入（默认查 poems.js），自检时换成固定表，
 * 好让这段逻辑不依赖诗库也能撞一遍。
 */
export function validateDelivery({ evalSet, delivery, referenceOf }) {
  const errors = []
  const accepted = []
  const rejected = []

  const freeze = evalSet?.freezeSet ?? {}
  const plan = freeze.batchPlan ?? {}
  const batches = Array.isArray(plan.batches) ? plan.batches : []

  if (delivery?.schema !== DELIVERY_SCHEMA) {
    errors.push(`交付清单的 schema 是「${delivery?.schema}」，认的是 ${DELIVERY_SCHEMA}`)
  }
  if (delivery?.freezeSetId !== freeze.id) {
    errors.push(`交付清单挂的批次 ${delivery?.freezeSetId} 不是当前冻结集 ${freeze.id}`)
  }
  const batch = batches.find((b) => b.id === delivery?.batch)
  if (!batch) errors.push(`批次 ${delivery?.batch} 不在批次计划里`)
  else if (batch.allocated <= 0) errors.push(`批次 ${batch.id} 的槽位还没排（allocated=0），先排位再录`)
  if (errors.length) return { ok: false, errors, accepted, rejected, summary: null }

  const speakerMap = new Map((evalSet.speakers ?? []).map((s) => [s.id, s]))
  const clipMap = new Map((evalSet.clips ?? []).map((c) => [c.id, c]))
  const consentMap = new Map(
    (delivery.consent ?? []).map((entry) => [entry.speaker, entry])
  )
  /** 落库后每个孩子会有多少条实录——上限要按「现有 + 这一批」一起算。 */
  const recordedPerSpeaker = new Map()
  for (const clip of evalSet.clips ?? []) {
    if (clip.status === 'recorded') {
      recordedPerSpeaker.set(clip.speaker, (recordedPerSpeaker.get(clip.speaker) ?? 0) + 1)
    }
  }

  const seen = new Set()
  const reject = (entry, code, reason) => rejected.push({ clipId: entry?.clipId ?? '?', code, reason })

  for (const entry of delivery.clips ?? []) {
    const id = entry?.clipId
    if (seen.has(id)) {
      reject(entry, REJECT_CODES.DUPLICATE, `${id} 在同一份交付里出现了两次`)
      continue
    }
    seen.add(id)

    const slot = clipMap.get(id)
    if (!slot) {
      reject(entry, REJECT_CODES.UNKNOWN_SLOT, `${id} 不是批次计划里的槽位——录之前先排位`)
      continue
    }
    if (slot.batch !== batch.id) {
      reject(entry, REJECT_CODES.WRONG_BATCH, `${id} 属于 ${slot.batch}，这份交付报的是 ${batch.id}`)
      continue
    }
    if (slot.status === 'recorded') {
      reject(entry, REJECT_CODES.ALREADY_RECORDED, `${id} 已经落过库，重录要先作废旧的那一条`)
      continue
    }
    if (entry.speaker !== slot.speaker) {
      reject(
        entry,
        REJECT_CODES.SPEAKER_MISMATCH,
        `${id} 排的是 ${slot.speaker}，交付里写的是 ${entry.speaker}——换人等于换子组`
      )
      continue
    }

    const consent = consentMap.get(entry.speaker)
    const speaker = speakerMap.get(entry.speaker)
    if (!consent || consent.state !== 'signed' || !consent.formRef) {
      reject(
        entry,
        REJECT_CODES.CONSENT_MISSING,
        `${entry.speaker} 的家长同意书没在交付清单里签回（state=${consent?.state ?? '缺'}）`
      )
      continue
    }
    if (speaker?.consent === 'withdrawn') {
      reject(entry, REJECT_CODES.CONSENT_MISSING, `${entry.speaker} 已撤回同意，这条录音必须删除而不是落库`)
      continue
    }

    if (pointsIntoRepo(entry.audio)) {
      reject(
        entry,
        REJECT_CODES.AUDIO_IN_REPO,
        `${id} 的音频路径「${entry.audio}」不是受控目录下的相对路径——` +
          `绝对路径、../ 和仓库目录一律拒收，孩子的声音不进 git`
      )
      continue
    }
    if (!isHex64(entry.sha256)) {
      reject(entry, REJECT_CODES.AUDIO_FINGERPRINT, `${id} 没有合法的 sha256，日后换了文件没人发现`)
      continue
    }
    if (!(entry.seconds >= CLIP_SECONDS[0] && entry.seconds <= CLIP_SECONDS[1])) {
      reject(
        entry,
        REJECT_CODES.DURATION,
        `${id} 时长 ${entry.seconds}s 不在 ${CLIP_SECONDS.join('–')}s 内`
      )
      continue
    }
    if (!(entry.sampleRate >= MIN_SAMPLE_RATE)) {
      reject(
        entry,
        REJECT_CODES.SAMPLE_RATE,
        `${id} 采样率 ${entry.sampleRate} Hz 低于 ${MIN_SAMPLE_RATE} Hz`
      )
      continue
    }

    const labels = entry.labels ?? {}
    const a = normalize(labels.a)
    const b = normalize(labels.b)
    const category = entry.category ?? slot.category
    const silent = SILENT_CATEGORIES.includes(category)
    const hasA = labels.a !== undefined && labels.a !== null
    const hasB = labels.b !== undefined && labels.b !== null
    if (!hasA || !hasB) {
      reject(
        entry,
        REJECT_CODES.SINGLE_ANNOTATION,
        `${id} 只有一位标注员的结果——双标注不是走过场`
      )
      continue
    }
    if (a !== b) {
      const arbiter = labels.arbiter
      if (arbiter === undefined || arbiter === null) {
        reject(entry, REJECT_CODES.SINGLE_ANNOTATION, `${id} 两位标注不一致却没有仲裁`)
        continue
      }
      const picked = normalize(arbiter)
      if (picked !== a && picked !== b) {
        reject(
          entry,
          REJECT_CODES.ARBITER_INVENTED,
          `${id} 仲裁写了第三个版本——仲裁只能在两版里挑一版`
        )
        continue
      }
    }

    const spoken = arbitrated(labels)
    if (!silent && spoken === '' ) {
      reject(entry, REJECT_CODES.CATEGORY_MISMATCH, `${id} 标成 ${category} 却什么都没读到`)
      continue
    }
    const reference = referenceOf(slot)
    if (!categoryFits(category, reference, spoken)) {
      reject(
        entry,
        REJECT_CODES.CATEGORY_MISMATCH,
        `${id} 定稿转写「${spoken || '（空）'}」与类别 ${category} 对不上（原文「${normalize(reference)}」）`
      )
      continue
    }

    const after = (recordedPerSpeaker.get(entry.speaker) ?? 0) + 1
    if (after > freeze.maxClipsPerSpeaker) {
      reject(
        entry,
        REJECT_CODES.SPEAKER_OVER_CAP,
        `${entry.speaker} 落库后有 ${after} 条（上限 ${freeze.maxClipsPerSpeaker}）——他的口音会主导整份分数`
      )
      continue
    }
    recordedPerSpeaker.set(entry.speaker, after)

    accepted.push({
      clipId: id,
      speaker: entry.speaker,
      category,
      categoryChanged: category !== slot.category,
      audio: entry.audio,
      sha256: String(entry.sha256).toLowerCase(),
      seconds: entry.seconds,
      sampleRate: entry.sampleRate,
      spoken,
      labels: {
        a: normalize(labels.a),
        b: normalize(labels.b),
        arbiter: labels.arbiter === undefined || labels.arbiter === null ? null : normalize(labels.arbiter)
      },
      consentRef: consent.formRef,
      recordedAt: entry.recordedAt ?? delivery.deliveredAt ?? null
    })
  }

  return {
    ok: rejected.length === 0,
    errors,
    accepted,
    rejected,
    summary: summarize({ evalSet, batch, accepted, rejected })
  }
}

/**
 * 落库之后这一批会长成什么样：进度、配额漂移、还剩多少格子。
 *
 * 配额漂移不当红灯——孩子读成什么样是录出来的，不是排出来的。
 * 但它必须显示出来：批次 1 若整体往 normal 漂，剩下两批就得反向配平，
 * 而不是等到 300 条录完才发现漏字样本只有一半。
 */
function summarize({ evalSet, batch, accepted, rejected }) {
  const freeze = evalSet.freezeSet
  const slots = (evalSet.clips ?? []).filter((c) => c.batch === batch.id)
  const acceptedIds = new Set(accepted.map((a) => a.clipId))
  const categoryOf = new Map(accepted.map((a) => [a.clipId, a.category]))

  const planned = new Map()
  const after = new Map()
  for (const slot of slots) {
    planned.set(slot.category, (planned.get(slot.category) ?? 0) + 1)
    const category = categoryOf.get(slot.id) ?? slot.category
    after.set(category, (after.get(category) ?? 0) + 1)
  }
  const drift = []
  for (const category of new Set([...planned.keys(), ...after.keys()])) {
    const delta = (after.get(category) ?? 0) - (planned.get(category) ?? 0)
    if (delta !== 0) drift.push({ category, planned: planned.get(category) ?? 0, after: after.get(category) ?? 0, delta })
  }

  const recordedBefore = slots.filter((c) => c.status === 'recorded').length
  return {
    batch: batch.id,
    slots: slots.length,
    recordedBefore,
    accepted: accepted.length,
    rejected: rejected.length,
    recordedAfter: recordedBefore + acceptedIds.size,
    remaining: slots.length - recordedBefore - acceptedIds.size,
    freezeRecordedAfter:
      (evalSet.clips ?? []).filter((c) => c.status === 'recorded').length + acceptedIds.size,
    recordedFloor: freeze.recordedFloor,
    drift: drift.sort((x, y) => y.delta - x.delta)
  }
}

/**
 * 纯函数：把通过的条目写进评测集的一份副本。
 *
 * 三件事顺带做掉，因为忘一件就会让整份数据说两套话：
 *   - `mock` 删掉。真音频到了还留着模拟转写，真假指标迟早混进同一张表。
 *   - 孩子的 `consent` 落成 signed，并记下同意书编号。
 *   - 进度现算：freezeSet.recorded、批次 recorded、stage 从 skeleton 推到 recording。
 *
 * `available` 一个字都不碰，`stage` 也永远不会被这里写成 frozen——
 * 冻结是 300 条 + 五层门槛的结论，不是落库这一步的副作用。
 */
export function applyDelivery({ evalSet, accepted, batchId }) {
  const next = structuredClone(evalSet)
  const byId = new Map(accepted.map((a) => [a.clipId, a]))

  next.clips = next.clips.map((clip) => {
    const hit = byId.get(clip.id)
    if (!hit) return clip
    const merged = {
      ...clip,
      category: hit.category,
      seconds: hit.seconds,
      spoken: hit.spoken,
      status: 'recorded',
      audio: hit.audio,
      sha256: hit.sha256,
      sampleRate: hit.sampleRate,
      labels: hit.labels,
      consentRef: hit.consentRef,
      recordedAt: hit.recordedAt
    }
    delete merged.mock
    return merged
  })

  const signed = new Set(accepted.map((a) => a.speaker))
  next.speakers = next.speakers.map((speaker) =>
    signed.has(speaker.id) ? { ...speaker, consent: 'signed' } : speaker
  )

  const recorded = next.clips.filter((c) => c.status === 'recorded')
  next.freezeSet.recorded = recorded.length
  if (next.freezeSet.stage === 'skeleton' && recorded.length > 0) {
    next.freezeSet.stage = 'recording'
  }
  for (const batch of next.freezeSet.batchPlan?.batches ?? []) {
    const mine = recorded.filter((c) => c.batch === batch.id).length
    batch.recorded = mine
    if (batch.id === batchId && batch.stage === 'planned' && mine > 0) batch.stage = 'recording'
    if (batch.allocated > 0 && mine >= batch.allocated) batch.stage = 'ingested'
  }
  return next
}

/** 批次还差什么：给排班表用的只读视图。 */
export function planGaps(evalSet, batchId) {
  const freeze = evalSet.freezeSet ?? {}
  const batch = (freeze.batchPlan?.batches ?? []).find((b) => b.id === batchId)
  if (!batch) return null
  const slots = (evalSet.clips ?? []).filter((c) => c.batch === batchId)
  const pending = slots.filter((c) => c.status !== 'recorded')
  const byCategory = new Map()
  for (const clip of pending) byCategory.set(clip.category, (byCategory.get(clip.category) ?? 0) + 1)
  const bySpeaker = new Map()
  for (const clip of pending) bySpeaker.set(clip.speaker, (bySpeaker.get(clip.speaker) ?? 0) + 1)
  const speakerMap = new Map((evalSet.speakers ?? []).map((s) => [s.id, s]))
  return {
    batch: batch.id,
    stage: batch.stage,
    slots: slots.length,
    allocated: batch.allocated,
    recorded: slots.length - pending.length,
    pending: pending.length,
    pendingByCategory: Object.fromEntries([...byCategory].sort((a, b) => b[1] - a[1])),
    pendingBySpeaker: Object.fromEntries([...bySpeaker].sort()),
    consentPending: [...new Set(pending.map((c) => c.speaker))]
      .filter((id) => speakerMap.get(id)?.consent !== 'signed')
      .sort()
  }
}

/* ---------------------------------------------------------------- 自检 */

/**
 * 内置样例：一条应当放行的，外加每一条拒收闸各撞一次。
 *
 * 用的是自带的小评测集，不碰 poems.js 也不碰真数据——
 * 自检要能回答的是「闸本身还在不在」，不是「今天的数据长什么样」。
 */
export function selfTestFixture() {
  const evalSet = {
    freezeSet: {
      id: 'FS-TEST',
      stage: 'skeleton',
      recorded: 0,
      recordedFloor: 300,
      maxClipsPerSpeaker: 2,
      batchPlan: {
        batches: [
          { id: 'B1', slots: 7, allocated: 7, stage: 'recording', recorded: 1 },
          { id: 'B2', slots: 7, allocated: 0, stage: 'unplanned', recorded: 0 }
        ]
      }
    },
    speakers: [
      { id: 'S01', split: 'dev', consent: 'pending' },
      { id: 'S02', split: 'dev', consent: 'pending' },
      { id: 'S03', split: 'dev', consent: 'withdrawn' },
      { id: 'S04', split: 'dev', consent: 'signed' }
    ],
    clips: [
      { id: 'T01', speaker: 'S01', category: 'normal', spoken: '床前明月光', mock: '床前明月光', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T02', speaker: 'S01', category: 'miss', spoken: '床前明月', mock: '床前明月', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T03', speaker: 'S01', category: 'silence', spoken: '', mock: '', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T04', speaker: 'S02', category: 'normal', spoken: '床前明月光', mock: '床前明月光', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T05', speaker: 'S03', category: 'normal', spoken: '床前明月光', mock: '床前明月光', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T06', speaker: 'S02', category: 'normal', spoken: '床前明月光', mock: '床前明月光', status: 'placeholder', audio: null, batch: 'B1' },
      { id: 'T07', speaker: 'S04', category: 'normal', spoken: '床前明月光', status: 'recorded', audio: 'B1/S04/T07.wav', batch: 'B1' },
      { id: 'T99', speaker: 'S02', category: 'normal', spoken: '床前明月光', mock: '床前明月光', status: 'placeholder', audio: null, batch: 'B2' }
    ]
  }
  const referenceOf = () => '床前明月光'
  const good = {
    clipId: 'T01',
    speaker: 'S01',
    audio: 'B1/S01/T01.wav',
    sha256: 'a'.repeat(64),
    seconds: 4.2,
    sampleRate: 16000,
    labels: { a: '床前明月光', b: '床前明月光' }
  }
  const delivery = {
    schema: DELIVERY_SCHEMA,
    freezeSetId: 'FS-TEST',
    batch: 'B1',
    deliveredAt: '2026-09-12',
    consent: [
      { speaker: 'S01', state: 'signed', formRef: 'consent/S01-2026-09-01.pdf' },
      { speaker: 'S02', state: 'signed', formRef: 'consent/S02-2026-09-01.pdf' },
      { speaker: 'S03', state: 'signed', formRef: 'consent/S03-2026-09-01.pdf' },
      { speaker: 'S04', state: 'signed', formRef: 'consent/S04-2026-09-01.pdf' }
    ],
    clips: [good]
  }
  return { evalSet, referenceOf, delivery, good }
}

/**
 * 每条闸一个反例。左边是拒收码，右边是「怎么把交付改坏到该被这条闸拦下」。
 * 加一条闸就要在这里加一条反例，否则那条闸没人守着它自己。
 */
export const SELF_TEST_CASES = [
  [REJECT_CODES.DUPLICATE, (d, good) => { d.clips = [good, { ...good }] }],
  [REJECT_CODES.UNKNOWN_SLOT, (d, good) => { d.clips = [{ ...good, clipId: 'T77' }] }],
  [REJECT_CODES.WRONG_BATCH, (d, good) => { d.clips = [{ ...good, clipId: 'T99', speaker: 'S02' }] }],
  [REJECT_CODES.ALREADY_RECORDED, (d, good) => { d.clips = [{ ...good, clipId: 'T07', speaker: 'S04' }] }],
  [REJECT_CODES.SPEAKER_MISMATCH, (d, good) => { d.clips = [{ ...good, speaker: 'S02' }] }],
  [REJECT_CODES.CONSENT_MISSING, (d) => { d.consent = [] }],
  [REJECT_CODES.CONSENT_MISSING, (d, good) => {
    d.clips = [{ ...good, clipId: 'T05', speaker: 'S03' }]
  }],
  [REJECT_CODES.AUDIO_IN_REPO, (d, good) => { d.clips = [{ ...good, audio: 'apps/literacy-app/public/asr/T01.wav' }] }],
  [REJECT_CODES.AUDIO_IN_REPO, (d, good) => { d.clips = [{ ...good, audio: '../../workspace/T01.wav' }] }],
  [REJECT_CODES.AUDIO_FINGERPRINT, (d, good) => { d.clips = [{ ...good, sha256: 'nope' }] }],
  [REJECT_CODES.DURATION, (d, good) => { d.clips = [{ ...good, seconds: 12.5 }] }],
  [REJECT_CODES.SAMPLE_RATE, (d, good) => { d.clips = [{ ...good, sampleRate: 8000 }] }],
  [REJECT_CODES.SINGLE_ANNOTATION, (d, good) => { d.clips = [{ ...good, labels: { a: '床前明月光' } }] }],
  [REJECT_CODES.SINGLE_ANNOTATION, (d, good) => {
    d.clips = [{ ...good, labels: { a: '床前明月光', b: '床前明月' } }]
  }],
  [REJECT_CODES.ARBITER_INVENTED, (d, good) => {
    d.clips = [{ ...good, labels: { a: '床前明月光', b: '床前明月', arbiter: '床前明' } }]
  }],
  [REJECT_CODES.CATEGORY_MISMATCH, (d, good) => {
    d.clips = [{ ...good, labels: { a: '床前明月', b: '床前明月' } }]
  }],
  [REJECT_CODES.CATEGORY_MISMATCH, (d, good) => {
    d.clips = [{ ...good, clipId: 'T03', labels: { a: '床前明月光', b: '床前明月光' } }]
  }],
  [REJECT_CODES.SPEAKER_OVER_CAP, (d, good) => {
    d.clips = [
      good,
      { ...good, clipId: 'T02', labels: { a: '床前明月', b: '床前明月' } },
      { ...good, clipId: 'T03', labels: { a: '', b: '' } }
    ]
  }]
]

/**
 * 把每条闸撞一遍，外加三条正向断言：
 * 干净的交付放得过去、落库后 mock 被删掉、落库不会把 stage 写成 frozen。
 */
export function runSelfTest() {
  const failures = []
  const { evalSet, referenceOf, delivery, good } = selfTestFixture()

  const clean = validateDelivery({ evalSet, delivery: structuredClone(delivery), referenceOf })
  if (!clean.ok || clean.accepted.length !== 1) {
    failures.push(`干净的交付没放过去：${clean.rejected.map((r) => r.code).join('、') || clean.errors.join('；')}`)
  }

  for (const [code, breakIt] of SELF_TEST_CASES) {
    const broken = structuredClone(delivery)
    breakIt(broken, structuredClone(good))
    const result = validateDelivery({ evalSet, delivery: broken, referenceOf })
    if (!result.rejected.some((r) => r.code === code)) {
      failures.push(
        `${code} 这条闸没拦住：实得 ${result.rejected.map((r) => r.code).join('、') || '全部放行'}`
      )
    }
  }

  // 批次没排位就不许收
  const unplanned = validateDelivery({
    evalSet,
    delivery: { ...structuredClone(delivery), batch: 'B2' },
    referenceOf
  })
  if (unplanned.ok) failures.push('B2 槽位还没排就收下了交付')

  // 落库之后：mock 删干净、consent 落 signed、stage 只推到 recording
  const applied = applyDelivery({ evalSet, accepted: clean.accepted, batchId: 'B1' })
  const target = applied.clips.find((c) => c.id === 'T01')
  if (target.status !== 'recorded') failures.push('落库后 status 没改成 recorded')
  if ('mock' in target) failures.push('落库后还留着 mock —— 真假指标会混进同一张表')
  if (!target.audio || pointsIntoRepo(target.audio)) failures.push('落库后的音频指针指进了仓库')
  if (applied.speakers.find((s) => s.id === 'S01').consent !== 'signed') {
    failures.push('落库后没把同意状态落成 signed')
  }
  if (applied.freezeSet.recorded !== 2) failures.push('落库后 recorded 没现算')
  if (applied.freezeSet.stage !== 'recording') failures.push(`落库后 stage 是 ${applied.freezeSet.stage}`)
  if (applied.available !== undefined) failures.push('落库居然碰了 available')
  if (JSON.stringify(applied).includes('"frozen"')) failures.push('落库把 stage 写成了 frozen')

  return { passed: failures.length === 0, cases: SELF_TEST_CASES.length + 4, failures }
}

/* ---------------------------------------------------------------- CLI */

/** 一行一条地写回评测集：clips/speakers 保持原来的紧凑排版，diff 才看得出改了哪一条。 */
function serialize(set) {
  const inline = (obj) =>
    `{ ${Object.entries(obj)
      .map(([k, v]) => `${JSON.stringify(k)}: ${JSON.stringify(v)}`)
      .join(', ')} }`
  return `${JSON.stringify(set, null, 2)
    .replace(
      /"speakers": \[[\s\S]*?\n {2}\]/,
      `"speakers": [\n${set.speakers.map((s) => `    ${inline(s)}`).join(',\n')}\n  ]`
    )
    .replace(
      /"clips": \[[\s\S]*?\n {2}\]/,
      `"clips": [\n${set.clips.map((c) => `    ${inline(c)}`).join(',\n')}\n  ]`
    )}\n`
}

/** --verify-audio：只有拿着受控目录的那台机器能跑，CI 上这一段不会执行。 */
function verifyAudio(root, accepted) {
  const problems = []
  for (const entry of accepted) {
    const full = path.join(root, entry.audio)
    let body
    try {
      body = fs.readFileSync(full)
    } catch {
      problems.push(`${entry.clipId} 的音频不在 ${full}`)
      continue
    }
    const digest = createHash('sha256').update(body).digest('hex')
    if (digest !== entry.sha256) problems.push(`${entry.clipId} sha256 对不上：磁盘 ${digest.slice(0, 16)}…`)
  }
  return problems
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
if (isMain) {
  const argv = process.argv.slice(2)
  const flag = (name) => argv.includes(name)
  const value = (name) => {
    const at = argv.indexOf(name)
    return at >= 0 ? argv[at + 1] : null
  }
  const asJson = flag('--json')

  if (flag('--self-test')) {
    const result = runSelfTest()
    if (asJson) console.log(JSON.stringify({ marker: MARKER, ...result }, null, 2))
    else {
      for (const failure of result.failures) console.log(`  ✗ ${failure}`)
      console.log(
        `\n落库闸自检（${MARKER}）：${result.cases - result.failures.length} / ${result.cases} 条通过。`
      )
    }
    process.exit(result.passed ? 0 : 1)
  }

  const evalSet = JSON.parse(fs.readFileSync(evalSetPath, 'utf8'))

  if (flag('--plan') || argv.length === 0) {
    const gaps = planGaps(evalSet, value('--plan') ?? 'B1')
    if (!gaps) {
      console.error('批次不在计划里，先看 asr-eval-set.json 的 freezeSet.batchPlan')
      process.exit(1)
    }
    if (asJson) console.log(JSON.stringify({ marker: MARKER, ...gaps }, null, 2))
    else {
      console.log(
        `  批次 ${gaps.batch}（${gaps.stage}）：槽位 ${gaps.slots} 个 · 已落库 ${gaps.recorded} · 待录 ${gaps.pending}`
      )
      console.log(
        `  待录类别：${Object.entries(gaps.pendingByCategory).map(([k, v]) => `${k} ${v}`).join(' · ')}`
      )
      console.log(`  同意书未签回：${gaps.consentPending.length} 人（${gaps.consentPending.join(' ') || '无'}）`)
      console.log(`\n  交付清单模板见 .agent_workspace/r14-asr-recording-batch1.md §4。`)
    }
    process.exit(0)
  }

  const batchPath = value('--batch')
  if (!batchPath) {
    console.error('用法：--plan | --batch <delivery.json> [--apply] [--verify-audio <root>] | --self-test')
    process.exit(1)
  }

  const { POEM_MAP } = await import('../src/data/poems.js')
  const referenceOf = (clip) => POEM_MAP.get(clip.poem)?.lines?.[clip.line]?.text ?? ''
  const delivery = JSON.parse(fs.readFileSync(batchPath, 'utf8'))
  const result = validateDelivery({ evalSet, delivery, referenceOf })

  const audioRoot = value('--verify-audio')
  const audioProblems = audioRoot ? verifyAudio(audioRoot, result.accepted) : []

  if (asJson) {
    console.log(JSON.stringify({ marker: MARKER, ...result, audioProblems }, null, 2))
  } else {
    for (const error of result.errors) console.log(`  ✗ ${error}`)
    for (const item of result.rejected) console.log(`  ✗ [${item.code}] ${item.reason}`)
    for (const problem of audioProblems) console.log(`  ✗ [audio] ${problem}`)
    const s = result.summary
    if (s) {
      console.log(
        `\n  批次 ${s.batch}：收 ${s.accepted} 条 / 拒 ${s.rejected} 条 · ` +
          `落库后 ${s.recordedAfter}/${s.slots} 条，冻结集 ${s.freezeRecordedAfter}/${s.recordedFloor} 条`
      )
      if (s.drift.length) {
        console.log(
          `  类别漂移（录出来的和排的不一样，不红灯但要在后两批配平）：` +
            s.drift.map((d) => `${d.category} ${d.delta > 0 ? '+' : ''}${d.delta}`).join(' · ')
        )
      }
    }
  }

  if (result.errors.length || audioProblems.length) process.exit(1)

  if (flag('--apply')) {
    if (result.rejected.length) {
      console.log('\n  有条目被拒收，不做部分落库——先修交付清单再来一次。')
      process.exit(1)
    }
    const next = applyDelivery({ evalSet, accepted: result.accepted, batchId: delivery.batch })
    fs.writeFileSync(evalSetPath, serialize(next))
    console.log(`\n  已写回 ${path.relative(appRoot, evalSetPath)}；available 未改动（放行只走 Go/No-Go）。`)
  } else {
    console.log('\n  演练模式：一个字节都没写。确认无误后加 --apply。')
  }
  process.exit(result.rejected.length ? 1 : 0)
}
