/**
 * Play 层数据契约 —— 每个字进学习页先玩的那一分钟，从这里拿剧本。
 *
 * Round 15 的目标是「一字一动画」：孩子点开任意一个字，第一步不是认读，
 * 而是一段和字义相关的小互动（玩）。本模块回答一个问题：
 * 「这个字该怎么玩？」——答案是一个轻量的 CharPlay 描述对象，
 * 真正的舞台渲染（GSAP / OpenMoji）在 CharPlayStage 组件里按模板执行。
 *
 * 三层解析，优先级从高到低（详见 .agent_workspace/round15-architecture.md）：
 *
 *   1. RICH_PLAY        char-play-rich.js，人工定制脚本（≥200 条，H3）
 *   2. GENERATED_PLAY   char-play-index.js，gen-char-play.mjs 生成的补齐条目
 *   3. 运行时合成        下面的 synthesizePlay()，规则与生成器一致
 *
 * 铁律：getCharPlay() 对任何输入都不返回 null / undefined ——
 * 字表内 1820 字层层兜底（ROUND15_H2），字表外的字也给一个通用模板，
 * 调用方（CharPlayStage / 探针 / smoke）永远不用判空。
 * templateFallback: true 表示这条是自动补齐（第 2、3 层），
 * 富脚本没有这个标记；H3 只数没有该标记的条目，别造假。
 *
 * 本模块必须保持 Node 可直接 import（check-round15.mjs 会在 Node 里跑
 * 全库覆盖检查）：只 import 纯数据模块，不碰 Vue / DOM / GSAP。
 */

import { CHAR_INDEX } from './char-index.js'
import { hasEtymology } from './etymology-index.js'
import { getRadical } from './radicals.js'
import { GENERATED_PLAY } from './char-play-index.js'
import { RICH_PLAY } from './char-play-rich.js'

/**
 * @typedef {Object} CharPlay
 * @property {string} char       目标汉字
 * @property {string} theme      主题标签：number|nature|body|animal|family|action|food|object|position|abstract|general
 * @property {string} template   玩法模板 id，必须是 PLAY_TEMPLATES 的 key
 * @property {string} narration  开场引导语，孩子能听懂的一句话（TTS 播报 + 屏显字幕）
 * @property {string} emoji      主图标（OpenMoji 渲染；缺省取 char-index 的卡片图标）
 * @property {Object} [props]    模板参数，schema 见 PLAY_TEMPLATES[template].props
 * @property {boolean} [templateFallback] true = 自动补齐产物；缺省/false = 富脚本（H3 计数口径）
 * @property {('rich'|'generated'|'runtime')} [source] 这条剧本从哪层解析出来（调试 / 探针用）
 */

/**
 * 玩法模板注册表 —— CharPlayStage 按 id 动态加载对应场景实现。
 *
 * 每个模板都必须满足（引擎岗实现时的验收线）：
 *  - 可玩完：≥1 次有效交互后触发 complete，或点「跳过」直接完成
 *  - reduced-motion 下有静态可玩变体（不建 GSAP 时间线，交互照常）
 *  - 只消费 props 里声明的字段，缺字段用注册表里的 defaults 补
 *
 * props 一栏描述 schema：字段名 → 类型和含义。运行时不做严格校验
 * （生成器 gen-char-play.mjs 负责在构建期校验富脚本），但引擎对缺失
 * 字段必须按 defaults 兜底，不许抛错。
 */
export const PLAY_TEMPLATES = {
  'tap-reveal': {
    name: '点一点',
    desc: '点 N 次主图标，汉字随点击逐渐浮现',
    props: { emoji: 'string 主图标', taps: 'number 需点击次数（1–3）' },
    defaults: { taps: 3 }
  },
  'emoji-hunt': {
    name: '找一找',
    desc: '从若干图案里找出和字义相关的那个',
    props: { target: 'string 正确图标', decoys: 'string[] 干扰图标（2 个起）' },
    defaults: { decoys: [] }
  },
  'rain-catch': {
    name: '接一接',
    desc: '接住落下的目标图标/汉字，接满过关',
    props: { target: 'string 要接的图标或字', drops: 'number 需接住个数（2–4）' },
    defaults: { drops: 3 }
  },
  'sound-pop': {
    name: '听音点泡泡',
    desc: '播读音，点破写着目标字的泡泡',
    props: { rounds: 'number 轮数（1–3）', decoys: 'string[] 干扰字（可缺省由引擎取形近字）' },
    defaults: { rounds: 2, decoys: [] }
  },
  'morph-story': {
    name: '变一变',
    desc: '主图标经程序化补间渐变成汉字字形（象形叙事）',
    props: { emoji: 'string 起点图标' },
    defaults: {}
  },
  'drag-parts': {
    name: '拼一拼',
    desc: '把部件拖到一起拼出整字（会意/形声）',
    props: { parts: 'string[] 部件字形（2–3 个）', hint: 'string 部件提示语' },
    defaults: {}
  }
}

export const TEMPLATE_IDS = Object.keys(PLAY_TEMPLATES)

/** 富脚本按字索引；同字重复以先出现的为准（生成器会报告重复）。 */
const RICH_MAP = new Map()
for (const entry of RICH_PLAY) {
  if (entry?.char && !RICH_MAP.has(entry.char)) RICH_MAP.set(entry.char, entry)
}

const INDEX_MAP = new Map(CHAR_INDEX.map((c) => [c.char, c]))

/* ------------------------------------------------- 运行时合成（第 3 层兜底） */

/**
 * 部首 → 主题。生成器与运行时共用同一张表，保证两层产物一致；
 * 表外部首落到 general，由 emoji + 单元信息撑起差异化。
 */
