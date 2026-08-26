/**
 * 音效引擎 — Tone.js 程序化合成,零音频资源。
 * AudioContext 必须由用户手势解锁:首次任意 play* 调用时惰性初始化。
 */
import * as Tone from 'tone'

let synth = null
let ready = false
let enabled = true

async function ensureAudio() {
  if (!enabled) return false
  if (ready) return true
  try {
    await Tone.start()
    synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'triangle' },
      envelope: { attack: 0.005, decay: 0.15, sustain: 0.1, release: 0.3 }
    }).toDestination()
    synth.volume.value = -8
    ready = true
  } catch {
    ready = false
  }
  return ready
}

function playNotes(notes, gap = 0.09, dur = '16n') {
  if (!synth) return
  const now = Tone.now()
  notes.forEach((n, i) => synth.triggerAttackRelease(n, dur, now + i * gap))
}

export const sound = {
  /** 设置页的音效总开关 */
  setEnabled(value) {
    enabled = !!value
  },
  /** 界面点击:短促单音 */
  async click() {
    if (await ensureAudio()) playNotes(['C5'], 0, '32n')
  },
  /** 答对:大调上行琶音 */
  async correct() {
    if (await ensureAudio()) playNotes(['C5', 'E5', 'G5'])
  },
  /** 答错:柔和下行小二度(不刺耳,保护低龄挫败感) */
  async wrong() {
    if (await ensureAudio()) playNotes(['E4', 'Eb4'], 0.12, '8n')
  },
  /** 获得星星:高音闪烁 */
  async star() {
    if (await ensureAudio()) playNotes(['G5', 'C6', 'E6', 'G6'], 0.07)
  },
  /** 连击/通关:五声音阶庆祝 */
  async combo() {
    if (await ensureAudio()) playNotes(['C5', 'D5', 'E5', 'G5', 'A5', 'C6'], 0.06)
  }
}
