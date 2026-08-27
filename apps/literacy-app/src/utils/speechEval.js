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
 *   响度档（loudness）      只有麦克风、没有识别：判不了念得对不对，
 *                          只判「有没有认真开口」——有没有出声、读了多久、声音够不够。
 *                          这一档封顶 85 分，永远不会给出「满分」这种它其实不知道的结论。
 *
 * 两档之外还有第三种情况：连麦克风都没有。那时候不算分，只放录音让孩子自己听
 * （见 composables 里的 mode='listen'），界面上也不显示分数。
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
 * 一次跟读的完整结论，界面直接渲染它。
 * mode 决定了「这个分数是怎么来的」，界面要如实告诉孩子和家长。
 */
export function evaluate({ mode = 'recognition', reference = '', heard = '', sample } = {}) {
  if (mode === 'loudness') {
    const score = scoreFromLoudness(sample)
    return {
      mode,
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
