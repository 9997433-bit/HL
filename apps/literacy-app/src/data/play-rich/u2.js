/**
 * 富互动 play 分片 u2 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u2'

export const UNIT_RICH_PLAYS = [
  {
    char: '日', unit: 'u2', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '圆圆的太阳慢慢变方，就成了日。',
    props: { hero: '☀️', stages: ['☀️', '🌞', '日'], goal: 3 },
    templateFallback: false
  },
  {
    char: '月', unit: 'u2', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '满月一点点变弯，弯成月字。',
    props: { hero: '🌙', stages: ['🌕', '🌙', '月'], goal: 3 },
    templateFallback: false
  },
  {
    char: '山', unit: 'u2', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '把三个山尖尖立起来，就是山。',
    props: { hero: '⛰️', parts: ['⛰️', '⛰️', '⛰️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '水', unit: 'u2', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '带着小水滴顺着山坡流下来。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '火', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '添一根柴，火苗就往上蹿一点。',
    props: { hero: '🔥', stages: ['🕯️', '🔥', '🌋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '木', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '小树苗喝饱水，长成一棵大树。',
    props: { hero: '🌲', stages: ['🌱', '🌿', '🌲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '田', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '一格一格的田里，点点种了什么。',
    props: { hero: '🌾', items: ['🌾', '🌽', '🥬', '🍠'], goal: 4 },
    templateFallback: false
  },
  {
    char: '土', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '挖挖泥土，看看土里藏着谁。',
    props: { hero: '🟫', items: ['🌱', '🐛', '🥔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '天', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '抬头看天，天上都有些什么。',
    props: { hero: '🌤️', items: ['☁️', '🐦', '🌈', '✈️'], goal: 4 },
    templateFallback: false
  },
  {
    char: '花', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '浇浇水，花骨朵一点点开了。',
    props: { hero: '🌸', stages: ['🌱', '🌷', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '海', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '大海好宽，点点浪里的小伙伴。',
    props: { hero: '🌊', items: ['🐬', '🐠', '🐚', '⛵'], goal: 4 },
    templateFallback: false
  },
  {
    char: '河', unit: 'u2', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '带小船顺着弯弯的小河往前漂。',
    props: { hero: '⛵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '林', unit: 'u2', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个木是树，两个木并排就是林。',
    props: { hero: '🌳', parts: ['木', '木'], goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
