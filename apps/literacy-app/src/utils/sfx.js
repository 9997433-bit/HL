/**
 * 用 WebAudio 合成的音效，避免打包任何音频文件。
 * 全部音效都很短，音量压得比较低，适合小朋友长时间使用。
 */

let ctx = null
let muted = false

function audioCtx() {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext || window.webkitAudioContext
  if (!Ctor) return null
  if (!ctx) ctx = new Ctor()
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx
}

export function setSfxMuted(value) {
  muted = Boolean(value)
}

function tone({ freq, start = 0, dur = 0.14, type = 'sine', gain = 0.12 }) {
  const ac = audioCtx()
  if (!ac || muted) return
  const t0 = ac.currentTime + start
  const osc = ac.createOscillator()
  const g = ac.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  g.gain.setValueAtTime(0.0001, t0)
  g.gain.exponentialRampToValueAtTime(gain, t0 + 0.02)
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  osc.connect(g).connect(ac.destination)
  osc.start(t0)
  osc.stop(t0 + dur + 0.02)
}

export const sfx = {
  tap() {
    tone({ freq: 660, dur: 0.08, gain: 0.07, type: 'triangle' })
  },
  correct() {
    tone({ freq: 660, start: 0, dur: 0.13 })
    tone({ freq: 880, start: 0.1, dur: 0.14 })
    tone({ freq: 1174, start: 0.2, dur: 0.22 })
  },
  wrong() {
    tone({ freq: 300, dur: 0.16, type: 'sawtooth', gain: 0.07 })
    tone({ freq: 210, start: 0.12, dur: 0.2, type: 'sawtooth', gain: 0.06 })
  },
  levelUp() {
    ;[523, 659, 784, 1047].forEach((f, i) =>
      tone({ freq: f, start: i * 0.09, dur: 0.2, gain: 0.1 })
    )
  },
  page() {
    tone({ freq: 480, dur: 0.06, type: 'triangle', gain: 0.05 })
    tone({ freq: 720, start: 0.05, dur: 0.07, type: 'triangle', gain: 0.05 })
  }
}
