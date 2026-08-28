/**
 * 富互动 play 分片 u35 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u35'

export const UNIT_RICH_PLAYS = [
  {
    char: '论', unit: 'u35', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '大家讨论，同意的和不同意的分开。',
    props: { hero: '💬', items: [{ item: '🍎', bucket: '同意' }, { item: '📚', bucket: '同意' }, { item: '🔥', bucket: '不同意' }, { item: '🗑️', bucket: '不同意' }], buckets: [{ label: '同意', emoji: '👍' }, { label: '不同意', emoji: '👎' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '议', unit: 'u35', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '商量一件事，把问题和办法配好。',
    props: { hero: '🗣️', pairs: [{ a: '🍽️', b: '🥢' }, { a: '🚗', b: '🔑' }, { a: '💡', b: '🔌' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '述', unit: 'u35', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '把看到的说一遍，讲给大家听。',
    props: { hero: '🗣️', sound: '我来说', goal: 3 },
    templateFallback: false
  },
  {
    char: '例', unit: 'u35', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '照着例子做，找出一样的那个。',
    props: { hero: '🔢', pairs: [{ a: '🔺', b: '🔺' }, { a: '🔵', b: '🔵' }, { a: '🟩', b: '🟩' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '句', unit: 'u35', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '把词连起来，就成了一句。',
    props: { hero: '📏', parts: ['句', '子'], word: '句子', goal: 2 },
    templateFallback: false
  },
  {
    char: '词', unit: 'u35', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '两个字凑一块，就成了一个词。',
    props: { hero: '🔤', parts: ['词', '语'], word: '词语', goal: 2 },
    templateFallback: false
  },
  {
    char: '段', unit: 'u35', theme: 'word',
    template: 'drag-parts', interaction: 'drag',
    narration: '一段一段接起来，路就长了。',
    props: { hero: '🛣️', parts: ['🟫', '🟫', '🟫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '篇', unit: 'u35', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数数今天读了几篇小文章。',
    props: { hero: '📃', items: ['📃', '📃', '📃'], goal: 3 },
    templateFallback: false
  },
  {
    char: '章', unit: 'u35', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翻开一章，看看讲的什么故事。',
    props: { hero: '📖', items: ['🐉', '🏰', '🧚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '页', unit: 'u35', theme: 'school',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '轻轻一翻，翻到下一页去。',
    props: { hero: '📄', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '册', unit: 'u35', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '一本一本册子，摞成一小摞。',
    props: { hero: '📚', items: ['📔', '📓', '📒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '版', unit: 'u35', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小板子拼成一整版。',
    props: { hero: '🔲', parts: ['🔲', '🔲', '🔲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '印', unit: 'u35', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '按一下印章，纸上留下红印。',
    props: { hero: '🔖', items: ['🟥', '🟥', '🟥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '刷', unit: 'u35', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿刷子来回一刷，墙就白了。',
    props: { hero: '🖌️', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '表', unit: 'u35', theme: 'time',
    template: 'trace-path', interaction: 'drag',
    narration: '拨一拨手表，指针转起来。',
    props: { hero: '⌚', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '现', unit: 'u35', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盖着的东西现出来，看是什么。',
    props: { hero: '🎩', items: ['🐇', '🌸', '🎀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '由', unit: 'u35', theme: 'word',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着路自由地走，想去哪去哪。',
    props: { hero: '🧭', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '及', unit: 'u35', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '伸长手够一够，看能不能碰到。',
    props: { hero: '🙋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '与', unit: 'u35', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '你与我，把两个凑到一起。',
    props: { hero: '🤝', pairs: [{ a: '🧒', b: '👧' }, { a: '🐱', b: '🐭' }, { a: '☕', b: '🍰' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '或', unit: 'u35', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '吃苹果或者吃梨，选一样就行。',
    props: { hero: '🔀', items: [{ item: '🍎', bucket: '选这个' }, { item: '🍏', bucket: '选这个' }, { item: '🍐', bucket: '选那个' }, { item: '🥝', bucket: '选那个' }], buckets: [{ label: '选这个', emoji: '🍎' }, { label: '选那个', emoji: '🍐' }], goal: 4 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
