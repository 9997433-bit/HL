/**
 * 一字一玩法 —— 「玩」这一步的数据层（ROUND15_H2）。
 *
 * 洪恩识字每个字进学习前先玩一个小情境，问题是那套东西是一字一美术、
 * 一字一脚本，覆盖不到的字就没有。我们的字表是 1820 个字，手写脚本永远追不上，
 * 所以这里分两层：
 *
 *   富脚本   char-play-rich.js（以及运行时 registerCharPlays 注册进来的批次）
 *            人工写的情境：这个字该玩什么、旁白怎么说、道具是哪几个。
 *   模板补齐 没有富脚本的字，用字表里现成的信息（单元 / 部首 / 卡片图标）
 *            按主题挑一个模板、配齐道具，标 templateFallback: true。
 *
 * 于是 getCharPlay() 对任何字都给得出一个能玩完的场景——包括字表里没有的字
 * （孩子从搜索或绘本里点进来的生字）。**它永远不返回 null**，这是 CharPlayStage
 * 唯一依赖的契约。
 *
 * 补齐是纯函数式的：同一个字每次算出来的道具、乱序、落点都一样（字的哈希做种子），
 * 孩子第二次进来看到的还是那一关，不会因为刷新换了张脸；单测也因此可断言。
 *
 * 包体：本模块只吃已经在主包里的 char-index / unit-index / radicals，
 * 富脚本那份跟着 CharPlayStage 一起进「玩」的异步块，不进首屏。
 */

import { CHAR_INDEX } from './char-index.js'
import { UNITS } from './unit-index.js'
import { getRadical } from './radicals.js'
import * as richModule from './char-play-rich.js'

/* ------------------------------------------------------------------ 模板 */

/**
 * 可玩的模板。新增模板要同时在 CharPlayStage.vue 里给出渲染分支，
 * 否则舞台会退回 tap-reveal（见 normalizeTemplate）。
 */
export const PLAY_TEMPLATES = [
  {
    id: 'tap-reveal',
    label: '点一点',
    icon: '👆',
    hint: '盖子下面藏着东西，一个个点开'
  },
  {
    id: 'morph-story',
    label: '变一变',
    icon: '✨',
    hint: '图画一步一步变成这个字'
  },
  {
    id: 'emoji-hunt',
    label: '找一找',
    icon: '🔍',
    hint: '在一堆图里找出对的那个'
  },
  {
    id: 'drag-parts',
    label: '拼一拼',
    icon: '🧩',
    hint: '把偏旁送回字里'
  },
  {
    id: 'rain-catch',
    label: '接一接',
    icon: '☔',
    hint: '掉下来的东西，接住对的'
  }
]

export const PLAY_TEMPLATE_IDS = PLAY_TEMPLATES.map((t) => t.id)

const TEMPLATE_MAP = new Map(PLAY_TEMPLATES.map((t) => [t.id, t]))

export function getPlayTemplate(id) {
  return TEMPLATE_MAP.get(id) ?? TEMPLATE_MAP.get('tap-reveal')
}

/* ------------------------------------------------------------------ 主题 */

/**
 * 主题决定三件事：道具池（找不到同单元的字时用它兜底）、舞台配色、模板轮转。
 * 配色一律走设计令牌，别在这里写死颜色。
 */
