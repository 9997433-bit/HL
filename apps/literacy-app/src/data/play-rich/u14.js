/**
 * 富互动 play 分片 u14 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u14'

export const UNIT_RICH_PLAYS = [
  {
    char: '桌', unit: 'u14', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '在桌子上摆好碗和杯子。',
    props: { hero: '🍽️', items: ['🥣', '🥛', '🥢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '椅', unit: 'u14', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '装上靠背和椅子腿，坐上去。',
    props: { hero: '🪑', parts: ['🪑', '🦵', '🦵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '床', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '铺好被子，晚安，该睡觉了。',
    props: { hero: '🛏️', items: ['🛌', '🧸', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '灯', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '按一下开关，灯就亮了。',
    props: { hero: '💡', items: ['💡', '🔦', '🕯️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '窗', unit: 'u14', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推开窗户，风吹进来啦。',
    props: { hero: '🪟', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '衣', unit: 'u14', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '天冷穿厚衣，天热穿薄衣。',
    props: { hero: '👕', items: [{ item: '🧥', bucket: '冷' }, { item: '🧣', bucket: '冷' }, { item: '👕', bucket: '热' }, { item: '🩳', bucket: '热' }], buckets: [{ label: '冷', emoji: '❄️' }, { label: '热', emoji: '🌞' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '鞋', unit: 'u14', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '把左脚右脚的鞋配成一双。',
    props: { hero: '👟', pairs: [{ a: '👟', b: '👟' }, { a: '🥾', b: '🥾' }, { a: '👢', b: '👢' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '帽', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '挑一顶帽子戴在头上。',
    props: { hero: '🧢', items: ['🎩', '👒', '⛑️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '碗', unit: 'u14', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '摆好三只碗，一人一只。',
    props: { hero: '🥣', items: ['🥣', '🥣', '🥣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杯', unit: 'u14', theme: 'object',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把杯子里的水喝得光光的。',
    props: { hero: '🥛', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伞', unit: 'u14', theme: 'object',
    template: 'rain-catch', interaction: 'drag',
    narration: '下雨了，快撑开伞挡住雨点。',
    props: { hero: '☂️', items: ['💧', '💧', '💧'], tool: '☂️', goal: 3 },
    templateFallback: false
  },
  {
    char: '房', unit: 'u14', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '盖房子：先砌墙，再放屋顶。',
    props: { hero: '🏡', parts: ['🧱', '🧱', '🔺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '电', unit: 'u14', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '电顺着电线跑过来，灯就亮了。',
    props: { hero: '⚡', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
