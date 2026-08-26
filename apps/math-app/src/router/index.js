import { createRouter, createWebHashHistory } from 'vue-router'

// hash 模式:静态托管(GitHub Pages / 本地 file 部署)零配置
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '学习地图' },
  },
  {
    path: '/number-sense',
    name: 'number-sense',
    component: () => import('@/modules/number-sense/NumberSenseView.vue'),
    meta: { title: '数量星云' },
  },
  {
    path: '/arithmetic',
    name: 'arithmetic',
    component: () => import('@/modules/arithmetic/ArithmeticView.vue'),
    meta: { title: '算术恒星' },
  },
  {
    path: '/geometry',
    name: 'geometry',
    component: () => import('@/modules/geometry/GeometryView.vue'),
    meta: { title: '形状卫星' },
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
