/**
 * 形近字库生成器 —— 「这两个字长得像」要算出来，不能靠手写。
 *
 * 听音识字和单字页的「考一考」都要出四选一。以前的干扰项是从学过的字里随机
 * 抽三个，孩子只要认出目标字的轮廓就能排除掉其余三个，题目基本白出。真正
 * 该练的是「日 / 曰 / 旦」「未 / 末」「己 / 已 / 巳」这种一眼扫过去几乎一样
 * 的字——干扰项必须是形近字，题目才有分辨的价值。
 *
 * 形近怎么算？离线笔顺数据（hanzi-writer-data，makemeahanzi 一脉）里每个字都有
 * 一份 medians：每一笔的中线折线，坐标在 1024 × 1024 的字框里。把它当成这个字的
 * 「骨架」，就能直接比形状，不需要任何在线服务：
 *
 *   1. 占格图    把所有笔画的中线密集采样，落进 12 × 12 的格子里，
 *                得到一张粗糙的「墨在哪儿」热力图。两个字的热力图越像，
 *                看上去就越像（日 / 曰 / 旦 会挤在一起，日 / 森 不会）。
 *   2. 笔向直方图 每一小段的方向按 8 个方位统计，长度加权。
 *                光看占格图分不出「人」和「八」，笔向能。
 *   3. 笔画数    差三笔以上的两个字，孩子不会看错，直接排除。
 *   4. 同部首    加一点分：形近又同旁的（清 / 情 / 晴）是最典型的错例。
 *
 * 另外压一份人工清单（CONFUSABLE）兜底。教学上公认最容易混的那些组合
 * （己已巳、未末、土士、乌鸟…）不能指望算法一定捞得到，写死进去更稳。
 *
 * 输出：src/data/similar-chars.js（生成物，勿手改）
 * 用法：node scripts/gen-similar-chars.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

import { CHARACTERS } from '../src/data/characters.js'

const require = createRequire(import.meta.url)
const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const outFile = path.join(appDir, 'src', 'data', 'similar-chars.js')

/** 每个字最多留几个形近字。四选一只要三个，留 5 个是为了让重复出题时有变化。 */
const NEIGHBOURS = 5

/** 分数低于这条线的不算「像」，宁可少给也不给凑数的。 */
const MIN_SCORE = 0.62

/** 笔画差超过这个数，孩子一眼就分得开，不必当干扰项。 */
const MAX_STROKE_GAP = 3

const GRID = 12
const BOX = 1024

/* ------------------------------------------------------------ 人工形近清单
 *
 * 每行是一组两两互为形近的字。只写「教学上真的会错」的组合：
 * 低年级作业本上最常见的那些订正，就是这张表的来源。
 * 字不在字表里的会被自动丢掉，所以可以写得宽松一点。
 */
const CONFUSABLE = [
  '日曰旦目自白',
  '田由甲申电',
  '未末木本术',
  '土士干千于王玉主',
  '己已巳',
  '人入八九几儿',
  '大太犬天夭夫失',
  '刀力办万方',
  '乌鸟马与',
  '免兔龟',
  '白百自首',
  '手毛予书',
  '问间闪闻闷闲闯',
  '青请清情晴睛精蜻',
  '找我划戏成',
  '拾抬治冶',
  '密蜜',
  '竟竞意',
  '抱泡跑炮苞饱袍',
  '峰蜂锋逢缝',
  '渴喝揭',
  '沙纱妙秒抄吵少',
  '江红工空功杠',
  '巴把爸吧芭爬',
  '争净静',
  '象像橡',
  '直真具且县',
  '买卖实头',
  '千干于午牛半',
  '广厂户尸元',
  '冷冰次决冬',
  '汗汁汉汇江',
  '快块决怪',
  '跳桃挑逃兆',
  '波破坡披玻被皮',
  '消削悄',
  '传转团',
  '休体',
  '阴阳阶阵队',
  '棵颗课',
  '球救求',
  '往住注驻柱',
  '外处夕',
  '鸟岛乌',
  '牛午半年',
  '还这近远',
  '斤斥丘兵',
  '包句勺匀勾',
  '刚网冈',
  '衣农表依',
  '今令冷含',
  '低底抵',
  '园圆团回国因',
  '折拆析',
  '货贷代货',
  '睡锤捶垂',
  '慢漫谩',
  '幕墓慕暮募',
  '辨辩辫瓣',
  '篮蓝',
  '第弟递',
  '带戴',
  '在再',
  '万方力',
  '午牛年',
  '看着差羊',
  '木禾米末',
  '几凡儿',
  '瓜爪抓',
  '鱼角鲁',
  '虫电申',
  '雨两西',
  '车东',
  '开井升',
  '正止上',
  '走足是',
  '风凤凡',
  '玉王主全',
  '生牛失',
  '石右左友',
  '子孑了予',
  '门问们闪',
  '早草旱昌',
  '林森材村',
  '和知种',
  '果东',
  '香看春',
  '色包免',
  '会全金',
  '朋明用',
  '姐组租且',
  '妹味未',
  '很跟根恨狠痕',
  '现观规',
  '师帅归',
  '钱线浅践',
  '暖援缓',
  '喝渴谒',
  '住往柱',
  '推堆维',
  '搬般船',
  '睛精晴',
  '扫归妇',
  '飘漂票',
  '喊减感',
  '篇偏遍编',
  '躲朵',
  '嘴最',
  '慢馒漫',
  '厉励历',
  '猫描瞄苗',
  '拔拨',
  '棒捧',
  '辆两俩',
  '座坐',
  '席度',
  '锋峰蜂',
  '摘滴',
  '袋代贷',
  '账帐张',
  '踢锡',
  '燥躁澡操噪'
]

