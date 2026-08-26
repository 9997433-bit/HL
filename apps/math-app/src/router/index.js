import { createRouter, createWebHashHistory } from 'vue-router'

// hash 模式:静态托管(GitHub Pages / 本地 file 部署)零配置
const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  { path: '/number-sense', name: 'number-sense', component: () => import('@/modules/number-sense/NumberSenseView.vue') },
  { path: '/arithmetic', name: 'arithmetic', component: () => import('@/modules/arithmetic/ArithmeticView.vue') },
  { path: '/geometry', name: 'geometry', component: () => import('@/modules/geometry/GeometryView.vue') },
  { path: '/logic', name: 'logic', component: () => import('@/modules/logic/LogicView.vue') },
  { path: '/sudoku', name: 'sudoku', component: () => import('@/modules/sudoku/SudokuView.vue') },
  { path: '/word-problems', name: 'word-problems', component: () => import('@/modules/word-problems/WordProblemsView.vue') },
  { path: '/progress', name: 'progress', component: () => import('@/modules/progress/ProgressView.vue') }
]

export default createRouter({
  history: createWebHashHistory(),
  routes
})
