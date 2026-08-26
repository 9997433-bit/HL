/**
 * 音效引擎 —— 全应用唯一的声音入口。
 *
 * 五种反馈音全部用 Web Audio 现场合成，不打包任何音频文件，也不依赖音频库：
 * 一个三角波振荡器 + 一条 ADSR 增益包络就够用，整套引擎不到 3KB。
 *
 * 浏览器要求 AudioContext 由用户手势创建，所以这里在第一次 play* 调用时才惰性初始化；
 * 页面加载即调用（例如自动播放）会被浏览器挂起，这属于预期行为，不作为错误上报。
 */

/** Tone.js 时值记号 → 秒（按 120 BPM 换算），保留记号是为了让音效谱面仍然好读。 */
const DURATIONS = { '32n': 0.0625, '16n': 0.125, '8n': 0.25, '4n': 0.5 }

/** 主音量 −8 dB，与原 Tone.PolySynth 的响度保持一致。 */
const MASTER_GAIN = 10 ** (-8 / 20)

const ATTACK = 0.005
const DECAY = 0.15
const SUSTAIN = 0.1
const RELEASE = 0.3

const SEMITONES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }

/**
 * 五种反馈音的谱面：{ notes, gap, dur }。
 * gap 为 0 表示同时发声（和弦），否则是相邻音符的起始间隔（秒）。
 */
export const CUES = {
  /** 界面点击:短促单音 */
  click: { notes: ['C5'], gap: 0, dur: '32n' },
  /** 答对:大调上行琶音 */
  correct: { notes: ['C5', 'E5', 'G5'], gap: 0.09, dur: '16n' },
  /** 答错:柔和下行小二度(不刺耳,保护低龄挫败感) */
  wrong: { notes: ['E4', 'Eb4'], gap: 0.12, dur: '8n' },
  /** 获得星星:高音闪烁 */
  star: { notes: ['G5', 'C6', 'E6', 'G6'], gap: 0.07, dur: '16n' },
  /** 连击/通关:五声音阶庆祝 */
  combo: { notes: ['C5', 'D5', 'E5', 'G5', 'A5', 'C6'], gap: 0.06, dur: '16n' },
}

/** 'C5' / 'Eb4' / 'F#3' → 频率（Hz），以 A4 = 440Hz 为基准；音名非法时返回 null。 */
export function noteToFreq(note) {
  const m = /^([A-G])([#b]?)(-?\d+)$/.exec(note)
  if (!m) return null
  const [, letter, accidental, octave] = m
  const offset = accidental === '#' ? 1 : accidental === 'b' ? -1 : 0
  const midi = (Number(octave) + 1) * 12 + SEMITONES[letter] + offset
  return 440 * 2 ** ((midi - 69) / 12)
}

let ctx = null
let master = null
let enabled = true

function ensureAudio() {
  if (!enabled) return false
  if (typeof window === 'undefined') return false
  const Ctor = window.AudioContext ?? window.webkitAudioContext
  if (!Ctor) return false

  if (!ctx) {
    try {
      ctx = new Ctor()
      master = ctx.createGain()
      master.gain.value = MASTER_GAIN
      master.connect(ctx.destination)
    } catch {
      ctx = null
      return false
    }
  }
  // 手势之前创建的 context 是 suspended 的，首次点击时恢复
  if (ctx.state === 'suspended') ctx.resume().catch(() => {})
  return ctx.state !== 'closed'
}

/** 奏出一段谱面。 */
function play({ notes, gap, dur }) {
  if (!ensureAudio()) return
  const hold = Math.max(DURATIONS[dur] ?? 0.125, ATTACK + DECAY)
  const start = ctx.currentTime + 0.01

  for (const [i, note] of notes.entries()) {
    const freq = noteToFreq(note)
    if (freq === null) continue
    const t0 = start + i * gap
    const osc = ctx.createOscillator()
    const env = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = freq

    env.gain.setValueAtTime(0, t0)
    env.gain.linearRampToValueAtTime(1, t0 + ATTACK)
    env.gain.linearRampToValueAtTime(SUSTAIN, t0 + ATTACK + DECAY)
    env.gain.setValueAtTime(SUSTAIN, t0 + hold)
    env.gain.linearRampToValueAtTime(0, t0 + hold + RELEASE)

    osc.connect(env)
    env.connect(master)
    osc.start(t0)
    osc.stop(t0 + hold + RELEASE + 0.02)
    osc.onended = () => env.disconnect()
  }
}

export const sound = {
  /** 设置页的音效总开关 */
  setEnabled(value) {
    enabled = !!value
  },
  click: () => play(CUES.click),
  correct: () => play(CUES.correct),
  wrong: () => play(CUES.wrong),
  star: () => play(CUES.star),
  combo: () => play(CUES.combo),
}

/** 语义化别名：玩法层按「发生了什么」调用，而不用关心奏的是哪几个音。 */
export const sfx = {
  tap: () => sound.click(),
  correct: () => sound.correct(),
  wrong: () => sound.wrong(),
  star: () => sound.star(),
  levelUp: () => sound.combo(),
}
