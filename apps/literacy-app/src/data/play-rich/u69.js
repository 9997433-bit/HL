/**
 * 富互动 play 分片 u69 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u69'

export const UNIT_RICH_PLAYS = [
  {
    char: '杂', unit: 'u69', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '东西太杂，分成吃的和玩的。',
    props: { hero: '🧺', items: [{ item: '🍞', bucket: '吃的' }, { item: '🍌', bucket: '吃的' }, { item: '🪀', bucket: '玩的' }, { item: '🎈', bucket: '玩的' }], buckets: [{ label: '吃的', emoji: '🍎' }, { label: '玩的', emoji: '🧸' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '旬', unit: 'u69', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '十天算一旬，翻过三个旬。',
    props: { hero: '📅', items: ['🔟', '🔟', '🔟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '旨', unit: 'u69', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '话里的主旨在哪？找出靶心。',
    props: { hero: '🎯', target: '🎯', decoys: ['🟠', '🟡', '🟢'], goal: 1 },
    templateFallback: false
  },
  {
    char: '旭', unit: 'u69', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '旭日一点点爬上山头。',
    props: { hero: '🌅', stages: ['🌌', '🌄', '🌅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '负', unit: 'u69', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '背上小书包，负在肩膀上。',
    props: { hero: '🎒', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '争', unit: 'u69', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '礼物掉下来，快去争一个。',
    props: { hero: '🙋', items: ['🎁', '🎁', '🎁'], tool: '🧺', goal: 3 },
    templateFallback: false
  },
  {
    char: '壮', unit: 'u69', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '吃得好睡得香，长得壮壮的。',
    props: { hero: '💪', stages: ['🧒', '💪', '🏋️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '冲', unit: 'u69', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '水一冲，泡沫都冲走了。',
    props: { hero: '🚿', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '妆', unit: 'u69', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '化个小妆，脸上点点腮红。',
    props: { hero: '💄', color: '腮红', goal: 3 },
    templateFallback: false
  },
  {
    char: '庄', unit: 'u69', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '村庄里有什么？挨个点点。',
    props: { hero: '🏡', items: ['🐓', '🌾', '🚜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '亦', unit: 'u69', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '我做一下，你也亦做三下。',
    props: { hero: '🔁', items: ['🔁', '🔁', '🔁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '刘', unit: 'u69', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '门上贴着刘字，敲开瞧瞧。',
    props: { hero: '👤', items: ['🚪', '🏮', '👋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '交', unit: 'u69', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '把东西交给对方，配成一对。',
    props: { hero: '🤝', pairs: [{ a: '📕', b: '🧒' }, { a: '🍎', b: '👧' }, { a: '✏️', b: '👦' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '产', unit: 'u69', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '工厂里一件件产出新东西。',
    props: { hero: '🏭', stages: ['🏭', '📦', '🚚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '充', unit: 'u69', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '电充满了，格子一格格涨。',
    props: { hero: '🔋', stages: ['🪫', '🔋', '⚡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '闭', unit: 'u69', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把门轻轻闭上，关好它。',
    props: { hero: '🚪', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '闯', unit: 'u69', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小马一下子闯进了院子。',
    props: { hero: '🐎', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '并', unit: 'u69', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个小的并到一起，成一个。',
    props: { hero: '➕', parts: ['🔵', '🔵'], goal: 2 },
    templateFallback: false
  },
  {
    char: '污', unit: 'u69', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '干净的和污脏的，分开放。',
    props: { hero: '🧼', items: [{ item: '👕', bucket: '干净' }, { item: '🧦', bucket: '污脏' }, { item: '🧤', bucket: '干净' }, { item: '🩳', bucket: '污脏' }], buckets: [{ label: '干净', emoji: '🧼' }, { label: '污脏', emoji: '🧺' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '兴', unit: 'u69', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '高兴得放礼花，一朵朵放。',
    props: { hero: '🎉', items: ['🎆', '🎆', '🎆'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
