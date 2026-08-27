import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import './styles/main.css'

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    const baseUrl = new URL(import.meta.env.BASE_URL, document.baseURI)
    navigator.serviceWorker
      .register(new URL('sw.js', baseUrl), { scope: baseUrl.href })
      .catch((error) => console.warn('[offline] Service Worker 注册失败：', error))
  })
}

createApp(App).use(createPinia()).use(router).mount('#app')
