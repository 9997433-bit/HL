/**
 * 富互动 play 分片 u34 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u34'

export const UNIT_RICH_PLAYS = [
  {
    char: '铃', unit: 'u34', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '上课铃响了，叮铃铃。',
    props: { hero: '🔔', sound: '叮铃', goal: 3 },
    templateFallback: false
  },
  {
    char: '操', unit: 'u34', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '做早操，两只手一起往上伸。',
    props: { hero: '🤸', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '训', unit: 'u34', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '跟着老师练三遍，一遍点一下。',
    props: { hero: '🧑‍🏫', items: ['✔️', '✔️', '✔️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '育', unit: 'u34', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小苗要人养，小孩要人育。',
    props: { hero: '🌱', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '座', unit: 'u34', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '摆好三个小座位，请大家坐。',
    props: { hero: '🪑', parts: ['🪑', '🪑', '🪑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '席', unit: 'u34', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '铺开一张席子，上面摆什么。',
    props: { hero: '🧺', items: ['🍉', '🥤', '📕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '卷', unit: 'u34', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '把画纸从一头卷到另一头。',
    props: { hero: '📜', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '考', unit: 'u34', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '考一考，点开题目做一做。',
    props: { hero: '📝', items: ['❔', '❔', '❔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '测', unit: 'u34', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '量一量测三次，看看是多少。',
    props: { hero: '📐', items: ['📏', '📏', '📏'], goal: 3 },
    templateFallback: false
  },
  {
    char: '优', unit: 'u34', theme: 'school',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一份最好？点出得优的那张。',
    props: { hero: '🌟', target: '🏅', decoys: ['📄', '📄', '📄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '良', unit: 'u34', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '做得好的贴星，还要加油的贴脸。',
    props: { hero: '👌', items: [{ item: '💯', bucket: '好' }, { item: '🏅', bucket: '好' }, { item: '📄', bucket: '加油' }, { item: '✏️', bucket: '加油' }], buckets: [{ label: '好', emoji: '⭐' }, { label: '加油', emoji: '🙂' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '差', unit: 'u34', theme: 'school',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出不一样的那个，它差一点。',
    props: { hero: '❗', target: '🔺', decoys: ['🔵', '🔵', '🔵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '错', unit: 'u34', theme: 'school',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '队伍里谁站错了？把他找出来。',
    props: { hero: '✖️', target: '🐧', decoys: ['🧒', '🧒', '🧒'], goal: 1 },
    templateFallback: false
  },
  {
    char: '改', unit: 'u34', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '写错了别急，擦掉改成对的。',
    props: { hero: '🔁', stages: ['❌', '🧽', '改'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抄', unit: 'u34', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '照着黑板，把字一个个抄下来。',
    props: { hero: '✍️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '默', unit: 'u34', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '不出声默默想，再点开对答案。',
    props: { hero: '🤫', items: ['✅', '✅', '❌'], goal: 3 },
    templateFallback: false
  },
  {
    char: '复', unit: 'u34', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '学过的再复习一遍，点满四下。',
    props: { hero: '🔁', items: ['📕', '📗', '📘', '📙'], goal: 4 },
    templateFallback: false
  },
  {
    char: '温', unit: 'u34', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '温故知新，旧本子再翻一翻。',
    props: { hero: '🌡️', stages: ['📕', '🔁', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '预', unit: 'u34', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '先预备好，明天要用的都装上。',
    props: { hero: '🎒', items: ['📕', '✏️', '🥤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '编', unit: 'u34', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把三根绳子编成一条辫子。',
    props: { hero: '🧶', parts: ['🧵', '🧵', '🧵'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
