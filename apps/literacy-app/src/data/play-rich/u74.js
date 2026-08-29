/**
 * 富互动 play 分片 u74 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u74'

export const UNIT_RICH_PLAYS = [
  {
    char: '吴', unit: 'u74', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '找到姓吴的小朋友卡片。',
    props: { hero: '👤', items: [{ item: '👤', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '呆', unit: 'u74', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '他发呆了，戳醒他一下。',
    props: { hero: '😳', color: 'brown', goal: 3 },
    templateFallback: false
  },
  {
    char: '吱', unit: 'u74', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '老鼠吱吱叫，跟着念三声。',
    props: { hero: '🐭', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '吠', unit: 'u74', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小狗吠起来，汪汪三声。',
    props: { hero: '🐕', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '旷', unit: 'u74', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '旷野空荡荡，往远处看。',
    props: { hero: '🌄', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '围', unit: 'u74', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '手拉手围成一个大圈。',
    props: { hero: '⭕', items: ['⭕', '⭕', '⭕', '⭕', '⭕'], goal: 5 },
    templateFallback: false
  },
  {
    char: '呀', unit: 'u74', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '呀！吓了一跳，点感叹号。',
    props: { hero: '❗', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '困', unit: 'u74', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '困得睁不开眼，打个哈欠。',
    props: { hero: '😴', target: '😴', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '吵', unit: 'u74', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '太吵了，把音量按下去。',
    props: { hero: '📢', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '串', unit: 'u74', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '糖葫芦串成一串，数一数。',
    props: { hero: '🍡', parts: ['🧩', '🌱', '🍡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '呐', unit: 'u74', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '摇旗呐喊，大声喊三声。',
    props: { hero: '📣', sound: '咔咔', goal: 3 },
    templateFallback: false
  },
  {
    char: '吟', unit: 'u74', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '轻轻吟诵古诗，点亮诗行。',
    props: { hero: '📜', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '呛', unit: 'u74', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '烟味呛鼻子，捂住鼻子。',
    props: { hero: '😷', items: ['😷', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '吻', unit: 'u74', theme: 'number',
    template: 'sound-tap', interaction: 'tap',
    narration: '轻轻吻一下脸颊，再见。',
    props: { hero: '😘', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '吹', unit: 'u74', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '一口气吹灭三根蜡烛。',
    props: { hero: '🎂', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '呜', unit: 'u74', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '火车呜呜响，跟着学三声。',
    props: { hero: '🚂', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '吧', unit: 'u74', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '好吧，点头答应这一回。',
    props: { hero: '💬', items: [{ item: '💬', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '吼', unit: 'u74', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '狮子大吼一声，山谷回响。',
    props: { hero: '🦁', stages: ['❄️', '🦁', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '囤', unit: 'u74', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '松鼠囤松果，藏进洞里。',
    props: { hero: '🐿️', items: ['🌙', '🎈', '🧩'], tool: '🐿️', goal: 3 },
    templateFallback: false
  },
  {
    char: '岗', unit: 'u74', theme: 'shape',
    template: 'tap-reveal', interaction: 'tap',
    narration: '站上岗位，认真守着岗。',
    props: { hero: '👮', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
