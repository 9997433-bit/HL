/**
 * 一字一玩法 —— 「玩」这一步的解析层（ROUND15_H2）。
 *
 * 洪恩的「玩」是一字一美术脚本，覆盖不到的字就没有。我们要的是 1820 个字
 * 同一密度，所以剧本从三处来，这里负责合成一份舞台真的能渲染的东西：
 *
 *   1. 富脚本   char-play-rich.js —— 人手写的剧本（雨接雨滴、火添柴），最优先
 *   2. 自动补齐 char-play-generated.js + char-play-templates.js —— 生成器按
 *               部首 / 主题 / 字源 / 组词给每个字配的一场，标 templateFallback
 *   3. 兜底合成 下面的 emergencyPlay() —— 字表外的生字、上面两层都读不到时用，
 *               只靠字表图标和主题池，也一定凑得出一关
 *
 * 三处的剧本是三套方言：富脚本写 `{hero, items, goal}`，生成器写
 * `{options, rounds}` / `{whole, slots, pieces}`，模板 id 加起来二十多个。
 * 舞台不该认识这么多方言，所以这里把它们**归一到六种渲染器**（kind）：
 *
 *   pick      从几个选项里点中对的
 *   catch     一堆东西里点够次数（会掉下来的也算，减少动态时就不掉）
 *   assemble  把零件放回位置
 *   watch     一帧一帧看完，点一下推进一帧
 *   match     左边一个右边一个，配成一对
 *   push      顺着一个方向推 / 拉 / 举
 *
 * 认识的模板照表映射，不认识的按作者标的 interaction 归类，再不行就归到
 * catch——**永远不返回 null，也永远不给舞台一份它读不懂的道具**。
 * 归一后的道具形状见下面各 stageXxx() 的返回值，CharPlayStage 只认这一份。
 *
 * 归一是纯函数：同一个字每次算出来的选项、乱序、落点都一样（字的哈希做种子），
 * 孩子重进看到的还是那一关，单测也因此可断言。
 */

import { CHAR_INDEX } from './char-index.js'
import { UNITS } from './unit-index.js'
import { getRadical } from './radicals.js'
import { PLAY_ROWS } from './char-play-generated.js'
import {
  buildPlay as buildTemplatePlay,
  templateForChar,
  themeForChar
} from './char-play-templates.js'
import * as richModule from './char-play-rich.js'

/* ------------------------------------------------------------------ 渲染器 */

/** 舞台实现的六种互动。模板再多，最后都落到这六种之一。 */
export const PLAY_KINDS = ['pick', 'catch', 'assemble', 'watch', 'match', 'push']

/**
 * 模板 id → 渲染器。三套方言的模板都在这里登记：
 * 上排是生成器（char-play-templates.js），中排是富脚本（char-play-rich.js），
 * 下排是本模块兜底用的。没登记的模板按 interaction 归类，见 INTERACTION_KIND。
 */
const TEMPLATE_KIND = {
  'emoji-hunt': 'pick',
  'scene-tap': 'pick',
  'tap-reveal': 'pick',
  'pair-match': 'pick',
  'sound-echo': 'pick',
  'sound-pop': 'pick',
  'rain-catch': 'catch',
  'count-tap': 'catch',
  'pop-bubbles': 'catch',
  'scene-poke': 'catch',
  'color-fill': 'catch',
  'sound-tap': 'catch',
  'drag-parts': 'assemble',
  'word-build': 'assemble',
  'morph-story': 'watch',
  'mirror-move': 'watch',
  'grow-tap': 'watch',
  'sort-buckets': 'match',
  'swipe-motion': 'push',
  'trace-path': 'push'
}

/** 作者只标了 interaction（没登记模板）时按这张表归类。 */
const INTERACTION_KIND = {
  pick: 'pick',
  catch: 'catch',
  assemble: 'assemble',
  watch: 'watch',
  tap: 'catch',
  drag: 'assemble',
  swipe: 'push',
  sequence: 'watch'
}

/** 舞台角上那个小标签。念给孩子听的是 narration，这里只是玩法的名字。 */
const TEMPLATE_LABEL = {
  'emoji-hunt': '找一找',
  'scene-tap': '点一点',
  'tap-reveal': '揭一揭',
  'pair-match': '连一连',
  'sound-echo': '听音点',
  'sound-pop': '点泡泡',
  'rain-catch': '接一接',
  'count-tap': '数一数',
  'pop-bubbles': '戳一戳',
  'scene-poke': '找场景',
  'color-fill': '涂一涂',
  'sound-tap': '响一响',
  'drag-parts': '拼一拼',
  'word-build': '补词语',
  'morph-story': '变一变',
  'mirror-move': '跟着做',
  'grow-tap': '长一长',
  'sort-buckets': '分一分',
  'swipe-motion': '划一划',
  'trace-path': '带一带'
}

