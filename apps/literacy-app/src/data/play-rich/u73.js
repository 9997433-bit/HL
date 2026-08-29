/**
 * 富互动 play 分片 u73 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u73'

export const UNIT_RICH_PLAYS = [
  {
    char: '克', unit: 'u73', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '称一称，正好一千克。',
    props: { hero: '⚖️', items: ['⚖️', '⚖️', '⚖️', '⚖️'], goal: 4 },
    templateFallback: false
  },
  {
    char: '芭', unit: 'u73', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '芭蕉叶又大又绿，点三片。',
    props: { hero: '🍌', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '苏', unit: 'u73', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小种子苏醒了，钻出土。',
    props: { hero: '🌱', stages: ['🪵', '🌱', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杆', unit: 'u73', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '旗杆立起来，旗子升上去。',
    props: { hero: '🚩', stages: ['💧', '🚩', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杠', unit: 'u73', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '抓住单杠，身体荡过去。',
    props: { hero: '🤸', items: [{ item: '🤸', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '杜', unit: 'u73', theme: 'nature',
    template: 'color-fill', interaction: 'tap',
    narration: '杜鹃花开了，数满四朵。',
    props: { hero: '🌺', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '材', unit: 'u73', theme: 'nature',
    template: 'rain-catch', interaction: 'drag',
    narration: '木头是材料，拼成小屋。',
    props: { hero: '🪵', items: ['🌙', '🎈', '🧩'], tool: '🪵', goal: 3 },
    templateFallback: false
  },
  {
    char: '杖', unit: 'u73', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拄着手杖，慢慢往前走。',
    props: { hero: '🦯', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '杉', unit: 'u73', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '水杉又高又直，往上看。',
    props: { hero: '🌲', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '李', unit: 'u73', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '树上结了李子，摘三颗。',
    props: { hero: '🍑', items: ['🍑', '🍑', '🍑', '🍑'], goal: 4 },
    templateFallback: false
  },
  {
    char: '求', unit: 'u73', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '双手合十，请求帮个忙。',
    props: { hero: '🙏', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '束', unit: 'u73', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '花束扎紧，送出一束花。',
    props: { hero: '💐', parts: ['🔑', '🔔', '💐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '两', unit: 'u73', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数数看，正好有两个。',
    props: { hero: '2️⃣', items: ['2️⃣', '2️⃣', '2️⃣', '2️⃣'], goal: 4 },
    templateFallback: false
  },
  {
    char: '丽', unit: 'u73', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '彩虹真美丽，点亮七色。',
    props: { hero: '🌈', parts: ['🧩', '🌱', '🌈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '励', unit: 'u73', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '拍拍肩，给他鼓劲激励。',
    props: { hero: '📣', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '否', unit: 'u73', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '摇头说否，把叉叉点亮。',
    props: { hero: '❌', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '连', unit: 'u73', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '把链条一节节连起来。',
    props: { hero: '🔗', parts: ['🌱', '💧', '🔗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坚', unit: 'u73', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '石头坚硬，敲不碎它。',
    props: { hero: '🪨', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '盯', unit: 'u73', theme: 'shape',
    template: 'morph-story', interaction: 'sequence',
    narration: '眼睛盯紧，别让它跑掉。',
    props: { hero: '👀', stages: ['🪵', '👀', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '呈', unit: 'u73', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '晚霞呈现出来，越来越红。',
    props: { hero: '🌇', pairs: [{ a: '🌇', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌇' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
