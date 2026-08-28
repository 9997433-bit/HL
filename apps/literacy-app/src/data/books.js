/**
 * 分级绘本。
 *
 * 硬性约束：正文只允许使用 characters.js 里已收录的汉字 + 标点。
 * `verifyBookCoverage()` 会在 dev 模式下逐字校验，越界的字会在控制台报警，
 * 这样以后加新绘本时不会不小心用到孩子还没学过的字。
 *
 * 分级的意思是句子长度和情节复杂度，不是「新字数量」：
 * 第 1 级一句一行、第 2 级出现对话、第 3 级有完整的一天、
 * 第 4 级开始有起承转合、第 5 级是多角色的故事、第 6 级接近小小章节书。
 *
 * 书目分两摞：
 *   books/core.js        最早手写的 30 本，注音逐句校过，是语感基准；
 *   books/extended.js    批量扩充的那一百多本，由 scripts/gen-books.mjs
 *                        从 scripts/data/book-seed-*.mjs 生成，注音也是算出来的。
 * 两摞的字段完全一致，读者侧感知不到区别。
 *
 * 首页和进度 store 只需要「一共几本」，别从这里 import——正文会跟着进主包，
 * 那两处用 book-index.js。
 *
 * 页面插图有两档（ROUND11_H4）：老的一档是一页一个大 emoji，新的一档是
 * 下面这套场景 DSL——一页摆几件东西，各有位置、大小和一点轻微的动。
 * 两档并存，没写 `scene` 的页照旧显示 `emoji`，扩充绘本不必一次性全改。
 *
 * ROUND12_H3 把场景从 3 本样板铺到读得最多的 17 本，ROUND13_H3 再推到 33 本；
 * 剩下 99 本仍走单 emoji，那条退化路径是硬要求，不是过渡态——
 * 绘本会一直往下加，新书进来时先有兜底。
 * 扩充绘本（books/l*.js）是生成的，它们的场景写在
 * scripts/data/book-scene-seed.mjs，手写的 30 本直接写在 books/core.js。
 */

import { CHARACTER_MAP } from './characters.js'
import { CORE_BOOKS } from './books/core.js'
import { EXTENDED_BOOKS } from './books/extended.js'

const PUNCTUATION = new Set([
  '，', '。', '！', '？', '：', '、', '；', '「', '」', '《', '》', '…', '—', ' ', '\n'
])

/* --------------------------------------------------------- 页级场景 DSL
 *
 * 一页一个 emoji 说不清「谁在哪儿、发生了什么」。场景把一页摆成几件东西：
 *
 *   {
 *     emoji: '🌅',                     没有场景的旧路径仍然用它
 *     text: '天上有日，天上有月。',
 *     p: 'tiān shàng yǒu rì, tiān shàng yǒu yuè.',
 *     sceneBg: 'dawn',                 背景预设，缺省用绘本自己的 palette
 *     sceneAlt: '天上有日，也有月',      读屏念的一句话，同样受用字约束
 *     scene: [
 *       { e: '☀️', x: 72, y: 24, s: 1.3, m: 'float' },
 *       { e: '⛰️', x: 34, y: 80, s: 1.8 }
 *     ]
 *   }
 *
 * 字段名短是为了体积：一页场景压出来一百来字节，二十页也就 2 KB 上下，
 * 而且 books.js 只在绘本路由里按需加载，首屏预算不受影响。
 *   e   一个图形（不许放汉字——要给孩子读的字都在正文里）
 *   x/y 舞台内的百分比坐标，0–100；y 越大越靠近读者，用来排前后
 *   s   相对大小，0.4–3，缺省 1
 *   m   轻微动效：float 上下浮 / sway 左右摆 / drift 缓慢横移 / still 不动
 */

