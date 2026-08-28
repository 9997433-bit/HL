/**
 * 富互动 play 分片 u66 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u66'

export const UNIT_RICH_PLAYS = [
  {
    char: '场', unit: 'u66', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '操场上真热闹，点点在玩啥。',
    props: { hero: '🏟️', items: ['⚽', '🏀', '🏸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扬', unit: 'u66', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把小旗高高扬起来。',
    props: { hero: '🚩', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '芋', unit: 'u66', theme: 'food',
    template: 'tap-reveal', interaction: 'tap',
    narration: '泥里埋着芋头，挖开瞧瞧。',
    props: { hero: '🍠', items: ['🍠', '🥔', '🌰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '芒', unit: 'u66', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪根麦芒最尖？把它找出来。',
    props: { hero: '🌾', target: '🌾', decoys: ['🍃', '🌸', '🍄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '亚', unit: 'u66', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '第一第二排好队，配一配。',
    props: { hero: '🥈', pairs: [{ a: '🥇', b: '1️⃣' }, { a: '🥈', b: '2️⃣' }, { a: '🥉', b: '3️⃣' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '芝', unit: 'u66', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '小芝麻发了芽，冒出嫩苗。',
    props: { hero: '🌱', stages: ['🌰', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '朽', unit: 'u66', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '木头搁久了，慢慢就朽了。',
    props: { hero: '🪵', stages: ['🪵', '🍂', '🍄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '朴', unit: 'u66', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '朴素的一边，花哨的一边。',
    props: { hero: '🧺', items: [{ item: '🥣', bucket: '朴素' }, { item: '🧦', bucket: '朴素' }, { item: '👑', bucket: '花哨' }, { item: '💎', bucket: '花哨' }], buckets: [{ label: '朴素', emoji: '🧺' }, { label: '花哨', emoji: '✨' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '权', unit: 'u66', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '天平两边配平，才算公道。',
    props: { hero: '⚖️', pairs: [{ a: '⚖️', b: '⚖️' }, { a: '🍎', b: '🍎' }, { a: '🪨', b: '🪨' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '协', unit: 'u66', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '大家协力，一起把车推动。',
    props: { hero: '🤝', parts: ['🧒', '🧒', '🚗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '西', unit: 'u66', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '太阳往西边落，跟着走。',
    props: { hero: '🧭', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '压', unit: 'u66', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用手往下压一压，压扁它。',
    props: { hero: '⬇️', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '厌', unit: 'u66', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪张脸在讨厌？找出皱眉的。',
    props: { hero: '😒', target: '😒', decoys: ['😄', '😍', '😃'], goal: 1 },
    templateFallback: false
  },
  {
    char: '匠', unit: 'u66', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '木匠抡起锤子，钉好板子。',
    props: { hero: '🔨', parts: ['🔨', '🪵', '🔩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '夸', unit: 'u66', theme: 'feeling',
    template: 'count-tap', interaction: 'tap',
    narration: '夸一夸，一起鼓三下掌。',
    props: { hero: '👏', items: ['👏', '👏', '👏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '夺', unit: 'u66', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '奖杯掉下来，抢先夺一个。',
    props: { hero: '🏆', items: ['🏆', '🏅', '🎖️'], tool: '🧤', goal: 3 },
    templateFallback: false
  },
  {
    char: '达', unit: 'u66', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '一路走呀走，终于到达。',
    props: { hero: '🎯', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '列', unit: 'u66', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '排成一列，一个一个数四个。',
    props: { hero: '📋', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '夹', unit: 'u66', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '用筷子把丸子夹起来。',
    props: { hero: '🥢', parts: ['🥢', '🍡'], goal: 2 },
    templateFallback: false
  },
  {
    char: '毕', unit: 'u66', theme: 'school',
    template: 'morph-story', interaction: 'sequence',
    narration: '学完啦，戴上毕业的帽子。',
    props: { hero: '🎓', stages: ['📚', '🎓', '🎉'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
