import { createRouter, createWebHashHistory } from 'vue-router'

// hash 模式:静态托管(GitHub Pages / 本地 file 部署)零配置
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/modules/home/HomeView.vue'),
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
