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

export const sfx = {
  tap: () => tone({ freq: 520, duration: 0.07, type: 'triangle', gain: 0.045 }),
  page: () => {
    tone({ freq: 380, duration: 0.09, type: 'triangle', gain: 0.04 })
    tone({ freq: 560, duration: 0.1, type: 'triangle', gain: 0.035, delay: 0.05 })
  },
  /** 每写完一笔的轻脆反馈，笔序越靠后音越高。 */
  stroke: (index = 0) =>
    tone({ freq: 480 + index * 40, duration: 0.08, type: 'sine', gain: 0.05 }),
  correct: () => {
    tone({ freq: 660, duration: 0.14 })
    tone({ freq: 880, duration: 0.16, delay: 0.09 })
    tone({ freq: 1180, duration: 0.22, delay: 0.18, gain: 0.055 })
  },
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
  })
}

/** 系统里到底有没有中文嗓音——没有的话界面上要提示家长。 */
export function hasChineseVoice() {
  if (!synth) return false
  if (!voicesReady) cachedVoice = pickVoice()
  return !!cachedVoice
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
