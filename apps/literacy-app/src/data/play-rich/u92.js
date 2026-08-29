/**
 * 富互动 play 分片 u92 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u92'

export const UNIT_RICH_PLAYS = [
  {
    char: '砍', unit: 'u92', theme: 'object',
    template: 'grow-tap', interaction: 'tap',
    narration: '斧头砍柴，劈成三段。',
    props: { hero: '🪓', stages: ['📦', '🪓', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '耐', unit: 'u92', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '耐心等一等，沙漏走完。',
    props: { hero: '⏳', parts: ['🧩', '🌱', '⏳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '耍', unit: 'u92', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '一起玩耍，点亮玩具。',
    props: { hero: '🤹', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '牵', unit: 'u92', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '牵着小牛的绳子往前走。',
    props: { hero: '🐄', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸥', unit: 'u92', theme: 'animal',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '海鸥飞过，跟着往上看。',
    props: { hero: '🕊️', items: ['🕊️', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '轴', unit: 'u92', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '车轴转起来，轮子滚动。',
    props: { hero: '🎡', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '皆', unit: 'u92', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '大家皆大欢喜，击掌。',
    props: { hero: '✅', stages: ['🪵', '✅', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '战', unit: 'u92', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '穿上盔甲，准备作战。',
    props: { hero: '⚔️', pairs: [{ a: '⚔️', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '⚔️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '临', unit: 'u92', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '临摹字帖，一笔笔描。',
    props: { hero: '✍️', items: [{ item: '✍️', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '览', unit: 'u92', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '展览馆里，一幅幅看。',
    props: { hero: '🖼️', color: 'pink', goal: 3 },
    templateFallback: false
  },
  {
    char: '竖', unit: 'u92', theme: 'shape',
    template: 'rain-catch', interaction: 'drag',
    narration: '把旗杆竖起来，立住。',
    props: { hero: '📏', items: ['🌙', '🎈', '🧩'], tool: '📏', goal: 3 },
    templateFallback: false
  },
  {
    char: '尝', unit: 'u92', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '尝一口汤，烫不烫？',
    props: { hero: '👅', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '盼', unit: 'u92', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '盼着流星，许个愿。',
    props: { hero: '🌟', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '眨', unit: 'u92', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '眨眨眼睛，再睁开看。',
    props: { hero: '👁️', stages: ['🎈', '👁️', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哇', unit: 'u92', theme: 'number',
    template: 'sound-tap', interaction: 'tap',
    narration: '哇！好惊喜，拍拍手。',
    props: { hero: '😲', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '哄', unit: 'u92', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '轻轻哄宝宝，摇摇篮。',
    props: { hero: '👶', target: '👶', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '哑', unit: 'u92', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '嘴巴哑了，用手比划。',
    props: { hero: '🤐', stages: ['📦', '🤐', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '显', unit: 'u92', theme: 'weather',
    template: 'drag-parts', interaction: 'drag',
    narration: '谜底显示出来，点开它。',
    props: { hero: '🔎', parts: ['🧩', '🌱', '🔎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '映', unit: 'u92', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '水面映出月亮，看倒影。',
    props: { hero: '🪞', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '畏', unit: 'u92', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '别畏惧黑暗，打开手电。',
    props: { hero: '😨', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
