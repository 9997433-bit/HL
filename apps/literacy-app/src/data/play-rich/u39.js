/**
 * 富互动 play 分片 u39 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u39'

export const UNIT_RICH_PLAYS = [
  {
    char: '耕', unit: 'u39', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '牵着牛，把地一垄一垄耕开。',
    props: { hero: '🐂', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '播', unit: 'u39', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '抓一把种子，一粒粒撒进地。',
    props: { hero: '🌾', items: ['🌰', '🌰', '🌰'], tool: '🕳️', goal: 3 },
    templateFallback: false
  },
  {
    char: '割', unit: 'u39', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿起镰刀，把麦子一把割下。',
    props: { hero: '🌾', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '犁', unit: 'u39', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '犁头插进土里，翻出新泥来。',
    props: { hero: '🐄', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '锄', unit: 'u39', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '举起锄头，一下一下锄草。',
    props: { hero: '⛏️', dir: 'down', goal: 4 },
    templateFallback: false
  },
  {
    char: '秧', unit: 'u39', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '一株一株插秧，插满四株。',
    props: { hero: '🌱', items: ['🌱', '🌱', '🌱', '🌱'], goal: 4 },
    templateFallback: false
  },
  {
    char: '稻', unit: 'u39', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '稻子灌了浆，垂下沉沉的头。',
    props: { hero: '🌾', stages: ['🌱', '🌾', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '穗', unit: 'u39', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '数数手里握着几个麦穗。',
    props: { hero: '🌾', items: ['🌾', '🌾', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '粮', unit: 'u39', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '粮食收进仓，别的放外面。',
    props: { hero: '🍚', items: [{ item: '🍚', bucket: '粮食' }, { item: '🌽', bucket: '粮食' }, { item: '🪨', bucket: '不是粮食' }, { item: '🍂', bucket: '不是粮食' }], buckets: [{ label: '粮食', emoji: '🌾' }, { label: '不是粮食', emoji: '🪨' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '仓', unit: 'u39', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '盖个大仓库，把粮食堆进去。',
    props: { hero: '🏚️', parts: ['🧱', '🧱', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '畜', unit: 'u39', theme: 'animal',
    template: 'sort-buckets', interaction: 'drag',
    narration: '家里养的进圈，山里的留在野外。',
    props: { hero: '🐖', items: [{ item: '🐄', bucket: '家养' }, { item: '🐖', bucket: '家养' }, { item: '🦌', bucket: '野生' }, { item: '🐺', bucket: '野生' }], buckets: [{ label: '家养', emoji: '🏠' }, { label: '野生', emoji: '🌲' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '牧', unit: 'u39', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '赶着羊群，上山坡去吃草。',
    props: { hero: '🐑', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '渔', unit: 'u39', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '撒下渔网，接住游过来的鱼。',
    props: { hero: '🎣', items: ['🐟', '🐟', '🐟'], tool: '🥅', goal: 3 },
    templateFallback: false
  },
  {
    char: '猎', unit: 'u39', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '草丛里藏着谁？把它找出来。',
    props: { hero: '🏹', target: '🐗', decoys: ['🌿', '🌾', '🍂'], goal: 1 },
    templateFallback: false
  },
  {
    char: '沿', unit: 'u39', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '沿着河边一直走，别走岔了。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '涌', unit: 'u39', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '水从地下涌上来，一股又一股。',
    props: { hero: '🌊', stages: ['💧', '💦', '⛲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '溪', unit: 'u39', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '小溪叮咚，一路流下山去。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '瀑', unit: 'u39', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '瀑布从崖上冲下来，白花花。',
    props: { hero: '💦', dir: 'down', goal: 4 },
    templateFallback: false
  },
  {
    char: '岩', unit: 'u39', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '大岩石一块压一块，堆成崖。',
    props: { hero: '🪨', parts: ['🪨', '🪨', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坡', unit: 'u39', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '顺着山坡往下滑，冲呀。',
    props: { hero: '🛷', dir: 'down', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
