/**
 * 富互动 play 分片 u54 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u54'

export const UNIT_RICH_PLAYS = [
  {
    char: '古', unit: 'u54', theme: 'object',
    template: 'morph-story', interaction: 'sequence',
    narration: '挖出个老陶罐，是古时候的。',
    props: { hero: '🏺', stages: ['⛏️', '🕰️', '🏺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '昔', unit: 'u54', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往回翻，翻到从前那一页。',
    props: { hero: '📜', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '曾', unit: 'u54', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '这些事你曾经做过吗？点开。',
    props: { hero: '🔙', items: ['🚲', '🏊', '🎂'], goal: 3 },
    templateFallback: false
  },
  {
    char: '久', unit: 'u54', theme: 'time',
    template: 'grow-tap', interaction: 'tap',
    narration: '等了好久好久，天都黑了。',
    props: { hero: '⏳', stages: ['🌅', '🌇', '🌃'], goal: 3 },
    templateFallback: false
  },
  {
    char: '暂', unit: 'u54', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '先暂停一下，数两下再走。',
    props: { hero: '⏸️', items: ['⏸️', '⏸️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '瞬', unit: 'u54', theme: 'time',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一眨眼的工夫，星星就没了。',
    props: { hero: '⚡', items: ['✨', '✨', '✨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '世', unit: 'u54', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '从一个村到一座城到全世界。',
    props: { hero: '🌏', stages: ['🏘️', '🏙️', '🌏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '纪', unit: 'u54', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '日历一年翻一页，翻四页。',
    props: { hero: '📆', items: ['📆', '📆', '📆', '📆'], goal: 4 },
    templateFallback: false
  },
  {
    char: '代', unit: 'u54', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '爷爷、爸爸、我，一代配一代。',
    props: { hero: '👴', pairs: [{ a: '👴', b: '👨' }, { a: '👨', b: '👦' }, { a: '👵', b: '👧' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '朝', unit: 'u54', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '天亮了，早朝的太阳升起来。',
    props: { hero: '🏯', stages: ['🌃', '🌄', '🌞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '史', unit: 'u54', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '翻开史书，看看从前的事。',
    props: { hero: '📜', items: ['🏯', '⚔️', '🏺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '始', unit: 'u54', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '按下开始键，比赛开始了。',
    props: { hero: '▶️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '终', unit: 'u54', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '一路跑到终点，冲过线。',
    props: { hero: '🏁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '留', unit: 'u54', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '走之前留下三样东西。',
    props: { hero: '📌', items: ['📌', '📌', '📌'], goal: 3 },
    templateFallback: false
  },
  {
    char: '守', unit: 'u54', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '守着门口，看好这几样。',
    props: { hero: '🛡️', items: ['🚪', '🔑', '🧳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '变', unit: 'u54', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '毛毛虫变蝴蝶，样子全变了。',
    props: { hero: '🔄', stages: ['🐛', '🌿', '🦋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '化', unit: 'u54', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '雪化了，变成一滩水。',
    props: { hero: '💧', stages: ['❄️', '💧', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '成', unit: 'u54', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '零件拼齐，就做成一辆车。',
    props: { hero: '✅', parts: ['🛞', '🛞', '🚗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '完', unit: 'u54', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把最后三块吃完，一点不剩。',
    props: { hero: '🏁', items: ['🍪', '🍪', '🍪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '顺', unit: 'u54', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着箭头走，一路不拐弯。',
    props: { hero: '➡️', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
