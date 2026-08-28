/**
 * 富互动 play 分片 u30 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u30'

export const UNIT_RICH_PLAYS = [
  {
    char: '从', unit: 'u30', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '从家门口出发，一路走到学校。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '被', unit: 'u30', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '饼干被谁吃掉了？点开找找看。',
    props: { hero: '🍪', items: ['🐭', '🐱', '🧒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '让', unit: 'u30', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '让一让，请老爷爷先过去。',
    props: { hero: '👴', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '但', unit: 'u30', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '这些随便吃，但糖只能少少吃。',
    props: { hero: '↩️', items: [{ item: '🍎', bucket: '可以' }, { item: '🥕', bucket: '可以' }, { item: '🍬', bucket: '但是' }, { item: '🍭', bucket: '但是' }], buckets: [{ label: '可以', emoji: '👍' }, { label: '但是', emoji: '✋' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '因', unit: 'u30', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '因为下雨，所以要打伞，连一连。',
    props: { hero: '❓', pairs: [{ a: '🌧️', b: '☂️' }, { a: '🍽️', b: '😋' }, { a: '🌙', b: '😴' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '为', unit: 'u30', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '为什么要做？把事和道理配好。',
    props: { hero: '💡', pairs: [{ a: '🧼', b: '🤲' }, { a: '🪥', b: '🦷' }, { a: '🧥', b: '🥶' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '所', unit: 'u30', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '每样东西都有它待的地方。',
    props: { hero: '🏠', items: ['🛏️', '🚿', '🍳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '以', unit: 'u30', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '现在能玩的放左，以后再玩的放右。',
    props: { hero: '🔜', items: [{ item: '🎨', bucket: '现在' }, { item: '🧩', bucket: '现在' }, { item: '🚗', bucket: '以后' }, { item: '✈️', bucket: '以后' }], buckets: [{ label: '现在', emoji: '🧒' }, { label: '以后', emoji: '🧑' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '而', unit: 'u30', theme: 'word',
    template: 'grow-tap', interaction: 'tap',
    narration: '太阳出来，而后花儿就开了。',
    props: { hero: '🔗', stages: ['🌞', '🌱', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '就', unit: 'u30', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '说走就走，一下子跑出门。',
    props: { hero: '🏃', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '还', unit: 'u30', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '书看完了，还回图书馆去。',
    props: { hero: '📚', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '又', unit: 'u30', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '吃了一个又一个，一共三个。',
    props: { hero: '🍡', items: ['🍡', '🍡', '🍡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '更', unit: 'u30', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '大的放这边，更大的放那边。',
    props: { hero: '⬆️', items: [{ item: '🐕', bucket: '大' }, { item: '🐎', bucket: '大' }, { item: '🐘', bucket: '更大' }, { item: '🐋', bucket: '更大' }], buckets: [{ label: '大', emoji: '🔵' }, { label: '更大', emoji: '🔴' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '最', unit: 'u30', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁最高？点出个子最高的那个。',
    props: { hero: '🥇', target: '🦒', decoys: ['🐕', '🐈', '🐇'], goal: 1 },
    templateFallback: false
  },
  {
    char: '别', unit: 'u30', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '能做的点头，别做的摇摇头。',
    props: { hero: '🚫', items: [{ item: '🧼', bucket: '能做' }, { item: '📚', bucket: '能做' }, { item: '🔥', bucket: '别做' }, { item: '🔌', bucket: '别做' }], buckets: [{ label: '能做', emoji: '🙆' }, { label: '别做', emoji: '🙅' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '没', unit: 'u30', theme: 'word',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '吃着吃着，盘子里就没有了。',
    props: { hero: '🍽️', items: ['🍪', '🍪', '🍪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '太', unit: 'u30', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '太阳太晒啦，快躲到树荫下。',
    props: { hero: '‼️', stages: ['🌞', '🥵', '🌳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '真', unit: 'u30', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '真的放这边，编出来的放那边。',
    props: { hero: '💯', items: [{ item: '🐟会游泳', bucket: '真' }, { item: '🌞很亮', bucket: '真' }, { item: '🐘会飞', bucket: '假' }, { item: '🪨会说话', bucket: '假' }], buckets: [{ label: '真', emoji: '✔️' }, { label: '假', emoji: '❔' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
