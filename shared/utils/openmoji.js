/**
 * OpenMoji 图标解析 —— 两 App 共用。
 * SVG 由 Vite ?url 导入，随 dist 打包并进入 Service Worker 预缓存。
 */

const modules = import.meta.glob('../assets/openmoji/*.svg', {
  eager: true,
  query: '?url',
  import: 'default',
})

/** 界面里仍在用的 emoji → shared/assets/openmoji 文件名（不含 .svg） */
export const EMOJI_TO_OPENMOJI = {
  '🏡': 'house',
  '✏️': 'pencil',
  '👂': 'ear',
  '📚': 'books',
  '📖': 'open-book',
  '📘': 'green-book',
  '🏮': 'lantern',
  '🎧': 'headphones',
  '🧩': 'puzzle-piece',
  '🎭': 'performing-arts',
  '👨‍👩‍👧': 'family',
  '🔒': 'locked',
  '🏆': 'trophy',
  '🌱': 'seedling',
  '✨': 'sparkles',
  '⭐': 'star',
  '🚀': 'rocket',
  '🎯': 'target',
  '🔥': 'fire',
  '🈶': 'japanese-beginner',
  '🗺️': 'world-map',
  '🪐': 'ringed-planet',
  '☀️': 'sun',
  '🛰️': 'satellite',
  '🌀': 'cyclone',
  '🌍': 'globe',
  '🎉': 'party',
  '🏅': 'medal',
  '🔁': 'repeat',
  '🔊': 'speaker',
  '💡': 'light-bulb',
  '🍎': 'apple',
  '🔢': 'numbers',
  '🧮': 'abacus',
  '🗣️': 'microphone',
  '🎤': 'microphone',
  '📜': 'scroll',
}

export const OPENMOJI_ATTRIBUTION =
  '界面图标来自 OpenMoji（https://openmoji.org/），许可：CC BY-SA 4.0。'

/** @param {string} name 不含扩展名的文件名，如 "star" */
export function openMojiUrl(name) {
  if (!name) return null
  return modules[`../assets/openmoji/${name}.svg`] ?? null
}

/** @param {string} [emoji] */
export function resolveOpenMojiName(emoji) {
  if (!emoji) return null
  return EMOJI_TO_OPENMOJI[emoji] ?? null
}

/** @param {{ name?: string, emoji?: string }} opts */
export function resolveIcon(opts) {
  return opts.name || resolveOpenMojiName(opts.emoji)
}

export const OPENMOJI_ICON_NAMES = Object.keys(modules).map((k) =>
  k.replace('../assets/openmoji/', '').replace('.svg', ''),
)