export const PLAY_THEMES = {
  number: {
    label: '数一数',
    emoji: '🔢',
    accent: 'var(--mango-500)',
    pool: [
      ['1️⃣', '一个'],
      ['2️⃣', '两个'],
      ['3️⃣', '三个'],
      ['🧮', '算盘'],
      ['🎲', '骰子'],
      ['🔢', '数字']
    ]
  },
  nature: {
    label: '大自然',
    emoji: '🌿',
    accent: 'var(--leaf-500)',
    pool: [
      ['🌳', '大树'],
      ['🌻', '花'],
      ['🍃', '叶子'],
      ['⛰️', '高山'],
      ['🪨', '石头'],
      ['🌱', '小苗']
    ]
  },
  water: {
    label: '水边',
    emoji: '💧',
    accent: 'var(--sky-500)',
    pool: [
      ['💧', '水滴'],
      ['🌊', '浪花'],
      ['🐟', '小鱼'],
      ['⛵', '小船'],
      ['🫧', '泡泡'],
      ['🏖️', '沙滩']
    ]
  },
  weather: {
    label: '天上',
    emoji: '🌤️',
    accent: 'var(--sky-400)',
    pool: [
      ['☀️', '太阳'],
      ['☁️', '云'],
      ['🌧️', '下雨'],
      ['❄️', '雪花'],
      ['🌈', '彩虹'],
      ['🌙', '月亮']
    ]
  },
  animal: {
    label: '小动物',
    emoji: '🐾',
    accent: 'var(--mint-500)',
    pool: [
      ['🐱', '小猫'],
      ['🐶', '小狗'],
      ['🐦', '小鸟'],
      ['🐟', '小鱼'],
      ['🐝', '蜜蜂'],
      ['🐘', '大象']
    ]
  },
  body: {
    label: '我的身体',
    emoji: '🧒',
    accent: 'var(--coral-400)',
    pool: [
      ['👀', '眼睛'],
      ['👂', '耳朵'],
      ['👄', '嘴巴'],
      ['🖐️', '手'],
      ['🦶', '脚'],
      ['🧒', '小朋友']
    ]
  },
  feeling: {
    label: '心情',
    emoji: '😊',
    accent: 'var(--grape-400)',
    pool: [
      ['😊', '开心'],
      ['😢', '难过'],
      ['😴', '困了'],
      ['😮', '吃惊'],
      ['❤️', '喜欢'],
      ['🤗', '抱抱']
    ]
  },
  family: {
    label: '一家人',
    emoji: '👨‍👩‍👧',
    accent: 'var(--coral-500)',
    pool: [
      ['👩', '妈妈'],
      ['👨', '爸爸'],
      ['👵', '奶奶'],
      ['👴', '爷爷'],
      ['👶', '宝宝'],
      ['🏡', '家']
    ]
  },
  action: {
    label: '动起来',
    emoji: '🏃',
    accent: 'var(--mango-400)',
    pool: [
      ['🏃', '跑'],
      ['🤸', '翻跟头'],
      ['👏', '拍手'],
      ['🙌', '举起来'],
      ['🚶', '走'],
      ['🤾', '扔']
    ]
  },
  speech: {
    label: '说和写',
    emoji: '💬',
    accent: 'var(--grape-500)',
    pool: [
      ['💬', '说话'],
      ['🗣️', '大声说'],
      ['📣', '喇叭'],
      ['📖', '读书'],
      ['✏️', '写字'],
      ['🎤', '唱歌']
    ]
  },
  food: {
    label: '好吃的',
    emoji: '🍚',
    accent: 'var(--coral-500)',
    pool: [
      ['🍚', '米饭'],
      ['🍎', '苹果'],
      ['🥕', '胡萝卜'],
      ['🍜', '面条'],
      ['🥛', '牛奶'],
      ['🍲', '汤']
    ]
  },
  clothes: {
    label: '穿戴',
    emoji: '👕',
    accent: 'var(--mint-500)',
    pool: [
      ['👕', '上衣'],
      ['👖', '裤子'],
      ['🧦', '袜子'],
      ['🧢', '帽子'],
      ['👟', '鞋子'],
      ['🧣', '围巾']
    ]
  },
  home: {
    label: '房子里外',
    emoji: '🏠',
    accent: 'var(--mango-500)',
    pool: [
      ['🏠', '房子'],
      ['🚪', '门'],
      ['🪟', '窗'],
      ['🛏️', '床'],
      ['🪑', '椅子'],
      ['🔑', '钥匙']
    ]
  },
  travel: {
    label: '去远方',
    emoji: '🚗',
    accent: 'var(--sky-500)',
    pool: [
      ['🚗', '小汽车'],
      ['🚂', '火车'],
      ['🚢', '轮船'],
      ['✈️', '飞机'],
      ['🚲', '自行车'],
      ['🛣️', '大路']
    ]
  },
  tool: {
    label: '好用的东西',
    emoji: '🔨',
    accent: 'var(--star-500)',
    pool: [
      ['🔨', '锤子'],
      ['✂️', '剪刀'],
      ['📏', '尺子'],
      ['🔧', '扳手'],
      ['🖌️', '画笔'],
      ['🧰', '工具箱']
    ]
  },
  school: {
    label: '在学校',
    emoji: '🎒',
    accent: 'var(--grape-500)',
    pool: [
      ['📚', '书'],
      ['✏️', '铅笔'],
      ['🎒', '书包'],
      ['🖍️', '蜡笔'],
      ['🔔', '上课铃'],
      ['🏫', '学校']
    ]
  },
  life: {
    label: '身边',
    emoji: '✨',
    accent: 'var(--brand)',
    pool: [
      ['✨', '亮晶晶'],
      ['🎈', '气球'],
      ['🎁', '礼物'],
      ['🧩', '拼图'],
      ['⭐', '星星'],
      ['🎵', '音乐']
    ]
  }
}

