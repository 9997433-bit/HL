/**
 * 跟读评测 v3：范读 → 孩子跟读 → 当场给一句评价与离线学伴回复。
 *
 * 这一层只负责和浏览器打交道（朗读、录音、识别、回放），算分规则在
 * utils/speechEval.js 里，那份是纯函数，可以脱离浏览器单独验。
 *
 * 设备能力差得很远，所以按四档降级；对外仍然只有三个 mode，
 * 第一档是 recognition 的内部实现，进度数据和界面不因为换了内核而分叉：
 *
 *   offline-asr  本机装了离线评测包：sherpa-onnx 在 Worker 里逐字识别，不联网。
 *   recognition  家长显式打开浏览器 SpeechRecognition：可能走厂商在线服务。
 *   recording    只有麦克风：录下来、按响度和时长给一个「有没有认真读完」的分，
 *                并把录音放回去让孩子自己听——这一档听不出字，分数封顶 85。
 *   listen-only  连麦克风都没有（或家长不允许）：只放范读，读完由孩子自己选
 *                「很流利 / 有点卡 / 还要再来」，不假装打分。
 *
 * 降级只许往下走：离线引擎起不来、超时或校验失败时落到 recording，
 * 绝不悄悄改用可能联网的浏览器识别——那等于替家长做了隐私决定。
 *
 * 隐私：录音与 PCM 只存在内存里，页面一关就没了，不写盘也不上传；
 * 离线评测包由家长点了才下载，同源自托管并逐文件校验 sha256。
 */

import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { cancelSpeech, speak, speechSupported } from '@/utils/audio.js'
import {
  companionReplyForResult,
  evaluate,
  normalizeTranscript
} from '@/utils/speechEval.js'
import {
  OFFLINE_ASR,
  asrAssetUrl,
  chooseTier,
  createOfflineRecognizer,
  describeAsrStep,
  floatToPcm16,
  installOfflinePack,
  modeOfTier,
  probeOfflinePack,
  removeOfflinePack,
  resampleTo16k,
  sourceOfTier
} from '@/utils/offlineAsr.js'

/** ROUND10_H1：跟读 v3 的离线 ASR 接线标记，check:round10 与 smoke 都认它。 */
export const ROUND10_H1_OFFLINE_ASR = `${OFFLINE_ASR.engine}/${OFFLINE_ASR.runtime}`

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

