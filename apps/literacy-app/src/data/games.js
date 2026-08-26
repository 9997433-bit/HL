/**
 * 识字小游戏注册表（纯数据，供 check:round5 与大厅渲染共用）。
 * 每项 route 必须在 router/index.js 接线。
 */
export const GAMES = [
  {
    id: 'listen',
    name: '听音识字',
    route: '/listen',
    skill: 'listen',
    view: 'ListenGameView'
  },
  {
    id: 'maze',
    name: '字迷宫',
    route: '/games/maze',
    skill: 'spatial',
    view: 'MazeGameView'
  },
  {
    id: 'memory',
    name: '配对记忆',
    route: '/games/memory',
    skill: 'memory',
    view: 'MemoryGameView'
  },
  {
    id: 'spot',
    name: '找不同',
    route: '/games/spot',
    skill: 'discriminate',
    view: 'SpotGameView'
  }
]
