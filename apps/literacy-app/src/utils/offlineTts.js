/**
 * Round 12 H7：固定语料离线 TTS 试点。
 * Round 14 H5：首单元字卡离线朗读批次。
 *
 * 模型与推理运行时不进入安装包；只发布经过压缩和逐条校验的语音资产。
 * 本模块只认稳定内容 ID，找不到、解码失败或自动播放被拦截时返回 false，
 * 由调用方回退到现有系统 TTS。ROUND12_H7 ROUND14_H5
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

const l1Card = (id, character, sentence) =>
  Object.freeze({
    id: `char:u1:${id}`,
    unit: 'u1',
    character: `audio/tts-l1/${character}`,
    sentence: `audio/tts-l1/${sentence}`
  })

/**
 * 首单元「我和数字」12 张字卡，每张包含单字和例句两份音频。
 * key 直接使用课程字表里的汉字，避免显示文案与音频另维护一套 ID。
 */
export const OFFLINE_TTS_L1 = Object.freeze({
  '一': l1Card('一', 'u1-01-yi-char.ogg', 'u1-01-yi-sentence.ogg'),
  '二': l1Card('二', 'u1-02-er-char.ogg', 'u1-02-er-sentence.ogg'),
  '三': l1Card('三', 'u1-03-san-char.ogg', 'u1-03-san-sentence.ogg'),
  '上': l1Card('上', 'u1-04-shang-char.ogg', 'u1-04-shang-sentence.ogg'),
  '下': l1Card('下', 'u1-05-xia-char.ogg', 'u1-05-xia-sentence.ogg'),
  '人': l1Card('人', 'u1-06-ren-char.ogg', 'u1-06-ren-sentence.ogg'),
  '口': l1Card('口', 'u1-07-kou-char.ogg', 'u1-07-kou-sentence.ogg'),
  '大': l1Card('大', 'u1-08-da-char.ogg', 'u1-08-da-sentence.ogg'),
  '小': l1Card('小', 'u1-09-xiao-char.ogg', 'u1-09-xiao-sentence.ogg'),
  '我': l1Card('我', 'u1-10-wo-char.ogg', 'u1-10-wo-sentence.ogg'),
  '个': l1Card('个', 'u1-11-ge-char.ogg', 'u1-11-ge-sentence.ogg'),
  '们': l1Card('们', 'u1-12-men-char.ogg', 'u1-12-men-sentence.ogg')
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

export function getOfflineTtsL1Card(char) {
  return OFFLINE_TTS_L1[char] ?? null
}

export function hasOfflineTtsL1Card(char) {
  const card = getOfflineTtsL1Card(char)
  return !!(card?.character && card?.sentence)
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

function playOfflineAsset(relativePath, { rate = 1, volume = 1 } = {}) {
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

/**
 * 播放一条随包安装的固定语料。
 * @returns {Promise<boolean>} true 表示完整播完；false 表示调用方应走系统 TTS。
 */
export function playOfflineTtsLine(contentId, lineIndex, options = {}) {
  return playOfflineAsset(getOfflineTtsPilot(contentId)?.lines?.[lineIndex], options)
}

/**
 * 播放首单元字卡的单字或例句，未知字/类型立即返回 false。
 * @param {string} char
 * @param {'character'|'sentence'} kind
 */
export function playOfflineTtsL1(char, kind = 'character', options = {}) {
  const relativePath = getOfflineTtsL1Card(char)?.[kind]
  return playOfflineAsset(relativePath, options)
}
