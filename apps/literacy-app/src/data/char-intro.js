/**
 * 认步讲解解析层（Round 16 H2 的数据契约，见 .agent_workspace/round16-architecture.md §1）。
 *
 * 有字源的 808 字进「认」有 EtymologyStage 撑场，其余 1012 字（以及字表外的生字）
 * 之前只有一行释义。这里给每个字凑出一场**讲得出来的**认字讲解，三种模式三选一：
 *
 *   radical  部首讲解 —— 部首登场 + 同部首兄弟字，永远可用（radicals.js 查不到也能
 *            用字形本身 + 笔画数凑一块）
 *   parts    零件合体 —— 复用玩步富剧本 drag-parts 的零件序列，看零件飞入拼成字
 *   word     组词情境 —— 组词逐条弹出朗读（词条来自单元详情，由调用方透传）
 *
 * 与 getCharPlay 同一套纪律：同步、纯函数、永不返回 null；模式用字的哈希挑，
 * 同一个字同样的入参永远同一模式，孩子重进看到的还是那一场，单测也因此可断言。
 *
 * 渲染归 CharIntroStage.vue（实现岗），探针标记 ROUND16_H2 也放在那边的
 * 可执行代码里——本模块只管「讲什么」，不管「怎么演」。
 * 禁止在本模块 import Vue / DOM / GSAP：探针和单测要在 Node 里同步遍历全库。
 */

import { CHAR_INDEX } from './char-index.js'
import { getRadical } from './radicals.js'
import { hashSeed } from './char-play-templates.js'
import { getRichPlay } from './char-play-rich.js'

const INDEX_MAP = new Map(CHAR_INDEX.map((c) => [c.char, c]))

export const INTRO_MODES = ['radical', 'parts', 'word']

/**
 * 部首讲解块。任何模式下都随 CharIntro 一起返回：radical 模式拿它当主角，
 * parts / word 模式把它放在脚注（「它的部首是…」）。
 * radicals.js 的兜底条目没有 hint / meaning，这里再兜一层，保证句子不空。
 */
function radicalBlock(char, entry) {
  const rad = entry ? getRadical(entry.radical) : null
  const strokes = entry?.strokes ?? 0
  const siblings = (rad?.chars ?? [])
    .filter((c) => c !== char && INDEX_MAP.has(c))
    .slice(0, 3)
  return {
    glyph: rad?.glyph ?? char,
    name: rad?.name ?? '基本字形',
    hint:
      rad?.hint ??
      (strokes > 0 ? `「${char}」一共 ${strokes} 画，看清它的样子。` : `看清「${char}」的样子。`),
    meaning: rad?.meaning ?? '',
    siblings
  }
}

/** 玩步富剧本里 drag-parts 的零件序列；没有或太少（拼不起来）返回 null。 */
function partsOf(char) {
  const rich = getRichPlay(char)
  if (!rich || rich.template !== 'drag-parts') return null
  const parts = Array.isArray(rich.props?.parts) ? rich.props.parts.filter(Boolean) : []
  return parts.length >= 2 ? parts.slice(0, 4) : null
}

/** 调用方透传的组词，容忍字符串和 {w,p} 两种写法，最多讲 3 条。 */
function normalizeWords(words) {
  if (!Array.isArray(words)) return null
  const list = words
    .map((item) =>
      typeof item === 'string'
        ? { w: item, p: '' }
        : item && typeof item.w === 'string'
          ? { w: item.w, p: item.p ?? '' }
          : null
    )
    .filter((item) => item && item.w.trim())
    .slice(0, 3)
  return list.length > 0 ? list : null
}

/**
 * 认步讲解描述对象。形状见 round16-architecture.md §1.1 的 CharIntro typedef。
 *
 * @param {string} char
 * @param {{ words?: Array<{w: string, p?: string}|string> }} [ctx]
 *        words 传 CharDetailView 已加载的 item.words；详情没到就不传，
 *        解析器自然落到 radical / parts。组件 mount 时解析一次就冻结。
 * @returns {import('./char-intro.js').CharIntro} 永不为 null
 */
export function getCharIntro(char, { words } = {}) {
  const entry = INDEX_MAP.get(char) ?? null
  const radical = radicalBlock(char, entry)
  const parts = partsOf(char)
  const wordList = normalizeWords(words)

  const candidates = ['radical']
  if (parts) candidates.push('parts')
  if (wordList) candidates.push('word')
  const mode = candidates[hashSeed(char) % candidates.length]

  const intro = {
    char,
    mode,
    emoji: entry?.emoji ?? '✨',
    pinyin: entry?.pinyin ?? '',
    radical,
    source: 'char-intro'
  }

  if (mode === 'parts') {
    intro.parts = parts
    intro.narration = `看好啦，这几块合在一起，就变成「${char}」。`
  } else if (mode === 'word') {
    intro.words = wordList
    intro.narration = `「${char}」常常和别的字搭伙，听听这些词。`
  } else {
    intro.narration = radical.siblings.length
      ? `「${char}」带着${radical.name}，和它的兄弟字一起认。`
      : `一起看看「${char}」长什么样。${radical.hint}`
  }
  return intro
}

/**
 * 0 空洞断言（实现岗与探针自验用）：每个字都要有模式、有讲解词、
 * 模式对应的道具真的在（parts 模式必须有零件，word 模式必须有词条）。
 */
export function findIntroHoles(chars = CHAR_INDEX.map((c) => c.char)) {
  const holes = []
  for (const char of chars) {
    const intro = getCharIntro(char)
    const bad =
      !intro ||
      !INTRO_MODES.includes(intro.mode) ||
      !intro.narration ||
      !intro.radical?.glyph ||
      (intro.mode === 'parts' && !(intro.parts?.length >= 2)) ||
      (intro.mode === 'word' && !(intro.words?.length >= 1))
    if (bad) holes.push(char)
  }
  return holes
}
