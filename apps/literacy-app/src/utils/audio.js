/**
 * 声音层：合成音效 + 中文朗读。
 *
 * 两块都刻意做成「零素材」：
 *   - 音效由 WebAudio 振荡器实时合成，不打包任何 mp3；
 *   - 朗读走浏览器自带的 SpeechSynthesis，不请求任何在线 TTS。
 * 结果是整个应用离线可用，也不会把孩子的语音数据发到任何地方。
 */

let ctx = null
let soundEnabled = true
let speechEnabled = true

function audioCtx() {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext || window.webkitAudioContext
  if (!Ctor) return null
  if (!ctx) ctx = new Ctor()
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

export function setSoundEnabled(value) {
  soundEnabled = !!value
}

export function setSpeechEnabled(value) {
  speechEnabled = !!value
  if (!speechEnabled) cancelSpeech()
}

function tone({ freq = 440, duration = 0.16, type = 'sine', gain = 0.07, delay = 0 }) {
  if (!soundEnabled) return
  const ac = audioCtx()
  if (!ac) return
  const start = ac.currentTime + delay
  const osc = ac.createOscillator()
  const amp = ac.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  amp.gain.setValueAtTime(0.0001, start)
  amp.gain.exponentialRampToValueAtTime(gain, start + 0.02)
  amp.gain.exponentialRampToValueAtTime(0.0001, start + duration)
  osc.connect(amp).connect(ac.destination)
  osc.start(start)
  osc.stop(start + duration + 0.02)
}

/**
 * 连对音阶与数学 App 保持同一走向。第 7 档封顶，长连击不会无限升高。
 * 每一档的收尾音严格递增，孩子不用看数字也能听出连对在累积。
 */
export const STREAK_CHORDS = [
  [523.25, 659.25, 783.99],
  [587.33, 739.99, 880],
  [659.25, 830.61, 987.77],
  [698.46, 880, 1046.5],
  [783.99, 987.77, 1174.66],
  [880, 1108.73, 1318.51],
  [1046.5, 1318.51, 1567.98]
]

function streakIndex(streak = 1) {
  const value = Number(streak)
  const count = Number.isFinite(value) ? Math.floor(value) : 1
  return Math.min(STREAK_CHORDS.length, Math.max(1, count)) - 1
}

/** 把任意 streak 值归一到安全音域，便于独立验证谱面。 */
export function streakChord(streak = 1) {
  return STREAK_CHORDS[streakIndex(streak)]
}

function playStreak(streak = 1) {
  const index = streakIndex(streak)
  const gap = 0.09 - index * 0.005
  streakChord(streak).forEach((freq, noteIndex, notes) =>
    tone({
      freq,
      duration: noteIndex === notes.length - 1 ? 0.22 : 0.14,
      type: noteIndex % 2 ? 'sine' : 'triangle',
      gain: noteIndex === notes.length - 1 ? 0.055 : 0.05,
      delay: noteIndex * gap
    })
  )
}

/* -------------------------------------------------------------------------
   儿歌旋律
   ------------------------------------------------------------------------- */

/**
 * 儿歌能用的音名表。
 *
 * 只到 C4–E5 一个八度多一点：再低这个年龄段的嗓子够不着，再高合成音会发尖。
 * data/songs.js 的每个字配一个音名，`verifySongCoverage()` 会校验音名都在这张表里。
 */
export const NOTE_HZ = {
  C4: 261.63,
  D4: 293.66,
  E4: 329.63,
  F4: 349.23,
  G4: 392,
  A4: 440,
  B4: 493.88,
  C5: 523.25,
  D5: 587.33,
  E5: 659.25
}

/**
 * 按谱子逐音播放一段旋律，返回每个音相对开始时刻的毫秒偏移。
 *
 * 返回时间表而不是逐音回调，是因为界面要做的是「唱到哪个字就高亮哪个字」：
 * 拿着这张表用一个定时器推进比给每个音挂回调稳得多，静音时（家长关了音效）
 * 时间表照样准确，高亮不会因此停摆。
 *
 * @param {string[]} notes 音名序列，不认识的音名当休止符跳过
 * @param {{bpm?: number, gain?: number, holdLast?: number}} [opts]
 *        holdLast 收尾音的拍数，默认 2 拍——每句最后一个字拖长一点才像唱歌。
 * @returns {{offsets: number[], duration: number}} 逐音起始毫秒与总时长
 */
export function playMelody(notes = [], { bpm = 96, gain = 0.06, holdLast = 2 } = {}) {
  const beat = 60 / Math.min(200, Math.max(40, bpm))
  const offsets = []
  let at = 0
  notes.forEach((name, index) => {
    const last = index === notes.length - 1
    const beats = last ? holdLast : 1
    const freq = NOTE_HZ[name]
    if (freq) {
      tone({ freq, duration: beat * beats * 0.92, type: 'triangle', gain, delay: at })
    }
    offsets.push(Math.round(at * 1000))
    at += beat * beats
  })
  return { offsets, duration: Math.round(at * 1000) }
}

export const sfx = {
  tap: () => tone({ freq: 520, duration: 0.07, type: 'triangle', gain: 0.045 }),
  page: () => {
    tone({ freq: 380, duration: 0.09, type: 'triangle', gain: 0.04 })
    tone({ freq: 560, duration: 0.1, type: 'triangle', gain: 0.035, delay: 0.05 })
  },
  /** 每写完一笔的轻脆反馈，笔序越靠后音越高。 */
  stroke: (index = 0) =>
    tone({ freq: 480 + index * 40, duration: 0.08, type: 'sine', gain: 0.05 }),
  correct: () => playStreak(1),
  /** 连对越多音高越高、节拍越紧；供答题链路传入最新 streak。 */
  streak: (count) => playStreak(count),
  wrong: () => {
    tone({ freq: 240, duration: 0.16, type: 'sawtooth', gain: 0.045 })
    tone({ freq: 175, duration: 0.22, type: 'sawtooth', gain: 0.045, delay: 0.09 })
  },
  star: () => tone({ freq: 1320, duration: 0.12, type: 'triangle', gain: 0.05 }),
  celebrate: () => {
    ;[523, 659, 784, 1046, 1318].forEach((f, i) =>
      tone({ freq: f, duration: 0.2, type: 'triangle', delay: i * 0.085, gain: 0.055 })
    )
  }
}

/* -------------------------------------------------------------------------
   中文朗读
   ------------------------------------------------------------------------- */

const synth = typeof window !== 'undefined' ? window.speechSynthesis : null

export const speechSupported = !!synth

let cachedVoice = null
let voicesReady = false

/** 嗓音列表是异步到位的，界面要在它变化时重画提示。 */
const voiceListeners = new Set()

function notifyVoiceListeners() {
  for (const fn of voiceListeners) {
    try {
      fn(voiceStatus())
    } catch {
      /* 某个订阅者抛错不该拖垮其他订阅者 */
    }
  }
}

/** 挑一个中文嗓音；不同系统上可用嗓音差别很大，按优先级降级。 */
function pickVoice() {
  if (!synth) return null
  const voices = synth.getVoices()
  if (!voices.length) return null
  voicesReady = true

  const score = (v) => {
    const lang = (v.lang || '').toLowerCase().replace('_', '-')
    if (lang === 'zh-cn') return 4
    if (lang.startsWith('zh-han') || lang === 'zh') return 3
    if (lang.startsWith('zh')) return 2
    return 0
  }

  return (
    voices
      .map((v) => ({ v, s: score(v) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)[0]?.v ?? null
  )
}

if (synth) {
  cachedVoice = pickVoice()
  // Chrome 首次调用 getVoices() 往往返回空数组，要等这个事件。
  synth.addEventListener?.('voiceschanged', () => {
    cachedVoice = pickVoice()
    notifyVoiceListeners()
  })
}

/** 系统里到底有没有中文嗓音——没有的话界面上要提示家长。 */
export function hasChineseVoice() {
  if (!synth) return false
  if (!voicesReady) cachedVoice = pickVoice()
  return !!cachedVoice
}

/**
 * 朗读能力的四种状态，界面据此决定提示什么：
 *   unsupported 浏览器根本没有 SpeechSynthesis
 *   pending     还没拿到嗓音列表，先别下结论（Chrome 冷启动常见）
 *   missing     有朗读能力，但系统里一个中文嗓音都没装
 *   ready       能正常读中文
 */
export function voiceStatus() {
  if (!synth) return 'unsupported'
  if (!voicesReady) {
    cachedVoice = pickVoice()
    if (!voicesReady) return 'pending'
  }
  return cachedVoice ? 'ready' : 'missing'
}

/** 订阅嗓音状态变化，返回退订函数。 */
export function onVoicesChanged(fn) {
  voiceListeners.add(fn)
  return () => voiceListeners.delete(fn)
}

/** 家长面板要显示的技术详情：到底用的哪个嗓音、系统里一共有几个。 */
export function voiceInfo() {
  return {
    status: voiceStatus(),
    name: cachedVoice?.name ?? '',
    lang: cachedVoice?.lang ?? '',
    total: synth?.getVoices?.().length ?? 0
  }
}

export function cancelSpeech() {
  try {
    synth?.cancel()
  } catch {
    /* 某些浏览器在没有排队任务时会抛错，忽略 */
  }
}

/**
 * 朗读一段中文。
 * @param {string} text 要读的内容
 * @param {{rate?: number, pitch?: number, interrupt?: boolean}} [opts]
 *        rate 默认 0.85——给孩子听要比默认语速慢一些。
 * @returns {Promise<boolean>} 是否真的读出来了
 */
export function speak(text, opts = {}) {
  if (!speechEnabled || !synth || !text) return Promise.resolve(false)

  const { rate = 0.85, pitch = 1.1, interrupt = true } = opts
  if (interrupt) cancelSpeech()

  if (!cachedVoice) cachedVoice = pickVoice()

  return new Promise((resolve) => {
    let settled = false
    const done = (ok) => {
      if (settled) return
      settled = true
      resolve(ok)
    }

    try {
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = cachedVoice?.lang || 'zh-CN'
      if (cachedVoice) utter.voice = cachedVoice
      utter.rate = rate
      utter.pitch = pitch
      utter.onend = () => done(true)
      utter.onerror = () => done(false)
      synth.speak(utter)
      // 部分 WebView 上 onend 不会触发，兜一个超时避免 Promise 永远挂着。
      setTimeout(() => done(true), 400 + text.length * 420)
    } catch {
      done(false)
    }
  })
}