export const PLAY_THEME_IDS = Object.keys(PLAY_THEMES)

const theme = (id) => PLAY_THEMES[id] ?? PLAY_THEMES.life

/** 部首 → 主题。判不出来的部首交给单元名（UNIT_THEME_RULES）继续猜。 */
const RADICAL_THEME = {
  // 自然
  mu: 'nature', cao: 'nature', he: 'nature', zhutou: 'nature', shan: 'nature',
  tu: 'nature', shitou: 'nature', tian: 'nature', ri: 'nature', huo: 'nature',
  sidian: 'nature', li: 'nature', sheng: 'nature', gua: 'nature', leibu: 'nature',
  // 水
  shui: 'water', liangdian: 'water', shuidi: 'water', chuanbu: 'water',
  zhoubu: 'travel', feng: 'weather', yutou: 'weather', qibu: 'weather',
  // 动物
  quan: 'animal', chong: 'animal', niao: 'animal', ma: 'animal', yu: 'animal',
  niu: 'animal', yang: 'animal', zhipang: 'animal', zhuibu: 'animal',
  shizhu: 'animal', guibu: 'animal', lubu: 'animal', shubu: 'animal',
  longbu: 'animal', jiaobu: 'animal', yubu: 'animal', feibu: 'animal',
  maobu: 'animal', hutou: 'animal',
  // 身体
  kou: 'body', mubu: 'body', er: 'body', zu: 'body', shenbu: 'body',
  yebu: 'body', guzi: 'body', xuebu: 'body', rou: 'body', bizi: 'body',
  pibu: 'body', mianbu: 'body', shoubu: 'body', yue: 'body', zibu: 'body',
  ya: 'body', bingtou: 'body', xingbu: 'body',
  // 心情
  xin: 'feeling', xindi: 'feeling', se: 'feeling',
  // 人和家人
  ren: 'family', renzitou: 'family', nv: 'family', zi: 'family', erbu: 'family',
  muqin: 'family', fu: 'family', lao: 'family', shibu: 'family',
  shuangren: 'action', rutou: 'action',
  // 动作
  shou: 'action', zouzhi: 'action', pu: 'action', lizi: 'action', zou: 'action',
  you: 'action', cun: 'action', zhiwen: 'action', zhua: 'action',
  zhuabu: 'action', shupang: 'action', bozitou: 'action', zhizibu: 'action',
  // 说话
  yan: 'speech', yuebu: 'speech', wenbu: 'speech', yinbu: 'speech',
  qianbu: 'speech', sanpie: 'speech',
  // 吃的
  shipang: 'food', shidi: 'food', mi: 'food', doubu: 'food', gubu: 'food',
  maibu: 'food', xiangzi: 'food', youzi: 'food', mindi: 'food',
  // 穿的
  yibu: 'clothes', yifu: 'clothes', jin: 'clothes', gebu: 'clothes',
  jiaosi: 'clothes',
  // 房子
  mian: 'home', guang: 'home', men: 'home', xue: 'home', wei: 'home',
  changtou: 'home', tongkuang: 'home', youer: 'home', gao: 'home',
  hubu: 'home', mibao: 'home', tou: 'home',
  // 车船
  che: 'travel', fang: 'travel',
  // 工具
  jinzi: 'tool', gongzi: 'tool', ge: 'tool', jinpang: 'tool', doupang: 'tool',
  pianbu: 'tool', daopang: 'tool', beibu: 'tool', sankuang: 'tool',
  gongbu: 'tool', gupang: 'tool', jibu: 'tool', nongdi: 'tool',
  // 数字与笔画
  yi: 'number', erzi: 'number', shi: 'number', ba: 'number', pie: 'number',
  shu: 'number', dian: 'number', yizhe: 'number', daoba: 'number',
  xiao: 'number', da: 'number', ganbu: 'number', bibu: 'number'
}