/** 背景预设：id → [上方色, 下方色]。放在数据层，校验和组件共用同一份。 */
export const SCENE_BACKDROPS = new Map([
  ['dawn', ['#ffe7bd', '#ffd0c4']],
  ['sky', ['#cfe8ff', '#eaf7ff']],
  ['water', ['#bfe6f5', '#dff5e6']],
  ['field', ['#e6f5c9', '#fff3d0']],
  ['storm', ['#c3ccdd', '#a7b6cc']],
  ['dusk', ['#ffd6c2', '#d7c6f0']],
  ['night', ['#54618a', '#8a95b8']],
  ['snow', ['#e8f1fa', '#ffffff']],
  ['room', ['#ffeede', '#f6e3ff']]
])

export const SCENE_MOTIONS = new Set(['float', 'sway', 'drift', 'still'])

/** 一页最多摆几件东西。再多就挤成一团，孩子找不到主角。 */
export const SCENE_ITEM_LIMIT = 6

/** 这一页升级成场景了没有。 */
export function hasScene(page) {
  return Array.isArray(page?.scene) && page.scene.length > 0
}

/** 整本书里升级成场景的那些页。 */
export function scenePages(book) {
  return (book?.pages ?? []).filter(hasScene)
}

/** 书架按分级排，同级内保持「先手写、后扩充」的原始顺序。 */
export const BOOKS = [...CORE_BOOKS, ...EXTENDED_BOOKS].sort((a, b) => a.level - b.level)

export const BOOK_MAP = new Map(BOOKS.map((b) => [b.id, b]))

export function getBook(id) {
  return BOOK_MAP.get(id) || null
}

/** 绘本里出现的所有生字（去重、保持出现顺序）。 */
export function charsInBook(book) {
  const seen = []
  const set = new Set()
  for (const page of book.pages) {
    for (const ch of page.text) {
      if (PUNCTUATION.has(ch) || set.has(ch)) continue
      set.add(ch)
      seen.push(ch)
    }
  }
  return seen
}

/** 开发期自检：绘本用到的字必须都在语料库里。 */
export function verifyBookCoverage() {
  const problems = []
  for (const book of BOOKS) {
    const missing = charsInBook(book).filter((ch) => !CHARACTER_MAP.has(ch))
    if (missing.length) problems.push({ book: book.title, missing })
  }
  return problems
}

/** 已经用上场景的绘本 id，按书架顺序。 */
export const SCENE_BOOK_IDS = BOOKS.filter((b) => scenePages(b).length).map((b) => b.id)

export const TOTAL_SCENE_PAGES = BOOKS.reduce((n, b) => n + scenePages(b).length, 0)

/**
 * ROUND12_H3 铺开台账。
 *
 * 数字是手写的，不是从上面那两行算出来的——算出来的数永远等于自己，
 * 挡不住任何事。写死一份，让 `check:data` 拿它跟实际数据对：
 * 谁把一本书的 `scene` 删了、谁生成器跑歪了少写一页，都会在这里炸出来，
 * 而不是等到有人翻到那一页才发现插图退回了单 emoji。
 *
 * 铺的是「读得最多的那一摞」：L1 前 15 本（含 R11 的样板 b1）整本升级，
 * 加上 R11 已升的 b10（L2）和 b14（L3），三个分级各有实例。
 */
export const ROUND12_H3 = Object.freeze({
  /** 硬门槛，见 .agent_workspace/ROUND12-ACCEPTANCE.md。 */
  target: 60,
  books: 17,
  pages: 105
})

/**
 * ROUND13_H3 终局台账。
 *
 * R12 那份留着不动：它记的是「铺开那一轮铺到了哪儿」，改掉就没人知道
 * 105 页是从哪来的了。当期台账是这一份，`check:data` 对的是它，
 * 同时拿 R12 的数当地板——场景只能往上加，退回去就是有人把书吃了。
 *
 * 33 本的选法接着 R12 的思路走「整级铺满」：L1 扩充绘本 bx1–bx20 补齐，
 * L2 从 bx21 起接上前六本。同一分级里一半有场景一半没有，孩子翻到后半摞
 * 会以为书坏了；按级推进至少让「这一级都是这样」成立。
 */
