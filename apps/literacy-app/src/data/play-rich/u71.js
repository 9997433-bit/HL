/**
 * 富互动 play 分片 u71 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u71'

export const UNIT_RICH_PLAYS = [
  {
    char: '纫', unit: 'u71', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '线头穿进针眼，纫一针试试。',
    props: { hero: '🧵', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '寿', unit: 'u71', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '寿星吹蜡烛，祝他长寿。',
    props: { hero: '🎂', stages: ['🎈', '🎂', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弄', unit: 'u71', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '把小积木弄一弄，摆整齐。',
    props: { hero: '🔧', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '形', unit: 'u71', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找一找，哪块积木形状怪。',
    props: { hero: '🔷', target: '🔷', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '进', unit: 'u71', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推开门，往前走进屋里。',
    props: { hero: '➡️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '戒', unit: 'u71', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把坏习惯戒掉，打个叉。',
    props: { hero: '🚭', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '吞', unit: 'u71', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '小蛇一口吞下那颗蛋。',
    props: { hero: '🐍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '违', unit: 'u71', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '红灯亮了，别违反规则。',
    props: { hero: '🚫', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抚', unit: 'u71', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '轻轻抚摸小猫的背。',
    props: { hero: '🤲', items: ['🤲', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坛', unit: 'u71', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '花坛里种了什么？点一点。',
    props: { hero: '🏺', stages: ['🪨', '🏺', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坏', unit: 'u71', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '哪个玩具坏掉了？找出来。',
    props: { hero: '💔', stages: ['🪵', '💔', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扰', unit: 'u71', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '嘘——别打扰正在睡觉的人。',
    props: { hero: '🤫', pairs: [{ a: '🤫', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🤫' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '拒', unit: 'u71', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '摇摇头，拒绝收下这份。',
    props: { hero: '🙅', parts: ['🔥', '☀️', '🙅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '批', unit: 'u71', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '老师批改作业，圈出三份。',
    props: { hero: '📦', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '扯', unit: 'u71', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '抓住绳子往回扯一扯。',
    props: { hero: '🪢', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '贡', unit: 'u71', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '把礼物献上去，做个贡献。',
    props: { hero: '🎁', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '坝', unit: 'u71', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '大坝拦住河水，别让它冲。',
    props: { hero: '🌊', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '攻', unit: 'u71', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '小兵往前攻，冲过那道门。',
    props: { hero: '📚', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '折', unit: 'u71', theme: 'shape',
    template: 'trace-path', interaction: 'drag',
    narration: '把纸对折，再折一次。',
    props: { hero: '📄', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '扳', unit: 'u71', theme: 'body',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '用力一扳，把扳手拧开。',
    props: { hero: '🔩', target: '🔩', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
