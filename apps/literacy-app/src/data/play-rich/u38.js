/**
 * 富互动 play 分片 u38 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u38'

export const UNIT_RICH_PLAYS = [
  {
    char: '晴', unit: 'u38', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '云散开了，天一下子晴起来。',
    props: { hero: '☀️', stages: ['☁️', '⛅', '☀️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '阴', unit: 'u38', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '云飘过来遮住太阳，天阴了。',
    props: { hero: '☁️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '霜', unit: 'u38', theme: 'weather',
    template: 'color-fill', interaction: 'tap',
    narration: '一夜过去，叶子上结了白霜。',
    props: { hero: '🍂', color: 'white', goal: 3 },
    templateFallback: false
  },
  {
    char: '露', unit: 'u38', theme: 'nature',
    template: 'rain-catch', interaction: 'drag',
    narration: '清早的露珠滚下来，接住它。',
    props: { hero: '🌿', items: ['💧', '💧', '💧'], tool: '🍃', goal: 3 },
    templateFallback: false
  },
  {
    char: '冻', unit: 'u38', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '水在外面放一夜，冻成硬块。',
    props: { hero: '🧊', stages: ['💧', '🧊', '冻'], goal: 3 },
    templateFallback: false
  },
  {
    char: '霞', unit: 'u38', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把天边的云涂成红彤彤的霞。',
    props: { hero: '🌇', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '虹', unit: 'u38', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '雨停了，天上架起一道彩虹。',
    props: { hero: '🌈', stages: ['🌧️', '⛅', '🌈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '潮', unit: 'u38', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '潮水涨上来，一直漫到脚边。',
    props: { hero: '🌊', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '旱', unit: 'u38', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '好久不下雨，地都晒裂了。',
    props: { hero: '🏜️', stages: ['🌱', '🌵', '旱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '涝', unit: 'u38', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '雨下个不停，赶紧把水舀走。',
    props: { hero: '🌊', items: ['💧', '💧', '💧', '💧'], tool: '🪣', goal: 4 },
    templateFallback: false
  },
  {
    char: '暴', unit: 'u38', theme: 'weather',
    template: 'sound-tap', interaction: 'tap',
    narration: '暴风雨来了，呼呼直响。',
    props: { hero: '⛈️', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '烈', unit: 'u38', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '日头越来越烈，晒得人躲开。',
    props: { hero: '🔥', stages: ['🌤️', '🌞', '🔥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '寒', unit: 'u38', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '风一阵比一阵寒，冻得发抖。',
    props: { hero: '🥶', stages: ['🍃', '❄️', '🥶'], goal: 3 },
    templateFallback: false
  },
  {
    char: '凉', unit: 'u38', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '天热喝点凉的，点开挑一样。',
    props: { hero: '🧊', items: ['🥤', '🍧', '🍉'], goal: 3 },
    templateFallback: false
  },
  {
    char: '洪', unit: 'u38', theme: 'nature',
    template: 'rain-catch', interaction: 'drag',
    narration: '大水冲过来，快拿沙袋挡住。',
    props: { hero: '🌊', items: ['🌊', '🌊', '🌊'], tool: '🧱', goal: 3 },
    templateFallback: false
  },
  {
    char: '浇', unit: 'u38', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '提起水壶，给小花浇点水。',
    props: { hero: '🚿', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '泼', unit: 'u38', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '一盆水往外泼，哗地一下。',
    props: { hero: '🪣', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '溅', unit: 'u38', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '踩进水坑，水花溅得到处都是。',
    props: { hero: '💦', items: ['💦', '💦', '💦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '淹', unit: 'u38', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '水越涨越高，把小船淹住了。',
    props: { hero: '🌊', stages: ['⛵', '💧', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '冒', unit: 'u38', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '锅盖一掀，热气直往上冒。',
    props: { hero: '💨', stages: ['🍲', '♨️', '☁️'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