export const PLAY_TEMPLATES = Object.fromEntries(
  Object.entries(TEMPLATE_KIND).map(([id, kind]) => [
    id,
    { id, kind, label: TEMPLATE_LABEL[id] ?? '玩一玩' }
  ])
)

export const PLAY_TEMPLATE_IDS = Object.keys(PLAY_TEMPLATES)

export function getPlayTemplate(id) {
  return PLAY_TEMPLATES[id] ?? { id: id || 'tap-reveal', kind: 'catch', label: '玩一玩' }
}

/**
 * 主题配色。两套主题表（生成器的 plant/hand/…、富脚本的 nature/number/…）
 * 的 id 都收在这里，认不出来就用品牌色——配色错不了大事，空着才难看。
 */
const THEME_ACCENT = {
  number: 'var(--mango-500)',
  plant: 'var(--leaf-500)',
  nature: 'var(--leaf-500)',
  earth: 'var(--leaf-700)',
  water: 'var(--sky-500)',
  weather: 'var(--sky-400)',
  sky: 'var(--sky-400)',
  animal: 'var(--mint-500)',
  body: 'var(--coral-400)',
  hand: 'var(--coral-400)',
  mouth: 'var(--coral-500)',
  person: 'var(--coral-500)',
  family: 'var(--coral-500)',
  feeling: 'var(--grape-400)',
  heart: 'var(--grape-400)',
  word: 'var(--grape-500)',
  speech: 'var(--grape-500)',
  school: 'var(--grape-500)',
  time: 'var(--sky-700)',
  place: 'var(--mango-500)',
  travel: 'var(--sky-500)',
  food: 'var(--coral-500)',
  cloth: 'var(--mint-500)',
  color: 'var(--star-500)',
  shape: 'var(--star-500)',
  object: 'var(--star-500)',
  tool: 'var(--star-500)',
  action: 'var(--mango-400)'
}

const accentOf = (theme) => THEME_ACCENT[theme] ?? 'var(--brand)'

/* -------------------------------------------------------------- 确定性随机 */

/** FNV-1a：同一个字（加不同 salt）永远得到同一串数，玩法才不会每次刷新换脸。 */
function hashOf(text, salt = 0) {
  let h = (2166136261 ^ salt) >>> 0
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619) >>> 0
  }
  return h >>> 0
}

/** xorshift32：只要种子一样，取数序列就一样。 */
function rngOf(seed) {
  let s = seed >>> 0 || 0x9e3779b9
  return () => {
    s ^= s << 13
    s >>>= 0
    s ^= s >>> 17
    s ^= s << 5
    s >>>= 0
    return s / 0x100000000
  }
}

function shuffled(list, rand) {
  const out = [...list]
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))

/* ------------------------------------------------------------ 字表侧的信息 */

const CHAR_MAP = new Map(CHAR_INDEX.map((c) => [c.char, c]))
const UNIT_MAP = new Map(UNITS.map((u) => [u.id, u]))

/** 同单元的同学，生成器拿它出干扰项。按笔画接近排在前面。 */
let unitSiblings = null
function siblingsOf(entry) {
  if (!entry) return []
  if (!unitSiblings) {
    unitSiblings = new Map()
    for (const c of CHAR_INDEX) {
      const bucket = unitSiblings.get(c.unit) ?? []
      bucket.push(c)
      unitSiblings.set(c.unit, bucket)
    }
  }
  return (unitSiblings.get(entry.unit) ?? [])
    .filter((c) => c.char !== entry.char)
    .map((c) => ({
      char: c.char,
      emoji: c.emoji,
      pinyin: c.pinyin,
      strokes: c.strokes,
      radicalGlyph: getRadical(c.radical)?.glyph ?? ''
    }))
}

/** 同单元的字图标；兜底合成拿它当道具，主题才对得上。 */
let unitIcons = null
function iconsOfUnit(unitId) {
  if (!unitIcons) {
    unitIcons = new Map()
    for (const c of CHAR_INDEX) {
      if (!c.emoji) continue
      const bucket = unitIcons.get(c.unit) ?? []
      bucket.push([c.emoji, `「${c.char}」`])
      unitIcons.set(c.unit, bucket)
    }
  }
  return unitIcons.get(unitId) ?? []
}

