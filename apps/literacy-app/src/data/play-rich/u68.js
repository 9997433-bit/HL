/**
 * 富互动 play 分片 u68 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u68'

export const UNIT_RICH_PLAYS = [
  {
    char: '伍', unit: 'u68', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '排队站成一伍，数五个人。',
    props: { hero: '🚶', items: ['🚶', '🚶', '🚶', '🚶', '🚶'], goal: 5 },
    templateFallback: false
  },
  {
    char: '伏', unit: 'u68', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '老虎趴下来，伏在草里。',
    props: { hero: '🐅', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '伐', unit: 'u68', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '咚咚伐木，砍满三下。',
    props: { hero: '🪓', items: ['🪓', '🪓', '🪓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '仲', unit: 'u68', theme: 'time',
    template: 'sort-buckets', interaction: 'drag',
    narration: '夏天分几段，仲夏在中间。',
    props: { hero: '☀️', items: [{ item: '🌸', bucket: '开头' }, { item: '🐝', bucket: '开头' }, { item: '🍉', bucket: '中间' }, { item: '🏖️', bucket: '中间' }], buckets: [{ label: '开头', emoji: '🌱' }, { label: '中间', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '件', unit: 'u68', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '一件一件挂好衣服，挂三件。',
    props: { hero: '🧥', items: ['🧥', '👕', '👖'], goal: 3 },
    templateFallback: false
  },
  {
    char: '任', unit: 'u68', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '这件事任给你，接过去。',
    props: { hero: '🎯', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '伪', unit: 'u68', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个是假的？找出面具脸。',
    props: { hero: '🎭', target: '🎭', decoys: ['😀', '😃', '🙂'], goal: 1 },
    templateFallback: false
  },
  {
    char: '份', unit: 'u68', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '蛋糕分成两份，一人一份。',
    props: { hero: '🍰', items: [{ item: '🍰', bucket: '你的一份' }, { item: '🍓', bucket: '你的一份' }, { item: '🧁', bucket: '我的一份' }, { item: '🍫', bucket: '我的一份' }], buckets: [{ label: '你的一份', emoji: '🧒' }, { label: '我的一份', emoji: '🧑' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '仰', unit: 'u68', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '仰起头来，看看天上边。',
    props: { hero: '🙆', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '仿', unit: 'u68', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '照葫芦画瓢，一样的配一起。',
    props: { hero: '🪞', pairs: [{ a: '🍎', b: '🍎' }, { a: '🌵', b: '🌵' }, { a: '🐟', b: '🐟' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '自', unit: 'u68', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '指指自己的鼻子，那就是我。',
    props: { hero: '🙋', items: ['👃'], goal: 1 },
    templateFallback: false
  },
  {
    char: '似', unit: 'u68', theme: 'weather',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '雾里瞧一瞧，哪个像小船？',
    props: { hero: '🌫️', target: '⛵', decoys: ['🌫️', '☁️', '🌁'], goal: 1 },
    templateFallback: false
  },
  {
    char: '行', unit: 'u68', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '一步一步往前行，走起来。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '合', unit: 'u68', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '两只手一合，掌心贴一起。',
    props: { hero: '🤝', parts: ['🤚', '✋'], goal: 2 },
    templateFallback: false
  },
  {
    char: '兆', unit: 'u68', theme: 'number',
    template: 'tap-reveal', interaction: 'tap',
    narration: '好兆头藏在里头，揭开看。',
    props: { hero: '🔮', items: ['🍀', '🌈', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '企', unit: 'u68', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '企鹅踮起脚，往上看一眼。',
    props: { hero: '🐧', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '创', unit: 'u68', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '从一个念头，创出新玩意。',
    props: { hero: '💡', stages: ['💡', '✏️', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肌', unit: 'u68', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '使劲一鼓，肌肉鼓起来了。',
    props: { hero: '💪', stages: ['🦴', '💪', '🏋️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肋', unit: 'u68', theme: 'body',
    template: 'count-tap', interaction: 'tap',
    narration: '摸摸小肋骨，一根一根数。',
    props: { hero: '🦴', items: ['🦴', '🦴', '🦴', '🦴'], goal: 4 },
    templateFallback: false
  },
  {
    char: '朵', unit: 'u68', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '一朵一朵摘花，摘满三朵。',
    props: { hero: '🌸', items: ['🌸', '🌺', '🌼'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