/* ------------------------------------------------------------------ 字形特征 */

function resolveDataDir() {
  try {
    return path.dirname(require.resolve('hanzi-writer-data/package.json'))
  } catch {
    return null
  }
}

/**
 * 把一个字的中线折线摊成 12 × 12 的占格图 + 8 方位笔向直方图。
 *
 * 采样步长取 16（字框是 1024），比格子边长小得多，短笔画也不会漏格。
 * 占格图开方压一下：让「有没有墨」比「墨有多浓」更重要，
 * 不然一笔来回描的地方会把整张图的相似度带跑。
 */
function features(data) {
  const medians = data?.medians ?? []
  if (!medians.length) return null

  const grid = new Float64Array(GRID * GRID)
  const dirs = new Float64Array(8)
  let ink = 0

  for (const stroke of medians) {
    for (let i = 1; i < stroke.length; i += 1) {
      const [x0, y0] = stroke[i - 1]
      const [x1, y1] = stroke[i]
      const dx = x1 - x0
      const dy = y1 - y0
      const len = Math.hypot(dx, dy)
      if (len === 0) continue

      // 笔向：0..2π 分 8 档，用段长加权
      const bucket = Math.floor(((Math.atan2(dy, dx) + Math.PI * 2) % (Math.PI * 2)) / (Math.PI / 4))
      dirs[bucket % 8] += len

      const steps = Math.max(1, Math.ceil(len / 16))
      for (let s = 0; s <= steps; s += 1) {
        const t = s / steps
        // hanzi-writer 的 y 轴朝上，翻过来只是为了让占格图和肉眼看到的字同向
        const gx = Math.min(GRID - 1, Math.max(0, Math.floor(((x0 + dx * t) / BOX) * GRID)))
        const gy = Math.min(GRID - 1, Math.max(0, Math.floor((1 - (y0 + dy * t) / BOX) * GRID)))
        grid[gy * GRID + gx] += 1
        ink += 1
      }
    }
  }

  if (!ink) return null
  for (let i = 0; i < grid.length; i += 1) grid[i] = Math.sqrt(grid[i])

  return { grid: normalise(grid), dirs: normalise(dirs), strokes: medians.length }
}

function normalise(vec) {
  let sum = 0
  for (const v of vec) sum += v * v
  const norm = Math.sqrt(sum) || 1
  const out = new Float64Array(vec.length)
  for (let i = 0; i < vec.length; i += 1) out[i] = vec[i] / norm
  return out
}

function dot(a, b) {
  let sum = 0
  for (let i = 0; i < a.length; i += 1) sum += a[i] * b[i]
  return sum
}

function score(a, b) {
  const gap = Math.abs(a.strokes - b.strokes)
  if (gap > MAX_STROKE_GAP) return 0
  const shape = dot(a.grid, b.grid)
  const flow = dot(a.dirs, b.dirs)
  const count = 1 - gap / (MAX_STROKE_GAP + 1)
  const kin = a.radical && a.radical === b.radical ? 1 : 0
  return 0.6 * shape + 0.2 * flow + 0.14 * count + 0.06 * kin
}

/* ---------------------------------------------------------------------- 生成 */

const dataDir = resolveDataDir()
if (!dataDir) {
  console.error('[similar-chars] 找不到 hanzi-writer-data，无法计算字形相似度。')
  process.exit(1)
}

