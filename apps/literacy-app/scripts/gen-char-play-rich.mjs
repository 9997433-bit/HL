/**
 * ROUND15_H3 · 富互动 play 脚本生成器 —— 把手写 seed 编译成运行时能直接吃的数据。
 *
 * 「玩」这一步要的不是又一张卡片，是和字义对得上的小互动：雨接雨滴、火添柴、
 * 口张嘴发声、推往前推、拉往回拉。这类脚本只能人写，写在
 * scripts/data/char-play-seed.txt 里（前 20 个单元，一字一条）。这个脚本负责：
 *
 *   1. 解析 seed 的五段式行（字 | 主题 | 模板 | 旁白 | 道具）；
 *   2. 按 TEMPLATE_CATALOG 校验每条脚本的道具齐不齐——舞台跑起来才不会开天窗；
 *   3. 把没写的 goal 补成模板的自然完成条件（拼几块就是几下），
 *      把没写的 hero 补成字表里的卡片 emoji，保证每条都有主角可画；
 *   4. 落成 src/data/char-play-rich.js，每条都带 templateFallback: false。
 *
 * 没手写到的字不归这里管：gen-char-play.mjs 会按部首 / 主题模板自动补齐，
 * 那批条目带 templateFallback: true。两份合起来才是全库 1820 字的 Play 覆盖。
 *
 * 用法：
 *   node scripts/gen-char-play-rich.mjs          生成 src/data/char-play-rich.js
 *   node scripts/gen-char-play-rich.mjs --check  只校验不落盘（CI / 提交前用）
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHAR_INDEX } from '../src/data/char-index.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const seedFile = path.join(appDir, 'scripts', 'data', 'char-play-seed.txt')
const outFile = path.join(appDir, 'src', 'data', 'char-play-rich.js')
const checkOnly = process.argv.includes('--check')

/** 手写脚本覆盖到第几个单元。往后扩就改这里，校验会跟着放宽。 */
const RICH_UNIT_LIMIT = 20

/** 主题只是给舞台挑配色和音效用的粗分类，别再细分了，多了没人维护得动。 */
const THEMES = [
  'number',
  'nature',
  'weather',
  'animal',
  'body',
  'family',
  'school',
  'food',
  'color',
  'shape',
  'time',
  'place',
  'action',
  'object',
  'word',
  'feeling'
]

/**
 * 模板名录 —— 舞台按 template 挑具体演法，按 interaction 决定「怎么算玩完了」。
 *
 * interaction 是给降级用的：某个模板还没实现具体动效时，舞台可以退回
 * 同交互类型的通用演法（点 / 拖 / 划 / 顺序播），孩子仍然玩得完，
 * 而不是掉进一张空白卡——这条是 Round 15 的红线。
 *
 * requires 列的是这个模板缺了就玩不成的道具；goal 缺省时按 defaultGoal 推。
 */
