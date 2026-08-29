/**
 * 富互动 play 分片 u72 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u72'

export const UNIT_RICH_PLAYS = [
  {
    char: '扮', unit: 'u72', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '换上面具，扮成小兔子。',
    props: { hero: '🎭', stages: ['📦', '🎭', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抢', unit: 'u72', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '快！把球抢到手心里。',
    props: { hero: '🏃', parts: ['🧩', '🌱', '🏃'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坎', unit: 'u72', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '跨过门坎，一步迈进去。',
    props: { hero: '🪜', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '抛', unit: 'u72', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把皮球往上抛得高高的。',
    props: { hero: '🏐', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '坑', unit: 'u72', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小心地上的坑，绕过去。',
    props: { hero: '🕳️', items: ['🕳️', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抗', unit: 'u72', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '举起盾牌，挡住这一击。',
    props: { hero: '🛡️', pairs: [{ a: '🛡️', b: '🪨' }, { a: '🔥', b: '⭐' }, { a: '🪨', b: '🛡️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '坊', unit: 'u72', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '走进小作坊，看看在做什么。',
    props: { hero: '🏭', items: ['🪵', '❄️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '壳', unit: 'u72', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '敲开蛋壳，小鸡出来了。',
    props: { hero: '🐚', pairs: [{ a: '🐚', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🐚' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '志', unit: 'u72', theme: 'body',
    template: 'sort-buckets', interaction: 'drag',
    narration: '心里立下志向，点亮星星。',
    props: { hero: '🎯', items: [{ item: '🎯', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '扭', unit: 'u72', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '身子一扭，转过身来。',
    props: { hero: '🔄', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '芙', unit: 'u72', theme: 'nature',
    template: 'sound-tap', interaction: 'tap',
    narration: '池塘里，芙蓉花开了。',
    props: { hero: '🌺', sound: '咚咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '苇', unit: 'u72', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '风吹芦苇，叶子沙沙晃。',
    props: { hero: '🌾', stages: ['☀️', '🌾', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '芹', unit: 'u72', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '洗净芹菜，一根根数清。',
    props: { hero: '🥬', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '芬', unit: 'u72', theme: 'color',
    template: 'count-tap', interaction: 'tap',
    narration: '闻一闻，花香芬芬的。',
    props: { hero: '🌸', items: ['🌸', '🌸', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '苍', unit: 'u72', theme: 'color',
    template: 'tap-reveal', interaction: 'tap',
    narration: '给苍松涂上深绿的颜色。',
    props: { hero: '🌲', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '芳', unit: 'u72', theme: 'color',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '花瓣散发芳香，闻一闻。',
    props: { hero: '🌷', target: '🌷', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '严', unit: 'u72', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '板起脸，严格检查一遍。',
    props: { hero: '😐', stages: ['📦', '😐', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '芦', unit: 'u72', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '芦苇荡里藏着谁？找找。',
    props: { hero: '🌾', parts: ['🧩', '🌱', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '芯', unit: 'u72', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '换上新笔芯，又能写了。',
    props: { hero: '✏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '劳', unit: 'u72', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '动手劳动，把地扫干净。',
    props: { hero: '🧹', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
