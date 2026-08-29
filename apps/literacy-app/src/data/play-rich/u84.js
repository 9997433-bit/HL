/**
 * 富互动 play 分片 u84 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u84'

export const UNIT_RICH_PLAYS = [
  {
    char: '败', unit: 'u84', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '这一局败了，再来一局。',
    props: { hero: '😔', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '账', unit: 'u84', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '翻开账本，记下今天的数。',
    props: { hero: '🧾', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '贩', unit: 'u84', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小贩摆摊，卖出三件货。',
    props: { hero: '🧺', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '钓', unit: 'u84', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '甩出鱼钩，钓上小鱼。',
    props: { hero: '🎣', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '制', unit: 'u84', theme: 'school',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '零件制成小汽车，拼好。',
    props: { hero: '🏭', items: ['🏭', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '氛', unit: 'u84', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '派对气氛好，点亮气球。',
    props: { hero: '🎉', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '垂', unit: 'u84', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '柳枝下垂，轻轻晃一晃。',
    props: { hero: '🌾', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '物', unit: 'u84', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '这些物品分类，放进筐。',
    props: { hero: '📦', pairs: [{ a: '📦', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '📦' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '乖', unit: 'u84', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '乖乖坐好，听老师讲。',
    props: { hero: '😇', items: [{ item: '😇', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '刮', unit: 'u84', theme: 'weather',
    template: 'sound-tap', interaction: 'tap',
    narration: '大风刮过来，抓紧衣角。',
    props: { hero: '🌬️', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '秆', unit: 'u84', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '麦秆立起来，金灿灿的。',
    props: { hero: '🌾', items: ['🌙', '🎈', '🧩'], tool: '🌾', goal: 3 },
    templateFallback: false
  },
  {
    char: '季', unit: 'u84', theme: 'time',
    template: 'sort-buckets', interaction: 'drag',
    narration: '四季转盘转，停在秋天。',
    props: { hero: '🍂', items: [{ item: '🍂', bucket: '左' }, { item: '🔔', bucket: '左' }, { item: '☀️', bucket: '右' }, { item: '🎁', bucket: '右' }], buckets: [{ label: '左', emoji: '☀️' }, { label: '右', emoji: '🎁' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '委', unit: 'u84', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把任务委托给小助手。',
    props: { hero: '📋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '佳', unit: 'u84', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '佳节到了，挂上红灯笼。',
    props: { hero: '🌟', items: ['🌟', '🌟', '🌟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '岳', unit: 'u84', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '爬上高高的山岳，看风景。',
    props: { hero: '⛰️', stages: ['🎁', '⛰️', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '供', unit: 'u84', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '把水果供到桌上，分享。',
    props: { hero: '🤲', stages: ['🔑', '🤲', '🪵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '侄', unit: 'u84', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '侄子来串门，递上糖果。',
    props: { hero: '👦', stages: ['📦', '👦', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '侦', unit: 'u84', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '戴上放大镜，侦察线索。',
    props: { hero: '🔍', parts: ['🧩', '🌱', '🔍'], goal: 3 },
    templateFallback: false
  },
  {
    char: '凭', unit: 'u84', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '凭这张票，才能进场。',
    props: { hero: '🎫', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '佩', unit: 'u84', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '胸前佩戴奖章，亮闪闪。',
    props: { hero: '🎖️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