const RADICAL_THEME = {
  shui: 'nature', shan: 'nature', ri: 'nature', yue: 'nature', huo: 'nature',
  mu: 'nature', cao: 'nature', tu: 'nature', tian: 'nature', yutou: 'nature',
  kou: 'body', shou: 'action', xin: 'abstract', yan: 'body', er: 'body',
  mubu: 'body', zu: 'body', ren: 'family', nv: 'family', renzitou: 'family',
  niu: 'animal', yang: 'animal', niao: 'animal', quan: 'animal', chong: 'animal',
  yu: 'animal', ma: 'animal', shizi: 'food', mi: 'food', yi: 'number',
  erzi: 'number', shi: 'number'
}

/** 无字源、无定向模板时的轮换池：靠字符哈希决定，冷门字也不会千篇一律。 */
const FALLBACK_POOL = ['tap-reveal', 'emoji-hunt', 'rain-catch', 'sound-pop']

const hashOf = (char) => {
  let h = 0
  for (const ch of char) h = (h * 31 + ch.codePointAt(0)) % 997
  return h
}

/** 同单元里挑两个不同 emoji 当干扰项（emoji-hunt 用）。 */
function unitDecoys(entry) {
  const out = []
  for (const c of CHAR_INDEX) {
    if (c.unit !== entry.unit || c.char === entry.char || c.emoji === entry.emoji) continue
    if (!out.includes(c.emoji)) out.push(c.emoji)
    if (out.length >= 2) break
  }
  return out.length >= 2 ? out : ['⭐', '🎈'].filter((e) => e !== entry.emoji)
}

function narrationFor(template, char, emoji) {
  switch (template) {
    case 'tap-reveal':
      return `点一点 ${emoji}，把「${char}」变出来！`
    case 'emoji-hunt':
      return `找一找，哪个图案和「${char}」是好朋友？`
    case 'rain-catch':
      return `「${char}」的朋友掉下来啦，快接住！`
    case 'sound-pop':
      return `听一听，点破写着「${char}」的泡泡！`
    case 'morph-story':
      return `看，${emoji} 慢慢变成了「${char}」！`
    case 'drag-parts':
      return `把零件拼一拼，变出「${char}」！`
    default:
      return `一起来玩「${char}」！`
  }
}

/**
 * 按既定规则给一个字合成补齐剧本。生成器（gen-char-play.mjs）必须实现
 * 完全相同的规则，这样「生成的索引」与「运行时兜底」给出的玩法一致：
 *
 *   1. 有字源（etymology-index）→ morph-story：玩里先看图变字，认里再看全套演变
 *   2. 部首命中 RADICAL_THEME → 主题化，从轮换池按 hash 取模板
 *   3. 其余 → theme 'general'，同样按 hash 从轮换池取
 *
 * 字表外的字（比如拍照识出的生僻字）也给一个通用 tap-reveal，
 * 保证任何调用路径都拿不到 null。
 */
export function synthesizePlay(char) {
  const entry = INDEX_MAP.get(char)
  if (!entry) {
    return {
      char,
      theme: 'general',
      template: 'tap-reveal',
      narration: narrationFor('tap-reveal', char, '✨'),
      emoji: '✨',
      props: { emoji: '✨', taps: 3 },
      templateFallback: true,
      source: 'runtime'
    }
  }

  const theme = RADICAL_THEME[entry.radical] ?? 'general'
  const template = hasEtymology(char)
    ? 'morph-story'
    : FALLBACK_POOL[hashOf(char) % FALLBACK_POOL.length]

  const props =
    template === 'tap-reveal'
      ? { emoji: entry.emoji, taps: 2 + (hashOf(char) % 2) }
      : template === 'emoji-hunt'
        ? { target: entry.emoji, decoys: unitDecoys(entry) }
        : template === 'rain-catch'
          ? { target: entry.emoji, drops: 3 }
          : template === 'sound-pop'
            ? { rounds: 2 }
            : { emoji: entry.emoji }

  return {
    char,
    theme,
    template,
    narration: narrationFor(template, char, entry.emoji),
    emoji: entry.emoji,
    props,
    templateFallback: true,
    source: 'runtime'
  }
}

/* ----------------------------------------------------------------- 解析入口 */

/** 补上缺省字段，保证下游拿到的对象形状总是完整的。 */
function normalize(entry, source, fallback) {
  const emoji = entry.emoji ?? entry.props?.emoji ?? INDEX_MAP.get(entry.char)?.emoji ?? '✨'
  return {
    char: entry.char,
    theme: entry.theme ?? 'general',
    template: TEMPLATE_IDS.includes(entry.template) ? entry.template : 'tap-reveal',
    narration: entry.narration || narrationFor(entry.template, entry.char, emoji),
    emoji,
    props: { ...(PLAY_TEMPLATES[entry.template]?.defaults ?? {}), ...(entry.props ?? {}) },
    ...(fallback ? { templateFallback: true } : {}),
    source
  }
}

/**
 * 取一个字的玩法剧本。同步、纯函数、永不返回 null（ROUND15_H2）。
 * @param {string} char
 * @returns {CharPlay}
 */
export function getCharPlay(char) {
  const rich = RICH_MAP.get(char)
  if (rich) return normalize(rich, 'rich', false)
  const gen = GENERATED_PLAY[char]
  if (gen) return normalize(gen, 'generated', true)
  return synthesizePlay(char)
}

/** 富脚本条数（H3 计数口径：不带 templateFallback 的定制脚本）。 */
export function countRichPlays() {
  return RICH_MAP.size
}

export { RICH_PLAY }
