/**
 * Play 场景的主题表与模板表 —— 「玩」这一步的公共词汇。
 *
 * 一个 Play 条目只存四样东西（见 char-play-generated.js 的每行）：
 *
 *   汉字 | 主题 | 模板 | 一句话线索[ | 额外料]
 *
 * 剩下的旁白、题面、选项、动画帧都在这里按主题和模板算出来。这样做有两个好处：
 * 生成物小（1820 个字只占几十 KB），并且改一句旁白不用重跑生成器。
 *
 * 主题（theme）回答「这个字大概在讲什么」：由部首推，推不出来再看单元名。
 * 模板（template）回答「用什么玩法讲」：由主题的候选模板加上手头有没有料
 * （字源小图、部件、组词）一起决定，同一个主题里的字不会全是同一张卡。
 *
 * 模板归到四种基础互动（interaction），舞台只要实现这四种就能跑全库：
 *
 *   pick      从几个选项里点中对的（找图、听音、配对、揭卡）
 *   catch     在会动/会多的东西里点够次数（接字雨、数一数）
 *   assemble  把零件放回位置（拼部件、补组词）
 *   watch     一帧一帧看完，中间点一下推进（字源演变、跟着做动作）
 *
 * 每个模板都必须能「玩完」：props 里给足选项/零件/帧，舞台点满 steps 次即通关。
 */

/* --------------------------------------------------------------- 小工具 */

