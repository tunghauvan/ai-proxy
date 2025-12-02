import { createRouter, createWebHistory } from 'vue-router'
import ModelList from './views/ModelList.vue'
import ModelDetail from './views/ModelDetail.vue'
import CreateModel from './views/CreateModel.vue'
import EditModel from './views/EditModel.vue'
import ChatPlayground from './views/ChatPlayground.vue'

const routes = [
  { path: '/', name: 'models', component: ModelList },
  { path: '/models/:id', name: 'detail', component: ModelDetail },
  { path: '/create', name: 'create', component: CreateModel },
  { path: '/edit/:id', name: 'edit', component: EditModel },
  { path: '/playground', name: 'playground', component: ChatPlayground },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
