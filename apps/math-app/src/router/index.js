import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from '@/modules/home/HomeView.vue'

// hash 模式:静态托管(GitHub Pages / 本地 file 部署)零配置
const routes = [
  {
    path: '/',
    name: 'home',
    // 首页是首个 LCP 的唯一必经视图。直接并入入口可消除路由启动后的 JS/CSS 串行请求；
    // 其余玩法仍按路由懒加载，不增加非首页的启动成本。
    component: HomeView,
    meta: { title: '学习地图' },
  },
  {
    path: '/number-sense',
    name: 'number-sense',
    component: () => import('@/modules/number-sense/NumberSenseView.vue'),
    meta: { title: '数量星云' },
  },
  {
    path: '/compose-ten',
    name: 'compose-ten',
    component: () => import('@/modules/number-sense/ComposeTenView.vue'),
    meta: { title: '10 的分与合' },
  },
  {
    // 比大小擂台：复用数量星云的玩法壳，只出 > < = 题
    path: '/compare',
    name: 'compare',
    component: () => import('@/modules/number-sense/NumberSenseView.vue'),
    props: { mode: 'compare' },
    meta: { title: '比大小擂台' },
  },
  {
    path: '/daily',
    name: 'daily',
    component: () => import('@/modules/daily/DailyView.vue'),
    meta: { title: '今日冒险' },
  },
  {
    path: '/arithmetic',
    name: 'arithmetic',
    component: () => import('@/modules/arithmetic/ArithmeticView.vue'),
    meta: { title: '算术恒星' },
  },
  {
    // 速算冲刺：复用算术恒星的玩法壳，只把节奏调成「多题 + 短秒答窗口」
    path: '/sprint',
    name: 'sprint',
    component: () => import('@/modules/arithmetic/ArithmeticView.vue'),
    props: { mode: 'sprint' },
    meta: { title: '速算冲刺' },
  },
  {
    path: '/column-arithmetic',
    name: 'column-arithmetic',
    component: () => import('@/modules/arithmetic/ColumnArithmeticView.vue'),
    meta: { title: '竖式工坊' },
  },
  {
    path: '/geometry',
    name: 'geometry',
    component: () => import('@/modules/geometry/GeometryView.vue'),
    meta: { title: '形状卫星' },
  },
  {
    path: '/tangram',
    name: 'tangram',
    component: () => import('@/modules/geometry/TangramView.vue'),
    meta: { title: '七巧板实验室' },
  },
  {
    path: '/visual-demos',
    name: 'visual-demos',
    component: () => import('@/modules/visual-demos/VisualDemosView.vue'),
    meta: { title: '数形演示中心' },
  },
  {
    path: '/logic',
    name: 'logic',
    component: () => import('@/modules/logic/LogicView.vue'),
    meta: { title: '规律环带' },
  },
  {
    // 配对记忆：Canvas 记忆矩阵，低龄档同图配对、高龄档同类配对
    path: '/memory-pairs',
    name: 'memory-pairs',
    component: () => import('@/modules/logic/MemoryPairsView.vue'),
    meta: { title: '配对记忆' },
  },
  {
    // 逻辑迷宫：Canvas 条件迷宫，按编号顺序收齐能量块才能通关
    path: '/maze',
    name: 'maze',
    component: () => import('@/modules/logic/MazeView.vue'),
    meta: { title: '逻辑迷宫' },
  },
  {
    path: '/sudoku',
    name: 'sudoku',
    component: () => import('@/modules/sudoku/SudokuView.vue'),
    meta: { title: '数独空间站' },
  },
  {
    path: '/word-problems',
    name: 'word-problems',
    component: () => import('@/modules/word-problems/WordProblemsView.vue'),
    meta: { title: '生活行星' },
  },
  {
    path: '/progress',
    name: 'progress',
    component: () => import('@/modules/progress/ProgressView.vue'),
    meta: { title: '成就墙' },
  },
  {
    path: '/parent',
    name: 'parent',
    component: () => import('@/modules/parent/ParentView.vue'),
    meta: { title: '家长中心' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · 星际数学冒险` : '星际数学冒险'
})

export default router
