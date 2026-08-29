/**
 * 富互动 play 分片 u76 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u76'

export const UNIT_RICH_PLAYS = [
  {
    char: '佛', unit: 'u76', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '大佛静静坐着，点三炷香。',
    props: { hero: '🛕', stages: ['📦', '🛕', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '囱', unit: 'u76', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '烟囱冒烟，一股股往上。',
    props: { hero: '🏭', parts: ['🧩', '🌱', '🏭'], goal: 3 },
    templateFallback: false
  },
  {
    char: '彻', unit: 'u76', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '打扫彻底，角落也擦到。',
    props: { hero: '🧹', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '返', unit: 'u76', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '走到尽头，再返回起点。',
    props: { hero: '🔙', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '希', unit: 'u76', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '许个愿望，希望实现它。',
    props: { hero: '🌟', items: ['🌟', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妥', unit: 'u76', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '安排妥当了，打个勾。',
    props: { hero: '👌', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '含', unit: 'u76', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '嘴里含着糖，慢慢化开。',
    props: { hero: '🍬', items: [{ item: '🍬', bucket: '左' }, { item: '🎈', bucket: '左' }, { item: '🪵', bucket: '右' }, { item: '❄️', bucket: '右' }], buckets: [{ label: '左', emoji: '🪵' }, { label: '右', emoji: '❄️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '岔', unit: 'u76', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '走到岔路口，选一条路。',
    props: { hero: '🛤️', items: [{ item: '🛤️', bucket: '左' }, { item: '🎁', bucket: '左' }, { item: '💧', bucket: '右' }, { item: '🌙', bucket: '右' }], buckets: [{ label: '左', emoji: '💧' }, { label: '右', emoji: '🌙' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '肝', unit: 'u76', theme: 'body',
    template: 'sort-buckets', interaction: 'drag',
    narration: '找到肝脏卡片，贴到身体上。',
    props: { hero: '🫀', items: [{ item: '🫀', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '肘', unit: 'u76', theme: 'body',
    template: 'color-fill', interaction: 'tap',
    narration: '弯起手肘，做个加油姿势。',
    props: { hero: '💪', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '肠', unit: 'u76', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '香肠一节节切开，数三节。',
    props: { hero: '🌭', stages: ['🌙', '🌭', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '免', unit: 'u76', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '这张票免费，不用付钱。',
    props: { hero: '🆓', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '狂', unit: 'u76', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '狂风刮来，抓紧帽子。',
    props: { hero: '🌪️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '犹', unit: 'u76', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '犹豫不决，两边都看看。',
    props: { hero: '🤔', items: ['🤔', '🤔', '🤔', '🤔', '🤔'], goal: 5 },
    templateFallback: false
  },
  {
    char: '删', unit: 'u76', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把错字删掉，换成对的。',
    props: { hero: '✂️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '卵', unit: 'u76', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '鸟卵孵化，小鸡破壳。',
    props: { hero: '🥚', target: '🥚', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '刨', unit: 'u76', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小狗刨土，挖出骨头。',
    props: { hero: '🐕', stages: ['📦', '🐕', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饮', unit: 'u76', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '渴了就饮一口凉水。',
    props: { hero: '🥤', items: ['🥤', '🧩', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '系', unit: 'u76', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '把鞋带系紧，打个结。',
    props: { hero: '🔗', parts: ['🔔', '🪨', '🔗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '况', unit: 'u76', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '看看情况卡片，了解一下。',
    props: { hero: '📋', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