const TEMPLATE_CATALOG = {
  'morph-story': {
    interaction: 'sequence',
    desc: '象形分镜：从实物 emoji 一步步变成字形',
    requires: ['stages'],
    defaultGoal: (p) => p.stages.length
  },
  'tap-reveal': {
    interaction: 'tap',
    desc: '点一点，藏起来的东西一个个露出来',
    requires: ['hero', 'items'],
    defaultGoal: (p) => p.items.length
  },
  'emoji-hunt': {
    interaction: 'tap',
    desc: '一堆干扰项里找出目标（找中后目标会换位置再出现）',
    requires: ['target', 'decoys'],
    defaultGoal: () => 1
  },
  'count-tap': {
    interaction: 'tap',
    desc: '一个一个点着数，点满为止',
    requires: ['items'],
    defaultGoal: (p) => p.items.length
  },
  'pop-bubbles': {
    interaction: 'tap',
    desc: '戳掉 / 吃掉 / 喝掉，点一个少一个',
    requires: ['items'],
    defaultGoal: (p) => p.items.length
  },
  'grow-tap': {
    interaction: 'tap',
    desc: '点一下长一点，按 stages 逐级长大',
    requires: ['stages'],
    defaultGoal: (p) => p.stages.length
  },
  'sound-tap': {
    interaction: 'tap',
    desc: '点了会发声，跟着念拟声词',
    requires: ['hero', 'sound'],
    defaultGoal: () => 3
  },
  'color-fill': {
    interaction: 'tap',
    desc: '点着把主角一块块涂上颜色',
    requires: ['hero', 'color'],
    defaultGoal: () => 3
  },
  'scene-poke': {
    interaction: 'tap',
    desc: '一幅小场景，挨个点亮里面的东西',
    requires: ['hero', 'items'],
    defaultGoal: (p) => p.items.length
  },
  'drag-parts': {
    interaction: 'drag',
    desc: '把零件 / 部件拖到一起，拼成主角',
    requires: ['parts'],
    defaultGoal: (p) => p.parts.length
  },
  'rain-catch': {
    interaction: 'drag',
    desc: '东西往下掉，拖着工具去接',
    requires: ['items', 'tool'],
    defaultGoal: (p) => p.items.length
  },
  'trace-path': {
    interaction: 'drag',
    desc: '按住主角顺着路线拖过去',
    requires: ['hero', 'dir'],
    defaultGoal: () => 3
  },
  'pair-match': {
    interaction: 'drag',
    desc: '左右连线，配成一对',
    requires: ['pairs'],
    defaultGoal: (p) => p.pairs.length
  },
  'sort-buckets': {
    interaction: 'drag',
    desc: '把每样东西拖进它该去的筐',
    requires: ['buckets', 'items'],
    defaultGoal: (p) => p.items.length
  },
  'word-build': {
    interaction: 'drag',
    desc: '把两个字拖到一起，组成一个词',
    requires: ['word', 'parts'],
    defaultGoal: (p) => p.parts.length
  },
  'swipe-motion': {
    interaction: 'swipe',
    desc: '照着字义的方向划：推向前、拉回来、举往上',
    requires: ['hero', 'dir'],
    defaultGoal: () => 3
  }
}

const LIST_KEYS = new Set(['items', 'decoys', 'parts', 'stages', 'pairs', 'buckets'])
const DIRS = new Set(['up', 'down', 'left', 'right'])
/** 旁白是念给 4–6 岁孩子听的，一口气念得完才行。 */
const MAX_NARRATION = 26

/* ------------------------------------------------------------------ 解析 seed */

const byChar = new Map(CHAR_INDEX.map((c) => [c.char, c]))
const errors = []
const warnings = []

/** `key=value;key=value` → 对象；带 , 的值成列表，带 : 的列表项成对。 */
function parseProps(raw, lineNo) {
  const props = {}
  if (!raw) return props
  for (const chunk of raw.split(';')) {
    const piece = chunk.trim()
    if (!piece) continue
    const eq = piece.indexOf('=')
    if (eq < 0) {
      errors.push(`第 ${lineNo} 行：道具「${piece}」不是 key=value`)
      continue
    }
    const key = piece.slice(0, eq).trim()
    const value = piece.slice(eq + 1).trim()
    if (key === 'goal') {
      const n = Number(value)
      if (!Number.isInteger(n) || n < 1 || n > 12) {
        errors.push(`第 ${lineNo} 行：goal=${value} 不在 1–12`)
        continue
      }
      props.goal = n
    } else if (key === 'pairs') {
      props.pairs = value.split(',').map((item) => {
        const [a, b] = item.split(':')
        if (!a || !b) errors.push(`第 ${lineNo} 行：pairs 的「${item}」要写成 左:右`)
        return { a: (a ?? '').trim(), b: (b ?? '').trim() }
      })
    } else if (key === 'buckets') {
      props.buckets = value.split(',').map((item) => {
        const [label, emoji] = item.split(':')
        if (!label || !emoji) errors.push(`第 ${lineNo} 行：buckets 的「${item}」要写成 筐名:emoji`)
        return { label: (label ?? '').trim(), emoji: (emoji ?? '').trim() }
      })
    } else if (LIST_KEYS.has(key)) {
      props[key] = value.split(',').map((v) => v.trim())
    } else {
      props[key] = value
    }
  }
  // 分桶模板的 items 写成「东西:筐名」，在这里拆成对象
  if (props.buckets && Array.isArray(props.items)) {
    props.items = props.items.map((item) => {
      const [thing, bucket] = String(item).split(':')
      if (!thing || !bucket) errors.push(`第 ${lineNo} 行：分桶 items 的「${item}」要写成 东西:筐名`)
      return { item: (thing ?? '').trim(), bucket: (bucket ?? '').trim() }
    })
  }
  return props
}