export const ROUND13_H3 = Object.freeze({
  /** 硬门槛，见 .agent_workspace/ROUND13-BRIEF.md H3。 */
  target: 200,
  books: 33,
  pages: 209
})

/** 场景旁白里出现的所有汉字（去重）。 */
export function charsInScenes(book) {
  const set = new Set()
  for (const page of scenePages(book)) {
    for (const ch of page.sceneAlt ?? '') {
      if (!PUNCTUATION.has(ch)) set.add(ch)
    }
  }
  return [...set]
}

const inRange = (v, lo, hi) => typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi
/** 图形位上放汉字就成了「画里写字」：孩子会去读它，而它不受用字约束。 */
const hasHan = (s) => /\p{Script=Han}/u.test(s)

/**
 * 开发期自检：场景摆得出来吗。
 *
 * 坐标越界不会报错，只会让那件东西飘到画框外——静态数据错得越安静越难发现，
 * 所以这些约束得在内容自检里挡住，而不是等谁在真机上看见半只小鸟。
 */
export function verifyScenes() {
  const problems = []
  for (const book of BOOKS) {
    const bad = []
    for (const [index, page] of (book.pages ?? []).entries()) {
      if (page.scene === undefined) continue
      const at = `p${index + 1}`
      if (!Array.isArray(page.scene) || !page.scene.length) {
        bad.push(`${at} 场景不是元素数组`)
        continue
      }
      // 单元素场景不如直接用 emoji：DSL 的意义就是「一页不止一件东西」。
      if (page.scene.length < 2) bad.push(`${at} 只摆了 1 件元素`)
      if (page.scene.length > SCENE_ITEM_LIMIT) {
        bad.push(`${at} 元素 ${page.scene.length} 件超过上限 ${SCENE_ITEM_LIMIT}`)
      }
      if (page.sceneBg && !SCENE_BACKDROPS.has(page.sceneBg)) {
        bad.push(`${at} 背景预设 ${page.sceneBg} 不存在`)
      }
      if (!page.sceneAlt) bad.push(`${at} 缺少读屏旁白`)
      else if (!hasHan(page.sceneAlt)) bad.push(`${at} 旁白不是中文`)
      // 兜底插图不能因为升级场景就丢：书架和不支持场景的旧入口还在用它。
      if (!page.emoji) bad.push(`${at} 丢了兜底 emoji`)
      for (const [i, item] of page.scene.entries()) {
        const where = `${at}#${i + 1}`
        if (!item || typeof item !== 'object') {
          bad.push(`${where} 不是元素对象`)
          continue
        }
        if (!item.e) bad.push(`${where} 没有图形`)
        else if (hasHan(item.e)) bad.push(`${where} 图形位放了汉字「${item.e}」`)
        if (!inRange(item.x, 0, 100) || !inRange(item.y, 0, 100)) {
          bad.push(`${where} 坐标 (${item.x}, ${item.y}) 不在画框内`)
        }
        if (item.s !== undefined && !inRange(item.s, 0.4, 3)) {
          bad.push(`${where} 大小 ${item.s} 越界`)
        }
        if (item.m !== undefined && !SCENE_MOTIONS.has(item.m)) {
          bad.push(`${where} 动效 ${item.m} 不认识`)
        }
      }
    }
    if (bad.length) problems.push({ book: book.title, bad })
  }
  return problems
}

/**
 * 开发期自检：场景旁白也归「用字零越界」管。
 * 旁白只念给读屏听，但它同样是绘本内容，越界就说明这本书悄悄超纲了。
 */
export function verifySceneCoverage() {
  const problems = []
  for (const book of BOOKS) {
    const missing = charsInScenes(book).filter((ch) => !CHARACTER_MAP.has(ch))
    if (missing.length) problems.push({ book: book.title, missing })
  }
  return problems
}
