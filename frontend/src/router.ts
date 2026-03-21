import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import DashboardView from './views/DashboardView.vue'
import LinksView from './views/LinksView.vue'
import TodosView from './views/TodosView.vue'
import ReportsView from './views/ReportsView.vue'
import SettingsView from './views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/', component: DashboardView },
    { path: '/links', component: LinksView },
    { path: '/todos', component: TodosView },
    { path: '/reports', component: ReportsView },
    { path: '/settings', component: SettingsView },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') return '/login'
  if (token && to.path === '/login') return '/'
  return true
})

export default router