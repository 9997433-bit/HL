/**
 * ROUND15_H3 / ROUND18_H3 · 富互动 play 脚本生成器 ——
 * 把手写 seed 编译成「一单元一片 + 一份轻量 manifest」。
 *
 * 「玩」这一步要的不是又一张卡片，是和字义对得上的小互动：雨接雨滴、火添柴、
 * 口张嘴发声、推往前推、拉往回拉。这类脚本只能人写，写在
 * scripts/data/char-play-seed.txt 里（前 RICH_UNIT_LIMIT 个单元，一字一条）。
 * 这个脚本负责：
 *
 *   1. 解析 seed 的五段式行（字 | 主题 | 模板 | 旁白 | 道具），旁白撞句就判错——
 *      一字不差要判，只差个标点 / 空格的「近似撞句」同样判，见 narrationKey()；
 *   2. 按 TEMPLATE_CATALOG 校验每条脚本的道具齐不齐——舞台跑起来才不会开天窗；
 *   3. 把没写的 goal 补成模板的自然完成条件（拼几块就是几下），
 *      把没写的 hero 补成字表里的卡片 emoji，保证每条都有主角可画；
 *   4. 落成 src/data/play-rich/ 下的分片与 manifest，每条都带 templateFallback: false。
 *
 * ## 为什么落成一个目录而不是一个文件（ROUND18_H3）
 *
 * 940 条脚本堆成一个 262 KB 的模块，被 char-play.js 顶层 import 之后整包都在
 * 单字详情的关键路径上：孩子点开「雨」，先下载另外 939 个字的剧本。可孩子一次
 * 只玩一个字，同一分钟里最多用到同单元的十几条。所以照 data/chars/uN.js 那批
 * 课文分片的先例，按**单元**切开：
 *
 *   src/data/play-rich/uN.js    一单元一片，UNIT_RICH_PLAYS 是这一单元的完整条目
 *   src/data/play-rich/index.js manifest + 每单元一个 () => import() 的加载器表；
 *                               **唯一允许被同步 import 的文件**，体积 O(单元数)
 *
 * manifest 里一句旁白、一件道具都不放，不然「轻量索引」会随 seed 一起长回整包。
 * 契约全文见 .agent_workspace/round18-architecture.md §2。
 *
 * 没手写到的字不归这里管：gen-char-play.mjs 会按部首 / 主题模板自动补齐，
 * 那批条目带 templateFallback: true。两份合起来才是全库 1820 字的 Play 覆盖。
 *
 * 用法：
 *   node scripts/gen-char-play-rich.mjs          生成 src/data/play-rich/
 *   node scripts/gen-char-play-rich.mjs --check  只校验不落盘（CI / 提交前用）
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHAR_INDEX } from '../src/data/char-index.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const argOf = (name) => {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`))
  return hit ? hit.slice(name.length + 3) : ''
}
// --seed= 只给负例测试用（拿一份改坏的 seed 验证撞句真的拦得住），正常跑不传。
const seedFile = argOf('seed') || path.join(appDir, 'scripts', 'data', 'char-play-seed.txt')
const dataDir = path.join(appDir, 'src', 'data')
/** 分片目录：一单元一片 + index.js manifest（契约 §2.2）。 */
const outDir = path.join(dataDir, 'play-rich')
/** 拆包前的单体脚本库，生成时顺手清掉——留着就是一扇再被同步 import 的门。 */
const legacyFile = path.join(dataDir, 'char-play-rich.js')
const checkOnly = process.argv.includes('--check')

/** 这一版 seed 的门槛标记，落在生成物里给探针读（Round 17 数的是 ≥900 条）。 */
const PROBE_MARK = 'ROUND17_H2'

/** 拆包这一层的标记：分片 + manifest 这套形状是 Round 18 H3 的交付物。 */
const SPLIT_MARK = 'ROUND18_H3'

/** 历轮标记，往轮探针剥掉注释后仍读得到自己那一枚。 */
const PROBE_HISTORY = ['ROUND15_H3', 'ROUND16_H3', PROBE_MARK]

/** 手写脚本覆盖到第几个单元。往后扩就改这里，校验会跟着放宽。 */
const RICH_UNIT_LIMIT = 55