const entries = []
const missing = []
for (const c of CHARACTERS) {
  const file = path.join(dataDir, `${c.char}.json`)
  if (!fs.existsSync(file)) {
    missing.push(c.char)
    continue
  }
  const f = features(JSON.parse(fs.readFileSync(file, 'utf8')))
  if (!f) {
    missing.push(c.char)
    continue
  }
  f.char = c.char
  f.radical = c.radical
  entries.push(f)
}

// 人工清单先落成 字 → 同组其它字，保证这些组合一定在结果最前面
const inTable = new Set(entries.map((e) => e.char))
const curated = new Map()
for (const group of CONFUSABLE) {
  const chars = [...new Set([...group])].filter((ch) => inTable.has(ch))
  for (const ch of chars) {
    const bucket = curated.get(ch) ?? []
    for (const other of chars) {
      if (other !== ch && !bucket.includes(other)) bucket.push(other)
    }
    curated.set(ch, bucket)
  }
}

/**
 * 1820 × 1820 的两两比对是三百多万次点积，看着吓人，其实先按笔画数分桶
 * （只跟自己 ±3 笔的字比）就砍掉九成以上，跑下来不到几秒。
 */
const byStrokes = new Map()
for (const e of entries) {
  const bucket = byStrokes.get(e.strokes) ?? []
  bucket.push(e)
  byStrokes.set(e.strokes, bucket)
}

const groups = []
let computed = 0

for (const e of entries) {
  const ranked = []
  for (let n = e.strokes - MAX_STROKE_GAP; n <= e.strokes + MAX_STROKE_GAP; n += 1) {
    for (const other of byStrokes.get(n) ?? []) {
      if (other.char === e.char) continue
      const s = score(e, other)
      if (s >= MIN_SCORE) ranked.push([other.char, s])
    }
  }
  ranked.sort((a, b) => b[1] - a[1])

  const picked = []
  for (const ch of curated.get(e.char) ?? []) {
    if (picked.length < NEIGHBOURS) picked.push(ch)
  }
  for (const [ch] of ranked) {
    if (picked.length >= NEIGHBOURS) break
    if (!picked.includes(ch)) picked.push(ch)
  }

  if (picked.length) {
    groups.push(e.char + picked.join(''))
    computed += picked.length
  }
}

/* ---------------------------------------------------------------------- 落盘 */

const PER_LINE = 8
const lines = []
for (let i = 0; i < groups.length; i += PER_LINE) {
  lines.push(`  ${groups.slice(i, i + PER_LINE).map((g) => `'${g}'`).join(', ')}`)
}

const body = `/**
 * 形近字库 —— 每个字后面跟着几个「长得像它」的字，相似度从高到低。
 *
 * 听音识字和单字页的选择题拿它出干扰项：四个选项都长得差不多，孩子才必须
 * 真的听清读音、真的记住字形，而不是靠排除法蒙。取不到形近字的生僻组合
 * 会自动退回同部首 / 笔画相近，见 utils/distractors.js。
 *
 * 相似度由 scripts/gen-similar-chars.mjs 从离线笔顺数据（medians 骨架）算出，
 * 再压一份人工形近清单兜底。本文件是生成物，请勿手改。
 *
 * 数据形状：每条字符串的第一个字是「主字」，后面是它的形近字。
 */

const GROUPS = [
${lines.join(',\n')}
]

/** 主字 → 形近字（字符串，按相似度降序）。 */
export const SIMILAR_MAP = new Map(GROUPS.map((g) => [g[0], g.slice(1)]))

export const TOTAL_SIMILAR = SIMILAR_MAP.size

/** 这个字的形近字，没有就返回空数组。 */
export function similarChars(char) {
  const packed = SIMILAR_MAP.get(char)
  return packed ? [...packed] : []
}

/** 两个字算不算形近（任一方向命中都算）。 */
export function isSimilar(a, b) {
  return (SIMILAR_MAP.get(a)?.includes(b) ?? false) || (SIMILAR_MAP.get(b)?.includes(a) ?? false)
}
`

fs.writeFileSync(outFile, body)

const kb = (Buffer.byteLength(body) / 1024).toFixed(0)
console.log(
  `[similar-chars] ${groups.length} 个字有形近字（共 ${computed} 条，约 ${kb} KB）；` +
    `${entries.length} 个字参与计算${missing.length ? `，${missing.length} 个字缺笔顺数据` : ''}。`
)
if (missing.length) console.warn(`[similar-chars] 缺笔顺：${missing.join(' ')}`)
