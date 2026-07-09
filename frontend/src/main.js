import { createApp, h } from 'vue'
import { createRouter, createWebHistory, RouterView } from 'vue-router'
import MapView from './pages/MapView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: MapView },
    // Дальше по мере готовности:
    // { path: '/dashboard', component: () => import('./pages/Dashboard.vue') },
    // { path: '/comparison', component: () => import('./pages/SeasonComparison.vue') },
    // { path: '/import/:category', component: () => import('./pages/ImportPage.vue'), props: true },
    // { path: '/imports', component: () => import('./pages/ImportHistory.vue') },
    // { path: '/danger-admin', component: () => import('./pages/DangerAdmin.vue') },
  ],
})

// render-функция вместо строкового template:
// продакшн-сборка Vue идёт без компилятора шаблонов,
// поэтому корневой компонент рендерим через h(RouterView).
const App = {
  render: () => h(RouterView),
}

createApp(App).use(router).mount('#app')