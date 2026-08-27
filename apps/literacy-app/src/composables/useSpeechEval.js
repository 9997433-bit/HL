/**
 * 跟读评测 v2：范读 → 孩子跟读 → 当场给一句评价与离线学伴回复。
 *
 * 这一层只负责和浏览器打交道（朗读、录音、识别、回放），算分规则在
 * utils/speechEval.js 里，那份是纯函数，可以脱离浏览器单独验。
 *
 * 设备能力差得很远，所以按三档降级，界面上如实说明这一档能做到什么：
 *
 *   recognition  有 SpeechRecognition：听清孩子念了什么，逐字标出念对念漏。
 *   recording    只有麦克风：录下来、按响度和时长给一个「有没有认真读完」的分，
 *                并把录音放回去让孩子自己听——这一档听不出字，分数封顶 85。
 *   listen-only  连麦克风都没有（或家长不允许）：只放范读，读完由孩子自己选
 *                「很流利 / 有点卡 / 还要再来」，不假装打分。
 *
 * 隐私：录音只存在内存里的 Blob，页面一关就没了，不写盘也不上传。
 * SpeechRecognition 在部分浏览器上会把音频送到厂商的在线服务，
 * 所以它默认关着，要家长在跟读页显式打开（`allowRecognition`）。
 */

import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { cancelSpeech, speak, speechSupported } from '@/utils/audio.js'
import {
  companionReplyForResult,
  evaluate,
  normalizeTranscript
} from '@/utils/speechEval.js'

/** 一帧的响度超过这个值就算「出声了」。经验值，太低会把风扇声算进去。 */
const VOICED_THRESHOLD = 0.045
/** 录音最长时长，防止忘了按停止。 */
const MAX_RECORD_MS = 20000
const SAMPLE_INTERVAL_MS = 50

function recognitionCtor() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null
}

function micSupported() {
  if (typeof navigator === 'undefined') return false
  return typeof navigator.mediaDevices?.getUserMedia === 'function'
}

export const MODE_LABELS = {
  recognition: '逐字评测',
  recording: '录音回放',
  'listen-only': '只听范读'
}

