/**
 * 跟读评测的算分内核。
 *
 * 这里一行浏览器 API 都不碰：录音、识别、播放都在 composables/useSpeechEval.js 里，
 * 算分留在这一层，好处是它可以在 Node 里直接跑（scripts/test-speech-eval.mjs），
 * 不用起浏览器就能守住「读对了给几分」这条最容易悄悄改坏的规则。
 *
 * 评测分两档，按设备能力降级：
 *
 *   识别档（recognition）  浏览器有 SpeechRecognition：把听到的字和原文对齐，
 *                          逐字标出念对 / 念漏，分数就是对齐后的相似度。
 *   录音档（recording）     只有麦克风、没有识别：判不了念得对不对，
 *                          只判「有没有认真开口」——有没有出声、读了多久、声音够不够。
 *                          这一档封顶 85 分，永远不会给出「满分」这种它其实不知道的结论。
 *
 * 两档之外还有第三种情况：连麦克风都没有。那时候不算分，只放范读让孩子自己跟读
 * （见 composables 里的 mode='listen-only'），界面上也不显示分数。
 */

/** 分档：分数 → 给孩子看的评价。阈值按「宁可鼓励也不打击」调。 */
export const GRADES = [
  { id: 'gold', min: 85, label: '读得真棒', emoji: '🌟', tip: '一个字都没落下，可以读给家人听啦。' },
  { id: 'silver', min: 70, label: '读得不错', emoji: '✨', tip: '大部分都对，再读一遍会更顺。' },
  { id: 'bronze', min: 50, label: '有进步', emoji: '🌱', tip: '先跟着范读一句一句来，慢一点没关系。' },
  { id: 'again', min: 0, label: '再来一次', emoji: '🔁', tip: '先听我读一遍，然后大声跟着读。' }
]

const CJK = /[\u3400-\u4dbf\u4e00-\u9fff]/

/**
 * 把识别结果洗成「只剩汉字」的一串。
 * 识别引擎会自己加标点、有时会夹英文和数字，这些都不该算进对错。
 */
export function normalizeTranscript(text) {
  return [...String(text ?? '')].filter((ch) => CJK.test(ch)).join('')
}

/**
 * 编辑距离对齐：返回原文每个字是「念到了」还是「漏了/念错了」。
 *
 * 用完整的 DP 表回溯，而不是逐位比对——孩子多读或少读一个字之后，
 * 逐位比对会把后面全判错，那是最打击人的一种错判。
 */
