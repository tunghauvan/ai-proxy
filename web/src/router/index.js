import { createRouter, createWebHistory } from 'vue-router'

// Lazy load views
const Dashboard = () => import('../views/Dashboard.vue')
const Models = () => import('../views/Models.vue')
const ModelDetail = () => import('../views/ModelDetail.vue')
const Tools = () => import('../views/Tools.vue')
const ToolDetail = () => import('../views/ToolDetail.vue')
const KnowledgeBase = () => import('../views/KnowledgeBase.vue')
const KnowledgeBaseDetail = () => import('../views/KnowledgeBaseDetail.vue')
const Chat = () => import('../views/Chat.vue')
const Logs = () => import('../views/Logs.vue')

const routes = [
  { path: '/', component: Dashboard, name: 'Dashboard' },
  { path: '/models', component: Models, name: 'Models' },
  { path: '/models/:id', component: ModelDetail, name: 'ModelDetail' },
  { path: '/tools', component: Tools, name: 'Tools' },
  { path: '/tools/:id', component: ToolDetail, name: 'ToolDetail' },
  { path: '/kb', component: KnowledgeBase, name: 'KnowledgeBase' },
  { path: '/kb/:id', component: KnowledgeBaseDetail, name: 'KnowledgeBaseDetail' },
  { path: '/chat', component: Chat, name: 'Chat' },
  { path: '/logs', component: Logs, name: 'Logs' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
