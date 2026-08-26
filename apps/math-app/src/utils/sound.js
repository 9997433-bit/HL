/**
 * 极轻量的 WebAudio 音效，不依赖任何音频素材文件。
 * 全部音色由振荡器合成，保证离线可用与打包体积为零。
 */

let ctx = null
let enabled = true

function audioCtx() {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext || window.webkitAudioContext
  if (!Ctor) return null
  if (!ctx) ctx = new Ctor()
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

export function setSoundEnabled(value) {
  enabled = !!value
}

function tone({ freq = 440, duration = 0.16, type = 'sine', gain = 0.08, delay = 0 }) {
  if (!enabled) return
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
  tap: () => tone({ freq: 520, duration: 0.08, type: 'triangle', gain: 0.05 }),
  correct: () => {
    tone({ freq: 660, duration: 0.14, type: 'sine' })
    tone({ freq: 880, duration: 0.16, type: 'sine', delay: 0.09 })
    tone({ freq: 1180, duration: 0.22, type: 'sine', delay: 0.18, gain: 0.06 })
  },
  wrong: () => {
    tone({ freq: 240, duration: 0.18, type: 'sawtooth', gain: 0.05 })
    tone({ freq: 170, duration: 0.24, type: 'sawtooth', gain: 0.05, delay: 0.1 })
  },
  star: () => tone({ freq: 1320, duration: 0.12, type: 'triangle', gain: 0.05 }),
  levelUp: () => {
    ;[523, 659, 784, 1046].forEach((f, i) =>
      tone({ freq: f, duration: 0.18, type: 'triangle', delay: i * 0.09, gain: 0.06 }),
    )
  },
}
