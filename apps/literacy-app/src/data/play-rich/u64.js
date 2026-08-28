/**
 * 富互动 play 分片 u64 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u64'

export const UNIT_RICH_PLAYS = [
  {
    char: '仗', unit: 'u64', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '打仗要拿什么？找出那把剑。',
    props: { hero: '⚔️', target: '⚔️', decoys: ['🎈', '🍭', '🧸'], goal: 1 },
    templateFallback: false
  },
  {
    char: '仪', unit: 'u64', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '把礼物系上蝴蝶结，才有礼。',
    props: { hero: '🎀', parts: ['🎁', '🎀'], goal: 2 },
    templateFallback: false
  },
  {
    char: '仔', unit: 'u64', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '仔仔细细找，藏着的都揭开。',
    props: { hero: '🔍', items: ['🐞', '🍀', '🔑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '斥', unit: 'u64', theme: 'feeling',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '被训斥了一句，往后缩一缩。',
    props: { hero: '😠', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '乎', unit: 'u64', theme: 'word',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '你最在乎哪一个？挑出来。',
    props: { hero: '❓', target: '❓', decoys: ['❗', '💬', '💭'], goal: 1 },
    templateFallback: false
  },
  {
    char: '丛', unit: 'u64', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '几棵小草凑一起，成了草丛。',
    props: { hero: '🌿', parts: ['🌿', '🌿', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '令', unit: 'u64', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '发个口令，喊一声出发。',
    props: { hero: '📜', sound: '出发', goal: 3 },
    templateFallback: false
  },
  {
    char: '尔', unit: 'u64', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翻开小书，念念上面的字。',
    props: { hero: '📗', items: ['📗', '📖', '📕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '匆', unit: 'u64', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '匆匆忙忙，快步往前赶路。',
    props: { hero: '🏃', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '犯', unit: 'u64', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '该做的和犯规的，分清楚。',
    props: { hero: '⚠️', items: [{ item: '🚶', bucket: '该做' }, { item: '🧼', bucket: '该做' }, { item: '🏃', bucket: '犯规' }, { item: '🔥', bucket: '犯规' }], buckets: [{ label: '该做', emoji: '✅' }, { label: '犯规', emoji: '⚠️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '处', unit: 'u64', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '到处看一看，这处那处都有。',
    props: { hero: '📍', items: ['🏠', '🏫', '🏪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '务', unit: 'u64', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '把任务一件件做完，做三件。',
    props: { hero: '✅', items: ['✅', '✅', '✅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饥', unit: 'u64', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '肚子饥了，把饭一口口吃光。',
    props: { hero: '🍽️', items: ['🍚', '🍗', '🥕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '立', unit: 'u64', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '站立好，身子往上挺一挺。',
    props: { hero: '🧍', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '冯', unit: 'u64', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '信封上写着冯，是给冯家的。',
    props: { hero: '👤', items: ['✉️', '📮', '🏠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '闪', unit: 'u64', theme: 'weather',
    template: 'sound-tap', interaction: 'tap',
    narration: '闪电一闪，咔嚓一声响。',
    props: { hero: '⚡', sound: '咔嚓', goal: 3 },
    templateFallback: false
  },
  {
    char: '汁', unit: 'u64', theme: 'food',
    template: 'rain-catch', interaction: 'drag',
    narration: '果汁一滴滴落，拿杯子接住。',
    props: { hero: '🧃', items: ['🧃', '🍹', '🥤'], tool: '🥛', goal: 3 },
    templateFallback: false
  },
  {
    char: '汇', unit: 'u64', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '小溪汇到一处，成了大河。',
    props: { hero: '🌊', parts: ['💧', '💧', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '宁', unit: 'u64', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '吵闹慢慢停，屋里安宁下来。',
    props: { hero: '😌', stages: ['🔊', '🔉', '🔈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '穴', unit: 'u64', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '洞穴里黑黑的，照照有谁。',
    props: { hero: '🕳️', items: ['🦇', '🐻', '💎'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
