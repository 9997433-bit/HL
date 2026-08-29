/**
 * 富互动 play 分片 u88 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u88'

export const UNIT_RICH_PLAYS = [
  {
    char: '郎', unit: 'u88', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '新郎戴花，和新娘牵手。',
    props: { hero: '🤵', stages: ['📦', '🤵', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '诗', unit: 'u88', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '读一首短诗，点亮诗行。',
    props: { hero: '📜', parts: ['🧩', '🌱', '📜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '视', unit: 'u88', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '视线跟着小鸟，别丢了。',
    props: { hero: '👁️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '诞', unit: 'u88', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '小宝宝诞生了，送上礼物。',
    props: { hero: '🐴', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '询', unit: 'u88', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '询问路人，哪条路回家。',
    props: { hero: '❓', items: ['❓', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '该', unit: 'u88', theme: 'number',
    template: 'sound-tap', interaction: 'tap',
    narration: '该你了，轮到你点一下。',
    props: { hero: '✅', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '详', unit: 'u88', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '详细说说，把细节点开。',
    props: { hero: '📋', stages: ['🪵', '📋', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '帚', unit: 'u88', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '拿起扫帚，把地扫净。',
    props: { hero: '🧹', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '屉', unit: 'u88', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '拉开抽屉，看看里面有啥。',
    props: { hero: '🗄️', items: [{ item: '🗄️', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '居', unit: 'u88', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '小房子居住着，点亮窗灯。',
    props: { hero: '🏡', color: 'brown', goal: 3 },
    templateFallback: false
  },
  {
    char: '届', unit: 'u88', theme: 'number',
    template: 'sound-tap', interaction: 'tap',
    narration: '这一届运动会，挂上奖牌。',
    props: { hero: '🏅', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '屈', unit: 'u88', theme: 'shape',
    template: 'tap-reveal', interaction: 'tap',
    narration: '膝盖弯曲，蹲下休息。',
    props: { hero: '🙇', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弧', unit: 'u88', theme: 'shape',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '画一道弧线，弯弯的。',
    props: { hero: '🌈', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '承', unit: 'u88', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '双手承接住掉落的球。',
    props: { hero: '🤲', items: ['🎈', '📦', '🌱'], tool: '🤲', goal: 3 },
    templateFallback: false
  },
  {
    char: '孟', unit: 'u88', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '找到姓孟的卡片。',
    props: { hero: '👤', stages: ['🎁', '👤', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '陌', unit: 'u88', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '陌生人来了，礼貌问好。',
    props: { hero: '🚸', target: '🚸', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '孤', unit: 'u88', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '孤单的小鸟，找个伴。',
    props: { hero: '🕊️', stages: ['📦', '🕊️', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '降', unit: 'u88', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '降落伞降下，轻轻落地。',
    props: { hero: '⬇️', items: ['🧩', '🌱', '🔥'], tool: '⬇️', goal: 3 },
    templateFallback: false
  },
  {
    char: '限', unit: 'u88', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '时间有限，在线内完成。',
    props: { hero: '⏳', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '艰', unit: 'u88', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '路途艰难，一步步爬坡。',
    props: { hero: '⛰️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
