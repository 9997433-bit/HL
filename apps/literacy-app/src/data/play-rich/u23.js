/**
 * 富互动 play 分片 u23 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u23'

export const UNIT_RICH_PLAYS = [
  {
    char: '江', unit: 'u23', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '大江水哗哗，带着轮船顺流走。',
    props: { hero: '🚢', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '湖', unit: 'u23', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '平平的湖面上，点点都有谁。',
    props: { hero: '🏞️', items: ['🦢', '🐟', '🛶'], goal: 3 },
    templateFallback: false
  },
  {
    char: '池', unit: 'u23', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '小池塘里热闹极了，点一点。',
    props: { hero: '🪷', items: ['🐸', '🐟', '🪷'], goal: 3 },
    templateFallback: false
  },
  {
    char: '岛', unit: 'u23', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '水把地围起来，中间那块就是岛。',
    props: { hero: '🏝️', parts: ['🌊', '🏝️', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '泥', unit: 'u23', theme: 'nature',
    template: 'color-fill', interaction: 'tap',
    narration: '下过雨，路上和成黄黄的泥。',
    props: { hero: '🟤', color: 'brown', goal: 3 },
    templateFallback: false
  },
  {
    char: '雷', unit: 'u23', theme: 'weather',
    template: 'sound-tap', interaction: 'tap',
    narration: '乌云一撞，轰隆隆打雷了。',
    props: { hero: '🌩️', sound: '轰隆', goal: 3 },
    templateFallback: false
  },
  {
    char: '雾', unit: 'u23', theme: 'weather',
    template: 'tap-reveal', interaction: 'tap',
    narration: '雾好大，吹一吹才看得见东西。',
    props: { hero: '🌫️', items: ['🌳', '🏠', '🚗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '洋', unit: 'u23', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大洋比海还宽，推着船往远处开。',
    props: { hero: '🚢', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '波', unit: 'u23', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手指一划，水面荡起一道波。',
    props: { hero: '🌊', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '浪', unit: 'u23', theme: 'nature',
    template: 'rain-catch', interaction: 'drag',
    narration: '大浪打过来，接住溅起的水花。',
    props: { hero: '🌊', items: ['💦', '💦', '💦'], tool: '🪣', goal: 3 },
    templateFallback: false
  },
  {
    char: '流', unit: 'u23', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '水总是从高处往低处流。',
    props: { hero: '💦', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '洞', unit: 'u23', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '山上有个洞，看看里面住着谁。',
    props: { hero: '🕳️', items: ['🦇', '🐻', '🦉'], goal: 3 },
    templateFallback: false
  },
  {
    char: '井', unit: 'u23', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '两横两竖搭起来，就成了井。',
    props: { hero: '🕳️', parts: ['一', '一', '丨', '丨'], goal: 4 },
    templateFallback: false
  },
  {
    char: '泉', unit: 'u23', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '石头缝里冒出泉水，越冒越多。',
    props: { hero: '⛲', stages: ['🪨', '💧', '⛲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '岸', unit: 'u23', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '划呀划，把小船靠到岸边。',
    props: { hero: '🛶', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '湿', unit: 'u23', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '雨点打在身上，衣服都湿了。',
    props: { hero: '👕', items: ['💧', '💧', '💧'], tool: '👕', goal: 3 },
    templateFallback: false
  },
  {
    char: '干', unit: 'u23', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳一晒，湿衣服慢慢变干。',
    props: { hero: '🧻', stages: ['👕', '🌞', '干'], goal: 3 },
    templateFallback: false
  },
  {
    char: '净', unit: 'u23', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把桌上的脏东西擦得干干净净。',
    props: { hero: '🧽', items: ['🍂', '🕸️', '🧃'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