/** 补词语要的干扰字：同单元的同学优先，不够就借几个最常见的。 */
function decoyChars(ctx, n, rand) {
  const seen = new Set([ctx.char])
  const out = []
  const push = (char) => {
    if (out.length >= n || !char || seen.has(char)) return
    seen.add(char)
    out.push(char)
  }
  for (const mate of shuffled(siblingsOf(ctx.entry), rand)) push(mate.char)
  for (const char of ['人', '大', '小', '口', '手', '日']) push(char)
  return out
}

/** 任何字都凑得出来的一池小道具，同单元不够时补上。 */
const SPARE_ICONS = [
  ['⭐', '星星'],
  ['🎈', '气球'],
  ['🎁', '礼物'],
  ['🧩', '拼图'],
  ['🎵', '音乐'],
  ['🌈', '彩虹'],
  ['🍎', '苹果'],
  ['🐱', '小猫']
]

function contextOf(char) {
  const entry = CHAR_MAP.get(char) ?? null
  const radical = entry?.radical ? getRadical(entry.radical) : null
  const unit = entry?.unit ? UNIT_MAP.get(entry.unit) : null
  return {
    char,
    entry,
    emoji: entry?.emoji || '✨',
    pinyin: entry?.pinyin ?? '',
    strokes: entry?.strokes ?? 0,
    radicalGlyph: radical?.glyph ?? '',
    radicalName: radical?.name ?? '',
    unit: entry?.unit ?? '',
    unitName: unit?.name ?? '',
    icons: entry?.unit ? iconsOfUnit(entry.unit) : []
  }
}

/** 取 n 个「和这个字是一路」的图标，不含字自己的图标，不重样。 */
function companions(ctx, n, rand) {
  const seen = new Set([ctx.emoji])
  const out = []
  const push = ([emoji, label]) => {
    if (out.length >= n || !emoji || seen.has(emoji)) return
    seen.add(emoji)
    out.push({ emoji, label })
  }
  for (const item of shuffled(ctx.icons, rand)) push(item)
  for (const item of SPARE_ICONS) push(item)
  return out
}

/* ------------------------------------------------------- 第 2 层：自动补齐 */

/**
 * 生成物是一行行紧凑的文本（`字|主题|模板|线索|额外料`），
 * 展开成道具的规则在 char-play-templates.js 里。第一次用到时才解析，
 * 解析出来的是「这个字玩什么」，不是整份道具，1820 行也就几毫秒。
 */
let generatedRows = null
function rowOf(char) {
  if (!generatedRows) {
    generatedRows = new Map()
    for (const line of String(PLAY_ROWS ?? '').split('\n')) {
      const text = line.trim()
      if (!text || text.startsWith('#')) continue
      const [c, theme, template, hint, extraText] = text.split('|')
      if (!c) continue
      const extra = {}
      for (const pair of (extraText ?? '').split(';')) {
        const [k, v] = pair.split('=')
        if (!k || v === undefined) continue
        extra[k.trim()] = k.trim() === 'parts' ? v.split(',').filter(Boolean) : v.trim()
      }
      generatedRows.set(c, { char: c, theme, template, hint: hint ?? '', extra })
    }
  }
  return generatedRows.get(char) ?? null
}

function infoOf(ctx) {
  return {
    emoji: ctx.emoji,
    pinyin: ctx.pinyin,
    strokes: ctx.strokes,
    radicalGlyph: ctx.radicalGlyph,
    radicalName: ctx.radicalName,
    unit: ctx.unit,
    unitName: ctx.unitName,
    siblings: siblingsOf(ctx.entry)
  }
}

/** 字表里没有的字也走生成器：主题、模板照同一套规则挑，只是没有课文线索。 */
function generatedPlay(ctx) {
  const row = rowOf(ctx.char)
  if (row) return buildTemplatePlay(row, infoOf(ctx), { source: 'generated', templateFallback: true })

  // 字表外的字（绘本 / 搜索 / 拍照认出来的生字）没有拼音也没有同学，
  // 挑模板时避开要念音、要组词那几种，直接用「找一找」——它只要一个图标就成关
  const theme = themeForChar({ radical: ctx.entry?.radical, unitName: ctx.unitName })
  const template = ctx.entry
    ? templateForChar({ char: ctx.char, theme, extra: {} })
    : 'emoji-hunt'
  return buildTemplatePlay(
    { char: ctx.char, theme, template, hint: '', extra: {} },
    infoOf(ctx),
    { source: 'runtime', templateFallback: true }
  )
}

/* --------------------------------------------------------- 第 3 层：兜底 */