/** 四档各自的名字。对外 mode 仍是三档，这里只用于界面说明和回归测试。 */
export const TIER_LABELS = {
  'offline-asr': '离线逐字评测',
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

  /* --------------------------------------------------- 第一档：离线评测包 */

  /** unknown | checking | unavailable | available | installing | ready | failed */
  const offlineStatus = ref('unknown')
  const offlineNote = ref('还没查过这台设备装没装离线评测包。')
  const offlineProgress = ref(0)
  const offlineModel = ref('')
  /** 本轮会话里离线引擎已经证明起不来：此后一律走录音档，不改用在线识别。 */
  const offlineFault = ref(false)
  let offlineManifest = null

  const offlineReady = computed(() => offlineStatus.value === 'ready')
  const offlineBusy = computed(() => ['checking', 'installing'].includes(offlineStatus.value))

  const tier = computed(() =>
    chooseTier({
      offlineReady: offlineReady.value,
      offlineFault: offlineFault.value,
      canRecognize: canRecognize.value,
      allowRecognition: allowRecognition.value,
      canRecord: canRecord.value,
      micDenied: micDenied.value
    })
  )

  const mode = computed(() => modeOfTier(tier.value))
  const source = computed(() => sourceOfTier(tier.value))

  const modeLabel = computed(() => TIER_LABELS[tier.value] ?? MODE_LABELS[mode.value])

  const modeNote = computed(() => {
    if (tier.value === 'offline-asr') {
      return '会听清你念的每一个字，念漏了会标出来——识别全在这台设备上做，不联网。'
    }
    if (mode.value === 'recognition') return '会听清你念的每一个字，念漏了会标出来。'
    if (mode.value === 'recording') return '会把你读的录下来放给你听，并看看有没有大声读完。'
    return micDenied.value
      ? '没拿到麦克风，先跟着范读读出声，读完自己评一评。'
      : '这台设备没有麦克风，先跟着范读读出声，读完自己评一评。'
  })

  async function checkOfflinePack() {
    if (offlineBusy.value) return offlineStatus.value
    offlineStatus.value = 'checking'
    offlineNote.value = describeAsrStep('probing')
    const probe = await probeOfflinePack()
    offlineManifest = probe.manifest
    offlineModel.value = probe.manifest ? `${probe.manifest.modelId}@${probe.manifest.modelVersion}` : ''
    offlineStatus.value = probe.status
    offlineNote.value = probe.note
    if (probe.status === 'ready') offlineFault.value = false
    return offlineStatus.value
  }

  /** 家长点了才下载：显示进度，失败就退回录音档并说清为什么。 */
  async function downloadOfflinePack() {
    if (offlineBusy.value) return false
    offlineStatus.value = 'installing'
    offlineProgress.value = 0
    offlineNote.value = describeAsrStep('downloading')
    try {
      const manifest = await installOfflinePack({
        onProgress: ({ step, done, total }) => {
          offlineProgress.value = total ? Math.min(100, Math.round((done / total) * 100)) : 0
          offlineNote.value = describeAsrStep(step)
        }
      })
      offlineManifest = manifest
      offlineModel.value = `${manifest.modelId}@${manifest.modelVersion}`
      offlineStatus.value = 'ready'
      offlineFault.value = false
      offlineNote.value = describeAsrStep('ready')
      return true
    } catch (err) {
      offlineManifest = null
      offlineStatus.value = 'failed'
      offlineNote.value = `离线评测包没装上：${err.message}。这一档先不用，跟读改按「有没有大声读完」来评。`
      return false
    }
  }

  async function deleteOfflinePack() {
    await removeOfflinePack()
    offlineManifest = null
    offlineModel.value = ''
    offlineStatus.value = 'available'
    offlineNote.value = describeAsrStep('removed')
  }

  const busy = computed(() => phase.value === 'demo' || phase.value === 'recording')
  const companionReply = computed(() => companionReplyForResult(result.value))

  /* ------------------------------------------------------------ 运行时句柄 */

  let stream = null
  let audioCtx = null
  let analyser = null
  let micSource = null
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
  /** 离线档的运行时：Worker 句柄 + 采音 worklet 节点。 */
  let asrEngine = null
  let asrNode = null
  let asrMute = null
  let engineConfidence = null
  let engineModelVersion = ''

  function releaseRecording() {
    if (recordingUrl.value) URL.revokeObjectURL(recordingUrl.value)
    recordingUrl.value = ''
  }

  function disposeOfflineCapture() {
    try {
      asrNode?.port?.postMessage({ type: 'stop' })
      asrNode?.disconnect()
      asrMute?.disconnect()
    } catch {
      /* 图已经拆了 */
    }
    asrNode = null
    asrMute = null
    asrEngine?.dispose()
    asrEngine = null
  }

  /**
   * 起离线档：先确认 Worker 里的引擎真的活了，再把麦克风接到采音 worklet 上。
   * 顺序反过来的话，引擎起不来时孩子已经在对着一条不通的管子读了。
   */
  async function bootOfflineCapture() {
    if (!audioCtx || !micSource) throw new Error('这台设备没有可用的音频上下文')
    if (typeof audioCtx.audioWorklet?.addModule !== 'function') {
      throw new Error('这台设备不支持 AudioWorklet')
    }
    if (!offlineManifest) throw new Error('离线评测包清单丢了')

    const engine = createOfflineRecognizer(offlineManifest)
    await engine.ready

    await audioCtx.audioWorklet.addModule(asrAssetUrl(OFFLINE_ASR.worklet))
    const node = new AudioWorkletNode(audioCtx, 'pcm-capture')
    node.port.onmessage = (event) => {
      const { chunk, sampleRate } = event.data ?? {}
      if (!chunk) return
      engine.accept(floatToPcm16(resampleTo16k(chunk, sampleRate)))
    }
    // worklet 不发声，但图里没有终点就不会被渲染；接一个静音增益把它拉进渲染链
    const mute = audioCtx.createGain()
    mute.gain.value = 0
    micSource.connect(node)
    node.connect(mute)
    mute.connect(audioCtx.destination)

    asrEngine = engine
    asrNode = node
    asrMute = mute
    engineModelVersion = engine.modelVersion
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
    disposeOfflineCapture()
    stream?.getTracks?.().forEach((track) => track.stop())
    stream = null
    analyser = null
    micSource = null
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

  /**
   * 结算这一轮。
   *
   * 结果对象只加不改：老字段（mode/score/grade/chars/heard/note）原样保留，
   * v3 追加 source / modelVersion / confidence，好让家长中心和回归测试
   * 分得清这一分是离线引擎给的、浏览器识别给的，还是只按响度给的。
   */
  function settle(reference) {
    const usedTier = tier.value
    const heardByEngine = usedTier === 'offline-asr' || usedTier === 'recognition'
    const base = heardByEngine
      ? evaluate({ mode: 'recognition', reference, heard: heardText })
      : evaluate({ mode: 'recording', reference, sample: loudnessSample() })

    result.value = {
      ...base,
      source: sourceOfTier(usedTier),
      modelVersion: usedTier === 'offline-asr' ? engineModelVersion : '',
      confidence: usedTier === 'offline-asr' ? engineConfidence : null
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
    engineConfidence = null
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
        micSource = audioCtx.createMediaStreamSource(stream)
        micSource.connect(analyser)
        sampleTimer = setInterval(collectSample, SAMPLE_INTERVAL_MS)
      }
    } catch {
      analyser = null
      micSource = null
    }

    // 离线档：引擎起不来就当场降到录音档，孩子这一遍不白读，也不改用在线识别
    if (tier.value === 'offline-asr') {
      try {
        await bootOfflineCapture()
      } catch (err) {
        disposeOfflineCapture()
        offlineFault.value = true
        offlineStatus.value = 'failed'
        offlineNote.value = `离线评测引擎没起来：${err.message}`
        error.value = '离线评测这次没跑起来，按「有没有大声读完」来评。'
      }
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

    if (tier.value === 'recognition') {
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
    const waitTail = tier.value === 'recognition' ? 700 : 120
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

    if (asrEngine) {
      asrNode?.port?.postMessage({ type: 'stop' })
      const tail = await asrEngine.finish()
      heardText = tail.text ?? ''
      engineConfidence = tail.confidence ?? null
      // 一个字都没听出来就别硬撑：当作这一档不可用，按响度给分
      if (!normalizeTranscript(heardText)) {
        offlineFault.value = true
        error.value = '离线评测这次没听清，按「有没有大声读完」来评。'
      }
      disposeOfflineCapture()
    }

    await new Promise((r) => setTimeout(r, waitTail))

    settle(reference)
    stream?.getTracks?.().forEach((track) => track.stop())
    stream = null
    analyser = null
    micSource = null
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
      source: 'self',
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

  // 只读探测：读一次同源清单和本机缓存，不下载任何模型，也不碰麦克风。
  if (typeof window !== 'undefined') checkOfflinePack()

  return {
    phase,
    tier,
    mode,
    source,
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

    offlineStatus,
    offlineNote,
    offlineProgress,
    offlineModel,
    offlineReady,
    offlineBusy,
    offlineFault,

    playReference,
    stopReference,
    start,
    stop,
    selfAssess,
    reset,
    checkOfflinePack,
    downloadOfflinePack,
    deleteOfflinePack
  }
}
