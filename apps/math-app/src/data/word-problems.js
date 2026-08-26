/**
 * 应用题母题模板库 — Round 1 样例 4 类,Round 2 扩展至 ~40 类语义类别
 * (合并/剩余/比较差/倍数/等分/包含除/两步混合/年龄/行程/工程/植树/鸡兔同笼…)。
 * 模板字段:
 *   text: 占位符文本,{a}{b} 取自 params,{item}{place}{who} 取自皮肤;
 *   params: 各参数的 [min, max] 采样域;
 *   constraint: 可选,参数合法性校验(保证正数/整除等);
 *   solve: 由参数计算标准答案;
 *   skins: 场景皮肤 —— 同一母题 × 多皮肤 = 多道"母题面貌"。
 */

export const WP_TEMPLATES = [
  {
    id: 'combine',
    category: 'combine',
    skill: 'wp-combine',
    difficulty: 0.2,
    steps: 1,
    text: '{who}先摘了 {a} 个{item},又摘了 {b} 个{item}。一共摘了多少个{item}?',
    params: { a: [2, 9], b: [2, 9] },
    solve: ({ a, b }) => a + b,
    skins: [
      { name: 'farm', who: '小兔', item: '胡萝卜' },
      { name: 'orchard', who: '小猴', item: '桃子' },
      { name: 'space', who: '宇航员麦麦', item: '能量石' }
    ]
  },
  {
    id: 'remain',
    category: 'remain',
    skill: 'wp-remain',
    difficulty: 0.25,
    steps: 1,
    text: '{who}有 {a} 个{item},送给朋友 {b} 个。还剩多少个{item}?',
    params: { a: [5, 10], b: [1, 9] },
    constraint: ({ a, b }) => a > b,
    solve: ({ a, b }) => a - b,
    skins: [
      { name: 'candy', who: '小熊', item: '糖果' },
      { name: 'balloon', who: '小象', item: '气球' }
    ]
  },
  {
    id: 'diff',
    category: 'compare-diff',
    skill: 'wp-diff',
    difficulty: 0.45,
    steps: 1,
    text: '{whoA}有 {a} 本{item},{whoB}有 {b} 本{item}。{whoA}比{whoB}多多少本?',
    params: { a: [11, 20], b: [2, 10] },
    constraint: ({ a, b }) => a > b,
    solve: ({ a, b }) => a - b,
    skins: [
      { name: 'library', whoA: '明明', whoB: '红红', item: '故事书' },
      { name: 'stamp', whoA: '哥哥', whoB: '妹妹', item: '邮票册' }
    ]
  },
  {
    id: 'times',
    category: 'times',
    skill: 'wp-times',
    difficulty: 0.6,
    steps: 1,
    text: '{whoA}折了 {a} 只{item},{whoB}折的是{whoA}的 {b} 倍。{whoB}折了多少只{item}?',
    params: { a: [2, 9], b: [2, 5] },
    solve: ({ a, b }) => a * b,
    skins: [
      { name: 'origami', whoA: '小丽', whoB: '老师', item: '纸鹤' },
      { name: 'boat', whoA: '弟弟', whoB: '爸爸', item: '小纸船' }
    ]
  }
]

export function templateById(id) {
  return WP_TEMPLATES.find((t) => t.id === id) ?? null
}