/**
 * 上面两层都不灵（生成物被清空、模板表报错）时的最后一手：
 * 拿字表图标和同单元的小伙伴摆一桌卡片，点完就算玩过。
 * 它不好玩，但它一定玩得成——这一层存在的意义就是「绝不空场」。
 */
function emergencyPlay(ctx) {
  const rand = rngOf(hashOf(ctx.char, 17))
  const mates = companions(ctx, 3, rand)
  const drops = shuffled(
    [
      { key: 'c0', emoji: ctx.emoji, label: `「${ctx.char}」的图`, hit: true },
      ...mates.map((m, i) => ({ key: `c${i + 1}`, emoji: m.emoji, label: m.label, hit: true }))
    ],
    rand
  )
  return {
    char: ctx.char,
    theme: 'word',
    template: 'scene-poke',
    interaction: 'tap',
    emoji: ctx.emoji,
    narration: `和「${ctx.char}」有关的东西都在这儿，一个一个点点看。`,
    prompt: `点满 ${drops.length} 个`,
    props: { drops, rounds: drops.length },
    templateFallback: true,
    source: 'emergency'
  }
}

/* ------------------------------------------------------------ 富脚本注册表 */

/** char → 人手写的剧本。 */
const RICH = new Map()

function looksLikePlay(value) {
  return (
    Boolean(value) &&
    typeof value === 'object' &&
    (typeof value.template === 'string' || typeof value.narration === 'string')
  )
}

/**
 * 注册一批富脚本。数组、`{ 汉字: 条目 }` 映射都收，
 * 条目缺什么字段（模板、旁白、道具）取用时由归一层补，不必写全。
 *
 * @returns {number} 这一批真正登记进去的条数
 */
export function registerCharPlays(source) {
  let added = 0
  const take = (entry, key) => {
    if (!looksLikePlay(entry)) return
    const char = typeof entry.char === 'string' && entry.char ? entry.char : key
    if (typeof char !== 'string' || !char) return
    RICH.set(char, { ...entry, char })
    added += 1
  }
  if (Array.isArray(source)) {
    for (const entry of source) take(entry)
  } else if (source && typeof source === 'object') {
    for (const [key, entry] of Object.entries(source)) take(entry, key)
  }
  return added
}

/**
 * char-play-rich.js 里叫什么名字都行：只要导出的是「条目数组」或
 * 「汉字 → 条目」的映射就会被收进来。富脚本那一岗换了导出名也不至于整块失联。
 */
for (const value of Object.values(richModule ?? {})) {
  if (Array.isArray(value)) {
    registerCharPlays(value.filter(looksLikePlay))
  } else if (value && typeof value === 'object' && !(value instanceof Map)) {
    const map = {}
    for (const [key, entry] of Object.entries(value)) {
      if (looksLikePlay(entry)) map[key] = entry
    }
    registerCharPlays(map)
  }
}

export function hasRichPlay(char) {
  return RICH.has(char)
}

/** H3 探针口径：人手写的剧本有多少条（自动补齐的不算）。 */
export function countRichPlays() {
  return RICH.size
}

export function listRichPlays() {
  return [...RICH.values()]
}

/* ------------------------------------------------------------------ 归一 */

/** 一个字符串是不是图标（没有汉字 / 拉丁字母，就当它是 emoji）。 */
const isGlyphText = (text) => typeof text === 'string' && /[\u3400-\u9fff\uf900-\ufaffA-Za-z]/.test(text)

/** 作者可能把图标写在 emoji / label / char 任一处，这里统一拆成「图标 + 字」。 */
function faceOf(raw, fallbackEmoji = '') {
  if (typeof raw === 'string') {
    return isGlyphText(raw) ? { glyph: raw, emoji: '' } : { glyph: '', emoji: raw }
  }
  const glyph = raw?.glyph ?? raw?.char ?? (isGlyphText(raw?.label) ? raw.label : '')
  const emoji = raw?.emoji ?? (!isGlyphText(raw?.label) ? raw?.label : '') ?? ''
  if (!glyph && !emoji) return { glyph: '', emoji: fallbackEmoji }
  return { glyph: glyph || '', emoji: emoji || '' }
}

const labelOf = (raw, face, fallback) =>
  (typeof raw === 'object' && raw?.name) || face.glyph || face.emoji || fallback || ''

/* --- pick：从几个选项里点中对的 --- */

