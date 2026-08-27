/**
 * 配对记忆引擎 —— 牌堆编排，纯函数无框架依赖。
 *
 * 两种配对规则：
 *  · same     两张一模一样的牌配成一对，练的是「记住它在哪儿」（低龄档）
 *  · category 两张不同的牌只要同属一类就配成一对，记忆之外还要分类（高龄档）
 *
 * category 档是这个玩法进 logic 模块的理由：翻到 🍎 和 🍇 要能想到「都是水果」，
 * 对应技能图谱里的 classify（分类大师）。牌堆用 createRng(seed) 洗，
 * 同一个种子出同一副牌，check:content 才能对牌堆做回归。
 */
import { createRng } from '@/utils/random.js'

export const PAIR_GROUPS = Object.freeze([
  {
    id: 'fruit',
    name: '水果',
    items: [
      { glyph: '🍎', label: '苹果' },
      { glyph: '🍌', label: '香蕉' },
      { glyph: '🍇', label: '葡萄' },
      { glyph: '🍉', label: '西瓜' },
      { glyph: '🍓', label: '草莓' },
      { glyph: '🍐', label: '梨' },
    ],
  },
  {
    id: 'animal',
    name: '动物',
    items: [
      { glyph: '🐱', label: '小猫' },
      { glyph: '🐶', label: '小狗' },
      { glyph: '🐰', label: '兔子' },
      { glyph: '🐼', label: '熊猫' },
      { glyph: '🐸', label: '青蛙' },
      { glyph: '🐘', label: '大象' },
    ],
  },
  {
    id: 'vehicle',
    name: '交通工具',
    items: [
      { glyph: '🚗', label: '汽车' },
      { glyph: '🚌', label: '公交车' },
      { glyph: '🚲', label: '自行车' },
      { glyph: '✈️', label: '飞机' },
      { glyph: '🚢', label: '轮船' },
      { glyph: '🚂', label: '火车' },
    ],
  },
  {
    id: 'space',
    name: '太空',
    items: [
      { glyph: '🚀', label: '火箭' },
      { glyph: '🛰️', label: '卫星' },
      { glyph: '🪐', label: '行星' },
      { glyph: '🌙', label: '月亮' },
      { glyph: '⭐', label: '星星' },
      { glyph: '☄️', label: '彗星' },
    ],
  },
  {
    id: 'tool',
    name: '文具',
    items: [
      { glyph: '✏️', label: '铅笔' },
      { glyph: '📕', label: '课本' },
      { glyph: '📐', label: '三角尺' },
      { glyph: '✂️', label: '剪刀' },
      { glyph: '🖍️', label: '蜡笔' },
      { glyph: '📎', label: '回形针' },
    ],
  },
])

export const MEMORY_MODES = Object.freeze({
  same: { id: 'same', name: '同图配对', rule: '找出两张一模一样的卡片。' },
  category: { id: 'category', name: '同类配对', rule: '两张卡片只要是同一类，就能配成一对。' },
})

/** 各年龄档的默认对数与配对规则。 */
export const MEMORY_LEVELS = Object.freeze({
  L1: { pairs: 4, mode: 'same' },
  L2: { pairs: 6, mode: 'same' },
  L3: { pairs: 6, mode: 'category' },
  L4: { pairs: 8, mode: 'category' },
  L5: { pairs: 10, mode: 'category' },
})

export const memoryLevelOf = (ageBand) => MEMORY_LEVELS[ageBand] ?? MEMORY_LEVELS.L3

/** 牌堆最多能出多少对：same 档一张牌算一对，category 档两张牌才算一对。 */
export function maxPairs(mode = 'same') {
  return PAIR_GROUPS.reduce(
    (acc, group) => acc + (mode === 'category' ? Math.floor(group.items.length / 2) : group.items.length),
    0,
  )
}

/** 卡片张数 → 网格列行数，尽量铺成接近方形又不至于太窄的版面。 */
export function gridOf(count) {
  const cols = count <= 12 ? 4 : 5
  return { cols, rows: Math.ceil(count / cols) }
}

function samePairs(rng, count) {
  const pool = PAIR_GROUPS.flatMap((group) =>
    group.items.map((item) => ({ ...item, group: group.id, groupName: group.name })),
  )
  return rng.pick(pool, count).map((item, index) => ({
    pairId: `p${index}`,
    faces: [item, item],
  }))
}

function categoryPairs(rng, count) {
  // 先在每一类里两两成对，再从所有类的对子里抽，避免一副牌全是水果
  const pool = PAIR_GROUPS.flatMap((group) => {
    const items = rng.shuffle(group.items)
    const pairs = []
    for (let i = 0; i + 1 < items.length; i += 2) {
      pairs.push([
        { ...items[i], group: group.id, groupName: group.name },
        { ...items[i + 1], group: group.id, groupName: group.name },
      ])
    }
    return pairs
  })
  return rng.pick(pool, count).map((faces, index) => ({ pairId: `p${index}`, faces }))
}

/**
 * 发一副牌：返回洗好顺序的卡片数组，每张牌带着它属于哪一对。
 * @param {{ pairs?: number, mode?: 'same'|'category', seed?: string|number }} options
 */
export function buildMemoryDeck({ pairs = 6, mode = 'same', seed } = {}) {
  const rule = MEMORY_MODES[mode] ? mode : 'same'
  const count = Math.max(2, Math.min(pairs, maxPairs(rule)))
  const rng = createRng(seed)
  const built = rule === 'category' ? categoryPairs(rng, count) : samePairs(rng, count)

  const cards = built.flatMap(({ pairId, faces }) =>
    faces.map((face, side) => ({
      id: `${pairId}-${side}`,
      pairId,
      glyph: face.glyph,
      label: face.label,
      group: face.group,
      groupName: face.groupName,
    })),
  )

  return { mode: rule, pairs: count, cards: rng.shuffle(cards), grid: gridOf(cards.length), seed }
}

/** 两张牌能不能配上：同一对、且不是同一张。 */
export function isMatch(a, b) {
  return !!a && !!b && a.id !== b.id && a.pairId === b.pairId
}

/** 读屏用的卡片描述：没翻开时只报位置，翻开后才报内容。 */
export function describeCard(card, { index, total, state = 'down' }) {
  const where = `第 ${index + 1} / ${total} 张`
  if (state === 'down') return `${where}，还没翻开，点一下翻开`
  const what = `${card.label}，${card.groupName}`
  return state === 'matched' ? `${where}，${what}，已配对` : `${where}，${what}，已翻开`
}

/** 配对成功/失败时给孩子的说法，同类配对要把「为什么是一对」讲出来。 */
export function matchReason(a, b, mode) {
  if (!a || !b) return ''
  if (isMatch(a, b)) {
    return mode === 'category'
      ? `${a.glyph}${a.label} 和 ${b.glyph}${b.label} 都是${a.groupName}，配对成功！`
      : `两张${a.label}，配对成功！`
  }
  return mode === 'category'
    ? `${a.label}是${a.groupName}，${b.label}是${b.groupName}，不是同一类。`
    : `一张${a.label}、一张${b.label}，不是同一张卡。`
}
