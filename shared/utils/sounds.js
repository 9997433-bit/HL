/**
 * 零素材 Web Audio 音效。首次播放必须由点击/触摸等用户手势触发，
 * 以满足浏览器的自动播放策略。
 */

let context = null
let master = null
let enabled = true
let volume = 0.7

const AudioContextConstructor = () => {
  if (typeof window === 'undefined') return null
  return window.AudioContext || window.webkitAudioContext || null
}

const getContext = () => {
  const Constructor = AudioContextConstructor()
  if (!Constructor || !enabled) return null

  if (!context || context.state === 'closed') {
    context = new Constructor()
    master = context.createGain()
    master.gain.value = volume
    master.connect(context.destination)
  }

  if (context.state === 'suspended') {
    context.resume().catch(() => {})
  }
  return context
}

const playTone = ({
  frequency,
  endFrequency = frequency,
  delay = 0,
  duration = 0.14,
  gain = 0.1,
  type = 'sine',
}) => {
  const audioContext = getContext()
  if (!audioContext || !master) return null

  const start = audioContext.currentTime + Math.max(0, delay)
  const end = start + Math.max(0.03, duration)
  const oscillator = audioContext.createOscillator()
  const envelope = audioContext.createGain()

  oscillator.type = type
  oscillator.frequency.setValueAtTime(Math.max(1, frequency), start)
  oscillator.frequency.exponentialRampToValueAtTime(Math.max(1, endFrequency), end)
  envelope.gain.setValueAtTime(0.0001, start)
  envelope.gain.exponentialRampToValueAtTime(Math.max(0.0001, gain), start + 0.015)
  envelope.gain.exponentialRampToValueAtTime(0.0001, end)

  oscillator.connect(envelope)
  envelope.connect(master)
  oscillator.addEventListener(
    'ended',
    () => {
      oscillator.disconnect()
      envelope.disconnect()
    },
    { once: true },
  )
  oscillator.start(start)
  oscillator.stop(end + 0.02)
  return oscillator
}

export function click() {
  playTone({
    frequency: 620,
    endFrequency: 520,
    duration: 0.065,
    gain: 0.045,
    type: 'triangle',
  })
}

export function correct() {
  playTone({ frequency: 523.25, duration: 0.12, gain: 0.07, type: 'triangle' })
  playTone({
    frequency: 659.25,
    delay: 0.085,
    duration: 0.14,
    gain: 0.075,
    type: 'triangle',
  })
  playTone({
    frequency: 783.99,
    delay: 0.17,
    duration: 0.2,
    gain: 0.08,
    type: 'sine',
  })
}

export function error() {
  playTone({
    frequency: 260,
    endFrequency: 205,
    duration: 0.19,
    gain: 0.055,
    type: 'sawtooth',
  })
  playTone({
    frequency: 205,
    endFrequency: 165,
    delay: 0.12,
    duration: 0.22,
    gain: 0.045,
    type: 'sawtooth',
  })
}

export function celebration() {
  const melody = [523.25, 659.25, 783.99, 1046.5]
  melody.forEach((frequency, index) => {
    playTone({
      frequency,
      delay: index * 0.085,
      duration: index === melody.length - 1 ? 0.42 : 0.2,
      gain: 0.065,
      type: index % 2 ? 'sine' : 'triangle',
    })
  })
  ;[523.25, 659.25, 783.99].forEach((frequency) => {
    playTone({
      frequency,
      delay: 0.29,
      duration: 0.36,
      gain: 0.035,
      type: 'sine',
    })
  })
}

export function setSoundEnabled(value) {
  enabled = Boolean(value)
  if (master && context) {
    master.gain.setTargetAtTime(enabled ? volume : 0, context.currentTime, 0.015)
  }
}

export function setSoundVolume(value) {
  volume = Math.min(1, Math.max(0, Number(value) || 0))
  if (master && context && enabled) {
    master.gain.setTargetAtTime(volume, context.currentTime, 0.015)
  }
}

/** 在首次用户手势回调中调用，可显式解锁 Safari/iOS 音频。 */
export async function unlockAudio() {
  const audioContext = getContext()
  if (!audioContext) return false
  if (audioContext.state === 'suspended') await audioContext.resume()
  return audioContext.state === 'running'
}

export async function closeAudio() {
  if (!context || context.state === 'closed') return
  await context.close()
  context = null
  master = null
}

export const sounds = {
  correct,
  error,
  wrong: error,
  click,
  tap: click,
  celebration,
  setEnabled: setSoundEnabled,
  setVolume: setSoundVolume,
  unlock: unlockAudio,
  close: closeAudio,
}

export default sounds
