/**
 * 富互动 play 分片 u63 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u63'

export const UNIT_RICH_PLAYS = [
  {
    char: '东', unit: 'u63', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '太阳从东边出来，往东走。',
    props: { hero: '🧭', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '占', unit: 'u63', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小旗插上，这块地占住了。',
    props: { hero: '📍', parts: ['🚩', '⛰️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '卢', unit: 'u63', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '门口挂着卢家的灯笼。',
    props: { hero: '👤', items: ['🏮', '🏮', '🚪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '业', unit: 'u63', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '各行各业：种地的和看病的。',
    props: { hero: '💼', items: [{ item: '🚜', bucket: '种地' }, { item: '🌽', bucket: '种地' }, { item: '💊', bucket: '看病' }, { item: '🩹', bucket: '看病' }], buckets: [{ label: '种地', emoji: '🌾' }, { label: '看病', emoji: '🩺' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '帅', unit: 'u63', theme: 'feeling',
    template: 'color-fill', interaction: 'tap',
    narration: '给小队长的帽子涂个帅气色。',
    props: { hero: '😎', color: '蓝', goal: 3 },
    templateFallback: false
  },
  {
    char: '旦', unit: 'u63', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '天刚亮，太阳从地平线冒头。',
    props: { hero: '🌅', stages: ['🌃', '🌅', '🌞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '且', unit: 'u63', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '添了一个，而且再添一个。',
    props: { hero: '➕', items: ['🍊', '🍊'], goal: 2 },
    templateFallback: false
  },
  {
    char: '甲', unit: 'u63', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '给小乌龟穿上硬硬的甲壳。',
    props: { hero: '1️⃣', parts: ['🐢', '🛡️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '申', unit: 'u63', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '举手申请，把手往上伸。',
    props: { hero: '📝', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '叮', unit: 'u63', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小蚊子叮一下，叮的一声。',
    props: { hero: '🦟', sound: '叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '叭', unit: 'u63', theme: 'object',
    template: 'sound-tap', interaction: 'tap',
    narration: '喇叭一按，嘀嘀叭叭响。',
    props: { hero: '📣', sound: '叭', goal: 3 },
    templateFallback: false
  },
  {
    char: '兄', unit: 'u63', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '哥哥和弟弟，兄弟配成对。',
    props: { hero: '👦', pairs: [{ a: '👦', b: '👶' }, { a: '👧', b: '👶' }, { a: '👨', b: '👦' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '叽', unit: 'u63', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小鸡叽叽叫，跟着学一声。',
    props: { hero: '🐤', sound: '叽叽', goal: 3 },
    templateFallback: false
  },
  {
    char: '叼', unit: 'u63', theme: 'animal',
    template: 'drag-parts', interaction: 'drag',
    narration: '小狗把骨头叼在嘴里。',
    props: { hero: '🐕', parts: ['🦴', '🐕'], goal: 2 },
    templateFallback: false
  },
  {
    char: '叫', unit: 'u63', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '大声叫一句，喊出名字来。',
    props: { hero: '📢', sound: '喂', goal: 3 },
    templateFallback: false
  },
  {
    char: '叹', unit: 'u63', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '唉，长长地叹出一口气。',
    props: { hero: '😮‍💨', stages: ['🙂', '😔', '😮‍💨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '失', unit: 'u63', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '东西丢失了，找找在哪儿。',
    props: { hero: '❌', target: '🔑', decoys: ['🧦', '🧢', '📖'], goal: 1 },
    templateFallback: false
  },
  {
    char: '禾', unit: 'u63', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '一棵小禾苗，抽穗结出谷子。',
    props: { hero: '🌾', stages: ['🌱', '🌿', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '丘', unit: 'u63', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '土一堆堆起来，成了小土丘。',
    props: { hero: '⛰️', parts: ['🟫', '🟫', '⛰️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '付', unit: 'u63', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '该付钱啦，数出三个硬币。',
    props: { hero: '💰', items: ['🪙', '🪙', '🪙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
