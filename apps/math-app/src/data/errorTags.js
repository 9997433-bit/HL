/**
 * 错因标签词典。
 * 判题时打在 progress.errorTagCounts 上的是这里的 id，
 * QuizShell 与家长报告用同一份文案，避免两处各写一套说法。
 */
export const ERROR_TAGS = {
  carry: { label: '忘记进位', tip: '个位相加满 10，要往十位进 1。' },
  borrow: { label: '忘记退位', tip: '个位不够减，要向十位借 1 当作 10。' },
  'off-by-ten': { label: '差了整 10', tip: '差 10 通常就是进位或退位那一步漏掉了。' },
  'off-by-one': { label: '差了 1', tip: '数数时多数或少数了一格，检查一下起点。' },
  'wrong-op': { label: '用错运算', tip: '再读一遍题：是要合起来，还是要去掉？' },
  reversed: { label: '大小数颠倒', tip: '求「多几」要用大数减小数。' },
  'mul-table': { label: '口诀记错', tip: '把这句乘法口诀再背两遍。' },
  'div-remainder': { label: '余数处理', tip: '分不完时要看清楚问的是「分几份」还是「剩几个」。' },
  'one-step': { label: '一步题失误', tip: '算式列对了吗？可以把数字圈出来再算。' },
  'two-step': { label: '两步题漏一步', tip: '两步题要先算中间量，再算最终答案。' },
  'multi-step': { label: '多步题卡住', tip: '把大问题拆成两三个小问题，一步一步来。' },
  'skip-unit': { label: '看错单位', tip: '注意题目问的是元、个还是分钟。' },
  timeout: { label: '想得比较久', tip: '多练几遍就会越来越快。' },
  // 归不到具体类型时的兜底，保证每道错题在家长报告里都有归属
  miscalc: { label: '算错一步', tip: '再算一遍，注意每一位都别漏掉。' },
}

/** 取标签文案；未登记的 id 原样显示，保证不会漏掉新加的标签。 */
export function errorTagInfo(id) {
  return ERROR_TAGS[id] ?? { label: id, tip: '' }
}