function stagePick(play, ctx, rand) {
  const p = play.props ?? {}
  let options = []

  if (Array.isArray(p.options) && p.options.length) {
    options = p.options.map((o, i) => {
      const face = faceOf(o, ctx.emoji)
      return {
        id: String(o.key ?? o.id ?? `o${i}`),
        emoji: face.emoji,
        glyph: face.glyph,
        label: labelOf(o, face, `第 ${i + 1} 个`),
        correct: o.correct === true,
        reveal: o.reveal ?? ''
      }
    })
  } else if (Array.isArray(p.pairs) && p.pairs.length) {
    // 生成器的 pair-match 其实是「给这个字找它的图」，还是一道选择题
    options = p.pairs.map((o, i) => {
      const face = faceOf({ emoji: o.emoji, char: o.char }, ctx.emoji)
      return {
        id: String(o.key ?? `p${i}`),
        emoji: face.emoji,
        glyph: '',
        label: `「${o.char ?? ctx.char}」的图`,
        correct: o.correct === true || o.char === ctx.char,
        reveal: o.char ?? ''
      }
    })
  } else if (Array.isArray(p.cells) && p.cells.length) {
    options = p.cells.map((c, i) => {
      const face = faceOf(c, ctx.emoji)
      return {
        id: String(c.id ?? `c${i}`),
        emoji: face.emoji,
        glyph: face.glyph,
        label: c.label ?? '',
        correct: c.hit === true,
        reveal: ''
      }
    })
  } else {
    // 富脚本的 emoji-hunt 只给 target + decoys
    const target = p.target ?? p.hero ?? ctx.emoji
    const decoys = (Array.isArray(p.decoys) ? p.decoys : []).filter(Boolean)
    const filler = decoys.length ? decoys : companions(ctx, 3, rand).map((m) => m.emoji)
    options = shuffled(
      [
        { id: 't0', ...faceOf(target, ctx.emoji), label: `「${ctx.char}」的图`, correct: true, reveal: ctx.char },
        ...filler.map((d, i) => ({ id: `d${i}`, ...faceOf(d), label: '别的东西', correct: false, reveal: '' }))
      ],
      rand
    )
  }

  // 空脸的选项（作者少写了图标、拼音表凑不出干扰项）点了也看不出点没点，剔掉
  options = options.filter((o) => o.emoji || o.glyph)
  if (!options.some((o) => o.correct)) {
    options.unshift({
      id: 't0',
      emoji: ctx.emoji,
      glyph: '',
      label: `「${ctx.char}」的图`,
      correct: true,
      reveal: ctx.char
    })
  }
  // 一道只有一个选项的选择题不叫玩：拿同单元的小伙伴凑够三个
  if (options.length < 3) {
    for (const mate of companions(ctx, 3 - options.length, rand)) {
      options.push({ id: `f${options.length}`, emoji: mate.emoji, glyph: '', label: mate.label, correct: false, reveal: '' })
    }
    options = shuffled(options, rand)
  }

  const corrects = options.filter((o) => o.correct).length

  return {
    kind: 'pick',
    props: {
      options,
      need: clamp(Number(p.rounds ?? p.goal ?? 1) || 1, 1, Math.max(1, corrects)),
      /** 盖着的卡片：点开才知道是不是它（生成器的 tap-reveal 用）。 */
      cover: p.cover ?? '',
      scene: p.scene ?? '',
      sceneLabel: p.sceneLabel ?? '',
      /** 听音玩法：舞台会给一个「再听一遍」的喇叭。 */
      say: p.say ?? '',
      pinyin: p.pinyin ?? ''
    }
  }
}

/* --- catch：一堆东西里点够次数（会掉下来的也算） --- */

const MOVING_TEMPLATES = new Set(['rain-catch', 'pop-bubbles'])

