/**
 * 富互动 play 分片 u40 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u40'

export const UNIT_RICH_PLAYS = [
  {
    char: '斧', unit: 'u40', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '举起斧头，把木头劈成两半。',
    props: { hero: '🪓', dir: 'down', goal: 4 },
    templateFallback: false
  },
  {
    char: '锯', unit: 'u40', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '锯子来回拉，木板断成两截。',
    props: { hero: '🪚', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '锤', unit: 'u40', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '咚咚咚，把钉子锤进去三下。',
    props: { hero: '🔨', items: ['🔨', '🔨', '🔨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '钉', unit: 'u40', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '四颗钉子钉住板子，稳稳的。',
    props: { hero: '📌', parts: ['📌', '📌', '📌', '📌'], goal: 4 },
    templateFallback: false
  },
  {
    char: '钻', unit: 'u40', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '电钻转起来，在墙上钻个洞。',
    props: { hero: '🪛', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '尺', unit: 'u40', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '拿尺子比一比，画一条直线。',
    props: { hero: '📏', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '秤', unit: 'u40', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '放上秤称一称，沉的往下压。',
    props: { hero: '⚖️', items: [{ item: '🍉', bucket: '沉' }, { item: '🪨', bucket: '沉' }, { item: '🍃', bucket: '飘' }, { item: '🎈', bucket: '飘' }], buckets: [{ label: '沉', emoji: '⬇️' }, { label: '飘', emoji: '⬆️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '绳', unit: 'u40', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '长绳子一头，拉到另一头去。',
    props: { hero: '🪢', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '索', unit: 'u40', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '抓住绳索，手脚并用往上爬。',
    props: { hero: '🧗', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '链', unit: 'u40', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '一环扣一环，连成一条链。',
    props: { hero: '⛓️', parts: ['⭕', '⭕', '⭕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '锁', unit: 'u40', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '咔哒，把锁往下一按就锁好。',
    props: { hero: '🔒', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '钥', unit: 'u40', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '每把钥匙配一把锁，试试看。',
    props: { hero: '🔑', pairs: [{ a: '🔑', b: '🔒' }, { a: '🗝️', b: '🔐' }, { a: '🔑', b: '🧳' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '桶', unit: 'u40', theme: 'object',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '水桶里的水，一瓢一瓢舀完。',
    props: { hero: '🪣', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '盆', unit: 'u40', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '洗脸盆边放着什么？点点看。',
    props: { hero: '🛁', items: ['🧼', '🧽', '🪥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '篮', unit: 'u40', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '篮子里装了几样水果？数数。',
    props: { hero: '🧺', items: ['🍎', '🍌', '🍇', '🍐'], goal: 4 },
    templateFallback: false
  },
  {
    char: '筐', unit: 'u40', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把菜和果子分别放进两个筐。',
    props: { hero: '🧺', items: [{ item: '🥕', bucket: '菜筐' }, { item: '🥦', bucket: '菜筐' }, { item: '🍐', bucket: '果筐' }, { item: '🍇', bucket: '果筐' }], buckets: [{ label: '菜筐', emoji: '🥬' }, { label: '果筐', emoji: '🍎' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '箱', unit: 'u40', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打开箱子，看看里面装了啥。',
    props: { hero: '📦', items: ['👕', '🧸', '📕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '柜', unit: 'u40', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '衣服挂衣柜，碗筷收进碗柜。',
    props: { hero: '🗄️', items: [{ item: '👕', bucket: '衣柜' }, { item: '👖', bucket: '衣柜' }, { item: '🥣', bucket: '碗柜' }, { item: '🥢', bucket: '碗柜' }], buckets: [{ label: '衣柜', emoji: '🧥' }, { label: '碗柜', emoji: '🍽️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '架', unit: 'u40', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '一层一层搭个架子，好放书。',
    props: { hero: '🗄️', parts: ['🟫', '🟫', '🟫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '具', unit: 'u40', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '工具箱里的家伙，一样样点。',
    props: { hero: '🧰', items: ['🔨', '🔧', '🪛'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