/** 部首没判出来时，按单元名里的关键词兜一层。顺序即优先级。 */
const UNIT_THEME_RULES = [
  [/数字|数一数|量一量/, 'number'],
  [/江河|湖海|溪|海湾|瀑布|湖畔|渔村|码头|岛屿/, 'water'],
  [/天气|四季|时间|季节|雪|云|彩虹|星空|月亮|银河|雨/, 'weather'],
  [/动物|鸟兽|虫鱼|牧场|动物园/, 'animal'],
  [/身体|健康|看病/, 'body'],
  [/心情|感觉|用心/, 'feeling'],
  [/家人|名字|一家/, 'family'],
  [/动作|运动|动起来/, 'action'],
  [/说话|文章|讲故事|写信|消息|小词/, 'speech'],
  [/好吃|厨房|灶台/, 'food'],
  [/穿在身上/, 'clothes'],
  [/房子|家里|城|镇|集市|商店|书院|城堡|驿站|关口|塔|宝库|花园|门/, 'home'],
  [/出发|去玩|远方|车船|路|桥|梯|长桥/, 'travel'],
  [/工具|科学|音乐|画画|唱歌|游戏|颜色/, 'tool'],
  [/上学|学校|课堂|学习|识字|书/, 'school'],
  [/自然|花草|树木|田野|庄稼|果|竹|麦|草原|树林|果园|山|沙|石|土地|大地|荒野/, 'nature']
]

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

/* ------------------------------------------------------------ 字表侧的信息 */

const CHAR_MAP = new Map(CHAR_INDEX.map((c) => [c.char, c]))
const UNIT_MAP = new Map(UNITS.map((u) => [u.id, u]))

/** 同单元的字图标：找一找 / 接一接的干扰项优先从这里取，主题才对得上。 */
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

/** 拼一拼的干扰偏旁：常见、好认、和答案不重样。 */
const DECOY_RADICALS = [
  ['氵', '三点水'],
  ['木', '木字旁'],
  ['亻', '单人旁'],
  ['口', '口字旁'],
  ['扌', '提手旁'],
  ['艹', '草字头'],
  ['讠', '言字旁'],
  ['女', '女字旁'],
  ['日', '日字旁'],
  ['火', '火字旁'],
  ['心', '心字底'],
  ['山', '山字旁'],
  ['虫', '虫字旁'],
  ['土', '提土旁'],
  ['钅', '金字旁'],
  ['宀', '宝盖头']
]

function themeOf(entry) {
  const byRadical = entry?.radical ? RADICAL_THEME[entry.radical] : null
  if (byRadical) return byRadical
  const unitName = UNIT_MAP.get(entry?.unit)?.name ?? ''
  for (const [re, id] of UNIT_THEME_RULES) if (re.test(unitName)) return id
  return 'life'
}

/**
 * 把一个字摊平成模板要用的所有素材。字表里没有的字（绘本生字、搜索进来的字）
 * 也能走通：单元、部首缺了就用主题池顶上，绝不因此少一关。
 */
