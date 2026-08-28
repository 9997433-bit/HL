/**
 * 富互动 play 分片 u41 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u41'

export const UNIT_RICH_PLAYS = [
  {
    char: '药', unit: 'u41', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '药归药箱，糖归糖罐，别弄混。',
    props: { hero: '💊', items: [{ item: '💊', bucket: '药箱' }, { item: '🩹', bucket: '药箱' }, { item: '🍬', bucket: '糖罐' }, { item: '🍭', bucket: '糖罐' }], buckets: [{ label: '药箱', emoji: '💊' }, { label: '糖罐', emoji: '🍬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '疗', unit: 'u41', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '敷上药，伤口一天天好起来。',
    props: { hero: '🩺', stages: ['🤕', '🩹', '😊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '疾', unit: 'u41', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '疾是又急又重的病，别拖着。',
    props: { hero: '🤒', stages: ['😀', '🤧', '🤒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '症', unit: 'u41', theme: 'body',
    template: 'pair-match', interaction: 'drag',
    narration: '什么症状配什么样子，连起来。',
    props: { hero: '📋', pairs: [{ a: '🤧', b: '😷' }, { a: '🤒', b: '🌡️' }, { a: '🤕', b: '🩹' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '疼', unit: 'u41', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '哪里疼？点一点告诉医生。',
    props: { hero: '😣', items: ['🦷', '🦵', '🤕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伤', unit: 'u41', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '擦破皮了，贴上创可贴。',
    props: { hero: '🩹', parts: ['🩹', '🩹'], goal: 2 },
    templateFallback: false
  },
  {
    char: '治', unit: 'u41', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '吃了药看了病，慢慢治好了。',
    props: { hero: '🩺', stages: ['🤒', '💊', '😀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '救', unit: 'u41', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '救护车呜呜叫，快让开路。',
    props: { hero: '🚑', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '护', unit: 'u41', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '护住自己：口罩、帽子、手套。',
    props: { hero: '🛡️', items: ['😷', '🧢', '🧤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '康', unit: 'u41', theme: 'feeling',
    template: 'count-tap', interaction: 'tap',
    narration: '身体康健，连蹦三下试试。',
    props: { hero: '💪', items: ['💪', '💪', '💪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '健', unit: 'u41', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '每天跑一跑，跑满四圈更健。',
    props: { hero: '🏃', items: ['🏃', '🏃', '🏃', '🏃'], goal: 4 },
    templateFallback: false
  },
  {
    char: '诊', unit: 'u41', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '医生诊一诊：听心跳、看嗓子。',
    props: { hero: '🩺', items: ['🫀', '👅', '👂'], goal: 3 },
    templateFallback: false
  },
  {
    char: '检', unit: 'u41', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '检查一下，哪颗牙有小洞？',
    props: { hero: '🔍', target: '🦷', decoys: ['🍬', '🪥', '🧀'], goal: 1 },
    templateFallback: false
  },
  {
    char: '验', unit: 'u41', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '化验单和小瓶子，一一对上。',
    props: { hero: '🧪', pairs: [{ a: '🧪', b: '📋' }, { a: '🩸', b: '📄' }, { a: '🔬', b: '🧾' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '危', unit: 'u41', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个牌子在说「危险」？',
    props: { hero: '⚠️', target: '⚠️', decoys: ['🏳️', '🔵', '🟩'], goal: 1 },
    templateFallback: false
  },
  {
    char: '险', unit: 'u41', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '路边很险，往里边走一点。',
    props: { hero: '🚸', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '防', unit: 'u41', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '下雨防淋，出门带上伞和帽。',
    props: { hero: '🛡️', parts: ['☂️', '🧢'], goal: 2 },
    templateFallback: false
  },
  {
    char: '备', unit: 'u41', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '出门前备好四样，一样样点。',
    props: { hero: '🎒', items: ['🧴', '😷', '🧻', '🍼'], goal: 4 },
    templateFallback: false
  },
  {
    char: '洁', unit: 'u41', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '把小手搓一搓，洗得洁白。',
    props: { hero: '🧼', color: 'white', goal: 3 },
    templateFallback: false
  },
  {
    char: '梳', unit: 'u41', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿起梳子，从上往下梳一梳。',
    props: { hero: '💇', dir: 'down', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
