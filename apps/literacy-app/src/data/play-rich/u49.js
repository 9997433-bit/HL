/**
 * 富互动 play 分片 u49 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u49'

export const UNIT_RICH_PLAYS = [
  {
    char: '墙', unit: 'u49', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '一块砖压一块砖，砌成墙。',
    props: { hero: '🧱', parts: ['🧱', '🧱', '🧱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '顶', unit: 'u49', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把屋顶抬上去，盖在房上。',
    props: { hero: '🔺', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '梁', unit: 'u49', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '横着的大梁架上去，房才稳。',
    props: { hero: '🪵', parts: ['🪵', '🪵'], goal: 2 },
    templateFallback: false
  },
  {
    char: '柱', unit: 'u49', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '门口立着几根柱子？数数。',
    props: { hero: '🏛️', items: ['🏛️', '🏛️', '🏛️', '🏛️'], goal: 4 },
    templateFallback: false
  },
  {
    char: '檐', unit: 'u49', theme: 'place',
    template: 'rain-catch', interaction: 'drag',
    narration: '屋檐下滴水，拿盆接住。',
    props: { hero: '🏚️', items: ['💧', '💧', '💧'], tool: '🪣', goal: 3 },
    templateFallback: false
  },
  {
    char: '阶', unit: 'u49', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一级一级上台阶，走五级。',
    props: { hero: '🪜', items: ['🪜', '🪜', '🪜', '🪜', '🪜'], goal: 5 },
    templateFallback: false
  },
  {
    char: '廊', unit: 'u49', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着走廊一直走到那头。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '厅', unit: 'u49', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '客厅里摆着什么？点一点。',
    props: { hero: '🛋️', items: ['📺', '🪑', '🪴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '卧', unit: 'u49', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '卧室里，被子枕头都在哪？',
    props: { hero: '🛏️', items: ['🛏️', '🧸', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '厨', unit: 'u49', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '做饭的进厨房，睡觉的进卧室。',
    props: { hero: '🍳', items: [{ item: '🍲', bucket: '厨房' }, { item: '🔪', bucket: '厨房' }, { item: '🛏️', bucket: '卧室' }, { item: '🧸', bucket: '卧室' }], buckets: [{ label: '厨房', emoji: '🍳' }, { label: '卧室', emoji: '🛏️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '厕', unit: 'u49', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个门是厕所？找那个牌子。',
    props: { hero: '🚻', target: '🚻', decoys: ['🚪', '🪟', '🛗'], goal: 1 },
    templateFallback: false
  },
  {
    char: '阳', unit: 'u49', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '拉开窗帘，太阳照进屋里。',
    props: { hero: '☀️', stages: ['🌥️', '🌤️', '☀️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '橱', unit: 'u49', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '碗放碗橱，衣服挂衣橱。',
    props: { hero: '🗄️', items: [{ item: '🥣', bucket: '碗橱' }, { item: '🍵', bucket: '碗橱' }, { item: '👗', bucket: '衣橱' }, { item: '🧦', bucket: '衣橱' }], buckets: [{ label: '碗橱', emoji: '🍽️' }, { label: '衣橱', emoji: '🧥' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '毯', unit: 'u49', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '地毯铺好，涂成暖暖的橘色。',
    props: { hero: '🧶', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '帘', unit: 'u49', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把窗帘往两边拉开。',
    props: { hero: '🪟', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '巷', unit: 'u49', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '走进窄窄的小巷，穿过去。',
    props: { hero: '🛤️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '底', unit: 'u49', theme: 'shape',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '东西沉到水底，一直往下。',
    props: { hero: '⬇️', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '端', unit: 'u49', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '端着水杯慢慢走，别洒了。',
    props: { hero: '🥛', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '央', unit: 'u49', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个在正中央？点中间那个。',
    props: { hero: '🎯', target: '🎯', decoys: ['⬅️', '➡️', '⬆️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '侧', unit: 'u49', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '身子往侧边一让，让人过。',
    props: { hero: '↔️', dir: 'left', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