/** 探针数的两条线：条数和「旁白不重样」的句数。生成期就得自己先量一遍。 */
const MIN_RICH_PLAYS = 900
const MIN_DISTINCT_NARRATION = 720

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

/**
 * 撞句判定用的归一形：去掉标点、空格和语气词尾巴。
 *
 * 只比字符串相等挡不住「把句号换成感叹号」这种改法——念出来还是同一句，
 * 孩子听到的是两关一模一样的旁白。这里把这类差别抹平再比。
 */
const narrationKey = (s) =>
  String(s)
    .replace(/[\s，。！？、；：,.!?;:~—…·「」『』“”‘’"']/g, '')
    .replace(/(呀|吧|啦|呢|哦|哟)$/, '')

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
  // 旁白一句话对应一个字的意思，撞句就说明有一条是照抄邻居的——直接判错，
  // 不然「900 条」里混进 200 句一模一样的，探针数得到，孩子听得出来。
  // 两道闸都在生成期：一字不差的用 narrationOwner，改了标点的用 narrationKeyOwner。
  const narrationOwner = new Map()
  const narrationKeyOwner = new Map()
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
    const twin = narrationOwner.get(narration)
    if (twin) {
      errors.push(`第 ${lineNo} 行：「${char}」的旁白和「${twin}」一字不差，换一句`)
      return
    }
    const key = narrationKey(narration)
    const nearTwin = narrationKeyOwner.get(key)
    if (nearTwin) {
      errors.push(
        `第 ${lineNo} 行：「${char}」的旁白和「${nearTwin}」只差标点语气，念出来是同一句，换一句`
      )
      return
    }
    narrationOwner.set(narration, char)
    narrationKeyOwner.set(key, char)

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
  for (const r of rows) {
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

/** 一个单元一片。条目形状和拆包前一模一样，只是按单元装箱。 */
function renderUnitShard(unit, rows) {
  return `/**
 * 富互动 play 分片 ${unit} —— 这一单元的 ${rows.length} 条手写剧本（${SPLIT_MARK}）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = ${q(unit)}

export const UNIT_RICH_PLAYS = [
${renderRows(rows)}
]

export default UNIT_RICH_PLAYS
`
}

/**
 * manifest —— 唯一允许被同步 import 的生成物，所以只放「有几条、在哪片」，
 * 一句旁白、一件道具都不放：它一旦按条数长大，拆包就白拆了（契约 §2.2）。
 */
function renderManifest(units, perUnit, plays, narrations) {
  const loaders = units.map((u) => `  ${u}: () => import('./${u}.js')`).join(',\n')
  const counts = units.map((u) => `${u}: ${perUnit[u]}`).join(', ')
  return `/**
 * 富互动 play 分片名录（${SPLIT_MARK}）—— 手写剧本按单元切片之后的目录页。
 *
 * 这里**只有数字和加载器**：几条、分几片、每片几条、怎么把某一片取回来。
 * 旁白和道具都在各自的 ./uN.js 里，用到哪个单元才下载哪一片，
 * 所以本文件的体积随单元数长（O(单元)），不随脚本条数长（O(条)）。
 *
 * 加载器写成一条条字面量 import()，Vite / Rollup 才能据此每单元切一个 chunk；
 * 写成拼字符串的动态 import 会退化成「整目录一块」，等于没拆。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 生成，请勿手改。
 */

/** 分片加载器：单元 id → 取回那一片。char-play.js 的 ensurePlayUnit() 用它。 */
export const RICH_PLAY_UNIT_LOADERS = {
${loaders}
}

/** 手写覆盖到的单元，按 seed 顺序。 */
export const RICH_PLAY_UNITS = [${units.map(q).join(', ')}]

/**
 * 生成期实测的数字，给运行时和探针对账用：manifest 说 ${plays} 条，
 * 那么 loadAllRichPlays() 之后 countRichPlays() 也必须是 ${plays} 条，对不上就是管线出了问题。
 */
export const RICH_PLAY_MANIFEST = {
  plays: ${plays},
  narrations: ${narrations},
  units: RICH_PLAY_UNITS,
  perUnit: { ${counts} }
}

/** 模板名录：舞台照着 interaction 决定「怎么算玩完了」。 */
export const PLAY_TEMPLATES = {
${renderCatalog()}
}

/** 主题分类，舞台拿它挑配色和音效。 */
export const PLAY_THEMES = [${THEMES.map(q).join(', ')}]

/** 门槛标记，探针剥掉注释后仍读得到。 */
export const RICH_PLAY_PROBE = '${PROBE_MARK}'

/** 拆包这一层的标记：分片 + manifest 的形状是 Round 18 H3 的交付物。 */
export const RICH_SPLIT_PROBE = '${SPLIT_MARK}'

/** 历轮标记都留着，往轮探针各读各的那一枚。 */
export const RICH_PLAY_PROBE_HISTORY = [${PROBE_HISTORY.map(q).join(', ')}]

/** 本轮两条线，生成期已经卡过一遍，运行时再自报一次给探针核对。 */
export const RICH_PLAY_THRESHOLDS = { plays: ${MIN_RICH_PLAYS}, narrations: ${MIN_DISTINCT_NARRATION} }
`
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
const distinctNarration = new Set(rows.map((r) => r.narration)).size
const distinctNarrationKeys = new Set(rows.map((r) => narrationKey(r.narration))).size

// 归一后还比条数少，说明上面两道闸漏了一句——宁可不生成，也别把撞句写进库里。
if (distinctNarrationKeys !== rows.length) {
  console.error(
    `[play-rich] 旁白去重 ${distinctNarrationKeys} 条 ≠ 脚本 ${rows.length} 条，有撞句漏网。`
  )
  process.exit(1)
}
if (rows.length < MIN_RICH_PLAYS || distinctNarration < MIN_DISTINCT_NARRATION) {
  console.error(
    `[play-rich] 没到 ${PROBE_MARK} 的线：脚本 ${rows.length}（需 ≥${MIN_RICH_PLAYS}）、` +
      `旁白 ${distinctNarration} 句（需 ≥${MIN_DISTINCT_NARRATION}）。`
  )
  process.exit(1)
}

if (checkOnly) {
  console.log(
    `[play-rich] seed 校验通过：${rows.length} 条，覆盖 ${units.length} 个单元、` +
      `${templates.length} 个模板，旁白 ${distinctNarration} 句不重样。`
  )
  process.exit(0)
}

fs.mkdirSync(outDir, { recursive: true })

// 分片目录整个由生成器管：seed 缩了单元，对应的旧分片必须跟着消失，
// 不然 manifest 里查不到、目录里却还躺着一份，下一个人读起来会以为它还在用。
const wanted = new Set([...units.map((u) => `${u}.js`), 'index.js'])
for (const stale of fs.readdirSync(outDir)) {
  if (stale.endsWith('.js') && !wanted.has(stale)) fs.rmSync(path.join(outDir, stale))
}

const perUnit = {}
let shardBytes = 0
for (const unit of units) {
  const unitRows = rows.filter((r) => r.unit === unit)
  perUnit[unit] = unitRows.length
  const body = renderUnitShard(unit, unitRows)
  shardBytes += Buffer.byteLength(body)
  fs.writeFileSync(path.join(outDir, `${unit}.js`), body)
}

const manifest = renderManifest(units, perUnit, rows.length, distinctNarration)
fs.writeFileSync(path.join(outDir, 'index.js'), manifest)

// 拆包前的单体脚本库退休：留一层薄壳也不行，那等于给人再同步 import 回去的门。
if (fs.existsSync(legacyFile)) fs.rmSync(legacyFile)

const perTemplate = templates
  .map((t) => `${t} ${rows.filter((r) => r.template === t).length}`)
  .join('、')
const kb = (n) => (n / 1024).toFixed(0)
console.log(
  `[play-rich] ${rows.length} 条富脚本，覆盖 ${units.length} 个单元（${units[0]}–${units[units.length - 1]}）。`
)
console.log(
  `[play-rich] 分片 ${units.length} 片共 ${kb(shardBytes)} KB，平均每片 ${kb(shardBytes / units.length)} KB；` +
    `manifest ${kb(Buffer.byteLength(manifest))} KB（同步路径上只有它）。`
)
console.log(`[play-rich] 模板分布：${perTemplate}`)
