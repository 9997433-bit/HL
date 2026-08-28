/**
 * 富互动 play 分片 u29 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u29'

export const UNIT_RICH_PLAYS = [
  {
    char: '周', unit: 'u29', theme: 'time',
    template: 'trace-path', interaction: 'drag',
    narration: '从星期一绕到星期天，就是一周。',
    props: { hero: '🔄', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '午', unit: 'u29', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳升到头顶上，正午到了。',
    props: { hero: '🕛', stages: ['🌅', '🌞', '午'], goal: 3 },
    templateFallback: false
  },
  {
    char: '晨', unit: 'u29', theme: 'time',
    template: 'grow-tap', interaction: 'tap',
    narration: '天刚亮，公鸡把早晨叫醒了。',
    props: { hero: '🌅', stages: ['🌑', '🌄', '🐓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '夜', unit: 'u29', theme: 'time',
    template: 'tap-reveal', interaction: 'tap',
    narration: '夜深了，谁还在外面醒着。',
    props: { hero: '🌃', items: ['🦉', '🦇', '🌟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '昨', unit: 'u29', theme: 'time',
    template: 'sort-buckets', interaction: 'drag',
    narration: '昨天的事归昨天，今天的归今天。',
    props: { hero: '⏮️', items: [{ item: '🎂', bucket: '昨天' }, { item: '🌧️', bucket: '昨天' }, { item: '🏫', bucket: '今天' }, { item: '☀️', bucket: '今天' }], buckets: [{ label: '昨天', emoji: '⏮️' }, { label: '今天', emoji: '📍' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '秒', unit: 'u29', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '一秒滴答一下，数满五秒。',
    props: { hero: '⏱️', items: ['⏱️', '⏱️', '⏱️', '⏱️', '⏱️'], goal: 5 },
    templateFallback: false
  },
  {
    char: '钟', unit: 'u29', theme: 'time',
    template: 'sound-tap', interaction: 'tap',
    narration: '大钟当当响，告诉大家几点。',
    props: { hero: '🕰️', sound: '当当', goal: 3 },
    templateFallback: false
  },
  {
    char: '点', unit: 'u29', theme: 'time',
    template: 'pair-match', interaction: 'drag',
    narration: '把钟面和几点钟连到一起。',
    props: { hero: '🕒', pairs: [{ a: '🕐', b: '1' }, { a: '🕑', b: '2' }, { a: '🕒', b: '3' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '期', unit: 'u29', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '翻开日历，这星期有什么事。',
    props: { hero: '🗓️', items: ['🎂', '🏫', '⚽'], goal: 3 },
    templateFallback: false
  },
  {
    char: '假', unit: 'u29', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '放假啦，假期里想做点什么。',
    props: { hero: '🏖️', items: ['🎣', '🎠', '📕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '节', unit: 'u29', theme: 'time',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '过节了，烟花一朵一朵点开。',
    props: { hero: '🎏', items: ['🎆', '🎆', '🎆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忙', unit: 'u29', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '事情好多，一件一件做完它。',
    props: { hero: '😵', items: ['📚', '🧹', '🍽️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '常', unit: 'u29', theme: 'word',
    template: 'count-tap', interaction: 'tap',
    narration: '天天都做的事叫常，点满五天。',
    props: { hero: '🔁', items: ['🪥', '🪥', '🪥', '🪥', '🪥'], goal: 5 },
    templateFallback: false
  },
  {
    char: '总', unit: 'u29', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '两堆合到一起，数出总共几个。',
    props: { hero: '🧮', items: ['🍎', '🍎', '🍐', '🍐', '🍐'], goal: 5 },
    templateFallback: false
  },
  {
    char: '已', unit: 'u29', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '已经做完的打勾，没做的等着。',
    props: { hero: '✔️', items: [{ item: '🪥', bucket: '已做完' }, { item: '🍚', bucket: '已做完' }, { item: '📚', bucket: '还没做' }, { item: '🧹', bucket: '还没做' }], buckets: [{ label: '已做完', emoji: '✅' }, { label: '还没做', emoji: '⏳' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '才', unit: 'u29', theme: 'word',
    template: 'grow-tap', interaction: 'tap',
    narration: '等呀等，太阳才慢慢升起来。',
    props: { hero: '⏳', stages: ['🌑', '🌒', '🌅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '刚', unit: 'u29', theme: 'word',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个是刚出炉的？点热乎的。',
    props: { hero: '🆕', target: '🍞', decoys: ['🧊', '🥶', '❄️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '再', unit: 'u29', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '再来一次，把球再推出去。',
    props: { hero: '⚽', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