/** mulberry32：同一个字每次算出来的题面都一样，孩子重进不会看到两套东西。 */
function seededRandom(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** 字符串 → 32 位整数，用来给每个字配一个稳定的种子。 */
export function hashSeed(text) {
  let h = 2166136261
  for (const ch of String(text)) {
    h ^= ch.codePointAt(0)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

function shuffled(list, rng) {
  const out = [...list]
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/** 去重后按种子抽 n 个，池子不够就有多少给多少。 */
function sampleUnique(list, n, rng, exclude = []) {
  const skip = new Set(exclude)
  const pool = []
  for (const item of list) {
    const key = typeof item === 'string' ? item : item.key
    if (!key || skip.has(key)) continue
    skip.add(key)
    pool.push(item)
  }
  return shuffled(pool, rng).slice(0, n)
}

/** 线索 + 玩法提示拼成一句完整的话。 */
function line(hint, tail) {
  return hint ? `${hint}。${tail}` : tail
}

/* ----------------------------------------------------------------- 主题 */

/**
 * 24 个主题。`emojis` 是这一主题的图标池，用来出干扰项和布景；
 * `templates` 是这一主题默认的玩法候选（还会加上有料才能玩的模板）。
 */
export const PLAY_THEMES = [
  {
    id: 'hand',
    label: '手上的动作',
    emoji: '✋',
    scene: '小手工坊',
    emojis: ['✋', '👌', '👏', '🤲', '👊', '🤏', '🙌', '👋'],
    templates: ['mirror-move', 'emoji-hunt', 'tap-reveal', 'scene-tap']
  },
  {
    id: 'mouth',
    label: '嘴巴和声音',
    emoji: '👄',
    scene: '说话小屋',
    emojis: ['👄', '🗣️', '😋', '😮', '🎤', '😛', '🫦', '🔊'],
    templates: ['sound-echo', 'emoji-hunt', 'tap-reveal', 'rain-catch']
  },
  {
    id: 'water',
    label: '水和江河',
    emoji: '💧',
    scene: '小河边',
    emojis: ['💧', '🌊', '🏊', '🚿', '🫧', '⛵', '🐬', '🥤'],
    templates: ['rain-catch', 'scene-tap', 'emoji-hunt', 'pair-match']
  },
  {
    id: 'plant',
    label: '花草树木',
    emoji: '🌿',
    scene: '小花园',
    emojis: ['🌿', '🌳', '🌸', '🍃', '🌾', '🌵', '🍂', '🌻'],
    templates: ['scene-tap', 'emoji-hunt', 'tap-reveal', 'pair-match']
  },
  {
    id: 'person',
    label: '人和大家',
    emoji: '🧍',
    scene: '热闹的街上',
    emojis: ['🧍', '👥', '🧑', '👶', '🧓', '🚶', '🧑‍🤝‍🧑', '🙋'],
    templates: ['emoji-hunt', 'pair-match', 'tap-reveal', 'scene-tap']
  },
  {
    id: 'speech',
    label: '说话和文字',
    emoji: '💬',
    scene: '故事屋',
    emojis: ['💬', '🗨️', '📣', '📖', '✏️', '📝', '🔤', '📚'],
    templates: ['sound-echo', 'word-build', 'emoji-hunt', 'rain-catch']
  },
  {
    id: 'animal',
    label: '小动物',
    emoji: '🐾',
    scene: '动物园',
    emojis: ['🐾', '🐕', '🐈', '🐟', '🐦', '🐝', '🐘', '🐇'],
    templates: ['emoji-hunt', 'scene-tap', 'pair-match', 'tap-reveal']
  },
  {
    id: 'body',
    label: '我的身体',
    emoji: '🧒',
    scene: '身体检查台',
    emojis: ['🧒', '👁️', '👂', '🦶', '🦷', '💪', '👃', '🖐️'],
    templates: ['mirror-move', 'emoji-hunt', 'pair-match', 'tap-reveal']
  },
  {
    id: 'feeling',
    label: '心情和想法',
    emoji: '❤️',
    scene: '心情屋',
    emojis: ['❤️', '😊', '😢', '😠', '😴', '🤔', '😮', '🥰'],
    templates: ['tap-reveal', 'emoji-hunt', 'pair-match', 'sound-echo']
  },
  {
    id: 'earth',
    label: '土地和石头',
    emoji: '⛰️',
    scene: '山坡上',
    emojis: ['⛰️', '🪨', '🏞️', '🌋', '🕳️', '🏜️', '🟫', '🧱'],
    templates: ['scene-tap', 'emoji-hunt', 'rain-catch', 'tap-reveal']
  },
  {
    id: 'home',
    label: '房子和屋里',
    emoji: '🏠',
    scene: '屋子里',
    emojis: ['🏠', '🚪', '🪟', '🛏️', '🪑', '🧱', '🛋️', '🪞'],
    templates: ['scene-tap', 'tap-reveal', 'emoji-hunt', 'pair-match']
  },
  {
    id: 'family',
    label: '家里人',
    emoji: '👪',
    scene: '家里',
    emojis: ['👪', '👩', '👧', '👴', '👶', '🤱', '👨', '👵'],
    templates: ['pair-match', 'emoji-hunt', 'tap-reveal', 'scene-tap']
  },
  {
    id: 'time',
    label: '太阳和时间',
    emoji: '☀️',
    scene: '一天里',
    emojis: ['☀️', '🌙', '⏰', '📅', '🌅', '🌇', '⭐', '🕒'],
    templates: ['tap-reveal', 'emoji-hunt', 'pair-match', 'rain-catch']
  },
  {
    id: 'weather',
    label: '天气',
    emoji: '🌦️',
    scene: '天空下',
    emojis: ['🌦️', '🌧️', '❄️', '🌈', '⚡', '☁️', '🌪️', '💨'],
    templates: ['rain-catch', 'scene-tap', 'emoji-hunt', 'tap-reveal']
  },
  {
    id: 'travel',
    label: '走路和出发',
    emoji: '🚶',
    scene: '路上',
    emojis: ['🚶', '🏃', '🚗', '🚢', '🛤️', '🧭', '✈️', '🚲'],
    templates: ['mirror-move', 'scene-tap', 'emoji-hunt', 'rain-catch']
  },
  {
    id: 'food',
    label: '好吃的',
    emoji: '🍚',
    scene: '餐桌上',
    emojis: ['🍚', '🍜', '🍎', '🥣', '🍲', '🥕', '🍞', '🍡'],
    templates: ['scene-tap', 'emoji-hunt', 'pair-match', 'tap-reveal']
  },
  {
    id: 'tool',
    label: '好用的东西',
    emoji: '🔨',
    scene: '工具箱',
    emojis: ['🔨', '🔧', '✂️', '🔑', '🧰', '🪓', '📏', '🪛'],
    templates: ['emoji-hunt', 'tap-reveal', 'scene-tap', 'pair-match']
  },
  {
    id: 'cloth',
    label: '穿在身上',
    emoji: '👕',
    scene: '衣柜里',
    emojis: ['👕', '👖', '🧦', '🧣', '👞', '🧢', '🧥', '🧤'],
    templates: ['pair-match', 'emoji-hunt', 'scene-tap', 'tap-reveal']
  },
  {
    id: 'place',
    label: '城里城外',
    emoji: '🏙️',
    scene: '城里',
    emojis: ['🏙️', '🏘️', '🏫', '🏪', '🛣️', '🏯', '🌉', '⛩️'],
    templates: ['scene-tap', 'emoji-hunt', 'tap-reveal', 'pair-match']
  },
  {
    id: 'number',
    label: '数一数比一比',
    emoji: '🔢',
    scene: '数字乐园',
    emojis: ['🔢', '🧮', '➕', '📏', '⚖️', '🔟', '📊', '🎯'],
    templates: ['count-tap', 'rain-catch', 'emoji-hunt', 'pair-match']
  },
  {
    id: 'money',
    label: '买东西',
    emoji: '🪙',
    scene: '小商店',
    emojis: ['🪙', '💰', '🛒', '🧾', '💵', '🏪', '🎁', '💳'],
    templates: ['count-tap', 'scene-tap', 'emoji-hunt', 'tap-reveal']
  },
  {
    id: 'strength',
    label: '力气和运动',
    emoji: '💪',
    scene: '操场上',
    emojis: ['💪', '🏃', '🏅', '⚽', '🤸', '🚴', '🏋️', '🥇'],
    templates: ['mirror-move', 'rain-catch', 'emoji-hunt', 'scene-tap']
  },
  {
    id: 'color',
    label: '颜色和样子',
    emoji: '🎨',
    scene: '调色板',
    emojis: ['🎨', '🔴', '🟡', '🟢', '🔵', '⚪', '⚫', '🌈'],
    templates: ['pair-match', 'tap-reveal', 'emoji-hunt', 'scene-tap']
  },
  {
    id: 'word',
    label: '常用小词',
    emoji: '🔤',
    scene: '字宝宝乐园',
    emojis: ['🔤', '💭', '❓', '✨', '🔁', '➡️', '🧩', '🔖'],
    templates: ['word-build', 'rain-catch', 'sound-echo', 'emoji-hunt']
  }
]

export const PLAY_THEME_MAP = new Map(PLAY_THEMES.map((t) => [t.id, t]))

/** 推不出主题时用它，永远存在。 */
export const DEFAULT_THEME = 'word'

/**
 * 部首 id → 主题。部首是「这个字讲什么」最省事又最靠谱的线索：
 * 提手旁的字多半是手上的动作，三点水的多半和水有关。
 * 没列进来的部首走单元名，再不行落到 DEFAULT_THEME。
 */
export const RADICAL_THEME = {
  shou: 'hand', you: 'hand', zhua: 'hand', zhuabu: 'hand', cun: 'hand',
  nongdi: 'hand', pu: 'hand', zhibu: 'hand', shupang: 'hand',
  kou: 'mouth', ya: 'mouth', yinbu: 'mouth', gupang: 'mouth', qianbu: 'mouth',
  shui: 'water', liangdian: 'water', shuidi: 'water', chuanbu: 'water',
  mu: 'plant', cao: 'plant', he: 'plant', zhutou: 'plant', maibu: 'plant',
  gua: 'plant', leibu: 'plant', sheng: 'plant',
  ren: 'person', renzitou: 'person', erbu: 'person', shuangren: 'person',
  shibu: 'person', youwang: 'person', bibu: 'person', shenbu: 'person',
  zibu: 'person', shoubu: 'person', shizitou: 'person', shizibu: 'person',
  yan: 'speech', yuebu: 'speech', wenbu: 'speech', erzipang: 'speech',
  quan: 'animal', chong: 'animal', niao: 'animal', ma: 'animal', niu: 'animal',
  yang: 'animal', yu: 'animal', zhipang: 'animal', hutou: 'animal',
  shizhu: 'animal', longbu: 'animal', lubu: 'animal', shubu: 'animal',
  guibu: 'animal', zhuibu: 'animal', yubu: 'animal', feibu: 'animal',
  jiaobu: 'animal', maobu: 'animal',
  yue: 'body', rou: 'body', mubu: 'body', er: 'body', guzi: 'body',
  xuebu: 'body', pibu: 'body', bizi: 'body', mianbu: 'body', yebu: 'body',
  jianbu: 'body', zu: 'body',
  xin: 'feeling', xindi: 'feeling',
  tu: 'earth', shitou: 'earth', shan: 'earth', tian: 'earth', li: 'earth',
  changtou: 'earth',
  mian: 'home', guang: 'home', men: 'home', hubu: 'home', wei: 'home',
  mibao: 'home', tongkuang: 'home', xue: 'home',
  nv: 'family', zi: 'family', muqin: 'family', fu: 'family', lao: 'family',
  ri: 'time', xi: 'time',
  yutou: 'weather', feng: 'weather', qibu: 'weather', bingtou: 'weather',
  zouzhi: 'travel', zou: 'travel', zhizibu: 'travel', che: 'travel',
  zhoubu: 'travel', xingbu: 'travel', zhiwen: 'travel', fang: 'travel',
  shipang: 'food', shidi: 'food', mi: 'food', youzi: 'food', doubu: 'food',
  gubu: 'food', mindi: 'food', xiangzi: 'food', ganzitou: 'food',
  jinzi: 'tool', jinpang: 'tool', daopang: 'tool', gongzi: 'tool',
  gong: 'tool', jin: 'tool', doupang: 'tool', pianbu: 'tool', ge: 'tool',
  jibu: 'tool', sankuang: 'tool', ganbu: 'tool', yongbu: 'tool',
  yibu: 'cloth', yifu: 'cloth', jiaosi: 'cloth', sidi: 'cloth', gebu: 'cloth',
  youer: 'place', danerpang: 'place', gao: 'place',
  yi: 'number', erzi: 'number', shi: 'number', ba: 'number', daoba: 'number',
  shu: 'number', pie: 'number', dian: 'number', jizi: 'number', sibu: 'number',
  xiao: 'number', da: 'number', chang: 'number', yizhe: 'number',
  beibu: 'money',
  lizi: 'strength', bozitou: 'strength',
  se: 'color', qingbu: 'color', bai: 'color', hei: 'color', huang: 'color',
  wang: 'color', sanpie: 'color'
}

/** 部首落空时按单元名里的词猜主题，从上往下第一条命中的算数。 */
export const UNIT_THEME_HINTS = [
  ['动物', 'animal'], ['鸟兽', 'animal'], ['牧场', 'animal'], ['渔村', 'animal'],
  ['身体', 'body'], ['看病', 'body'], ['健康', 'body'],
  ['心情', 'feeling'], ['想一想', 'feeling'],
  ['家人', 'family'], ['名字', 'family'],
  ['天气', 'weather'], ['彩虹', 'weather'], ['云', 'weather'], ['雪', 'weather'],
  ['时间', 'time'], ['季节', 'time'], ['月亮', 'time'], ['星空', 'time'],
  ['吃', 'food'], ['厨房', 'food'], ['灶台', 'food'], ['果', 'food'], ['麦田', 'food'],
  ['学校', 'place'], ['课堂', 'place'], ['城', 'place'], ['集市', 'place'],
  ['古镇', 'place'], ['书院', 'place'], ['城堡', 'place'], ['驿站', 'place'],
  ['说话', 'speech'], ['文章', 'speech'], ['写信', 'speech'], ['讲故事', 'speech'],
  ['数', 'number'], ['量一量', 'number'], ['比一比', 'number'],
  ['颜色', 'color'], ['画画', 'color'], ['音乐', 'color'],
  ['花', 'plant'], ['树木', 'plant'], ['竹林', 'plant'], ['花园', 'plant'],
  ['果园', 'plant'], ['草原', 'plant'], ['树林', 'plant'],
  ['江河', 'water'], ['湖海', 'water'], ['溪边', 'water'], ['湖畔', 'water'],
  ['瀑布', 'water'], ['海湾', 'water'], ['码头', 'water'], ['岛屿', 'water'],
  ['车船', 'water'], ['远方', 'travel'], ['出发', 'travel'], ['去玩', 'travel'],
  ['动起来', 'strength'], ['动作', 'hand'], ['运动会', 'strength'],
  ['穿', 'cloth'], ['商店', 'money'], ['工具', 'tool'],
  ['房子', 'home'], ['家里', 'home'], ['山', 'earth'], ['沙丘', 'earth'],
  ['田野', 'earth'], ['大地', 'earth'], ['荒野', 'earth'], ['礁石', 'earth'],
  ['火山', 'earth'], ['峡谷', 'earth'], ['山洞', 'earth'], ['雪原', 'weather']
]

/** 部首 → 单元名 → 兜底，永远返回一个存在的主题 id。 */
export function themeForChar({ radical, unitName } = {}) {
  const byRadical = RADICAL_THEME[radical]
  if (byRadical && PLAY_THEME_MAP.has(byRadical)) return byRadical
  if (unitName) {
    for (const [word, theme] of UNIT_THEME_HINTS) {
      if (unitName.includes(word)) return theme
    }
  }
  return DEFAULT_THEME
}

/* ----------------------------------------------------------------- 模板 */

/** 选项统一长这样，舞台按 correct 判对错。 */
const option = (key, label, correct, extra = {}) => ({ key, label, correct, ...extra })

/** 干扰用的图标：先用同单元同学的卡片图标，不够再拿主题图标池补。 */
function decoyEmojis(ctx, n) {
  const fromUnit = ctx.siblings.map((s) => s.emoji).filter(Boolean)
  const picked = sampleUnique(fromUnit, n, ctx.rng, [ctx.emoji])
  if (picked.length >= n) return picked
  const rest = sampleUnique(ctx.theme.emojis, n - picked.length, ctx.rng, [ctx.emoji, ...picked])
  return [...picked, ...rest]
}

/**
 * 干扰用的汉字：同单元的同学，笔画最接近的先来。
 * `distinctEmoji` 用于要露出图标的玩法——两张牌画着同一个图标就没法连了。
 */
function decoyChars(ctx, n, { distinctEmoji = false } = {}) {
  const seenEmoji = new Set([ctx.emoji])
  const pool = ctx.siblings
    .filter((s) => s.char !== ctx.char)
    .filter((s) => {
      if (!distinctEmoji) return true
      if (!s.emoji || seenEmoji.has(s.emoji)) return false
      seenEmoji.add(s.emoji)
      return true
    })
    .sort((a, b) => Math.abs(a.strokes - ctx.strokes) - Math.abs(b.strokes - ctx.strokes))
    .slice(0, Math.max(n * 2, 6))
  return sampleUnique(
    pool.map((s) => ({ key: s.char, char: s.char, emoji: s.emoji, pinyin: s.pinyin, strokes: s.strokes })),
    n,
    ctx.rng,
    [ctx.char]
  )
}

/**
 * 11 个模板。`need` 写明这一玩法要什么料（没有料的字生成器不会挑它）：
 *   parts  字源部件   word 组词   sketch 字源小图   count 数得出来的数字
 */
export const PLAY_TEMPLATES = [
  {
    id: 'emoji-hunt',
    name: '找一找',
    interaction: 'pick',
    need: null,
    build(ctx) {
      const decoys = decoyEmojis(ctx, 3)
      const options = shuffled(
        [
          option(ctx.char, ctx.emoji, true, { emoji: ctx.emoji }),
          ...decoys.map((e, i) => option(`d${i}`, e, false, { emoji: e }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `图里有一个是「${ctx.char}」，把它找出来。`),
        prompt: `点中「${ctx.char}」的图`,
        props: { options, target: ctx.emoji, rounds: 1 }
      }
    }
  },
  {
    id: 'scene-tap',
    name: '场景点点看',
    interaction: 'pick',
    need: null,
    build(ctx) {
      const decoys = decoyEmojis(ctx, 4)
      const options = shuffled(
        [
          option(ctx.char, ctx.emoji, true, { emoji: ctx.emoji }),
          ...decoys.map((e, i) => option(`d${i}`, e, false, { emoji: e }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `${ctx.theme.scene}藏着「${ctx.char}」，点出来看看。`),
        prompt: `在${ctx.theme.scene}点出「${ctx.char}」`,
        props: { scene: ctx.theme.emoji, sceneLabel: ctx.theme.scene, options, target: ctx.emoji, rounds: 1 }
      }
    }
  },
  {
    id: 'tap-reveal',
    name: '揭开看看',
    interaction: 'pick',
    need: null,
    build(ctx) {
      const decoys = decoyEmojis(ctx, 2)
      const options = shuffled(
        [
          option(ctx.char, ctx.emoji, true, { emoji: ctx.emoji, reveal: ctx.char }),
          ...decoys.map((e, i) => option(`d${i}`, e, false, { emoji: e, reveal: '？' }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `三张卡片盖住了，「${ctx.char}」躲在其中一张后面。`),
        prompt: '点卡片，把它揭开',
        props: { cover: ctx.theme.emoji, options, target: ctx.char, rounds: 1 }
      }
    }
  },
  {
    id: 'pair-match',
    name: '连一连',
    interaction: 'pick',
    need: null,
    build(ctx) {
      const mates = decoyChars(ctx, 2, { distinctEmoji: true })
      const pairs = shuffled(
        [
          { key: ctx.char, char: ctx.char, emoji: ctx.emoji, correct: true },
          ...mates.map((m) => ({ key: m.char, char: m.char, emoji: m.emoji, correct: false }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `把「${ctx.char}」和它的图连起来。`),
        prompt: `给「${ctx.char}」找到它的图`,
        props: { pairs, target: ctx.char, rounds: 1 }
      }
    }
  },
  {
    id: 'sound-echo',
    name: '听音点亮',
    interaction: 'pick',
    need: null,
    build(ctx) {
      const others = [
        ...new Set(
          decoyChars(ctx, 4)
            .map((m) => m.pinyin)
            .filter((p) => p && p !== ctx.pinyin)
        )
      ].slice(0, 3)
      const options = shuffled(
        [
          option(ctx.pinyin, ctx.pinyin, true),
          ...others.map((p, i) => option(`d${i}-${p}`, p, false))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `「${ctx.char}」念 ${ctx.pinyin}，听一听，哪个是它。`),
        prompt: `点出 ${ctx.pinyin}`,
        props: { say: ctx.char, pinyin: ctx.pinyin, options, rounds: 1 }
      }
    }
  },
  {
    id: 'rain-catch',
    name: '接字雨',
    interaction: 'catch',
    need: null,
    build(ctx) {
      const decoys = decoyChars(ctx, 4)
      const drops = shuffled(
        [
          { key: `t-${ctx.char}`, label: ctx.char, char: ctx.char, hit: true },
          { key: `t2-${ctx.char}`, label: ctx.char, char: ctx.char, hit: true },
          ...decoys.map((d, i) => ({ key: `d${i}-${d.char}`, label: d.char, char: d.char, hit: false }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `字宝宝下雨啦，接住两个「${ctx.char}」。`),
        prompt: `点掉下来的「${ctx.char}」`,
        props: { target: ctx.char, drops, rounds: 2 }
      }
    }
  },
  {
    id: 'count-tap',
    name: '数一数',
    interaction: 'catch',
    need: 'count',
    build(ctx) {
      const count = Number(ctx.extra.count) || 3
      const emoji = ctx.emoji || ctx.theme.emoji
      const items = Array.from({ length: count }, (_, i) => ({
        key: `i${i}`,
        label: emoji,
        emoji,
        hit: true
      }))
      return {
        narration: line(ctx.hint, `「${ctx.char}」就是 ${count} 个，一个一个点着数。`),
        prompt: `点满 ${count} 个`,
        props: { target: ctx.char, count, drops: items, rounds: count }
      }
    }
  },
  {
    id: 'drag-parts',
    name: '拼零件',
    interaction: 'assemble',
    need: 'parts',
    build(ctx) {
      const parts = ctx.extra.parts ?? []
      const spare = ctx.siblings.find((s) => s.radicalGlyph && !parts.includes(s.radicalGlyph))
      const pieces = shuffled(
        [
          ...parts.map((g, i) => ({ key: `p${i}-${g}`, glyph: g, slot: i, correct: true })),
          ...(spare ? [{ key: `x-${spare.radicalGlyph}`, glyph: spare.radicalGlyph, slot: -1, correct: false }] : [])
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `「${ctx.char}」是${parts.join('、')}拼起来的，把零件送回家。`),
        prompt: `把零件拼成「${ctx.char}」`,
        props: { whole: ctx.char, slots: parts, pieces, rounds: parts.length }
      }
    }
  },
  {
    id: 'word-build',
    name: '补词语',
    interaction: 'assemble',
    need: 'word',
    build(ctx) {
      const word = ctx.extra.word ?? ctx.char
      const chars = [...word]
      const slot = Math.max(0, chars.indexOf(ctx.char))
      const decoys = decoyChars(ctx, 2)
      const pieces = shuffled(
        [
          { key: `p-${ctx.char}`, char: ctx.char, correct: true },
          ...decoys.map((d, i) => ({ key: `d${i}-${d.char}`, char: d.char, correct: false }))
        ],
        ctx.rng
      )
      return {
        narration: line(ctx.hint, `「${word}」缺了一个字，把「${ctx.char}」放回去。`),
        prompt: `补齐「${word}」`,
        props: { word, chars, slot, pieces, rounds: 1 }
      }
    }
  },
  {
    id: 'morph-story',
    name: '图变字',
    interaction: 'watch',
    need: 'sketch',
    build(ctx) {
      const kind = ctx.extra.kind ?? 'xiang'
      const frames = [
        { key: 'f0', kind: 'picture', emoji: ctx.emoji, caption: '古人看到的样子' },
        { key: 'f1', kind: 'sketch', char: ctx.char, caption: '照着它画了个记号' },
        { key: 'f2', kind: 'char', char: ctx.char, caption: `今天写成「${ctx.char}」` }
      ]
      return {
        narration: line(ctx.hint, `「${ctx.char}」是照着东西画出来的，点一点看它怎么变。`),
        prompt: '点一点，看它变',
        props: { kind, frames, rounds: frames.length }
      }
    }
  },
  {
    id: 'mirror-move',
    name: '跟着做',
    interaction: 'watch',
    need: null,
    build(ctx) {
      const poses = [ctx.emoji, ...decoyEmojis(ctx, 2)]
      const frames = poses.map((emoji, i) => ({
        key: `m${i}`,
        kind: 'pose',
        emoji,
        caption: i === 0 ? `做一个「${ctx.char}」` : '再来一次'
      }))
      return {
        narration: line(ctx.hint, `跟着做一做「${ctx.char}」这个动作，做一次点一下。`),
        prompt: `跟着做「${ctx.char}」`,
        props: { frames, rounds: frames.length }
      }
    }
  }
]

export const PLAY_TEMPLATE_MAP = new Map(PLAY_TEMPLATES.map((t) => [t.id, t]))

/** 什么料都没有时也一定玩得成的那一个。 */
export const DEFAULT_TEMPLATE = 'emoji-hunt'

/**
 * 挑模板：有料的玩法（字源小图 / 部件 / 组词 / 数得清的数）先进候选，
 * 再加上主题自带的候选，最后按字的种子定一个——同一主题的邻居不会撞卡。
 */
export function templateForChar({ char, theme, extra = {} }) {
  const themeEntry = PLAY_THEME_MAP.get(theme) ?? PLAY_THEME_MAP.get(DEFAULT_THEME)
  // 一到十这十来个字，没有比「点着数一数」更贴的玩法，直接定下来。
  if (extra.count) return 'count-tap'
  const candidates = []
  // 有自己字源小图的字统共三十来个，权重给重一点，免得这批最该
  // 「图变字」的字被通用玩法挤掉。
  if (extra.sketch) candidates.push('morph-story', 'morph-story')
  if (extra.parts?.length >= 2) candidates.push('drag-parts')
  if (extra.word) candidates.push('word-build')
  for (const id of themeEntry.templates) {
    const tpl = PLAY_TEMPLATE_MAP.get(id)
    if (!tpl) continue
    if (tpl.need === 'parts' && !(extra.parts?.length >= 2)) continue
    if (tpl.need === 'word' && !extra.word) continue
    if (tpl.need === 'sketch' && !extra.sketch) continue
    if (tpl.need === 'count' && !extra.count) continue
    candidates.push(id)
  }
  if (!candidates.length) candidates.push(DEFAULT_TEMPLATE)
  return candidates[hashSeed(char) % candidates.length]
}

/* ------------------------------------------------------------- 组装成条目 */

/**
 * 把一行数据展开成完整的 Play 条目。
 *
 * @param {object} row   { char, theme, template, hint, extra }
 * @param {object} info  字表信息 { emoji, pinyin, strokes, radicalGlyph, radicalName,
 *                                  unit, unitName, siblings: [{char, emoji, pinyin, strokes, radicalGlyph}] }
 * @param {object} [meta] { source, templateFallback }
 */
export function buildPlay(row, info = {}, meta = {}) {
  const theme = PLAY_THEME_MAP.get(row.theme) ?? PLAY_THEME_MAP.get(DEFAULT_THEME)
  const template =
    PLAY_TEMPLATE_MAP.get(row.template) ?? PLAY_TEMPLATE_MAP.get(DEFAULT_TEMPLATE)
  const ctx = {
    char: row.char,
    hint: row.hint ?? '',
    extra: row.extra ?? {},
    theme,
    emoji: info.emoji || theme.emoji,
    pinyin: info.pinyin || '',
    strokes: info.strokes ?? 0,
    radicalGlyph: info.radicalGlyph ?? '',
    radicalName: info.radicalName ?? '',
    unitName: info.unitName ?? '',
    siblings: info.siblings ?? [],
    rng: seededRandom(hashSeed(`${row.char}:${template.id}`))
  }
  const built = template.build(ctx)
  return {
    char: row.char,
    theme: theme.id,
    themeLabel: theme.label,
    themeEmoji: theme.emoji,
    template: template.id,
    templateName: template.name,
    interaction: template.interaction,
    emoji: ctx.emoji,
    pinyin: ctx.pinyin,
    narration: built.narration,
    prompt: built.prompt,
    props: built.props,
    steps: built.props.rounds ?? 1,
    skippable: true,
    templateFallback: meta.templateFallback ?? true,
    source: meta.source ?? 'generated'
  }
}
