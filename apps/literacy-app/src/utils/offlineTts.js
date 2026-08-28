/**
 * Round 12 H7：固定语料离线 TTS 试点。
 *
 * 模型与推理运行时不进入安装包；只发布经过压缩和逐条校验的语音资产。
 * 本模块只认稳定内容 ID，找不到、解码失败或自动播放被拦截时返回 false，
 * 由调用方回退到现有系统 TTS。ROUND12_H7
 */

const PUBLIC_BASE = import.meta.env?.BASE_URL ?? '/'

export const OFFLINE_TTS_PILOTS = Object.freeze({
  jingyesi: Object.freeze({
    id: 'poem:jingyesi',
    title: '静夜思离线范读试点',
    locale: 'zh-CN',
    model: 'Kokoro-82M-v1.1-zh',
    voice: 'zf_001',
    lines: Object.freeze([
      'audio/tts-pilot/jingyesi-1.ogg',
      'audio/tts-pilot/jingyesi-2.ogg',
      'audio/tts-pilot/jingyesi-3.ogg',
      'audio/tts-pilot/jingyesi-4.ogg'
    ])
  })
})

let activePlayback = null

function assetUrl(path) {
  const base = PUBLIC_BASE.endsWith('/') ? PUBLIC_BASE : `${PUBLIC_BASE}/`
  return `${base}${path.replace(/^\/+/, '')}`
}

export function getOfflineTtsPilot(contentId) {
  return OFFLINE_TTS_PILOTS[contentId] ?? null
}

export function hasOfflineTtsPilotLine(contentId, lineIndex) {
  const pilot = getOfflineTtsPilot(contentId)
  return !!pilot?.lines?.[lineIndex]
}

/** 停止当前离线范读，并让等待中的调用方收到 false。 */
export function cancelOfflineTts() {
  const current = activePlayback
  if (!current) return
  activePlayback = null
  current.audio.onended = null
  current.audio.onerror = null
  try {
    current.audio.pause()
    current.audio.currentTime = 0
  } catch {
    /* 某些 WebView 在资源尚未载入时不允许改 currentTime。 */
  }
  current.resolve(false)
}

/**
 * 播放一条随包安装的固定语料。
 * @returns {Promise<boolean>} true 表示完整播完；false 表示调用方应走系统 TTS。
 */
export function playOfflineTtsLine(contentId, lineIndex, { rate = 1, volume = 1 } = {}) {
  const relativePath = getOfflineTtsPilot(contentId)?.lines?.[lineIndex]
  const AudioCtor = globalThis.Audio
  if (!relativePath || typeof AudioCtor !== 'function') return Promise.resolve(false)

  cancelOfflineTts()

  return new Promise((resolve) => {
    const audio = new AudioCtor(assetUrl(relativePath))
    let settled = false
    const finish = (ok) => {
      if (settled) return
      settled = true
      if (activePlayback?.audio === audio) activePlayback = null
      audio.onended = null
      audio.onerror = null
      resolve(ok)
    }

    audio.preload = 'auto'
    audio.volume = Math.min(1, Math.max(0, Number(volume) || 0))
    audio.playbackRate = Math.min(1.25, Math.max(0.75, Number(rate) || 1))
    audio.onended = () => finish(true)
    audio.onerror = () => finish(false)
    activePlayback = { audio, resolve: finish }

    try {
      const started = audio.play()
      if (started?.catch) started.catch(() => finish(false))
    } catch {
      finish(false)
    }
  })
}
