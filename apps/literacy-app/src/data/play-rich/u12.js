/**
 * 富互动 play 分片 u12 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u12'

export const UNIT_RICH_PLAYS = [
  {
    char: '左', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往左边挥挥手，左手举起来。',
    props: { hero: '👈', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '右', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往右边挥挥手，右手举起来。',
    props: { hero: '👉', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '多', unit: 'u12', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哪一堆多？把多的挑出来。',
    props: { hero: '➕', items: [{ item: '🍎🍎🍎', bucket: '多' }, { item: '🍬🍬🍬', bucket: '多' }, { item: '🍎', bucket: '少' }, { item: '🍬', bucket: '少' }], buckets: [{ label: '多', emoji: '➕' }, { label: '少', emoji: '➖' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '少', unit: 'u12', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '吃掉几个，果子就变少了。',
    props: { hero: '🍓', items: ['🍓', '🍓', '🍓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '门', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推开大门，吱呀一声请进。',
    props: { hero: '🚪', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '车', unit: 'u12', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '开着小车沿着马路往前开。',
    props: { hero: '🚗', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '足', unit: 'u12', theme: 'body',
    template: 'count-tap', interaction: 'tap',
    narration: '数数小脚丫，一二，两只脚。',
    props: { hero: '🦶', items: ['🦶', '🦶'], goal: 2 },
    templateFallback: false
  },
  {
    char: '前', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '向前走三步，看看前面有什么。',
    props: { hero: '🚩', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '后', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往后退一退，站到后面去。',
    props: { hero: '🔙', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '里', unit: 'u12', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把玩具放进盒子里面。',
    props: { hero: '📥', items: [{ item: '🧸', bucket: '里面' }, { item: '🧩', bucket: '里面' }, { item: '🍂', bucket: '外面' }, { item: '🪨', bucket: '外面' }], buckets: [{ label: '里面', emoji: '📥' }, { label: '外面', emoji: '📤' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '外', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推门走到外面，外面太阳真好。',
    props: { hero: '🌞', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '边', unit: 'u12', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '左边右边，把东西摆到对的一边。',
    props: { hero: '🧭', items: [{ item: '🍎', bucket: '左边' }, { item: '🧸', bucket: '左边' }, { item: '🍐', bucket: '右边' }, { item: '🎈', bucket: '右边' }], buckets: [{ label: '左边', emoji: '👈' }, { label: '右边', emoji: '👉' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
