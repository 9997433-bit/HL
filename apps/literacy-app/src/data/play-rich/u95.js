/**
 * 富互动 play 分片 u95 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u95'

export const UNIT_RICH_PLAYS = [
  {
    char: '胆', unit: 'u95', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '壮起胆子，推开暗门。',
    props: { hero: '🦁', items: ['🦁', '🦁', '🦁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '胞', unit: 'u95', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '看看细胞图，放大一点。',
    props: { hero: '🔬', items: ['🔬', '🔬', '🔬', '🔬'], goal: 4 },
    templateFallback: false
  },
  {
    char: '胖', unit: 'u95', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '小猪胖乎乎，摸一摸肚。',
    props: { hero: '🐷', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '脉', unit: 'u95', theme: 'number',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '摸一摸脉搏，跳了几下。',
    props: { hero: '⛰️', target: '⛰️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '胎', unit: 'u95', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '给汽车换轮胎，拧紧。',
    props: { hero: '🛞', stages: ['📦', '🛞', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '勉', unit: 'u95', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '互相勉励，击掌加油。',
    props: { hero: '💪', parts: ['🧩', '🌱', '💪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '狭', unit: 'u95', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '窄窄的狭道，侧身过去。',
    props: { hero: '🚪', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '独', unit: 'u95', theme: 'number',
    template: 'scene-poke', interaction: 'tap',
    narration: '独自走夜路，点亮手电。',
    props: { hero: '1️⃣', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '狡', unit: 'u95', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '狡猾狐狸设圈套，识破它。',
    props: { hero: '🦊', items: ['🦊', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '怨', unit: 'u95', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '别埋怨，换成微笑。',
    props: { hero: '😤', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '饺', unit: 'u95', theme: 'food',
    template: 'morph-story', interaction: 'sequence',
    narration: '包饺子，捏紧饺边。',
    props: { hero: '🥟', stages: ['🪵', '🥟', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弯', unit: 'u95', theme: 'shape',
    template: 'pair-match', interaction: 'drag',
    narration: '弯下腰，捡起地上的笔。',
    props: { hero: '🌙', pairs: [{ a: '🌙', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌙' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '将', unit: 'u95', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '小将军出征，挥动手中旗。',
    props: { hero: '⏭️', items: [{ item: '⏭️', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '奖', unit: 'u95', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '发奖状，贴上光荣榜。',
    props: { hero: '🏅', color: 'brown', goal: 3 },
    templateFallback: false
  },
  {
    char: '哀', unit: 'u95', theme: 'feeling',
    template: 'rain-catch', interaction: 'drag',
    narration: '擦去哀伤的泪，抬头看。',
    props: { hero: '😢', items: ['🌙', '🎈', '🧩'], tool: '😢', goal: 3 },
    templateFallback: false
  },
  {
    char: '亭', unit: 'u95', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '凉亭歇脚，坐一会儿。',
    props: { hero: '⛩️', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '庭', unit: 'u95', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '庭院种花，浇三棵苗。',
    props: { hero: '🏡', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '疯', unit: 'u95', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '别发疯乱跑，静下来。',
    props: { hero: '🌪️', items: ['🌪️', '🌪️', '🌪️', '🌪️', '🌪️'], goal: 5 },
    templateFallback: false
  },
  {
    char: '疫', unit: 'u95', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打疫苗，防住小病菌。',
    props: { hero: '💉', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '疤', unit: 'u95', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '伤疤贴创可贴，慢慢好。',
    props: { hero: '🩹', target: '🩹', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
