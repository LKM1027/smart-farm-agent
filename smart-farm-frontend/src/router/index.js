import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import DataView from '../views/DataView.vue'
import HardwareView from '../views/HardwareView.vue'
import ReportView from '../views/ReportView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/',        name: 'Dashboard', component: DashboardView },
  { path: '/data',    name: 'Data',      component: DataView },
  { path: '/hardware',name: 'Hardware',  component: HardwareView },
  { path: '/reports', name: 'Reports',   component: ReportView },
  { path: '/settings',name: 'Settings',  component: SettingsView },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
