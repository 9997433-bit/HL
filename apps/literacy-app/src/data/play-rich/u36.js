/**
 * 富互动 play 分片 u36 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u36'

export const UNIT_RICH_PLAYS = [
  {
    char: '汽', unit: 'u36', theme: 'object',
    template: 'grow-tap', interaction: 'tap',
    narration: '水烧开了，冒出一团白汽。',
    props: { hero: '🚗', stages: ['💧', '♨️', '☁️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '轨', unit: 'u36', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '两条铁轨并排，火车顺着走。',
    props: { hero: '🚂', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '道', unit: 'u36', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '沿着大道一直往前，别拐弯。',
    props: { hero: '🛣️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '途', unit: 'u36', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '路上还远着呢，再往前赶一段。',
    props: { hero: '🎒', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '程', unit: 'u36', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一段一段记路程，走满四段。',
    props: { hero: '📍', items: ['📍', '📍', '📍', '📍'], goal: 4 },
    templateFallback: false
  },
  {
    char: '航', unit: 'u36', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大船起航，慢慢驶向大海去。',
    props: { hero: '🚢', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '舰', unit: 'u36', theme: 'object',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一艘最大？找出那艘军舰。',
    props: { hero: '🚢', target: '🚢', decoys: ['🛶', '⛵', '🛥️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '舱', unit: 'u36', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '钻进船舱看看，里面有什么。',
    props: { hero: '🛳️', items: ['🛏️', '🪟', '🧳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '帆', unit: 'u36', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '风一吹，把帆往上升起来。',
    props: { hero: '⛵', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '桨', unit: 'u36', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手划桨，一下一下往后拨。',
    props: { hero: '🛶', dir: 'left', goal: 4 },
    templateFallback: false
  },
  {
    char: '舵', unit: 'u36', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '握住舵轮，把船头掉个方向。',
    props: { hero: '🛞', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '轿', unit: 'u36', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '小轿车里坐得下谁？点点看。',
    props: { hero: '🚙', items: ['👨', '👩', '🧒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '卡', unit: 'u36', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '刷一下卡，门就打开了。',
    props: { hero: '💳', items: ['💳', '🎫', '🔑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '货', unit: 'u36', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '装车啦，重货轻货分开放。',
    props: { hero: '📦', items: [{ item: '🧱', bucket: '重货' }, { item: '🪑', bucket: '重货' }, { item: '🧸', bucket: '轻货' }, { item: '🪶', bucket: '轻货' }], buckets: [{ label: '重货', emoji: '📦' }, { label: '轻货', emoji: '🎈' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '载', unit: 'u36', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '车上装了几箱？一箱一箱数。',
    props: { hero: '🚚', items: ['📦', '📦', '📦', '📦'], goal: 4 },
    templateFallback: false
  },
  {
    char: '运', unit: 'u36', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把箱子从这头运到那头去。',
    props: { hero: '📦', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '输', unit: 'u36', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '水从这一头输到那一头。',
    props: { hero: '🚰', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '驾', unit: 'u36', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '握好方向盘，驾着车往前开。',
    props: { hero: '🚗', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '驶', unit: 'u36', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '车子飞快驶过，一眨眼没影。',
    props: { hero: '🚙', dir: 'right', goal: 5 },
    templateFallback: false
  },
  {
    char: '乘', unit: 'u36', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '乘车要排队，点点该做的事。',
    props: { hero: '🚌', items: ['🚏', '🎫', '🪑'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
