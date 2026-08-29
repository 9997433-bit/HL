/**
 * 富互动 play 分片 u75 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u75'

export const UNIT_RICH_PLAYS = [
  {
    char: '帐', unit: 'u75', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '支起帐篷，今晚住里边。',
    props: { hero: '⛺', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '财', unit: 'u75', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数钱财，攒满三枚。',
    props: { hero: '💰', items: ['💰', '💰', '💰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '牡', unit: 'u75', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '牡丹花开得又大又艳。',
    props: { hero: '🌺', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '告', unit: 'u75', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '举手告诉老师一个秘密。',
    props: { hero: '📢', target: '📢', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '乱', unit: 'u75', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '东西乱了，重新摆整齐。',
    props: { hero: '🌀', stages: ['📦', '🌀', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '利', unit: 'u75', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '刀刃锋利，切开西瓜。',
    props: { hero: '🔪', parts: ['🧩', '🌱', '🔪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '秃', unit: 'u75', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '山上光秃秃，种上小树。',
    props: { hero: '🪶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '秀', unit: 'u75', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '秀出你的画，给大家看。',
    props: { hero: '🌾', color: 'pink', goal: 3 },
    templateFallback: false
  },
  {
    char: '私', unit: 'u75', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '锁上私密小盒子，藏好。',
    props: { hero: '🔒', items: ['🔒', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '兵', unit: 'u75', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '小士兵排队，数满四个。',
    props: { hero: '🎖️', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '估', unit: 'u75', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '估一估这堆有多重。',
    props: { hero: '🤔', stages: ['🪵', '🤔', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '何', unit: 'u75', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '问一问：何时出发好？',
    props: { hero: '❓', pairs: [{ a: '❓', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '❓' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '佐', unit: 'u75', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '加点佐料，菜更香了。',
    props: { hero: '🧂', pairs: [{ a: '🧂', b: '🔥' }, { a: '☀️', b: '🔑' }, { a: '🔥', b: '🧂' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '佑', unit: 'u75', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '幸运星保佑你，接住它。',
    props: { hero: '🍀', color: 'green', goal: 3 },
    templateFallback: false
  },
  {
    char: '伸', unit: 'u75', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手臂伸长，够到高处。',
    props: { hero: '🙆', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '作', unit: 'u75', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打开作业本，写完三题。',
    props: { hero: '📝', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伯', unit: 'u75', theme: 'family',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大伯来了，挥手打个招呼。',
    props: { hero: '👨', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '低', unit: 'u75', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '把头低下，钻过矮门。',
    props: { hero: '⬇️', items: ['⬇️', '⬇️', '⬇️', '⬇️'], goal: 4 },
    templateFallback: false
  },
  {
    char: '住', unit: 'u75', theme: 'shape',
    template: 'tap-reveal', interaction: 'tap',
    narration: '钥匙开门，住进小房子。',
    props: { hero: '🏠', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '皂', unit: 'u75', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '拿肥皂搓一搓，洗干净。',
    props: { hero: '🧼', target: '🧼', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
