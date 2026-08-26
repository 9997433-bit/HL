/**
 * 成就定义。test(stats) 由 progress store 传入统计快照判定是否达成。
 * stats = { stars, totalAnswered, totalCorrect, bestStreak, modules, counters }
 */
export const ACHIEVEMENTS = [
  {
    id: 'first-launch',
    name: '首次升空',
    desc: '完成第一道题目',
    emoji: '🚀',
    test: (s) => s.totalAnswered >= 1,
  },
  {
    id: 'star-collector-10',
    name: '拾星者',
    desc: '累计获得 10 颗星星',
    emoji: '⭐',
    test: (s) => s.stars >= 10,
  },
  {
    id: 'star-collector-50',
    name: '星河富翁',
    desc: '累计获得 50 颗星星',
    emoji: '🌟',
    test: (s) => s.stars >= 50,
  },
  {
    id: 'combo-5',
    name: '五连击',
    desc: '连续答对 5 题',
    emoji: '🔥',
    test: (s) => s.bestStreak >= 5,
  },
  {
    id: 'combo-10',
    name: '十连爆发',
    desc: '连续答对 10 题',
    emoji: '💥',
    test: (s) => s.bestStreak >= 10,
  },
  {
    id: 'counting-master',
    name: '数量领航员',
    desc: '数量星云答对 20 题',
    emoji: '🪐',
    test: (s) => (s.modules.counting?.correct ?? 0) >= 20,
  },
  {
    id: 'arithmetic-master',
    name: '心算飞行员',
    desc: '算术恒星答对 30 题',
    emoji: '☀️',
    test: (s) => (s.modules.arithmetic?.correct ?? 0) >= 30,
  },
  {
    id: 'arithmetic-hard',
    name: '百以内挑战者',
    desc: '在 100 以内难度答对 10 题',
    emoji: '🧠',
    test: (s) => (s.counters.arithmeticHardCorrect ?? 0) >= 10,
  },
  {
    id: 'geometry-master',
    name: '形状鉴定师',
    desc: '形状卫星答对 20 题',
    emoji: '🛰️',
    test: (s) => (s.modules.geometry?.correct ?? 0) >= 20,
  },
  {
    id: 'logic-master',
    name: '规律破译者',
    desc: '规律环带答对 15 题',
    emoji: '🌀',
    test: (s) => (s.modules.logic?.correct ?? 0) >= 15,
  },
  {
    id: 'sudoku-first',
    name: '初入空间站',
    desc: '完成 1 个数独',
    emoji: '🎯',
    test: (s) => (s.counters.sudokuSolved ?? 0) >= 1,
  },
  {
    id: 'sudoku-five',
    name: '数独站长',
    desc: '完成 5 个数独',
    emoji: '🏗️',
    test: (s) => (s.counters.sudokuSolved ?? 0) >= 5,
  },
  {
    id: 'word-master',
    name: '生活解题家',
    desc: '生活行星答对 10 题',
    emoji: '🌍',
    test: (s) => (s.modules.word?.correct ?? 0) >= 10,
  },
  {
    id: 'explorer',
    name: '全星系探索者',
    desc: '在全部 6 个玩法星球都练习过',
    emoji: '🗺️',
    test: (s) =>
      ['counting', 'arithmetic', 'geometry', 'logic', 'sudoku', 'word'].every(
        (id) => (s.modules[id]?.answered ?? 0) > 0,
      ),
  },
  {
    id: 'perfect-run',
    name: '完美通关',
    desc: '一轮练习全部答对',
    emoji: '🏅',
    test: (s) => (s.counters.perfectRuns ?? 0) >= 1,
  },
  {
    id: 'marathon-100',
    name: '百题马拉松',
    desc: '累计作答 100 题',
    emoji: '🎽',
    test: (s) => s.totalAnswered >= 100,
  },
]

export const ACHIEVEMENT_MAP = Object.fromEntries(ACHIEVEMENTS.map((a) => [a.id, a]))
