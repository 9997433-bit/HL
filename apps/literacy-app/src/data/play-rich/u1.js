/**
 * 富互动 play 分片 u1 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u1'

export const UNIT_RICH_PLAYS = [
  {
    char: '一', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '只点一个苹果就好，一就是最小的数。',
    props: { hero: '☝️', items: ['🍎'], goal: 1 },
    templateFallback: false
  },
  {
    char: '二', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '再添一只小鸭，两只排排站就是二。',
    props: { hero: '✌️', items: ['🦆', '🦆'], goal: 2 },
    templateFallback: false
  },
  {
    char: '三', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '点亮三颗星星，三横就是三。',
    props: { hero: '🤟', items: ['⭐', '⭐', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '上', unit: 'u1', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往上一推，气球飞到高高的天上。',
    props: { hero: '🎈', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '下', unit: 'u1', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往下一拉，雨滴落到地面上。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '人', unit: 'u1', theme: 'body',
    template: 'morph-story', interaction: 'sequence',
    narration: '小人迈开两条腿，就走成了人字。',
    props: { hero: '🧍', stages: ['🧍', '🚶', '人'], goal: 3 },
    templateFallback: false
  },
  {
    char: '口', unit: 'u1', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '点点小嘴巴，张开说「啊」。',
    props: { hero: '👄', sound: '啊', goal: 3 },
    templateFallback: false
  },
  {
    char: '大', unit: 'u1', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '张开双手越张越开，这就是大。',
    props: { hero: '🙆', stages: ['🙋', '🙆', '🐘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '小', unit: 'u1', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁最小？把小小的那一个找出来。',
    props: { hero: '🐣', target: '🐣', decoys: ['🐔', '🐘', '🐄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '我', unit: 'u1', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '点点镜子里的小朋友，那就是我。',
    props: { hero: '🪞', items: ['🙋'], goal: 1 },
    templateFallback: false
  },
  {
    char: '个', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一个一个放进筐里，数数几个。',
    props: { hero: '🧺', items: ['🍎', '🍎', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '们', unit: 'u1', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一个人加上大家，就成了我们。',
    props: { hero: '👥', items: ['🧍', '🧍', '🧍'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
