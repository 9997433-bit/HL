/**
 * 富互动 play 分片 u17 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u17'

export const UNIT_RICH_PLAYS = [
  {
    char: '笔', unit: 'u17', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '拿起铅笔，跟着线画一道。',
    props: { hero: '✏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '纸', unit: 'u17', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '白白的一张纸，在上面画点什么。',
    props: { hero: '📄', items: ['🖍️', '✏️', '🖌️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '画', unit: 'u17', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '画一幅画，给它涂上颜色。',
    props: { hero: '🎨', color: 'rainbow', goal: 3 },
    templateFallback: false
  },
  {
    char: '课', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '上课啦，点点课上要用的东西。',
    props: { hero: '📚', items: ['📕', '✏️', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '班', unit: 'u17', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数数我们班有几个小朋友。',
    props: { hero: '🏫', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '同', unit: 'u17', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '一样的才是同，找出相同的。',
    props: { hero: '🤝', pairs: [{ a: '🍎', b: '🍎' }, { a: '📕', b: '📕' }, { a: '⚽', b: '⚽' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '朋', unit: 'u17', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个月字并排站，就是朋友的朋。',
    props: { hero: '🧑‍🤝‍🧑', parts: ['月', '月'], goal: 2 },
    templateFallback: false
  },
  {
    char: '友', unit: 'u17', theme: 'feeling',
    template: 'pair-match', interaction: 'drag',
    narration: '手拉着手，就成了好朋友。',
    props: { hero: '💞', pairs: [{ a: '🧒', b: '🧒' }, { a: '🐱', b: '🐶' }, { a: '👦', b: '👧' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '教', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '老师教一句，我们跟着念一句。',
    props: { hero: '👩‍🏫', sound: '跟我读', goal: 3 },
    templateFallback: false
  },
  {
    char: '室', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '教室里都有什么？点点看。',
    props: { hero: '🚪', items: ['🪑', '🖼️', '🪟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '队', unit: 'u17', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个跟着一个，排成一条队。',
    props: { hero: '🚶', parts: ['🧒', '🧒', '🧒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '讲', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '站上讲台，大声讲给大家听。',
    props: { hero: '🗣️', sound: '大家好', goal: 3 },
    templateFallback: false
  },
  {
    char: '台', unit: 'u17', theme: 'school',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把小凳子摞高，就成了小台子。',
    props: { hero: '🎤', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '板', unit: 'u17', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '在黑板上写写画画，再擦干净。',
    props: { hero: '🪵', color: 'black', goal: 3 },
    templateFallback: false
  },
  {
    char: '图', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '摊开地图，点点上面画了什么。',
    props: { hero: '🗺️', items: ['⛰️', '🏞️', '🏠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '数', unit: 'u17', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数，一共有几个。',
    props: { hero: '🔢', items: ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'], goal: 5 },
    templateFallback: false
  },
  {
    char: '语', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '说一句话，说出来的就是语。',
    props: { hero: '💬', sound: '你好呀', goal: 3 },
    templateFallback: false
  },
  {
    char: '文', unit: 'u17', theme: 'school',
    template: 'word-build', interaction: 'drag',
    narration: '把字连起来，就成了一篇文。',
    props: { hero: '📝', parts: ['语', '文'], word: '语文', goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
