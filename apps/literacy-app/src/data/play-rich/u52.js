/**
 * 富互动 play 分片 u52 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u52'

export const UNIT_RICH_PLAYS = [
  {
    char: '投', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把球往上一投，投进筐里。',
    props: { hero: '🤾', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '掷', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '飞盘往远处一掷，飞出去。',
    props: { hero: '🥏', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '射', unit: 'u52', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '拉满弓，箭嗖地射出去。',
    props: { hero: '🏹', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '拳', unit: 'u52', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '出拳三下，一二三。',
    props: { hero: '🥊', items: ['🥊', '🥊', '🥊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '剑', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '举起剑，往前一刺。',
    props: { hero: '🤺', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '泳', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手一划脚一蹬，往前游。',
    props: { hero: '🏊', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '潜', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '吸口气，潜到水底下去。',
    props: { hero: '🤿', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '滑', unit: 'u52', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '冰面上一滑，滑出老远。',
    props: { hero: '⛸️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '划', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '两只桨往后划，船就前进。',
    props: { hero: '🛶', dir: 'left', goal: 4 },
    templateFallback: false
  },
  {
    char: '攀', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '手脚并用，攀着岩壁往上。',
    props: { hero: '🧗', dir: 'up', goal: 4 },
    templateFallback: false
  },
  {
    char: '登', unit: 'u52', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一步一步登上山顶，走五步。',
    props: { hero: '🥾', items: ['🥾', '🥾', '🥾', '🥾', '🥾'], goal: 5 },
    templateFallback: false
  },
  {
    char: '冠', unit: 'u52', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '谁拿了冠军？揭开奖台看看。',
    props: { hero: '🏆', items: ['🥇', '🥈', '🥉'], goal: 3 },
    templateFallback: false
  },
  {
    char: '军', unit: 'u52', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '队伍排整齐，数数几列。',
    props: { hero: '🎖️', items: ['🎖️', '🎖️', '🎖️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '赢', unit: 'u52', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '冲过终点线，这局赢了。',
    props: { hero: '🎉', stages: ['🏃', '🏁', '🎉'], goal: 3 },
    templateFallback: false
  },
  {
    char: '步', unit: 'u52', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一步两步三步，走给我看。',
    props: { hero: '👣', items: ['👣', '👣', '👣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '迈', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '抬起腿，往前迈一大步。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '蹲', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '膝盖一弯，慢慢蹲下去。',
    props: { hero: '🧎', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '爬', unit: 'u52', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '小宝宝手脚并用往前爬。',
    props: { hero: '🧗', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '扶', unit: 'u52', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '奶奶要过马路，去扶一把。',
    props: { hero: '🤝', parts: ['👵', '🤝'], goal: 2 },
    templateFallback: false
  },
  {
    char: '捧', unit: 'u52', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手捧着，把花举起来。',
    props: { hero: '🙌', dir: 'up', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
