import { createRouter, createWebHashHistory } from 'vue-router'

/**
 * 用 hash 模式：打包出来的 dist 可以直接双击 index.html 打开，
 * 也能丢到任何静态目录（含子路径）下，不需要服务器改写规则。
 *
 * 「列表 / 详情」一律拆成两条路由，详情页通过 props 接收参数，
 * 这样组件不必自己去读 route.params，也方便单独测试。
 */

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '识字乐园', emoji: '🏡' }
  },
  {
    path: '/learn',
    name: 'learn',
    component: () => import('@/views/LearnView.vue'),
    meta: { title: '学汉字', emoji: '✏️' }
  },
  {
    path: '/learn/:char',
    name: 'char',
    component: () => import('@/views/CharDetailView.vue'),
    props: true,
    meta: { title: '写一写', emoji: '✍️' }
  },
  { path: '/learn/detail/:char', redirect: (to) => `/learn/${to.params.char}` },
  {
    path: '/listen',
    name: 'listen-game',
    component: () => import('@/views/ListenGameView.vue'),
    meta: { title: '听音识字', emoji: '👂' }
  },
  { path: '/game/listen', redirect: '/listen' },
  {
    path: '/games',
    name: 'games',
    component: () => import('@/views/GamesView.vue'),
    meta: { title: '小游戏', emoji: '🎲' }
  },
  {
    path: '/games/maze',
    name: 'game-maze',
    component: () => import('@/views/MazeGameView.vue'),
    meta: { title: '字迷宫', emoji: '🧭' }
  },
  {
    path: '/games/memory',
    name: 'game-memory',
    component: () => import('@/views/MemoryGameView.vue'),
    meta: { title: '配对记忆', emoji: '🃏' }
  },
  {
    path: '/games/spot',
    name: 'game-spot',
    component: () => import('@/views/SpotGameView.vue'),
    meta: { title: '找不同', emoji: '🔍' }
  },
  {
    path: '/games/spell',
    name: 'game-spell',
    component: () => import('@/views/SpellGameView.vue'),
    meta: { title: '拼音拼字', emoji: '🔤' }
  },
  {
    path: '/games/catch',
    name: 'game-catch',
    component: () => import('@/views/CatchGameView.vue'),
    meta: { title: '接字大冒险', emoji: '🧺' }
  },
  {
    path: '/radicals/:id?',
    name: 'radicals',
    component: () => import('@/views/RadicalsView.vue'),
    meta: { title: '偏旁部首', emoji: '🧩' }
  },
  {
    path: '/books',
    name: 'books',
    component: () => import('@/views/BooksView.vue'),
    meta: { title: '分级绘本', emoji: '📚' }
  },
  {
    path: '/books/:id',
    name: 'book',
    component: () => import('@/views/BookReadView.vue'),
    props: true,
    meta: { title: '读绘本', emoji: '📖' }
  },
  {
    path: '/etymology/:char?',
    name: 'etymology',
    component: () => import('@/views/EtymologyView.vue'),
    props: true,
    meta: { title: '字源馆', emoji: '🏺' }
  },
  {
    path: '/idioms',
    name: 'idioms',
    component: () => import('@/views/IdiomsView.vue'),
    meta: { title: '成语故事', emoji: '🏮' }
  },
  {
    path: '/poems',
    name: 'poems',
    component: () => import('@/views/PoemsView.vue'),
    meta: { title: '古诗长廊', emoji: '📜' }
  },
  {
    path: '/poems/:id',
    name: 'poem',
    component: () => import('@/views/PoemDetailView.vue'),
    props: true,
    meta: { title: '读古诗', emoji: '📜' }
  },
  /**
   * 跟读评测。不带 id 就自己挑一首生字最少的诗开始。
   * 这条路由和《古诗详情》的「跟着读」用的是同一个面板。
   *
   * 「带 id」和「不带 id」拆成两条而不是写成 `:id?`：可选参数会让整条路由
   * 变成动态路由，验收探针与冒烟脚本都只认得静态路径，写成两条它们才扫得到。
   */
  {
    path: '/follow-read',
    name: 'follow-read',
    component: () => import('@/views/FollowReadView.vue'),
    meta: { title: '跟读评测', emoji: '🎤' }
  },
  {
    path: '/follow-read/:id',
    name: 'follow-read-poem',
    component: () => import('@/views/FollowReadView.vue'),
    props: true,
    meta: { title: '跟读评测', emoji: '🎤' }
  },
  { path: '/speech', redirect: '/follow-read' },
  {
    path: '/idioms/:id',
    name: 'idiom',
    component: () => import('@/views/IdiomDetailView.vue'),
    props: true,
    meta: { title: '成语小剧场', emoji: '🎭' }
  },
  {
    path: '/parent',
    name: 'parent',
    component: () => import('@/views/ParentView.vue'),
    meta: { title: '家长中心', emoji: '👨‍👩‍👧' }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · 快乐识字` : '快乐识字'
})

export default router
