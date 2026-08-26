import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '识字乐园', emoji: '🏡' }
  },
  {
    path: '/learn/:char?',
    name: 'learn',
    component: () => import('@/views/LearnView.vue'),
    meta: { title: '学汉字', emoji: '✏️' }
  },
  {
    path: '/learn/detail/:char',
    name: 'char',
    component: () => import('@/views/CharDetailView.vue'),
    props: true,
    meta: { title: '写一写', emoji: '✍️' }
  },
  {
    path: '/listen',
    name: 'listen-game',
    component: () => import('@/views/ListenGameView.vue'),
    meta: { title: '听音识字', emoji: '👂' }
  },
  { path: '/game/listen', redirect: '/listen' },
  {
    path: '/radicals/:id?',
    name: 'radicals',
    component: () => import('@/views/RadicalsView.vue'),
    meta: { title: '偏旁部首', emoji: '🧩' }
  },
  {
    path: '/books/:id?',
    name: 'books',
    component: () => import('@/views/BooksView.vue'),
    meta: { title: '分级绘本', emoji: '📚' }
  },
  {
    path: '/idioms/:id?',
    name: 'idioms',
    component: () => import('@/views/IdiomsView.vue'),
    meta: { title: '成语故事', emoji: '🏮' }
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
