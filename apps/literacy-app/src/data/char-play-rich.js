/**
 * 富 play 脚本目录（人工/半人工定制，Round 15 H3 的计数来源）。
 *
 * 这里的每一条都是「有人为这个字想过怎么玩」的脚本：模板、引导语、道具
 * 都按字义挑过，不带 templateFallback 标记（缺省即 false = 富脚本）。
 * `check-round15.mjs` H3 统计本数组长度（或 countRichPlays()），
 * 要求 ≥ 200 条，优先覆盖 u1–u20。
 *
 * 归属：r15-play-catalog-rich 岗在此文件扩写到 ≥200 条；
 * 架构岗先放 5 条 u1 示例，示范每种字段怎么写。
 *
 * 写作规范（详见 .agent_workspace/round15-architecture.md 第 3 节）：
 *  - template 必须取自 char-play.js 的 PLAY_TEMPLATES；props 遵守各模板 schema
 *  - narration 是孩子能听懂的一句话（TTS 会读），≤ 30 字，别用书面语
 *  - 只用 emoji（OpenMoji 渲染）+ 程序化参数，禁止外链图片 / 洪恩素材
 *  - 每条控制在 ~120 字节内，200 条合计预算 ≤ 40KB 源码
 *
 * @type {import('./char-play.js').CharPlay[]}
 */
export const RICH_PLAY = [
  {
    char: '一',
    theme: 'number',
    template: 'tap-reveal',
    narration: '伸出一根手指，横着一划，就是「一」！',
    props: { emoji: '☝️', taps: 1 }
  },
  {
    char: '二',
    theme: 'number',
    template: 'tap-reveal',
    narration: '两根手指两条线，点两下变出「二」！',
    props: { emoji: '✌️', taps: 2 }
  },
  {
    char: '三',
    theme: 'number',
    template: 'rain-catch',
    narration: '接住三片小叶子，数一数，就是「三」！',
    props: { target: '🍃', drops: 3 }
  },
  {
    char: '上',
    theme: 'position',
    template: 'emoji-hunt',
    narration: '小火箭要往哪儿飞？找一找往「上」的箭头！',
    props: { target: '⬆️', decoys: ['⬇️', '➡️'] }
  },
  {
    char: '下',
    theme: 'position',
    template: 'emoji-hunt',
    narration: '雨点儿往哪儿落？找一找往「下」的箭头！',
    props: { target: '⬇️', decoys: ['⬆️', '⬅️'] }
  }
]
