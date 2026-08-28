/**
 * 富互动 play 分片 u67 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u67'

export const UNIT_RICH_PLAYS = [
  {
    char: '此', unit: 'u67', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '就在此处，找出那枚图钉。',
    props: { hero: '📍', target: '📌', decoys: ['📎', '🔖', '📏'], goal: 1 },
    templateFallback: false
  },
  {
    char: '尖', unit: 'u67', theme: 'shape',
    template: 'morph-story', interaction: 'sequence',
    narration: '上头细下头粗，就成了尖。',
    props: { hero: '📐', stages: ['🔻', '📐', '🔺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '劣', unit: 'u67', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '好的挑出来，劣的放一边。',
    props: { hero: '👎', items: [{ item: '🍎', bucket: '好' }, { item: '🍐', bucket: '好' }, { item: '🍂', bucket: '劣' }, { item: '🥀', bucket: '劣' }], buckets: [{ label: '好', emoji: '👍' }, { label: '劣', emoji: '👎' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '吐', unit: 'u67', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小鱼吐泡泡，一个个冒上来。',
    props: { hero: '💬', items: ['🫧', '🫧', '🫧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '吓', unit: 'u67', theme: 'feeling',
    template: 'sound-tap', interaction: 'tap',
    narration: '哇的一声，吓了一大跳。',
    props: { hero: '😱', sound: '哇', goal: 3 },
    templateFallback: false
  },
  {
    char: '吕', unit: 'u67', theme: 'word',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个口叠起来，就是吕。',
    props: { hero: '👤', parts: ['口', '口'], goal: 2 },
    templateFallback: false
  },
  {
    char: '吊', unit: 'u67', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '钩子把箱子往上吊。',
    props: { hero: '🪝', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '吸', unit: 'u67', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '深深吸一口气，呼一下。',
    props: { hero: '💨', sound: '呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '吗', unit: 'u67', theme: 'word',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '问一句好吗，找出那个问号。',
    props: { hero: '❓', target: '❓', decoys: ['❗', '➖', '💤'], goal: 1 },
    templateFallback: false
  },
  {
    char: '屹', unit: 'u67', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大山屹立着，稳稳当当。',
    props: { hero: '⛰️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '则', unit: 'u67', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '按规则来，一条一条数四条。',
    props: { hero: '📏', items: ['📏', '📏', '📏', '📏'], goal: 4 },
    templateFallback: false
  },
  {
    char: '网', unit: 'u67', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '拿网兜住掉下来的小球。',
    props: { hero: '🕸️', items: ['⚽', '🏀', '🎾'], tool: '🕸️', goal: 3 },
    templateFallback: false
  },
  {
    char: '朱', unit: 'u67', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '朱红朱红，把灯笼涂得通红。',
    props: { hero: '🏮', color: '朱红', goal: 3 },
    templateFallback: false
  },
  {
    char: '先', unit: 'u67', theme: 'time',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '你先走，往前迈出一步。',
    props: { hero: '1️⃣', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '丢', unit: 'u67', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '钥匙丢哪儿了？帮忙找一找。',
    props: { hero: '🫥', target: '🔑', decoys: ['🧦', '🍪', '🪀'], goal: 1 },
    templateFallback: false
  },
  {
    char: '迁', unit: 'u67', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '搬迁啦，把箱子搬上车。',
    props: { hero: '📦', parts: ['📦', '🚚'], goal: 2 },
    templateFallback: false
  },
  {
    char: '乔', unit: 'u67', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '小树长成高高的乔木。',
    props: { hero: '🌳', stages: ['🌱', '🌳', '🌲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伟', unit: 'u67', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '个子越长越高，长成伟人。',
    props: { hero: '🦸', stages: ['🧒', '🧑', '🦸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '乒', unit: 'u67', theme: 'object',
    template: 'sound-tap', interaction: 'tap',
    narration: '球拍一挥，乒的一声。',
    props: { hero: '🏓', sound: '乒', goal: 3 },
    templateFallback: false
  },
  {
    char: '乓', unit: 'u67', theme: 'object',
    template: 'sound-tap', interaction: 'tap',
    narration: '球弹回来，乓的一响。',
    props: { hero: '🏓', sound: '乓', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
