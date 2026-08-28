/**
 * 富互动 play 分片 u16 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u16'

export const UNIT_RICH_PLAYS = [
  {
    char: '这', unit: 'u16', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '指着近处说这个，就在手边。',
    props: { hero: '👇', items: ['🧸', '🍎', '🖍️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '那', unit: 'u16', theme: 'word',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '远远的那个才是那，点远处的。',
    props: { hero: '👆', target: '🏔️', decoys: ['🧸', '🍎', '🪑'], goal: 1 },
    templateFallback: false
  },
  {
    char: '什', unit: 'u16', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盒子里是什么？打开问一问。',
    props: { hero: '❔', items: ['🎁', '🎁', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '么', unit: 'u16', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '什么、怎么、这么，把两个字配好。',
    props: { hero: '🔎', pairs: [{ a: '什', b: '么' }, { a: '怎', b: '么' }, { a: '这', b: '么' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '都', unit: 'u16', theme: 'word',
    template: 'count-tap', interaction: 'tap',
    narration: '一个都不少，全点到才算都。',
    props: { hero: '🧑‍🤝‍🧑', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '要', unit: 'u16', theme: 'feeling',
    template: 'sort-buckets', interaction: 'drag',
    narration: '想要的放这边，不要的放那边。',
    props: { hero: '🙏', items: [{ item: '🍎', bucket: '要' }, { item: '🧸', bucket: '要' }, { item: '🗑️', bucket: '不要' }, { item: '🦟', bucket: '不要' }], buckets: [{ label: '要', emoji: '🙏' }, { label: '不要', emoji: '🙅' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '能', unit: 'u16', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '试一试就知道，我能行。',
    props: { hero: '💪', items: ['🏃', '🎨', '🎵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '想', unit: 'u16', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '闭上眼想一想，脑袋里冒出什么。',
    props: { hero: '💭', items: ['🍦', '🏖️', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '用', unit: 'u16', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '每样东西都有用处，配一配。',
    props: { hero: '🛠️', pairs: [{ a: '✏️', b: '📄' }, { a: '🥄', b: '🍚' }, { a: '🔑', b: '🚪' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '做', unit: 'u16', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '动手做一做：做饭、做手工。',
    props: { hero: '🧑‍🔧', items: ['🍳', '✂️', '🔨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '给', unit: 'u16', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把礼物送到小伙伴手里。',
    props: { hero: '🎁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '把', unit: 'u16', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把扫帚拿过来，抓住把手。',
    props: { hero: '🧹', parts: ['🧹', '✋'], goal: 2 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
