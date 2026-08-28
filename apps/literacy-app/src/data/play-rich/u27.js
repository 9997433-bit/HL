/**
 * 富互动 play 分片 u27 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u27'

export const UNIT_RICH_PLAYS = [
  {
    char: '船', unit: 'u27', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '小船在水上开，一直开到码头。',
    props: { hero: '⛵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '飞', unit: 'u27', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '张开翅膀，一下子飞上天。',
    props: { hero: '🕊️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '机', unit: 'u27', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '机场好大，飞机旁边有什么。',
    props: { hero: '✈️', items: ['🧳', '🛫', '🎫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '路', unit: 'u27', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着小路往前走，走到家门口。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '桥', unit: 'u27', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '把木板一块块架起来，搭成桥。',
    props: { hero: '🌉', parts: ['🟫', '🟫', '🟫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '票', unit: 'u27', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '上车要买票，点开看看是哪张。',
    props: { hero: '🎫', items: ['🎫', '🎟️', '🎫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '轮', unit: 'u27', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '圆轮子一转，车就往前走。',
    props: { hero: '🛞', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '骑', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '跨上自行车，骑着往前冲。',
    props: { hero: '🚲', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '停', unit: 'u27', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '红灯亮了，点一下让车都停住。',
    props: { hero: '🛑', items: ['🚗', '🚌', '🚲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '到', unit: 'u27', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '一步一步，终于走到终点了。',
    props: { hero: '🏁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '过', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '看看两边，牵着手过马路。',
    props: { hero: '🚸', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '转', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '方向盘往右一转，车就拐弯。',
    props: { hero: '🔄', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '追', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小狗在后面追，快跑别被追上。',
    props: { hero: '🐕', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '赶', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '使劲跑，赶上前面那一个。',
    props: { hero: '🏃', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '迎', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '张开手，迎着客人走过去。',
    props: { hero: '🤗', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '离', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挥挥手告别，小船离开岸。',
    props: { hero: '⛵', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '回', unit: 'u27', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '天黑了，小鸟回到自己的窝。',
    props: { hero: '🐦', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '向', unit: 'u27', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '向日葵总是朝着太阳那边。',
    props: { hero: '🌻', dir: 'up', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
