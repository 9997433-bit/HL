/**
 * 中文朗读 —— 吉祥物「小算」开口说话用的那一层。
 *
 * 和音效引擎一样是「零素材」的：走浏览器自带的 SpeechSynthesis，
 * 不打包音频、不请求在线 TTS，装成 PWA 断网也能说话。
 * 系统里没有中文嗓音时静默降级——气泡里的字还在，只是没声音。
 */

const synth = typeof window !== 'undefined' ? window.speechSynthesis : null

export const speechSupported = !!synth

let enabled = true
let cachedVoice = null

export function setSpeechEnabled(value) {
  enabled = !!value
  if (!enabled) cancelSpeech()
}

/** 挑一个中文嗓音；不同系统装的嗓音差别很大，按 zh-CN → zh 的顺序降级。 */
function pickVoice() {
  if (!synth) return null
  const voices = synth.getVoices()
  if (!voices.length) return null
  const score = (v) => {
    const lang = (v.lang || '').toLowerCase().replace('_', '-')
    if (lang === 'zh-cn') return 3
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

// Chrome 冷启动时 getVoices() 常常返回空数组，要等这个事件才拿得到列表。
synth?.addEventListener?.('voiceschanged', () => {
  cachedVoice = pickVoice()
})

export function cancelSpeech() {
  try {
    synth?.cancel()
  } catch {
    /* 没有排队任务时个别浏览器会抛错，忽略 */
  }
}

/**
 * 读一句中文。语速默认比系统慢一些——给孩子听，快了跟不上。
 * @param {string} text
 * @param {{rate?: number, pitch?: number}} [opts]
 */
export function speak(text, { rate = 0.9, pitch = 1.15 } = {}) {
  if (!enabled || !synth || !text) return false
  cancelSpeech()
  if (!cachedVoice) cachedVoice = pickVoice()
  try {
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = cachedVoice?.lang || 'zh-CN'
    if (cachedVoice) utter.voice = cachedVoice
    utter.rate = rate
    utter.pitch = pitch
    synth.speak(utter)
    return true
  } catch {
    return false
  }
}
