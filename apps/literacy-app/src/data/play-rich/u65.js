/**
 * 富互动 play 分片 u65 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u65'

export const UNIT_RICH_PLAYS = [
  {
    char: '它', unit: 'u65', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '它是谁？找出慢吞吞的乌龟。',
    props: { hero: '🐢', target: '🐢', decoys: ['🐇', '🐿️', '🦊'], goal: 1 },
    templateFallback: false
  },
  {
    char: '讨', unit: 'u65', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '去讨个主意，走过去问问。',
    props: { hero: '🗣️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '必', unit: 'u65', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '这几样必须做完，点满三下。',
    props: { hero: '❗', items: ['❗', '❗', '❗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '永', unit: 'u65', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '水流啊流，永远流不完。',
    props: { hero: '♾️', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '司', unit: 'u65', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '上公司的班车，看看车上有啥。',
    props: { hero: '🚌', items: ['💼', '📋', '☕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '叩', unit: 'u65', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '叩叩门环，问一句有人吗。',
    props: { hero: '🚪', sound: '叩叩', goal: 3 },
    templateFallback: false
  },
  {
    char: '辽', unit: 'u65', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '地方越看越辽阔，一望无边。',
    props: { hero: '🌏', stages: ['🏡', '🏞️', '🌏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '召', unit: 'u65', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '喊一嗓子召集大家，来三个。',
    props: { hero: '📣', items: ['🧒', '👧', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '圣', unit: 'u65', theme: 'feeling',
    template: 'color-fill', interaction: 'tap',
    narration: '给这颗圣诞星涂上金光。',
    props: { hero: '🌟', color: '金黄', goal: 3 },
    templateFallback: false
  },
  {
    char: '纠', unit: 'u65', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '绳子缠住了，纠出来解开。',
    props: { hero: '🔧', parts: ['🧵', '🪢'], goal: 2 },
    templateFallback: false
  },
  {
    char: '邦', unit: 'u65', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哪些在城里，哪些在乡下。',
    props: { hero: '🌐', items: [{ item: '🚇', bucket: '城里' }, { item: '🏢', bucket: '城里' }, { item: '🐓', bucket: '乡下' }, { item: '🌾', bucket: '乡下' }], buckets: [{ label: '城里', emoji: '🏙️' }, { label: '乡下', emoji: '🏡' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '动', unit: 'u65', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '别站着啦，动起来往前跑。',
    props: { hero: '🏃', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '扛', unit: 'u65', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '使劲把大袋子扛上肩。',
    props: { hero: '💪', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '寺', unit: 'u65', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '小寺庙里安安静静，点点看。',
    props: { hero: '🛕', items: ['🔔', '🕯️', '🧘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '吉', unit: 'u65', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '红包里装着吉利话，拆开看。',
    props: { hero: '🧧', items: ['🧧', '🍊', '🪙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '托', unit: 'u65', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '用手托住盘子，托稳三下。',
    props: { hero: '🤲', items: ['🍽️', '🍽️', '🍽️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弘', unit: 'u65', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '声音放得弘大，传得远远的。',
    props: { hero: '📣', sound: '喔', goal: 3 },
    templateFallback: false
  },
  {
    char: '圾', unit: 'u65', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把垃圾一样样清干净。',
    props: { hero: '🗑️', items: ['🍌', '🥤', '📄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '执', unit: 'u65', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '手里执着小旗，握紧不放。',
    props: { hero: '✋', parts: ['🚩', '✋'], goal: 2 },
    templateFallback: false
  },
  {
    char: '扩', unit: 'u65', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '圈圈慢慢扩大，越来越宽。',
    props: { hero: '↔️', stages: ['⚪', '🔵', '🌀'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
