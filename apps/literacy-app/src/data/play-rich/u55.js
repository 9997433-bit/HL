/**
 * 富互动 play 分片 u55 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u55'

export const UNIT_RICH_PLAYS = [
  {
    char: '寸', unit: 'u55', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一寸一寸量过去，量满四寸。',
    props: { hero: '📏', items: ['📏', '📏', '📏', '📏'], goal: 4 },
    templateFallback: false
  },
  {
    char: '亩', unit: 'u55', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '一亩地种菜，一亩地种花。',
    props: { hero: '🌾', items: [{ item: '🥕', bucket: '菜地' }, { item: '🥦', bucket: '菜地' }, { item: '🌻', bucket: '花地' }, { item: '🌹', bucket: '花地' }], buckets: [{ label: '菜地', emoji: '🥬' }, { label: '花地', emoji: '🌷' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '升', unit: 'u55', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '水一点点升上来，满一升。',
    props: { hero: '🥛', stages: ['🥛', '🥤', '🪣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '斗', unit: 'u55', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '用斗量米，量满三斗。',
    props: { hero: '🥣', items: ['🥣', '🥣', '🥣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '度', unit: 'u55', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '温度一格格升，越来越热。',
    props: { hero: '🌡️', stages: ['🌡️', '☀️', '🔥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '副', unit: 'u55', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '一副手套两只，配成一副。',
    props: { hero: '👓', pairs: [{ a: '🧤', b: '🧤' }, { a: '👓', b: '👓' }, { a: '🥢', b: '🥢' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '使', unit: 'u55', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '使一使这些工具，点开试试。',
    props: { hero: '🧰', items: ['🔨', '🪛', '🔧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '准', unit: 'u55', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一箭射得最准？中靶心的。',
    props: { hero: '🎯', target: '🎯', decoys: ['🟥', '🟩', '🟦'], goal: 1 },
    templateFallback: false
  },
  {
    char: '若', unit: 'u55', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '若是下雨就打伞，配一配。',
    props: { hero: '❔', pairs: [{ a: '🌧️', b: '☂️' }, { a: '☀️', b: '🕶️' }, { a: '❄️', b: '🧣' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '虽', unit: 'u55', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '虽然摔了一跤，还是站起来。',
    props: { hero: '↩️', stages: ['😣', '🧍', '😊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '然', unit: 'u55', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '先这样，然后再往前一步。',
    props: { hero: '➡️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '却', unit: 'u55', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '想往前，却被拉了回来。',
    props: { hero: '↔️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '仍', unit: 'u55', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '停了一下，仍旧接着跳三下。',
    props: { hero: '🔁', items: ['🦘', '🦘', '🦘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '竟', unit: 'u55', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盖子一掀，竟然是它。',
    props: { hero: '😲', items: ['🐸', '🎈', '🍰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '极', unit: 'u55', theme: 'number',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个最大？挑出极大的那个。',
    props: { hero: '🥇', target: '🐘', decoys: ['🐁', '🐜', '🐝'], goal: 1 },
    templateFallback: false
  },
  {
    char: '挺', unit: 'u55', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把胸脯一挺，站得笔直。',
    props: { hero: '🧍', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '稍', unit: 'u55', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '稍等一下，数两下就好。',
    props: { hero: '⏱️', items: ['⏱️', '⏱️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '略', unit: 'u55', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '太多了，略去两个不数。',
    props: { hero: '📉', items: ['🔵', '🔵'], goal: 2 },
    templateFallback: false
  },
  {
    char: '甚', unit: 'u55', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '一次比一次甚，声音越来越大。',
    props: { hero: '❗', stages: ['🔈', '🔉', '🔊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '各', unit: 'u55', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '各归各位：红的一边，蓝的一边。',
    props: { hero: '🔢', items: [{ item: '🍎', bucket: '红' }, { item: '🌹', bucket: '红' }, { item: '🫐', bucket: '蓝' }, { item: '🧊', bucket: '蓝' }], buckets: [{ label: '红', emoji: '🟥' }, { label: '蓝', emoji: '🟦' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
