/**
 * 富互动 play 分片 u91 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u91'

export const UNIT_RICH_PLAYS = [
  {
    char: '荡', unit: 'u91', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '秋千荡起来，越荡越高。',
    props: { hero: '🛝', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '荣', unit: 'u91', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '戴上光荣花，站上领奖台。',
    props: { hero: '🏅', stages: ['🎈', '🏅', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '胡', unit: 'u91', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '摸摸胡子，梳理整齐。',
    props: { hero: '🧔', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '荔', unit: 'u91', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '剥开荔枝，露出白肉。',
    props: { hero: '🍒', target: '🍒', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '南', unit: 'u91', theme: 'shape',
    template: 'pair-match', interaction: 'drag',
    narration: '指南针指向南，转过去。',
    props: { hero: '🧭', pairs: [{ a: '🧭', b: '📦' }, { a: '🎯', b: '💧' }, { a: '📦', b: '🧭' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '标', unit: 'u91', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '贴上标记，别认错了。',
    props: { hero: '🏷️', parts: ['🧩', '🌱', '🏷️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '柑', unit: 'u91', theme: 'food',
    template: 'trace-path', interaction: 'drag',
    narration: '剥开柑橘，分瓣吃掉。',
    props: { hero: '🍊', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '枯', unit: 'u91', theme: 'nature',
    template: 'sort-buckets', interaction: 'drag',
    narration: '枯叶掉了，扫成一堆。',
    props: { hero: '🍂', items: [{ item: '🍂', bucket: '左' }, { item: '🌙', bucket: '左' }, { item: '🎯', bucket: '右' }, { item: '🪵', bucket: '右' }], buckets: [{ label: '左', emoji: '🎯' }, { label: '右', emoji: '🪵' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '柄', unit: 'u91', theme: 'body',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '握住刀柄，切下一块。',
    props: { hero: '🍳', items: ['🍳', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '栋', unit: 'u91', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '一栋大楼盖好，升旗庆祝。',
    props: { hero: '🏢', items: ['🪨', '🔥', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '相', unit: 'u91', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '两人对视，相互点头。',
    props: { hero: '👀', pairs: [{ a: '👀', b: '🪵' }, { a: '❄️', b: '🎈' }, { a: '🪵', b: '👀' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '柏', unit: 'u91', theme: 'nature',
    template: 'pair-match', interaction: 'drag',
    narration: '柏树四季绿，摸一摸叶。',
    props: { hero: '🌲', pairs: [{ a: '🌲', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌲' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '栏', unit: 'u91', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '爬上栏杆边，往下看。',
    props: { hero: '🚧', items: [{ item: '🚧', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '柠', unit: 'u91', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '挤柠檬汁，酸得眨眼。',
    props: { hero: '🍋', color: 'khaki', goal: 3 },
    templateFallback: false
  },
  {
    char: '威', unit: 'u91', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '威风的狮子，昂首站立。',
    props: { hero: '🦁', items: ['🌙', '🎈', '🧩'], tool: '🦁', goal: 3 },
    templateFallback: false
  },
  {
    char: '歪', unit: 'u91', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '帽子歪了，扶正它。',
    props: { hero: '📐', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '研', unit: 'u91', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用放大镜研究小昆虫。',
    props: { hero: '🔬', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '砖', unit: 'u91', theme: 'shape',
    template: 'scene-poke', interaction: 'tap',
    narration: '一块砖一块砖，砌墙。',
    props: { hero: '🧱', items: ['🎈', '📦', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '厘', unit: 'u91', theme: 'number',
    template: 'tap-reveal', interaction: 'tap',
    narration: '量一量，正好三厘米。',
    props: { hero: '📏', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '砂', unit: 'u91', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '砂子漏过指缝，接住它。',
    props: { hero: '🏖️', target: '🏖️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
