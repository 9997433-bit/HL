/**
 * 富互动 play 分片 u59 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u59'

export const UNIT_RICH_PLAYS = [
  {
    char: '乙', unit: 'u59', theme: 'shape',
    template: 'morph-story', interaction: 'sequence',
    narration: '一笔弯弯拐个钩，就是乙。',
    props: { hero: '🔢', stages: ['〰️', '🪝', '乙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '丁', unit: 'u59', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '小钉子立起来，钉住木板。',
    props: { hero: '📌', parts: ['📌', '🪵'], goal: 2 },
    templateFallback: false
  },
  {
    char: '卜', unit: 'u59', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翻开小卦看一看，会是什么。',
    props: { hero: '🔮', items: ['☀️', '🌧️', '🌈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '入', unit: 'u59', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '带着小人往门里走进去。',
    props: { hero: '🚪', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '儿', unit: 'u59', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小娃娃一年年长，长成男孩。',
    props: { hero: '👦', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '于', unit: 'u59', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '东西在于哪儿？找到那个点。',
    props: { hero: '📍', target: '📍', decoys: ['🌳', '🚗', '🏠'], goal: 1 },
    templateFallback: false
  },
  {
    char: '亏', unit: 'u59', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '吃了亏，嘴巴一下子瘪下去。',
    props: { hero: '😖', stages: ['🙂', '😕', '😖'], goal: 3 },
    templateFallback: false
  },
  {
    char: '士', unit: 'u59', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小战士挺起胸，昂首站好。',
    props: { hero: '🎖️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '丈', unit: 'u59', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一丈一丈量墙，量满三丈。',
    props: { hero: '📏', items: ['📏', '📏', '📏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '巾', unit: 'u59', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小手巾叠好挂起来。',
    props: { hero: '🧣', parts: ['🧻', '🪝'], goal: 2 },
    templateFallback: false
  },
  {
    char: '川', unit: 'u59', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '三条水线往前淌，那是大川。',
    props: { hero: '🏞️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '亿', unit: 'u59', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数字大得数不完，先点五下。',
    props: { hero: '🔢', items: ['🔢', '🔢', '🔢', '🔢', '🔢'], goal: 5 },
    templateFallback: false
  },
  {
    char: '夕', unit: 'u59', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳落山，夕阳染红了天边。',
    props: { hero: '🌇', stages: ['🌞', '🌇', '🌆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '勺', unit: 'u59', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '拿小勺舀汤，舀满三勺。',
    props: { hero: '🥄', items: ['🥄', '🥄', '🥄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '凡', unit: 'u59', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个最平凡？挑出普通的那张脸。',
    props: { hero: '🙂', target: '🙂', decoys: ['👑', '🦄', '🌟'], goal: 1 },
    templateFallback: false
  },
  {
    char: '丸', unit: 'u59', theme: 'shape',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小圆丸滚过来，一个个收好。',
    props: { hero: '⚪', items: ['⚪', '⚪', '⚪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '广', unit: 'u59', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '广场好宽好大，点点有什么。',
    props: { hero: '🏞️', items: ['⛲', '🕊️', '🎠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '丫', unit: 'u59', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '树枝分出两个丫，拼一拼。',
    props: { hero: '🌿', parts: ['🌿', '🌿'], goal: 2 },
    templateFallback: false
  },
  {
    char: '义', unit: 'u59', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '讲义气的小伙伴，配成一对。',
    props: { hero: '🤝', pairs: [{ a: '🐶', b: '🦴' }, { a: '🐱', b: '🐟' }, { a: '🐰', b: '🥕' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '之', unit: 'u59', theme: 'word',
    template: 'trace-path', interaction: 'drag',
    narration: '沿着弯弯的之字路上山。',
    props: { hero: '📜', dir: 'up', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
