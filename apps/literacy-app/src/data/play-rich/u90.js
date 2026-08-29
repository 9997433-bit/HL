/**
 * 富互动 play 分片 u90 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u90'

export const UNIT_RICH_PLAYS = [
  {
    char: '赵', unit: 'u90', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '找到姓赵的小朋友。',
    props: { hero: '👤', items: [{ item: '👤', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '挡', unit: 'u90', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '树挡住路，绕到旁边。',
    props: { hero: '🌳', color: 'green', goal: 3 },
    templateFallback: false
  },
  {
    char: '括', unit: 'u90', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '用括号括住这几个字。',
    props: { hero: '🔖', items: ['🌙', '🎈', '🧩'], tool: '🔖', goal: 3 },
    templateFallback: false
  },
  {
    char: '拴', unit: 'u90', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小狗拴在桩子上。',
    props: { hero: '🪢', parts: ['☀️', '🎁', '🪢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拾', unit: 'u90', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把落叶拾起来，装进袋。',
    props: { hero: '🧹', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '挑', unit: 'u90', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '挑一个最大的苹果。',
    props: { hero: '🍎', target: '🍎', decoys: ['🎈', '📦', '🌱'], goal: 1 },
    templateFallback: false
  },
  {
    char: '垫', unit: 'u90', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '坐垫放好，坐上去试试。',
    props: { hero: '🛋️', items: [{ item: '🛋️', bucket: '左' }, { item: '🪨', bucket: '左' }, { item: '🎁', bucket: '右' }, { item: '🧩', bucket: '右' }], buckets: [{ label: '左', emoji: '🎁' }, { label: '右', emoji: '🧩' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '挣', unit: 'u90', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '努力挣钱，存进小猪罐。',
    props: { hero: '💰', pairs: [{ a: '💰', b: '🔑' }, { a: '🔔', b: '🪵' }, { a: '🔑', b: '💰' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '拼', unit: 'u90', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '拼图拼完整，缺哪块？',
    props: { hero: '🧩', stages: ['📦', '🧩', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '按', unit: 'u90', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '按下按钮，灯就亮了。',
    props: { hero: '🔘', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '挥', unit: 'u90', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '挥动手臂，跟大家再见。',
    props: { hero: '👋', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '挪', unit: 'u90', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '把椅子挪开一点，让路。',
    props: { hero: '📦', stages: ['🎯', '📦', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '荆', unit: 'u90', theme: 'nature',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '荆棘有刺，小心别碰。',
    props: { hero: '🌿', items: ['🌿', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '革', unit: 'u90', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '皮革鞋擦亮，闪闪发光。',
    props: { hero: '🥾', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '茬', unit: 'u90', theme: 'number',
    template: 'morph-story', interaction: 'sequence',
    narration: '麦茬割完，留下短根。',
    props: { hero: '🌾', stages: ['🪵', '🌾', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '荐', unit: 'u90', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推荐好书，推到书架前。',
    props: { hero: '👍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '带', unit: 'u90', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '带上水壶，出门远足。',
    props: { hero: '🎒', items: [{ item: '🎒', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '茧', unit: 'u90', theme: 'animal',
    template: 'color-fill', interaction: 'tap',
    narration: '蚕宝宝结茧，变成白壳。',
    props: { hero: '🐛', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '茵', unit: 'u90', theme: 'nature',
    template: 'rain-catch', interaction: 'drag',
    narration: '绿茵场上，踢球进门。',
    props: { hero: '🌱', items: ['🌙', '🎈', '🧩'], tool: '🌱', goal: 3 },
    templateFallback: false
  },
  {
    char: '茫', unit: 'u90', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '雾茫茫，拨开看清路。',
    props: { hero: '🌫️', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
