/**
 * 富互动 play 分片 u8 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u8'

export const UNIT_RICH_PLAYS = [
  {
    char: '学', unit: 'u8', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '每学会一样本领，就点亮一颗星。',
    props: { hero: '📚', stages: ['📖', '✏️', '🌟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '校', unit: 'u8', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '走进学校，点点里面都有什么。',
    props: { hero: '🏫', items: ['🚪', '🔔', '🏀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '老', unit: 'u8', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '谁年纪大？把老爷爷放到老这边。',
    props: { hero: '👴', items: [{ item: '👵', bucket: '老' }, { item: '🧓', bucket: '老' }, { item: '🧒', bucket: '小' }, { item: '👶', bucket: '小' }], buckets: [{ label: '老', emoji: '👴' }, { label: '小', emoji: '👶' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '师', unit: 'u8', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '老师教我们本领，点点她手里的东西。',
    props: { hero: '🧑‍🏫', items: ['📕', '✏️', '🗺️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '生', unit: 'u8', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '一颗种子从土里生出来，越长越高。',
    props: { hero: '🌱', stages: ['🌰', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '书', unit: 'u8', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一页一页翻开书，看看里面画了什么。',
    props: { hero: '📕', items: ['📖', '🖼️', '🔤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '字', unit: 'u8', theme: 'school',
    template: 'word-build', interaction: 'drag',
    narration: '一个个方块字，拼出「写字」。',
    props: { hero: '🔤', parts: ['写', '字'], word: '写字', goal: 2 },
    templateFallback: false
  },
  {
    char: '读', unit: 'u8', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴，把书上的字大声读出来。',
    props: { hero: '📖', sound: '一二三', goal: 3 },
    templateFallback: false
  },
  {
    char: '写', unit: 'u8', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '拿起笔，跟着线把字写下来。',
    props: { hero: '✍️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '听', unit: 'u8', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '竖起耳朵听一听，是什么在响。',
    props: { hero: '👂', sound: '叮咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '问', unit: 'u8', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '门里放一个口，站在门口问一问。',
    props: { hero: '❓', parts: ['门', '口'], goal: 2 },
    templateFallback: false
  },
  {
    char: '答', unit: 'u8', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '有问就有答，把问和答连起来。',
    props: { hero: '🗨️', pairs: [{ a: '🐶', b: '汪' }, { a: '🐱', b: '喵' }, { a: '🐄', b: '哞' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '本', unit: 'u8', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数，书架上有几本书。',
    props: { hero: '📔', items: ['📕', '📗', '📘'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