function contextOf(char) {
  const entry = CHAR_MAP.get(char) ?? null
  const themeId = themeOf(entry)
  const pack = theme(themeId)
  const radical = entry?.radical ? getRadical(entry.radical) : null
  const unit = entry?.unit ? UNIT_MAP.get(entry.unit) : null
  return {
    char,
    entry,
    unit,
    unitName: unit?.name ?? '',
    themeId,
    themeLabel: pack.label,
    themeEmoji: pack.emoji,
    accent: pack.accent,
    pool: pack.pool,
    emoji: entry?.emoji || pack.emoji,
    strokes: entry?.strokes ?? 0,
    radicalGlyph: radical?.glyph ?? '',
    radicalName: radical?.name ?? '',
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
  for (const item of shuffled(ctx.pool, rand)) push(item)
  // 同单元和主题池都不够了（生僻字 + 小主题）：拿别的主题池填满，玩法不能缺道具
  for (const id of PLAY_THEME_IDS) for (const item of PLAY_THEMES[id].pool) push(item)
  return out
}

/* -------------------------------------------------------------- 模板轮转 */

/**
 * 每个主题一条轮转序列，按字的哈希取一项：同主题的字不会连着是同一个玩法，
 * 而「接一接」这类和天气 / 水最搭的模板在对应主题里出现得更多。
 */
const THEME_ROTATION = {
  number: ['tap-reveal', 'emoji-hunt', 'morph-story', 'drag-parts'],
  nature: ['morph-story', 'emoji-hunt', 'tap-reveal', 'drag-parts', 'rain-catch'],
  water: ['rain-catch', 'emoji-hunt', 'morph-story', 'tap-reveal', 'drag-parts'],
  weather: ['rain-catch', 'morph-story', 'emoji-hunt', 'tap-reveal', 'drag-parts'],
  animal: ['emoji-hunt', 'tap-reveal', 'morph-story', 'drag-parts', 'rain-catch'],
  body: ['tap-reveal', 'morph-story', 'emoji-hunt', 'drag-parts'],
  feeling: ['tap-reveal', 'emoji-hunt', 'morph-story', 'drag-parts'],
  family: ['tap-reveal', 'morph-story', 'emoji-hunt', 'drag-parts'],
  action: ['emoji-hunt', 'rain-catch', 'tap-reveal', 'drag-parts', 'morph-story'],
  speech: ['morph-story', 'tap-reveal', 'drag-parts', 'emoji-hunt'],
  food: ['rain-catch', 'tap-reveal', 'emoji-hunt', 'drag-parts', 'morph-story'],
  clothes: ['tap-reveal', 'emoji-hunt', 'drag-parts', 'morph-story'],
  home: ['tap-reveal', 'drag-parts', 'emoji-hunt', 'morph-story'],
  travel: ['rain-catch', 'emoji-hunt', 'tap-reveal', 'drag-parts', 'morph-story'],
  tool: ['drag-parts', 'tap-reveal', 'emoji-hunt', 'morph-story'],
  school: ['tap-reveal', 'drag-parts', 'morph-story', 'emoji-hunt'],
  life: ['tap-reveal', 'emoji-hunt', 'morph-story', 'drag-parts', 'rain-catch']
}

function chooseTemplate(ctx) {
  const rotation = THEME_ROTATION[ctx.themeId] ?? THEME_ROTATION.life
  let id = rotation[hashOf(ctx.char, 7) % rotation.length]
  // 拼一拼要有偏旁可拼；部首就是字本身（木、山、口…）拼起来是废题，换成变一变
  if (id === 'drag-parts' && (!ctx.radicalGlyph || ctx.radicalGlyph === ctx.char)) {
    id = 'morph-story'
  }
  return id
}

/* ------------------------------------------------------------ 各模板的道具 */

function propsTapReveal(ctx, rand) {
  const mates = companions(ctx, 3, rand)
  const items = shuffled(
    [
      { id: 'p0', emoji: ctx.emoji, label: `「${ctx.char}」的样子`, isChar: true },
      ...mates.map((m, i) => ({ id: `p${i + 1}`, emoji: m.emoji, label: m.label, isChar: false }))
    ],
    rand
  )
  return {
    narration: `盖子下面藏着和「${ctx.char}」有关的东西，一个一个点开看看。`,
    props: {
      items,
      reveal: ctx.char,
      prompt: `点开 ${items.length} 个盖子`
    }
  }
}

function propsMorphStory(ctx, rand) {
  // 三帧：先看图 → 图和字叠在一起 → 只剩字。舞台把中间那帧做成交叉淡出
  const frames = [
    { id: 'f0', emoji: ctx.emoji, caption: `${ctx.themeLabel}里的一张图` },
    { id: 'f1', emoji: ctx.emoji, glyph: ctx.char, caption: '图慢慢变成字' },
    { id: 'f2', glyph: ctx.char, caption: `变好啦——「${ctx.char}」` }
  ]
  // rand 在这条分支上没用到，但保留形参签名，模板改写时不用改调用处
  void rand
  return {
    narration: `看好啦：${ctx.emoji} 一步一步变成「${ctx.char}」。`,
    props: {
      frames,
      target: ctx.char,
      button: '变！'
    }
  }
}

function huntGrid(ctx, rand, { size = 12, need = 3 } = {}) {
  const mates = companions(ctx, 4, rand)
  const cells = []
  for (let i = 0; i < size; i += 1) {
    const hit = i < need
    const mate = mates[i % mates.length]
    cells.push({
      id: `g${i}`,
      emoji: hit ? ctx.emoji : mate.emoji,
      label: hit ? `「${ctx.char}」的图` : mate.label,
      hit
    })
  }
  return shuffled(cells, rand)
}

function propsEmojiHunt(ctx, rand) {
  const need = 3
  return {
    narration: `在这一堆图里找出 ${need} 个 ${ctx.emoji}，找齐就认识「${ctx.char}」啦。`,
    props: {
      target: ctx.emoji,
      targetLabel: `「${ctx.char}」的图`,
      need,
      cells: huntGrid(ctx, rand, { size: 12, need })
    }
  }
}

function propsDragParts(ctx, rand) {
  const decoys = shuffled(
    DECOY_RADICALS.filter(([g]) => g !== ctx.radicalGlyph),
    rand
  ).slice(0, 2)
  const options = shuffled(
    [
      { id: 'o0', glyph: ctx.radicalGlyph, name: ctx.radicalName, correct: true },
      ...decoys.map(([glyph, name], i) => ({ id: `o${i + 1}`, glyph, name, correct: false }))
    ],
    rand
  )
  return {
    narration: `「${ctx.char}」少了一个零件。把对的偏旁送回格子里。`,
    props: {
      whole: ctx.char,
      options,
      answer: ctx.radicalGlyph,
      answerName: ctx.radicalName,
      hint: `想一想：「${ctx.char}」是不是和「${ctx.radicalName}」有关？`
    }
  }
}

function propsRainCatch(ctx, rand) {
  const mates = companions(ctx, 3, rand)
  const total = 9
  const need = 3
  const drops = []
  for (let i = 0; i < total; i += 1) {
    // 前 4 个是要接的，多给一个余量：漏掉一个也还能过关
    const hit = i < need + 1
    const mate = mates[i % mates.length]
    drops.push({
      id: `d${i}`,
      emoji: hit ? ctx.emoji : mate.emoji,
      label: hit ? `「${ctx.char}」的图` : mate.label,
      hit,
      // 落点、出场时间都跟着字的种子走，同一个字每次下的雨一模一样
      x: Math.round(8 + rand() * 80),
      delay: Math.round(i * 420 + rand() * 260),
      duration: Math.round(2600 + rand() * 1400)
    })
  }
  return {
    narration: `${ctx.emoji} 从天上落下来啦，接住 ${need} 个，「${ctx.char}」就跟你走。`,
    props: {
      target: ctx.emoji,
      targetLabel: `「${ctx.char}」的图`,
      need,
      drops: shuffled(drops, rand),
      // 减少动态时舞台不下雨，改用同一批道具铺成静止网格，照样能玩完
      staticCells: huntGrid(ctx, rand, { size: 9, need })
    }
  }
}

const BUILDERS = {
  'tap-reveal': propsTapReveal,
  'morph-story': propsMorphStory,
  'emoji-hunt': propsEmojiHunt,
  'drag-parts': propsDragParts,
  'rain-catch': propsRainCatch
}

/** 舞台不认识的模板一律退回点一点，宁可玩法平淡也不能空场。 */
function normalizeTemplate(id, ctx) {
  if (!id || !BUILDERS[id]) return chooseTemplate(ctx)
  if (id === 'drag-parts' && (!ctx.radicalGlyph || ctx.radicalGlyph === ctx.char)) {
    return 'tap-reveal'
  }
  return id
}

function buildPlay(ctx, templateId) {
  const rand = rngOf(hashOf(ctx.char, 31) ^ hashOf(templateId, 5))
  const built = BUILDERS[templateId](ctx, rand)
  return {
    char: ctx.char,
    theme: ctx.themeId,
    themeLabel: ctx.themeLabel,
    themeEmoji: ctx.themeEmoji,
    accent: ctx.accent,
    template: templateId,
    templateLabel: getPlayTemplate(templateId).label,
    emoji: ctx.emoji,
    narration: built.narration,
    props: built.props,
    templateFallback: true
  }
}

/* ------------------------------------------------------------ 富脚本注册表 */

/** char → 人工脚本（原始条目，取用时才和模板道具合并）。 */
const RICH = new Map()

function isPlayEntry(value) {
  return Boolean(value) && typeof value === 'object' && typeof value.char === 'string' && value.char
}

/**
 * 注册一批富脚本。数组、`{ 汉字: 条目 }` 映射都收，
 * 条目缺什么字段（模板、旁白、道具）取用时由模板补齐，不必写全。
 *
 * @returns {number} 这一批真正登记进去的条数
 */
export function registerCharPlays(source) {
  let added = 0
  const take = (entry, key) => {
    if (!entry || typeof entry !== 'object') return
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

/** 看着像一条 play 脚本：有模板或有旁白，才收。 */
function looksLikePlay(value) {
  return (
    Boolean(value) &&
    typeof value === 'object' &&
    (typeof value.template === 'string' || typeof value.narration === 'string')
  )
}

/**
 * char-play-rich.js 里叫什么名字都行：只要导出的是「条目数组」或
 * 「汉字 → 条目」的映射就会被收进来。富脚本那一岗换了导出名也不至于整块失联。
 */
for (const value of Object.values(richModule ?? {})) {
  if (Array.isArray(value)) {
    registerCharPlays(value.filter((v) => isPlayEntry(v) && looksLikePlay(v)))
  } else if (value && typeof value === 'object') {
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

/** H3 探针用：人工脚本（非模板补齐）到底有多少条。 */
export function countRichPlays() {
  return RICH.size
}

export function listRichPlays() {
  return [...RICH.values()]
}

/* ---------------------------------------------------------------- 对外入口 */

/**
 * 取一个字的「玩」场景。**永远不返回 null**：
 * 有富脚本用富脚本（缺的字段由模板补齐），没有就整关模板生成。
 *
 * @param {string} char 单个汉字；空值 / 多字时取第一个字符，实在没有就退到「字」
 * @returns {{char: string, theme: string, template: string, narration: string,
 *            props: object, templateFallback: boolean}}
 */
export function getCharPlay(char) {
  const text = typeof char === 'string' ? char.trim() : ''
  const one = text ? [...text][0] : '字'
  const ctx = contextOf(one)

  const rich = RICH.get(one)
  const templateId = normalizeTemplate(rich?.template, ctx)
  const base = buildPlay(ctx, templateId)
  if (!rich) return base

  // 富脚本只写了旁白 / 只改了几件道具也算数：其余照模板补齐，舞台拿到的永远是整份
  return {
    ...base,
    ...rich,
    char: one,
    template: templateId,
    templateLabel: getPlayTemplate(templateId).label,
    theme: rich.theme ?? base.theme,
    themeLabel: PLAY_THEMES[rich.theme]?.label ?? base.themeLabel,
    themeEmoji: PLAY_THEMES[rich.theme]?.emoji ?? base.themeEmoji,
    accent: PLAY_THEMES[rich.theme]?.accent ?? base.accent,
    emoji: rich.emoji ?? base.emoji,
    narration: rich.narration || base.narration,
    props: { ...base.props, ...(rich.props ?? {}) },
    templateFallback: false
  }
}

/** 批量体检：返回没能拿到 template 的字。正常情况下永远是空数组。 */
export function findPlayHoles(chars = CHAR_INDEX.map((c) => c.char)) {
  const holes = []
  for (const char of chars) {
    const play = getCharPlay(char)
    if (!play?.template || !BUILDERS[play.template] || !play.props) holes.push(char)
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
  PLAY_TEMPLATES,
  PLAY_TEMPLATE_IDS,
  PLAY_THEMES
}