function stageCatch(play, ctx, rand) {
  const p = play.props ?? {}
  const source = Array.isArray(p.drops) && p.drops.length
    ? p.drops
    : Array.isArray(p.items) && p.items.length
      ? p.items
      : Array.isArray(p.cells) && p.cells.length
        ? p.cells
        : null

  let items = (source ?? []).map((raw, i) => {
    const face = faceOf(raw, ctx.emoji)
    const hit = typeof raw === 'object' ? raw.hit !== false : true
    return {
      id: String(raw?.key ?? raw?.id ?? `d${i}`),
      emoji: face.emoji,
      glyph: face.glyph,
      label: labelOf(raw, face, `第 ${i + 1} 个`),
      hit
    }
  })

  if (!items.length) {
    // 只给了一个主角和次数（点小嘴巴三下、把苹果涂三下）：摆 count 个一样的，
    // 全是对的。这类玩法本来就没有「点错」这回事，掺干扰项只会让孩子犹豫。
    const hero = p.hero ?? ctx.emoji
    const count = clamp(Number(p.count ?? p.goal ?? p.rounds ?? 3) || 3, 1, 8)
    items = Array.from({ length: count }, (_, i) => ({
      id: `h${i}`,
      ...faceOf(hero, ctx.emoji),
      label: `第 ${i + 1} 个`,
      hit: true
    }))
  }

  const hits = items.filter((i) => i.hit).length
  const need = clamp(Number(p.rounds ?? p.count ?? p.goal ?? hits) || hits, 1, Math.max(1, hits))
  const moving = MOVING_TEMPLATES.has(play.template)

  return {
    kind: 'catch',
    props: {
      items: items.map((item, i) => ({
        ...item,
        // 会掉的那些要落点和时长；不掉的用不上，留着也不碍事
        x: clamp(12 + Math.round(rand() * 76), 8, 88),
        delay: Math.round(i * 380 + rand() * 240),
        duration: Math.round(2600 + rand() * 1400)
      })),
      need,
      moving,
      /** 盖着的卡片：先点开才看得见（揭一揭）。 */
      cover: p.cover ?? (play.template === 'tap-reveal' ? p.hero || '❓' : ''),
      /** 接东西的家伙（富脚本的 rain-catch 会给一个盆 / 纸巾）。 */
      tool: p.tool ?? '',
      target: p.target ?? ctx.char,
      sound: p.sound ?? ''
    }
  }
}

/* --- assemble：把零件放回位置 --- */

function stageAssemble(play, ctx, rand) {
  const p = play.props ?? {}

  // 补词语：一个词缺一个字，别的字是干扰
  if (p.word) {
    const chars = Array.isArray(p.chars) && p.chars.length ? [...p.chars] : [...String(p.word)]
    const blank = clamp(Number(p.slot ?? chars.indexOf(ctx.char)) || 0, 0, chars.length - 1)
    // 富脚本把候选字写在 parts，生成器写在 pieces；都没写就只剩这个字本身
    const pieceSource = Array.isArray(p.pieces) && p.pieces.length
      ? p.pieces
      : Array.isArray(p.parts) && p.parts.length
        ? p.parts
        : [ctx.char]
    const pieces = pieceSource.map((raw, i) => {
      const face = faceOf(raw, '')
      return {
        id: String(raw?.key ?? raw?.id ?? `w${i}`),
        glyph: face.glyph || face.emoji || String(raw),
        label: '',
        correct: typeof raw === 'object' ? raw.correct === true : String(raw) === ctx.char
      }
    })
    if (!pieces.some((piece) => piece.correct)) pieces[0].correct = true
    // 只有一张牌的「选择题」等于白送：借同单元的字凑够三张
    for (const decoy of decoyChars(ctx, 3 - pieces.length, rand)) {
      pieces.push({ id: `wd${pieces.length}`, glyph: decoy, label: '', correct: false })
    }
    return {
      kind: 'assemble',
      props: {
        mode: 'word',
        whole: p.word,
        chars,
        blank,
        slots: [{ id: 's0', glyph: chars[blank] ?? ctx.char }],
        pieces: shuffled(pieces, rand),
        hint: play.prompt ?? `补齐「${p.word}」`
      }
    }
  }

  // 拼零件：几个部件按顺序送回田字格
  const slotSource = Array.isArray(p.slots) && p.slots.length
    ? p.slots
    : Array.isArray(p.parts) && p.parts.length
      ? p.parts
      : null

  if (slotSource) {
    const slots = slotSource.map((raw, i) => {
      const face = faceOf(raw, ctx.emoji)
      return { id: `s${i}`, glyph: face.glyph || face.emoji }
    })
    const pieceSource = Array.isArray(p.pieces) && p.pieces.length ? p.pieces : slotSource
    const pieces = pieceSource.map((raw, i) => {
      const face = faceOf(raw, ctx.emoji)
      const glyph = face.glyph || face.emoji
      return {
        id: String(raw?.key ?? raw?.id ?? `p${i}`),
        glyph,
        label: typeof raw === 'object' ? (raw.name ?? '') : '',
        correct: typeof raw === 'object' && 'correct' in raw ? raw.correct === true : slots.some((s) => s.glyph === glyph)
      }
    })
    if (!pieces.some((piece) => piece.correct)) pieces[0].correct = true
    return {
      kind: 'assemble',
      props: {
        mode: 'parts',
        whole: p.whole ?? ctx.char,
        slots,
        pieces: shuffled(pieces, rand),
        hint: play.prompt ?? `把零件拼成「${ctx.char}」`
      }
    }
  }

  // 什么零件都没给：退成「挑出这个字的偏旁」，任何字都有部首可挑
  const answer = ctx.radicalGlyph || ctx.char
  const decoys = shuffled(
    [
      ['氵', '三点水'],
      ['木', '木字旁'],
      ['亻', '单人旁'],
      ['口', '口字旁'],
      ['扌', '提手旁'],
      ['艹', '草字头'],
      ['讠', '言字旁'],
      ['女', '女字旁']
    ].filter(([g]) => g !== answer),
    rand
  ).slice(0, 2)
  return {
    kind: 'assemble',
    props: {
      mode: 'parts',
      whole: ctx.char,
      slots: [{ id: 's0', glyph: answer }],
      pieces: shuffled(
        [
          { id: 'p0', glyph: answer, label: ctx.radicalName, correct: true },
          ...decoys.map(([glyph, name], i) => ({ id: `p${i + 1}`, glyph, label: name, correct: false }))
        ],
        rand
      ),
      hint: `想一想：「${ctx.char}」是不是和「${ctx.radicalName || answer}」有关？`
    }
  }
}