function parseSeed() {
  const rows = []
  const seen = new Set()
  const lines = fs.readFileSync(seedFile, 'utf8').split('\n')

  lines.forEach((raw, i) => {
    const lineNo = i + 1
    const line = raw.trim()
    if (!line || line.startsWith('#')) return

    const cols = line.split('|').map((c) => c.trim())
    if (cols.length !== 5) {
      errors.push(`第 ${lineNo} 行：应该是 5 段（字|主题|模板|旁白|道具），实际 ${cols.length} 段`)
      return
    }
    const [char, theme, template, narration, rawProps] = cols

    const indexed = byChar.get(char)
    if (!indexed) {
      errors.push(`第 ${lineNo} 行：「${char}」不在字表里`)
      return
    }
    if (seen.has(char)) {
      errors.push(`第 ${lineNo} 行：「${char}」重复了`)
      return
    }
    seen.add(char)

    const unitNo = Number(indexed.unit.slice(1))
    if (!(unitNo >= 1 && unitNo <= RICH_UNIT_LIMIT)) {
      warnings.push(`「${char}」在 ${indexed.unit}，超出手写覆盖的前 ${RICH_UNIT_LIMIT} 个单元`)
    }
    if (!THEMES.includes(theme)) {
      errors.push(`第 ${lineNo} 行：主题「${theme}」不在名录里`)
      return
    }
    const spec = TEMPLATE_CATALOG[template]
    if (!spec) {
      errors.push(`第 ${lineNo} 行：模板「${template}」不在名录里`)
      return
    }
    if (!narration) {
      errors.push(`第 ${lineNo} 行：「${char}」没有旁白`)
      return
    }
    if ([...narration].length > MAX_NARRATION) {
      warnings.push(`「${char}」旁白 ${[...narration].length} 字，超过 ${MAX_NARRATION}`)
    }

    const props = parseProps(rawProps, lineNo)
    if (!props.hero) props.hero = indexed.emoji

    for (const key of spec.requires) {
      const v = props[key]
      const empty = v == null || v === '' || (Array.isArray(v) && v.length === 0)
      if (empty) errors.push(`第 ${lineNo} 行：模板 ${template} 缺道具 ${key}`)
    }
    if (props.dir && !DIRS.has(props.dir)) {
      errors.push(`第 ${lineNo} 行：dir=${props.dir} 只能是 up / down / left / right`)
    }
    if (Array.isArray(props.decoys) && props.decoys.length < 2) {
      errors.push(`第 ${lineNo} 行：emoji-hunt 至少要 2 个干扰项`)
    }
    if (Array.isArray(props.buckets) && Array.isArray(props.items)) {
      const labels = new Set(props.buckets.map((b) => b.label))
      for (const it of props.items) {
        if (!labels.has(it.bucket)) {
          errors.push(`第 ${lineNo} 行：「${it.item}」要进的筐「${it.bucket}」不存在`)
        }
      }
    }

    if (props.goal == null) props.goal = spec.defaultGoal(props)
    // 点数玩法不能要求点得比东西还多，不然孩子点到最后一个也过不了关
    const tappable = Array.isArray(props.items) && typeof props.items[0] === 'string'
    if (tappable && ['count-tap', 'pop-bubbles', 'tap-reveal', 'scene-poke'].includes(template)) {
      if (props.goal > props.items.length) {
        errors.push(`第 ${lineNo} 行：goal=${props.goal} 比 items 还多（${props.items.length}）`)
      }
    }

    rows.push({
      char,
      unit: indexed.unit,
      theme,
      template,
      interaction: spec.interaction,
      narration,
      props
    })
  })

  return rows
}

/* ---------------------------------------------------------------------- 落盘 */

/** props 里的键按固定顺序输出，diff 才稳。 */
const PROP_ORDER = [
  'hero',
  'target',
  'decoys',
  'items',
  'buckets',
  'pairs',
  'parts',
  'stages',
  'tool',
  'dir',
  'sound',
  'color',
  'word',
  'goal'
]