export function alignChars(reference, heard) {
  const ref = [...normalizeTranscript(reference)]
  const got = [...normalizeTranscript(heard)]
  const rows = ref.length
  const cols = got.length

  // d[i][j] = 把 ref 前 i 个字变成 got 前 j 个字要改几处
  const d = Array.from({ length: rows + 1 }, (_, i) =>
    Array.from({ length: cols + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  )
  for (let i = 1; i <= rows; i += 1) {
    for (let j = 1; j <= cols; j += 1) {
      const cost = ref[i - 1] === got[j - 1] ? 0 : 1
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    }
  }

  const marks = new Array(rows).fill('miss')
  let i = rows
  let j = cols
  while (i > 0 && j > 0) {
    const cost = ref[i - 1] === got[j - 1] ? 0 : 1
    if (d[i][j] === d[i - 1][j - 1] + cost) {
      if (cost === 0) marks[i - 1] = 'hit'
      i -= 1
      j -= 1
    } else if (d[i][j] === d[i - 1][j] + 1) {
      i -= 1
    } else {
      j -= 1
    }
  }

  return {
    chars: ref.map((char, index) => ({ char, status: marks[index] })),
    hits: marks.filter((m) => m === 'hit').length,
    total: rows,
    distance: d[rows][cols],
    extra: Math.max(0, cols - rows)
  }
}

/**
 * 相似度 0-1。
 * 念到的字占原文的比例是主项，多念出来的字只轻罚——
 * 孩子读完常常会加一句「读完啦」，那不该被当成读错。
 */
export function similarity(reference, heard) {
  const { hits, total, extra } = alignChars(reference, heard)
  if (!total) return 0
  const recall = hits / total
  const penalty = Math.min(0.2, (extra / total) * 0.3)
  return Math.max(0, Math.min(1, recall - penalty))
}

/*
 * ROUND9_H4：跟读 v3 的纯函数探针。
 *
 * 这不是“从声音判音素”的声学模型，只把离线 ASR 的汉字结果映射为可解释的
 * 拼音近似标记。调用方必须继续把它称为诊断线索，不能把 tone/near 当作确定错误。
 * 真正的音素评分仍需拿声学后验做受限对齐，路线与上线门槛见评估文档。
 */
const PINYIN_TONES = {
  ā: 1, á: 2, ǎ: 3, à: 4,
  ē: 1, é: 2, ě: 3, è: 4,
  ī: 1, í: 2, ǐ: 3, ì: 4,
  ō: 1, ó: 2, ǒ: 3, ò: 4,
  ū: 1, ú: 2, ǔ: 3, ù: 4,
  ǖ: 1, ǘ: 2, ǚ: 3, ǜ: 4,
  ń: 2, ň: 3, ǹ: 4, ḿ: 2
}
const PINYIN_BASE = {
  ā: 'a', á: 'a', ǎ: 'a', à: 'a',
  ē: 'e', é: 'e', ě: 'e', è: 'e', ê: 'e',
  ī: 'i', í: 'i', ǐ: 'i', ì: 'i',
  ō: 'o', ó: 'o', ǒ: 'o', ò: 'o',
  ū: 'u', ú: 'u', ǔ: 'u', ù: 'u',
  ǖ: 'ü', ǘ: 'ü', ǚ: 'ü', ǜ: 'ü',
  ń: 'n', ň: 'n', ǹ: 'n', ḿ: 'm'
}
const PINYIN_INITIALS = [
  'zh', 'ch', 'sh',
  'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
  'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's'
]

function pinyinParts(value) {
  const raw = String(value ?? '').trim().toLowerCase().replace(/u:/g, 'ü').replace(/v/g, 'ü')
  if (!raw) return null

  // lookupPinyin 应返回单音节；遇到多音候选时不猜上下文，只取调用方排在首位的读音。
  const syllable = raw.split(/[\s,;/|]+/, 1)[0]
  const numbered = syllable.match(/([1-5])$/)
  let tone = numbered ? Number(numbered[1]) : 5
  let base = ''
  for (const char of syllable.replace(/[1-5]$/, '')) {
    if (PINYIN_TONES[char]) tone = PINYIN_TONES[char]
    base += PINYIN_BASE[char] ?? char
  }
  base = [...base].filter((char) => /[a-zü]/.test(char)).join('')
  if (!base) return null

  const initial = PINYIN_INITIALS.find((candidate) => base.startsWith(candidate)) ?? ''
  return { raw: syllable, base, tone, initial, final: base.slice(initial.length) }
}

function alignedHeardChars(reference, heard) {
  const ref = [...normalizeTranscript(reference)]
  const got = [...normalizeTranscript(heard)]
  const d = Array.from({ length: ref.length + 1 }, (_, i) =>
    Array.from({ length: got.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  )

  for (let i = 1; i <= ref.length; i += 1) {
    for (let j = 1; j <= got.length; j += 1) {
      const cost = ref[i - 1] === got[j - 1] ? 0 : 1
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    }
  }

  const aligned = new Array(ref.length).fill('')
  let i = ref.length
  let j = got.length
  while (i > 0 && j > 0) {
    const cost = ref[i - 1] === got[j - 1] ? 0 : 1
    if (d[i][j] === d[i - 1][j - 1] + cost) {
      aligned[i - 1] = got[j - 1]
      i -= 1
      j -= 1
    } else if (d[i][j] === d[i - 1][j] + 1) {
      i -= 1
    } else {
      j -= 1
    }
  }
  return { ref, aligned, extra: Math.max(0, got.length - ref.length) }
}

function safePinyinLookup(lookupPinyin, char) {
  if (typeof lookupPinyin !== 'function' || !char) return null
  try {
    return pinyinParts(lookupPinyin(char))
  } catch {
    return null
  }
}

/**
 * 用 ASR 转写字的拼音关系给原文逐字打“候选诊断”标记。
 *
 * hit：同字，或不同字但拼音与声调完全相同；tone：音节相同、声调不同；
 * near：声母或韵母相同；miss：漏字、查不到拼音或差异较大。
 * lookupPinyin 由调用方注入，纯函数层不依赖课程字库。
 */
export function phonemeMarks(reference, heard, lookupPinyin) {
  const { ref, aligned, extra } = alignedHeardChars(reference, heard)
  const chars = ref.map((char, index) => {
    const heardAs = aligned[index]
    if (char === heardAs) return { char, status: 'hit' }
    if (!heardAs) return { char, status: 'miss' }

    const expected = safePinyinLookup(lookupPinyin, char)
    const actual = safePinyinLookup(lookupPinyin, heardAs)
    if (!expected || !actual) return { char, status: 'miss', heardAs }

    let status = 'miss'
    if (expected.base === actual.base && expected.tone === actual.tone) status = 'hit'
    else if (expected.base === actual.base) status = 'tone'
    else if (
      (expected.initial && expected.initial === actual.initial) ||
      (expected.final && expected.final === actual.final)
    ) status = 'near'

    return {
      char,
      status,
      heardAs,
      expectedPinyin: expected.raw,
      heardPinyin: actual.raw
    }
  })

  return {
    chars,
    hits: chars.filter((item) => item.status === 'hit').length,
    toneErrors: chars.filter((item) => item.status === 'tone').length,
    nearMisses: chars.filter((item) => item.status === 'near').length,
    misses: chars.filter((item) => item.status === 'miss').length,
    total: chars.length,
    extra
  }
}

/**
 * 转写代理相似度：hit=1、tone=0.5、near=0.25，多读轻罚沿用 v1。
 * 返回值只能用于 PoC 排序；没有声学后验时不得展示成“音素准确率”。
 */
export function similarityV2(reference, heard, lookupPinyin) {
  const detail = phonemeMarks(reference, heard, lookupPinyin)
  if (!detail.total) return 0
  const weighted =
    (detail.hits + detail.toneErrors * 0.5 + detail.nearMisses * 0.25) / detail.total
  const penalty = Math.min(0.2, (detail.extra / detail.total) * 0.3)
  return Math.max(0, Math.min(1, weighted - penalty))
}

const clampScore = (n) => Math.max(0, Math.min(100, Math.round(n)))

/** 识别档得分：相似度直接映射成百分数。 */
export function scoreFromSimilarity(sim) {
  return clampScore(Number(sim) * 100)
}

/**
 * 响度档得分：判不了字，只判「开口了没有」。
 *
 * @param {object} sample
 * @param {number} sample.voicedRatio 采到的帧里有多少比例超过了出声阈值（0-1）
 * @param {number} sample.durationRatio 实际读了多久 / 范读多久（0 起，1 表示一样长）
 * @param {number} sample.peak 整段里最响的一帧（0-1）
 * @returns {number} 0-85，封顶 85：这一档没听清内容，不该给满分
 */
export const LOUDNESS_SCORE_CAP = 85

export function scoreFromLoudness({ voicedRatio = 0, durationRatio = 0, peak = 0 } = {}) {
  const voiced = Math.max(0, Math.min(1, voicedRatio))
  const peaked = Math.max(0, Math.min(1, peak))
  // 读得比范读长不加分，读到范读的八成就算读完了
  const length = Math.max(0, Math.min(1, durationRatio / 0.8))

  if (peaked < 0.04 || voiced < 0.05) return 0

  const score = (voiced * 0.45 + length * 0.35 + Math.min(1, peaked / 0.35) * 0.2) * LOUDNESS_SCORE_CAP
  return clampScore(Math.min(LOUDNESS_SCORE_CAP, score))
}

export function gradeOf(score) {
  const n = clampScore(score)
  return GRADES.find((g) => n >= g.min) ?? GRADES[GRADES.length - 1]
}

/**
 * 学伴对话只看本轮已经在本机算出的结果，用固定规则回复，不发网络请求。
 * 放在纯函数层，界面和 Node 单测可以共享同一套回复规则。
 */
export function companionReplyForResult(outcome) {
  if (!outcome) return ''

  if (outcome.mode === 'listen-only') {
    if (outcome.grade?.id === 'fluent') return '你觉得很流利，真棒！现在试试不看拼音再读一遍。'
    if (outcome.grade?.id === 'okay') return '找到卡住的地方就有进步啦。先听范读，再慢慢跟一句。'
    return '没关系，我陪你再听一遍；一句一句来就会越来越顺。'
  }

  if (outcome.mode === 'recording') {
    if (outcome.score >= 70) return '声音又清楚又完整！回放听一听，再试着读得更有节奏。'
    return '我听见你开口啦！靠近一点麦克风，慢慢把整句读完。'
  }

  const missed = (outcome.chars ?? [])
    .filter((item) => item.status === 'miss')
    .map((item) => item.char)
  if (missed.length) {
    const focus = [...new Set(missed)].slice(0, 3).join('、')
    return `大部分都跟上啦！再听听「${focus}」，把这${missed.length > 1 ? '几个字' : '个字'}慢慢读清楚。`
  }
  if (outcome.score >= 85) return '每个字都跟上啦！下一遍试试读出诗句的停顿。'
  return '这一遍有进步！先听一句，再用同样的速度跟着读。'
}

/**
 * 一次跟读的完整结论，界面直接渲染它。
 * mode 决定了「这个分数是怎么来的」，界面要如实告诉孩子和家长。
 */
export function evaluate({ mode = 'recognition', reference = '', heard = '', sample } = {}) {
  // loudness 是 v1 的内部名称，继续接受它以兼容已有进度与独立调用；
  // v2 对外统一使用三档契约里的 recording。
  if (mode === 'recording' || mode === 'loudness') {
    const score = scoreFromLoudness(sample)
    return {
      mode: 'recording',
      score,
      grade: gradeOf(score),
      chars: [...normalizeTranscript(reference)].map((char) => ({ char, status: 'unknown' })),
      heard: '',
      note: '这台设备听不出念的是哪个字，这一分是按「有没有大声读完」给的。'
    }
  }

  const detail = alignChars(reference, heard)
  const score = scoreFromSimilarity(similarity(reference, heard))
  return {
    mode: 'recognition',
    score,
    grade: gradeOf(score),
    chars: detail.chars,
    heard: normalizeTranscript(heard),
    note: detail.total ? `念对 ${detail.hits} / ${detail.total} 个字。` : ''
  }
}
