<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  LayoutDashboard, 
  Bot, 
  Wrench, 
  Database, 
  MessageSquare, 
  FileText,
  Menu,
  X
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const isSidebarOpen = ref(false)

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Models', href: '/models', icon: Bot },
  { name: 'Tools', href: '/tools', icon: Wrench },
  { name: 'Knowledge Base', href: '/kb', icon: Database },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Logs', href: '/logs', icon: FileText },
]

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div class="min-h-screen bg-background flex">
    <!-- Mobile sidebar backdrop -->
    <div 
      v-if="isSidebarOpen" 
      class="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
      @click="isSidebarOpen = false"
    ></div>

    <!-- Sidebar -->
    <div 
      class="fixed inset-y-0 z-50 flex w-72 flex-col border-r bg-card transition-transform duration-300 lg:static lg:translate-x-0"
      :class="isSidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="flex h-16 items-center border-b px-6">
        <h1 class="text-lg font-bold tracking-tight">LangChain Proxy</h1>
      </div>
      <div class="flex-1 overflow-y-auto py-4">
        <nav class="space-y-1 px-2">
          <router-link
            v-for="item in navigation"
            :key="item.name"
            :to="item.href"
            class="group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
            :class="route.path === item.href ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'"
            @click="isSidebarOpen = false"
          >
            <component 
              :is="item.icon" 
              class="mr-3 h-5 w-5 flex-shrink-0" 
              :class="route.path === item.href ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground'"
            />
            {{ item.name }}
          </router-link>
        </nav>
      </div>
    </div>

    <!-- Main content -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- Mobile header -->
      <header class="flex h-16 items-center border-b bg-card px-6 lg:hidden">
        <button 
          type="button" 
          class="-ml-2 rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          @click="toggleSidebar"
        >
          <Menu class="h-6 w-6" />
        </button>
        <h1 class="ml-4 text-lg font-bold">LangChain Proxy</h1>
      </header>

      <!-- Desktop top bar -->
      <header class="hidden lg:flex h-14 items-center justify-between border-b bg-card px-6">
        <div class="flex items-center space-x-4">
          <span class="text-sm text-muted-foreground">AI Proxy Admin Panel</span>
        </div>
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-2">
            <span class="h-2 w-2 rounded-full bg-green-500"></span>
            <span class="text-sm text-muted-foreground">Connected</span>
          </div>
          <div class="h-4 w-px bg-border"></div>
          <span class="text-sm text-muted-foreground">v1.0.0</span>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto bg-background p-4 lg:p-6">
        <router-view></router-view>
      </main>
    </div>
  </div>
</template>
