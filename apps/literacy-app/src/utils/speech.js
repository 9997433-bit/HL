/**
 * 中文朗读，基于浏览器内置的 SpeechSynthesis。
 * 不引入任何音频资源，也不需要联网；不支持的浏览器会静默降级。
 */

let cachedVoice
let voicesReady = false

function pickChineseVoice() {
  if (cachedVoice !== undefined) return cachedVoice
  const synth = window.speechSynthesis
  if (!synth) return (cachedVoice = null)

  const voices = synth.getVoices()
  if (!voices.length) return null // 还没加载好，下次再挑

  const score = (v) => {
    const lang = (v.lang || '').toLowerCase()
    if (lang.startsWith('zh-cn') || lang === 'zh_cn') return 3
    if (lang.startsWith('zh')) return 2
    return 0
  }
  const best = voices
    .map((v) => ({ v, s: score(v) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)[0]

  voicesReady = true
  return (cachedVoice = best ? best.v : null)
}

export function isSpeechSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function primeSpeech() {
  if (!isSpeechSupported() || voicesReady) return
  window.speechSynthesis.getVoices()
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = undefined
    pickChineseVoice()
  }
}

/**
 * @param {string} text 要读的内容
 * @param {{rate?: number, pitch?: number}} [opts] rate 默认偏慢，适合儿童跟读
 */
export function speak(text, opts = {}) {
  if (!isSpeechSupported() || !text) return false
  const synth = window.speechSynthesis
  try {
    synth.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    const voice = pickChineseVoice()
    if (voice) utter.voice = voice
    utter.lang = voice?.lang || 'zh-CN'
    utter.rate = opts.rate ?? 0.75
    utter.pitch = opts.pitch ?? 1.1
    utter.volume = opts.volume ?? 1
    synth.speak(utter)
    return true
  } catch {
    return false
  }
}

export function stopSpeaking() {
  if (isSpeechSupported()) window.speechSynthesis.cancel()
}