/* --- watch：一帧一帧看完 --- */

function stageWatch(play, ctx) {
  const p = play.props ?? {}
  const source = Array.isArray(p.frames) && p.frames.length
    ? p.frames
    : Array.isArray(p.stages) && p.stages.length
      ? p.stages
      : null

  let frames = (source ?? []).map((raw, i) => {
    const face = faceOf(raw, ctx.emoji)
    return {
      id: String(raw?.key ?? raw?.id ?? `f${i}`),
      emoji: face.emoji,
      glyph: face.glyph,
      caption: (typeof raw === 'object' && raw.caption) || ''
    }
  })

  if (!frames.length) {
    frames = [
      { id: 'f0', emoji: ctx.emoji, glyph: '', caption: '先看这张图' },
      { id: 'f1', emoji: ctx.emoji, glyph: ctx.char, caption: '图慢慢变成字' }
    ]
  }
  // 最后一帧必须是字：孩子看完得知道「刚才那张图就是这个字」
  const last = frames[frames.length - 1]
  if (last.glyph !== ctx.char) {
    frames = [...frames, { id: 'fz', emoji: '', glyph: ctx.char, caption: `就是「${ctx.char}」` }]
  }
  frames = frames.map((f, i) => ({
    ...f,
    caption: f.caption || (i === frames.length - 1 ? `就是「${ctx.char}」` : '再看一步')
  }))

  return { kind: 'watch', props: { frames, button: p.button ?? '变！' } }
}

/* --- match：左边一个右边一个，配成一对 --- */

function stageMatch(play, ctx, rand) {
  const p = play.props ?? {}
  const left = []
  const right = []

  if (Array.isArray(p.pairs) && p.pairs.length) {
    p.pairs.forEach((pair, i) => {
      const a = faceOf(pair.a ?? pair.left, ctx.emoji)
      const b = faceOf(pair.b ?? pair.right, ctx.emoji)
      left.push({ id: `a${i}`, ...a, label: '', key: `k${i}` })
      right.push({ id: `b${i}`, ...b, label: '', key: `k${i}` })
    })
  } else if (Array.isArray(p.items) && p.items.length && Array.isArray(p.buckets)) {
    p.items.forEach((item, i) => {
      const face = faceOf(item.item ?? item, ctx.emoji)
      left.push({ id: `i${i}`, ...face, label: '', key: String(item.bucket ?? '') })
    })
    p.buckets.forEach((bucket, i) => {
      const face = faceOf(bucket.emoji ?? bucket, ctx.emoji)
      right.push({ id: `b${i}`, ...face, label: bucket.label ?? '', key: String(bucket.label ?? '') })
    })
  }

  if (!left.length || !right.length) return stageCatch(play, ctx, rand)

  return {
    kind: 'match',
    props: {
      left: shuffled(left, rand),
      right: shuffled(right, rand),
      need: clamp(Number(p.goal ?? left.length) || left.length, 1, left.length)
    }
  }
}

/* --- push：顺着一个方向推 / 拉 / 举 --- */

const DIR_LABEL = { up: '往上', down: '往下', left: '往左', right: '往右' }

function stagePush(play, ctx) {
  const p = play.props ?? {}
  const dir = DIR_LABEL[p.dir] ? p.dir : 'right'
  return {
    kind: 'push',
    props: {
      hero: p.hero ?? ctx.emoji,
      dir,
      dirLabel: DIR_LABEL[dir],
      need: clamp(Number(p.goal ?? p.rounds ?? 3) || 3, 1, 6)
    }
  }
}

