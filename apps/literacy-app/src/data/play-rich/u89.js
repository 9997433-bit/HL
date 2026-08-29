/**
 * 富互动 play 分片 u89 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u89'

export const UNIT_RICH_PLAYS = [
  {
    char: '细', unit: 'u89', theme: 'weather',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '用细线缝，针脚要密。',
    props: { hero: '🧵', items: ['🧵', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '驻', unit: 'u89', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '小旗驻扎在营地，插好。',
    props: { hero: '🚩', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '绊', unit: 'u89', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '脚被绳子绊住，解开它。',
    props: { hero: '🪢', stages: ['🪵', '🪢', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '驼', unit: 'u89', theme: 'animal',
    template: 'pair-match', interaction: 'drag',
    narration: '骆驼驼着货，走过沙漠。',
    props: { hero: '🐫', pairs: [{ a: '🐫', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🐫' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '绍', unit: 'u89', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '介绍一下自己，挥挥手。',
    props: { hero: '🙋', items: [{ item: '🙋', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '经', unit: 'u89', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '经过这座桥，走到对岸。',
    props: { hero: '📚', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '贯', unit: 'u89', theme: 'number',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '线贯穿珠子，串成项链。',
    props: { hero: '🔗', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '珍', unit: 'u89', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '珍贵的宝石，小心捧好。',
    props: { hero: '💎', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '玲', unit: 'u89', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小铃铛玲珑响，摇三下。',
    props: { hero: '🔔', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '珊', unit: 'u89', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '海底珊瑚，找出粉红的。',
    props: { hero: '🪸', items: ['🪸', '🪸', '🪸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '玻', unit: 'u89', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '擦亮玻璃，窗明几净。',
    props: { hero: '🪟', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '型', unit: 'u89', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '按模型拼，拼成小飞机。',
    props: { hero: '🧩', target: '🧩', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '持', unit: 'u89', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '坚持举着旗，别放下。',
    props: { hero: '✊', stages: ['📦', '✊', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拷', unit: 'u89', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '文件拷贝一份，拖过去。',
    props: { hero: '💾', parts: ['🧩', '🌱', '💾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拱', unit: 'u89', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '拱桥弯弯，走过桥顶。',
    props: { hero: '🌉', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '项', unit: 'u89', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '完成这一项，勾掉清单。',
    props: { hero: '📋', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '垮', unit: 'u89', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '沙堡垮了，重新堆起来。',
    props: { hero: '🌊', items: ['🌊', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '挎', unit: 'u89', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '挎上小书包，出门上学。',
    props: { hero: '🎒', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '政', unit: 'u89', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '市政厅升旗，敬礼一下。',
    props: { hero: '🏛️', stages: ['🪵', '🏛️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '赴', unit: 'u89', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '赴约去公园，朝那边跑。',
    props: { hero: '🏃', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
