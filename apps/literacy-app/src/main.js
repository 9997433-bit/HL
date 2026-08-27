import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/base.css'
import { registerServiceWorkerAfterStartup } from '@shared/utils/registerServiceWorker.js'

if (import.meta.env.DEV) {
  // 绘本正文只能用字表里已有的字，写新绘本时如果越界要立刻发现。
  import('./data/books.js').then(({ verifyBookCoverage }) => {
    const problems = verifyBookCoverage()
    if (problems.length) {
      console.warn('[绘本自检] 以下绘本用到了字表之外的字：', problems)
    }
  })
}

if (import.meta.env.PROD) registerServiceWorkerAfterStartup(import.meta.env.BASE_URL)

createApp(App).use(createPinia()).use(router).mount('#app')
