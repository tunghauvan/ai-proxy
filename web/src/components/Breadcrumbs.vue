<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Home } from 'lucide-vue-next'

const props = defineProps({
  // Additional items to append (like tabs)
  items: {
    type: Array,
    default: () => []
  },
  // Show home icon
  showHome: {
    type: Boolean,
    default: true
  }
})

const route = useRoute()
const router = useRouter()

// Route meta configuration for breadcrumbs
const routeConfig = {
  'Dashboard': { label: 'Dashboard', path: '/' },
  'Models': { label: 'Models', path: '/models' },
  'ModelDetail': { label: 'Model Details', path: '/models/:id', parent: 'Models' },
  'Tools': { label: 'Tools', path: '/tools' },
  'ToolDetail': { label: 'Tool Details', path: '/tools/:id', parent: 'Tools' },
  'KnowledgeBase': { label: 'Knowledge Base', path: '/kb' },
  'KnowledgeBaseDetail': { label: 'KB Details', path: '/kb/:id', parent: 'KnowledgeBase' },
  'Chat': { label: 'Chat', path: '/chat' },
  'Logs': { label: 'Chat Logs', path: '/logs' },
  'ToolLogs': { label: 'Tool Logs', path: '/tool-logs' }
}

// Build breadcrumb trail from current route
const breadcrumbs = computed(() => {
  const crumbs = []
  const routeName = route.name
  
  if (!routeName || routeName === 'Dashboard') {
    return crumbs
  }
  
  // Build the parent chain
  const buildChain = (name) => {
    const config = routeConfig[name]
    if (!config) return
    
    if (config.parent) {
      buildChain(config.parent)
    }
    
    crumbs.push({
      label: config.label,
      path: config.path.includes(':id') ? route.path : config.path,
      isCurrentPage: name === routeName && props.items.length === 0
    })
  }
  
  buildChain(routeName)
  
  // Add additional items (like tabs)
  if (props.items.length > 0) {
    // Mark the last route crumb as not current
    if (crumbs.length > 0) {
      crumbs[crumbs.length - 1].isCurrentPage = false
    }
    
    props.items.forEach((item, index) => {
      crumbs.push({
        ...item,
        isCurrentPage: index === props.items.length - 1
      })
    })
  }
  
  return crumbs
})

const navigateTo = (crumb) => {
  if (crumb.isCurrentPage) return
  
  if (crumb.onClick) {
    crumb.onClick()
  } else if (crumb.path) {
    router.push(crumb.path)
  }
}
</script>

<template>
  <nav class="flex items-center space-x-1 text-sm" aria-label="Breadcrumb">
    <!-- Home -->
    <button
      v-if="showHome"
      @click="router.push('/')"
      class="flex items-center text-muted-foreground hover:text-foreground transition-colors"
      title="Dashboard"
    >
      <Home class="h-4 w-4" />
    </button>
    
    <!-- Separator after home -->
    <ChevronRight v-if="showHome && breadcrumbs.length > 0" class="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
    
    <!-- Breadcrumb items -->
    <template v-for="(crumb, index) in breadcrumbs" :key="index">
      <button
        @click="navigateTo(crumb)"
        :class="[
          'transition-colors',
          crumb.isCurrentPage
            ? 'text-foreground font-medium cursor-default'
            : 'text-muted-foreground hover:text-foreground cursor-pointer'
        ]"
        :disabled="crumb.isCurrentPage"
      >
        {{ crumb.label }}
      </button>
      
      <!-- Separator -->
      <ChevronRight 
        v-if="index < breadcrumbs.length - 1" 
        class="h-4 w-4 text-muted-foreground/50 flex-shrink-0" 
      />
    </template>
  </nav>
</template>