const q = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`

function renderValue(value) {
  if (typeof value === 'number') return String(value)
  if (Array.isArray(value)) {
    return `[${value.map((v) => (typeof v === 'object' ? renderObject(v) : q(v))).join(', ')}]`
  }
  return q(value)
}

function renderObject(obj) {
  return `{ ${Object.entries(obj)
    .map(([k, v]) => `${k}: ${renderValue(v)}`)
    .join(', ')} }`
}

function renderProps(props) {
  const keys = [
    ...PROP_ORDER.filter((k) => props[k] !== undefined),
    ...Object.keys(props).filter((k) => !PROP_ORDER.includes(k))
  ]
  return `{ ${keys.map((k) => `${k}: ${renderValue(props[k])}`).join(', ')} }`
}

function renderRows(rows) {
  const out = []
  let unit = null
  for (const r of rows) {
    if (r.unit !== unit) {
      unit = r.unit
      out.push(`  // ${unit}`)
    }
    out.push(
      '  {',
      `    char: ${q(r.char)}, unit: ${q(r.unit)}, theme: ${q(r.theme)},`,
      `    template: ${q(r.template)}, interaction: ${q(r.interaction)},`,
      `    narration: ${q(r.narration)},`,
      `    props: ${renderProps(r.props)},`,
      '    templateFallback: false',
      '  },'
    )
  }
  return out.join('\n')
}

function renderCatalog() {
  return Object.entries(TEMPLATE_CATALOG)
    .map(
      ([id, spec]) =>
        `  ${q(id)}: { interaction: ${q(spec.interaction)}, desc: ${q(spec.desc)} },`
    )
    .join('\n')
}

const rows = parseSeed()

if (warnings.length) {
  for (const w of warnings) console.warn(`[play-rich] 提醒：${w}`)
}
if (errors.length) {
  for (const e of errors) console.error(`[play-rich] ${e}`)
  console.error(`[play-rich] seed 有 ${errors.length} 处问题，没有生成。`)
  process.exit(1)
}

const units = [...new Set(rows.map((r) => r.unit))]
const templates = [...new Set(rows.map((r) => r.template))]

if (checkOnly) {
  console.log(
    `[play-rich] seed 校验通过：${rows.length} 条，覆盖 ${units.length} 个单元、` +
      `${templates.length} 个模板。`
  )
  process.exit(0)
}

const body = `/**
 * 富互动 play 脚本库 —— 「玩」这一步的手写剧本，覆盖前 ${units.length} 个单元共 ${rows.length} 个字。
 *
 * 每条都是照着字义写的：雨接雨滴、火添柴、口张嘴发声、推往前推、拉往回拉。
 * 这一层的 templateFallback 一律为假；剩下的字由 char-play.js 按部首 / 主题
 * 模板自动补齐（那批 templateFallback 为真）。两层加起来才是全库 Play 覆盖。
 *
 * 舞台怎么用：
 *   template     具体演法，取值见下面的 PLAY_TEMPLATES
 *   interaction  交互类型（tap / drag / swipe / sequence）。某个模板的专属动效
 *                还没实现时按它退回通用演法，孩子照样玩得完——绝不能退成空白卡。
 *   narration    念给孩子听的一句，也是无障碍朗读的文案
 *   props.goal   要完成几次有效交互才算通关；reduce-motion 和「跳过这一步」
 *                不改变通关条件，只是不播动效
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 模板名录：舞台照着 interaction 决定「怎么算玩完了」。 */
export const PLAY_TEMPLATES = {
${renderCatalog()}
}

/** 主题分类，舞台拿它挑配色和音效。 */
export const PLAY_THEMES = [${THEMES.map(q).join(', ')}]

export const CHAR_PLAY_RICH = [
${renderRows(rows)}
]

/** 字 → 富脚本。 */
export const RICH_PLAY_BY_CHAR = new Map(CHAR_PLAY_RICH.map((p) => [p.char, p]))

/** 这个字有没有手写剧本；没有就交给 char-play.js 的模板补齐。 */
export function getRichPlay(char) {
  return RICH_PLAY_BY_CHAR.get(char) ?? null
}

/** 手写剧本条数（Round 15 H3 数的就是它）。 */
export function countRichPlays() {
  return CHAR_PLAY_RICH.length
}

/** 手写覆盖到的单元。 */
export const RICH_PLAY_UNITS = [${units.map(q).join(', ')}]
`

fs.writeFileSync(outFile, body)

const perTemplate = templates
  .map((t) => `${t} ${rows.filter((r) => r.template === t).length}`)
  .join('、')
const kb = (Buffer.byteLength(body) / 1024).toFixed(0)
console.log(
  `[play-rich] ${rows.length} 条富脚本，覆盖 ${units.length} 个单元（${units[0]}–${units[units.length - 1]}），约 ${kb} KB。`
)
console.log(`[play-rich] 模板分布：${perTemplate}`)