const STAGERS = {
  pick: stagePick,
  catch: stageCatch,
  assemble: stageAssemble,
  watch: stageWatch,
  match: stageMatch,
  push: stagePush
}

/**
 * 归到哪个渲染器：先看道具长什么样，再看模板 id，最后看 interaction。
 *
 * 道具优先是因为同一个模板名在两套方言里指的不是一回事：生成器的 pair-match
 * 是「给这个字挑出它的图」（一道选择题），富脚本的 pair-match 是「左边连右边」。
 * 只认 id 就会把连线题渲染成选择题——三张牌全是对的，孩子随手一点就过。
 */
function kindOf(play) {
  const p = play?.props ?? {}
  const firstPair = Array.isArray(p.pairs) ? p.pairs[0] : null
  if (firstPair && (firstPair.a !== undefined || firstPair.left !== undefined)) return 'match'
  if (Array.isArray(p.buckets) && p.buckets.length) return 'match'
  // tap-reveal 同名不同玩法：生成器给 options，是「揭开找出对的那张」（选择题）；
  // 富脚本只给 items，是「盖着的全揭开」——按选择题渲染会变成三张牌全对。
  if (play?.template === 'tap-reveal' && !Array.isArray(p.options)) return 'catch'
  return TEMPLATE_KIND[play?.template] ?? INTERACTION_KIND[play?.interaction] ?? 'catch'
}

/** 把任何一套方言的剧本翻译成舞台读得懂的那一份。 */
function toStage(play, ctx) {
  const kind = kindOf(play)
  const rand = rngOf(hashOf(ctx.char, 31) ^ hashOf(String(play.template ?? kind), 5))
  let staged
  try {
    staged = STAGERS[kind](play, ctx, rand)
  } catch {
    // 道具再怪也不能让舞台空着：退到最稳的那一关
    staged = stageCatch(emergencyPlay(ctx), ctx, rand)
  }
  const theme = play.theme ?? 'word'
  const template = play.template && PLAY_TEMPLATES[play.template] ? play.template : 'scene-poke'
  return {
    char: ctx.char,
    theme,
    themeLabel: play.themeLabel ?? '',
    themeEmoji: play.themeEmoji ?? ctx.emoji,
    accent: accentOf(theme),
    template,
    templateLabel: play.templateName ?? getPlayTemplate(template).label,
    kind: staged.kind,
    emoji: play.emoji ?? ctx.emoji,
    narration: play.narration || `一起来玩「${ctx.char}」。`,
    prompt: play.prompt ?? '',
    props: staged.props,
    templateFallback: play.templateFallback === true,
    source: play.source ?? 'rich'
  }
}

/* ---------------------------------------------------------------- 对外入口 */

/**
 * 取一个字的「玩」场景。**永远不返回 null**：
 * 富脚本 → 自动补齐 → 兜底合成，层层往下，最后一层只要有个字就凑得出来。
 *
 * @param {string} char 单个汉字；空值 / 多字时取第一个字符，实在没有就退到「字」
 * @returns {{char: string, theme: string, template: string, kind: string,
 *            narration: string, props: object, templateFallback: boolean,
 *            source: 'rich'|'generated'|'runtime'|'emergency'}}
 */
export function getCharPlay(char) {
  const text = typeof char === 'string' ? char.trim() : ''
  const one = text ? [...text][0] : '字'
  const ctx = contextOf(one)

  const rich = RICH.get(one)
  if (rich) {
    return toStage(
      { ...rich, char: one, templateFallback: rich.templateFallback === true, source: 'rich' },
      ctx
    )
  }

  try {
    return toStage(generatedPlay(ctx), ctx)
  } catch {
    return toStage(emergencyPlay(ctx), ctx)
  }
}

/** 批量体检：返回玩不成的字（缺渲染器或缺道具）。正常永远是空数组。 */
export function findPlayHoles(chars = CHAR_INDEX.map((c) => c.char)) {
  const holes = []
  for (const char of chars) {
    const play = getCharPlay(char)
    if (!play?.template || !PLAY_KINDS.includes(play.kind) || !play.props) holes.push(char)
  }
  return holes
}

export default {
  getCharPlay,
  registerCharPlays,
  hasRichPlay,
  countRichPlays,
  listRichPlays,
  findPlayHoles,
  getPlayTemplate,
  PLAY_TEMPLATES,
  PLAY_TEMPLATE_IDS,
  PLAY_KINDS
}
