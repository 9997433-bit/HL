/**
 * 富互动 play 分片 u62 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u62'

export const UNIT_RICH_PLAYS = [
  {
    char: '办', unit: 'u62', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '事情分开办：先做的和后做的。',
    props: { hero: '🗂️', items: [{ item: '🪥', bucket: '先做' }, { item: '🍚', bucket: '先做' }, { item: '📺', bucket: '后做' }, { item: '🛏️', bucket: '后做' }], buckets: [{ label: '先做', emoji: '1️⃣' }, { label: '后做', emoji: '2️⃣' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '允', unit: 'u62', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '可以吗？找出允许通过的绿灯。',
    props: { hero: '✅', target: '✅', decoys: ['🚫', '❌', '⛔'], goal: 1 },
    templateFallback: false
  },
  {
    char: '邓', unit: 'u62', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '门牌上写着邓，去找邓家人。',
    props: { hero: '👤', items: ['🚪', '📛', '👋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '劝', unit: 'u62', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '好好劝一劝，请他别生气。',
    props: { hero: '🗣️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '未', unit: 'u62', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '时候还未到，果子没熟呢。',
    props: { hero: '⏳', stages: ['🌸', '🍏', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '末', unit: 'u62', theme: 'time',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '翻到最后一页，到了末尾。',
    props: { hero: '🔚', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '示', unit: 'u62', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '老师示范一遍，跟着揭开看。',
    props: { hero: '👉', items: ['✋', '👏', '🤙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '巧', unit: 'u62', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '手真巧，几块拼图巧巧拼好。',
    props: { hero: '🎯', parts: ['🧩', '🧩', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '正', unit: 'u62', theme: 'shape',
    template: 'count-tap', interaction: 'tap',
    narration: '一笔一笔写个正字，写五笔。',
    props: { hero: '📐', items: ['➖', '➖', '➖', '➖', '➖'], goal: 5 },
    templateFallback: false
  },
  {
    char: '扑', unit: 'u62', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小狗一下子扑了过来。',
    props: { hero: '🐕', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '予', unit: 'u62', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '把礼物给予朋友，配一配。',
    props: { hero: '🎁', pairs: [{ a: '🎁', b: '🧒' }, { a: '🍰', b: '👧' }, { a: '🎈', b: '👦' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '扒', unit: 'u62', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手往两边扒开草丛。',
    props: { hero: '🙌', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '功', unit: 'u62', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '一点一点练，最后练成功。',
    props: { hero: '🏆', stages: ['😣', '💪', '🏆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '甘', unit: 'u62', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '甘甜的蜜，一口一口尝。',
    props: { hero: '🍯', items: ['🍯', '🍯', '🍯'], goal: 3 },
    templateFallback: false
  },
  {
    char: '艾', unit: 'u62', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '艾草香香的，点点这些草药。',
    props: { hero: '🌿', items: ['🌿', '🍃', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '术', unit: 'u62', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '变个小魔术，帽子里有什么。',
    props: { hero: '🎩', items: ['🐇', '🌷', '🃏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '可', unit: 'u62', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '可以的话点点头，找出点头的。',
    props: { hero: '👍', target: '👍', decoys: ['👎', '✋', '🤷'], goal: 1 },
    templateFallback: false
  },
  {
    char: '丙', unit: 'u62', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '甲乙丙，一路数到第三个。',
    props: { hero: '3️⃣', items: ['🥇', '🥈', '🥉'], goal: 3 },
    templateFallback: false
  },
  {
    char: '厉', unit: 'u62', theme: 'feeling',
    template: 'sound-tap', interaction: 'tap',
    narration: '厉害的一声吼，好大的声。',
    props: { hero: '💪', sound: '吼', goal: 3 },
    templateFallback: false
  },
  {
    char: '灭', unit: 'u62', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一朵一朵小火苗，全浇灭。',
    props: { hero: '🧯', items: ['🔥', '🔥', '🔥'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