export function useSpeechEval(options = {}) {
  const { rate = 0.72 } = options

  /** idle | demo | recording | scoring | result */
  const phase = ref('idle')
  const result = shallowRef(null)
  const error = ref('')
  /** 实时响度 0-1，给音量条用。 */
  const level = ref(0)
  const recordingUrl = ref('')
  const elapsed = ref(0)
  /** 家长开关：识别可能把音频送到在线服务，默认不开。 */
  const allowRecognition = ref(false)

  const canRecognize = ref(!!recognitionCtor())
  const canRecord = ref(micSupported())
  /** 麦克风被拒绝过一次就别再问，直接降到自评档。 */
  const micDenied = ref(false)

  const mode = computed(() => {
    if (canRecognize.value && allowRecognition.value) return 'recognition'
    if (canRecord.value && !micDenied.value) return 'recording'
    return 'listen-only'
  })

  const modeLabel = computed(() => MODE_LABELS[mode.value])

  const modeNote = computed(() => {
    if (mode.value === 'recognition') return '会听清你念的每一个字，念漏了会标出来。'
    if (mode.value === 'recording') return '会把你读的录下来放给你听，并看看有没有大声读完。'
    return micDenied.value
      ? '没拿到麦克风，先跟着范读读出声，读完自己评一评。'
      : '这台设备没有麦克风，先跟着范读读出声，读完自己评一评。'
  })

  const busy = computed(() => phase.value === 'demo' || phase.value === 'recording')
  const companionReply = computed(() => companionReplyForResult(result.value))

  /* ------------------------------------------------------------ 运行时句柄 */

  let stream = null
  let audioCtx = null
  let analyser = null
  let recorder = null
  let recognizer = null
  let sampleTimer = null
  let stopTimer = null
  let chunks = []
  let samples = []
  let startedAt = 0
  let referenceMs = 0
  let heardText = ''
  let currentReference = ''

  function releaseRecording() {
    if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
    recordingUrl.value = ''
  }

  function teardown() {
    clearInterval(sampleTimer)
    clearTimeout(stopTimer)
    sampleTimer = null
    stopTimer = null
    try {
      recognizer?.stop()
    } catch {
      /* 已经停了 */
    }
    recognizer = null
    try {
      if (recorder && recorder.state !== 'inactive') recorder.stop()
    } catch {
      /* 同上 */
    }
    recorder = null
    stream?.getTracks?.().forEach((track) => track.stop())
    stream = null
    analyser = null
    audioCtx?.close?.().catch(() => {})
    audioCtx = null
    level.value = 0
  }

  /* ---------------------------------------------------------------- 范读 */

  /**
   * 读一遍原文。顺带量一下范读用了多久——响度档要拿它当「读完了没有」的尺子。
   */
  async function playReference(text) {
    if (!speechSupported) {
      error.value = '这台设备不会朗读，先请大人读给你听吧。'
      return false
    }
    error.value = ''
    phase.value = 'demo'
    const at = Date.now()
    const ok = await speak(text, { rate })
    referenceMs = Math.max(1200, Date.now() - at)
    if (phase.value === 'demo') phase.value = 'idle'
    return ok
  }

  function stopReference() {
    cancelSpeech()
    if (phase.value === 'demo') phase.value = 'idle'
  }

  /* -------------------------------------------------------------- 跟读录音 */

  function collectSample() {
    if (!analyser) return
    const buf = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(buf)
    let sum = 0
    for (let i = 0; i < buf.length; i += 1) {
      const v = (buf[i] - 128) / 128
      sum += v * v
    }
    const rms = Math.sqrt(sum / buf.length)
    samples.push(rms)
    level.value = Math.min(1, rms * 4)
    elapsed.value = Date.now() - startedAt
  }

  function loudnessSample() {
    if (!samples.length) return { voicedRatio: 0, durationRatio: 0, peak: 0 }
    const voiced = samples.filter((v) => v >= VOICED_THRESHOLD).length
    return {
      voicedRatio: voiced / samples.length,
      durationRatio: (Date.now() - startedAt) / (referenceMs || 3000),
      peak: Math.max(...samples)
    }
  }

  function settle(reference) {
    if (mode.value === 'recognition') {
      result.value = evaluate({ mode: 'recognition', reference, heard: heardText })
    } else {
      result.value = evaluate({ mode: 'recording', reference, sample: loudnessSample() })
    }
    phase.value = 'result'
  }

  /**
   * 开始跟读。
   * @param {string} reference 这一轮要读的原文（一句或整首）
   */
  async function start(reference) {
    if (busy.value) return false
    currentReference = String(reference ?? '')
    if (!normalizeTranscript(currentReference)) return false

    error.value = ''
    result.value = null
    heardText = ''
    samples = []
    chunks = []
    releaseRecording()
    elapsed.value = 0
    cancelSpeech()

    if (mode.value === 'listen-only') {
      // 没有麦克风就不假装在录，直接进「读完了自己评」的状态
      phase.value = 'recording'
      startedAt = Date.now()
      return true
    }

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      micDenied.value = true
      phase.value = 'recording'
      startedAt = Date.now()
      error.value = '没拿到麦克风，这一轮改成你自己听、自己评。'
      return true
    }

    startedAt = Date.now()
    phase.value = 'recording'

    try {
      const Ctor = window.AudioContext ?? window.webkitAudioContext
      audioCtx = Ctor ? new Ctor() : null
      if (audioCtx) {
        analyser = audioCtx.createAnalyser()
        analyser.fftSize = 1024
        audioCtx.createMediaStreamSource(stream).connect(analyser)
        sampleTimer = setInterval(collectSample, SAMPLE_INTERVAL_MS)
      }
    } catch {
      analyser = null
    }

    // 录音只为了放回去给孩子听，格式随浏览器给什么用什么
    try {
      if (typeof window.MediaRecorder === 'function') {
        recorder = new MediaRecorder(stream)
        recorder.ondataavailable = (e) => {
          if (e.data?.size) chunks.push(e.data)
        }
        recorder.onstop = () => {
          if (!chunks.length) return
          releaseRecording()
          recordingUrl.value = URL.createObjectURL(new Blob(chunks, { type: chunks[0].type }))
        }
        recorder.start()
      }
    } catch {
      recorder = null
    }

    if (mode.value === 'recognition') {
      try {
        const Ctor = recognitionCtor()
        recognizer = new Ctor()
        recognizer.lang = 'zh-CN'
        recognizer.interimResults = true
        recognizer.continuous = true
        recognizer.onresult = (event) => {
          let text = ''
          for (let i = 0; i < event.results.length; i += 1) text += event.results[i][0]?.transcript ?? ''
          heardText = text
        }
        recognizer.onerror = () => {
          // 识别挂了不算失败，退回响度档，孩子那一遍不白读
          recognizer = null
          canRecognize.value = false
          error.value = '这次没听清，按「有没有大声读完」来评。'
        }
        recognizer.start()
      } catch {
        recognizer = null
        canRecognize.value = false
      }
    }

    stopTimer = setTimeout(() => stop(), MAX_RECORD_MS)
    return true
  }

  /** 读完了，结算这一轮。 */
  async function stop() {
    if (phase.value !== 'recording') return null
    phase.value = 'scoring'
    const reference = currentReference

    if (mode.value === 'listen-only') {
      teardown()
      phase.value = 'result'
      result.value = null
      return null
    }

    // 识别引擎的最后一段结果常常在 stop() 之后才回来，给它一点时间
    const waitTail = mode.value === 'recognition' ? 700 : 120
    clearTimeout(stopTimer)
    clearInterval(sampleTimer)
    sampleTimer = null
    try {
      recognizer?.stop()
    } catch {
      /* 已经停了 */
    }
    try {
      if (recorder && recorder.state !== 'inactive') recorder.stop()
    } catch {
      /* 已经停了 */
    }
    await new Promise((r) => setTimeout(r, waitTail))

    settle(reference)
    stream?.getTracks?.().forEach((track) => track.stop())
    stream = null
    analyser = null
    audioCtx?.close?.().catch(() => {})
    audioCtx = null
    recognizer = null
    recorder = null
    level.value = 0
    return result.value
  }

  /** 自评档的结论：孩子自己说读得怎么样。分数留空，界面不显示打分。 */
  function selfAssess(choiceId) {
    const CHOICES = {
      fluent: { label: '很流利', emoji: '🌟', tip: '真棒，可以背给家人听了。' },
      okay: { label: '有点卡', emoji: '✨', tip: '再跟着范读一遍，就顺啦。' },
      again: { label: '还要再来', emoji: '🔁', tip: '没关系，一句一句慢慢来。' }
    }
    const choice = CHOICES[choiceId] ?? CHOICES.again
    result.value = {
      mode: 'listen-only',
      score: null,
      grade: { id: choiceId, label: choice.label, emoji: choice.emoji, tip: choice.tip },
      chars: [],
      heard: '',
      note: '这一条是你自己评的，没有打分。'
    }
    phase.value = 'result'
    return result.value
  }

  function reset() {
    teardown()
    releaseRecording()
    phase.value = 'idle'
    result.value = null
    error.value = ''
    elapsed.value = 0
  }

  onBeforeUnmount(() => {
    cancelSpeech()
    teardown()
    releaseRecording()
  })

  return {
    phase,
    mode,
    modeLabel,
    modeNote,
    result,
    error,
    level,
    elapsed,
    recordingUrl,
    busy,
    companionReply,
    canRecognize,
    canRecord,
    micDenied,
    allowRecognition,
    speechSupported,

    playReference,
    stopReference,
    start,
    stop,
    selfAssess,
    reset
  }
}
