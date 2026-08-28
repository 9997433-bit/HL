import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import './styles/main.css'
import { registerServiceWorkerAfterStartup } from '@shared/utils/registerServiceWorker.js'

if (import.meta.env.PROD) registerServiceWorkerAfterStartup(import.meta.env.BASE_URL)

createApp(App).use(createPinia()).use(router).mount('#app')
