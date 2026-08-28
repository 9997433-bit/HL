/**
 * 富互动 play 分片 u5 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u5'

export const UNIT_RICH_PLAYS = [
  {
    char: '四', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数四个草莓：一二三四。',
    props: { hero: '4️⃣', items: ['🍓', '🍓', '🍓', '🍓'], goal: 4 },
    templateFallback: false
  },
  {
    char: '五', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '张开一只手，正好五个手指。',
    props: { hero: '🖐️', items: ['👆', '👆', '👆', '👆', '👆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '六', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '六颗糖，把小盒子装满。',
    props: { hero: '6️⃣', items: ['🍬', '🍬', '🍬', '🍬', '🍬', '🍬'], goal: 6 },
    templateFallback: false
  },
  {
    char: '七', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一个星期七天，点满七格。',
    props: { hero: '7️⃣', items: ['📅', '📅', '📅', '📅', '📅', '📅', '📅'], goal: 7 },
    templateFallback: false
  },
  {
    char: '八', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '两撇往两边一分，就写成八。',
    props: { hero: '8️⃣', parts: ['丿', '乀'], goal: 2 },
    templateFallback: false
  },
  {
    char: '九', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '戳破九个泡泡，再一个就到十。',
    props: { hero: '9️⃣', items: ['🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧'], goal: 9 },
    templateFallback: false
  },
  {
    char: '十', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '一横加一竖，交叉就是十。',
    props: { hero: '🔟', parts: ['一', '丨'], goal: 2 },
    templateFallback: false
  },
  {
    char: '百', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '十个十个数，一百好多好多。',
    props: { hero: '💯', items: ['🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧'], goal: 10 },
    templateFallback: false
  },
  {
    char: '千', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一千颗星星撒满天，先点亮十颗。',
    props: { hero: '🌌', items: ['⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐'], goal: 10 },
    templateFallback: false
  },
  {
    char: '万', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一万像烟花一样多，点开看看。',
    props: { hero: '🎆', items: ['🎆', '🎆', '🎆', '🎆', '🎆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '半', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '把西瓜从中间切开，一人一半。',
    props: { hero: '🍉', parts: ['🍉', '🍉'], goal: 2 },
    templateFallback: false
  },
  {
    char: '双', unit: 'u5', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '两只一样的才叫一双，配对试试。',
    props: { hero: '🙌', pairs: [{ a: '🧦', b: '🧦' }, { a: '👟', b: '👟' }, { a: '🧤', b: '🧤' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
