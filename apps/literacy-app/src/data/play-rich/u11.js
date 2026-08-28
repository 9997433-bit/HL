/**
 * 富互动 play 分片 u11 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u11'

export const UNIT_RICH_PLAYS = [
  {
    char: '春', unit: 'u11', theme: 'time',
    template: 'grow-tap', interaction: 'tap',
    narration: '春风一吹，花全都开了。',
    props: { hero: '🌷', stages: ['🌱', '🌷', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '夏', unit: 'u11', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '夏天太阳好大，点点消暑的东西。',
    props: { hero: '🌞', items: ['🍉', '🏖️', '🍦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '秋', unit: 'u11', theme: 'time',
    template: 'rain-catch', interaction: 'drag',
    narration: '秋风起，接住飘下来的黄叶子。',
    props: { hero: '🍂', items: ['🍁', '🍂', '🍁'], tool: '🧺', goal: 3 },
    templateFallback: false
  },
  {
    char: '冬', unit: 'u11', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '冬天冷冰冰，给雪人穿戴好。',
    props: { hero: '⛄', items: ['🧣', '🧤', '🎩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '早', unit: 'u11', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳从地平线上升起来，早上到了。',
    props: { hero: '🌅', stages: ['🌑', '🌅', '🌞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '晚', unit: 'u11', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳落下去月亮爬上来，天晚了。',
    props: { hero: '🌆', stages: ['🌇', '🌆', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '明', unit: 'u11', theme: 'time',
    template: 'drag-parts', interaction: 'drag',
    narration: '日和月放在一起，天亮堂堂。',
    props: { hero: '🌞', parts: ['日', '月'], goal: 2 },
    templateFallback: false
  },
  {
    char: '今', unit: 'u11', theme: 'time',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '一堆日子里，找出今天那一格。',
    props: { hero: '📅', target: '📅', decoys: ['🗓️', '🗓️', '🗓️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '年', unit: 'u11', theme: 'time',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '新年到，点响四个小烟花。',
    props: { hero: '🎊', items: ['🎆', '🎆', '🎆', '🎆'], goal: 4 },
    templateFallback: false
  },
  {
    char: '时', unit: 'u11', theme: 'time',
    template: 'trace-path', interaction: 'drag',
    narration: '拨一拨时针，让钟走一圈。',
    props: { hero: '⏰', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '分', unit: 'u11', theme: 'time',
    template: 'drag-parts', interaction: 'drag',
    narration: '把一块饼干平平地分成两半。',
    props: { hero: '🍪', parts: ['🍪', '🍪'], goal: 2 },
    templateFallback: false
  },
  {
    char: '刻', unit: 'u11', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '一刻是十五分，点四下就一小时。',
    props: { hero: '⏳', items: ['⏳', '⏳', '⏳', '⏳'], goal: 4 },
    templateFallback: false
  },
  {
    char: '岁', unit: 'u11', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '过一个生日长一岁，点亮蜡烛数数。',
    props: { hero: '🎂', items: ['🕯️', '🕯️', '🕯️', '🕯️', '🕯️'], goal: 5 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
