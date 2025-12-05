<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import { Plus, Trash2, Code, Settings, Search, Filter, Wrench, Eye } from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const router = useRouter()
const toast = useToast()

const tools = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const searchQuery = ref('')
const categoryFilter = ref('')

const form = ref({
  name: '',
  description: '',
  category: '',
  function_code: ''
})

const fetchTools = async () => {
  loading.value = true
  try {
    const response = await api.getTools(true)
    tools.value = response.data
  } catch (error) {
    console.error('Error fetching tools:', error)
    toast.error('Failed to load tools')
  } finally {
    loading.value = false
  }
}

// Computed properties for filtering
const categories = computed(() => {
  const cats = new Set()
  tools.value.forEach(tool => {
    if (tool.category) cats.add(tool.category)
  })
  return Array.from(cats).sort()
})

const filteredTools = computed(() => {
  return tools.value.filter(tool => {
    const matchesSearch = !searchQuery.value || 
      tool.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      tool.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
    
    const matchesCategory = !categoryFilter.value || tool.category === categoryFilter.value
    
    return matchesSearch && matchesCategory
  })
})

const builtinCount = computed(() => tools.value.filter(t => t.is_builtin).length)
const customCount = computed(() => tools.value.filter(t => !t.is_builtin).length)

const openCreateModal = () => {
  form.value = {
    name: '',
    description: '',
    category: '',
    function_code: 'def main(args):\n    """\n    Tool entry point.\n    \n    Args:\n        args: Dictionary of input arguments\n        \n    Returns:\n        Result string or dictionary\n    """\n    return "Hello World"'
  }
  showCreateModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const createTool = async () => {
  try {
    await api.createTool({
      name: form.value.name,
      description: form.value.description,
      category: form.value.category,
      function_code: form.value.function_code,
      enabled: true
    })
    closeCreateModal()
    toast.success('Tool created successfully!')
    fetchTools()
  } catch (error) {
    console.error('Error creating tool:', error)
    toast.error(error.response?.data?.detail || 'Failed to create tool')
  }
}

const closeCreateModal = () => {
  showCreateModal.value = false
  form.value = {
    name: '',
    description: '',
    category: '',
    function_code: ''
  }

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event) => {
  if (event.key === 'Escape' && showCreateModal.value) {
    closeCreateModal()
  }
}

const handleBackdropClick = (event) => {
  if (event.target === event.currentTarget) {
    closeCreateModal()
  }
}

const deleteTool = async (tool) => {
  if (!confirm(`Are you sure you want to delete "${tool.name}"?`)) return
  try {
    await api.deleteTool(tool.id)
    toast.success('Tool deleted successfully!')
    fetchTools()
  } catch (error) {
    console.error('Error deleting tool:', error)
    toast.error('Failed to delete tool')
  }
}

const viewToolDetails = (tool) => {
  router.push(`/tools/${tool.id}`)
}

onMounted(() => {
  fetchTools()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <Breadcrumbs />
      <button 
        @click="openCreateModal"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <Plus class="mr-2 h-4 w-4" />
        Create Tool
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid gap-4 md:grid-cols-3">
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Total Tools</h3>
          <Wrench class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ tools.length }}</div>
      </div>
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Built-in</h3>
          <Code class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold text-primary">{{ builtinCount }}</div>
      </div>
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Custom</h3>
          <Settings class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ customCount }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-4">
      <div class="relative flex-1">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input 
          v-model="searchQuery"
          type="text"
          placeholder="Search tools..."
          class="flex h-10 w-full rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>
      <div class="relative">
        <Filter class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <select 
          v-model="categoryFilter"
          class="flex h-10 w-full sm:w-48 rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 appearance-none"
        >
          <option value="">All Categories</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
    </div>

    <!-- Tools Table -->
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading tools...</div>
    </div>

    <div v-else-if="filteredTools.length === 0" class="text-center py-12">
      <Wrench class="h-12 w-12 mx-auto text-muted-foreground mb-4" />
      <h3 class="text-lg font-semibold">No tools found</h3>
      <p class="text-muted-foreground mt-1">
        {{ searchQuery || categoryFilter ? 'Try adjusting your filters' : 'Create your first custom tool to get started' }}
      </p>
    </div>

    <div v-else class="rounded-md border bg-card">
      <div class="relative w-full overflow-auto">
        <table class="w-full caption-bottom text-sm">
          <thead class="[&_tr]:border-b">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Name</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Category</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Type</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Description</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Status</th>
              <th class="h-8 px-3 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr 
              v-for="tool in filteredTools" 
              :key="tool.id" 
              class="border-b transition-colors hover:bg-muted/50 cursor-pointer"
              @click="viewToolDetails(tool)"
            >
              <td class="px-3 py-2 align-middle font-medium">{{ tool.name }}</td>
              <td class="px-3 py-2 align-middle">
                <span v-if="tool.category" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors border-transparent bg-secondary text-secondary-foreground">
                  {{ tool.category }}
                </span>
                <span v-else class="text-muted-foreground">-</span>
              </td>
              <td class="px-3 py-2 align-middle">
                <span v-if="tool.is_builtin" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors border-transparent bg-primary/10 text-primary">
                  Built-in
                </span>
                <span v-else class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors border-transparent bg-secondary text-secondary-foreground">
                  Custom
                </span>
              </td>
              <td class="px-3 py-2 align-middle text-muted-foreground max-w-[300px] truncate">
                {{ tool.description || 'No description available' }}
              </td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                  :class="{
                    'border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100': tool.enabled,
                    'border-transparent bg-secondary text-secondary-foreground': !tool.enabled
                  }"
                >
                  {{ tool.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle text-right" @click.stop>
                <div class="flex justify-end gap-2">
                  <button 
                    @click="viewToolDetails(tool)" 
                    class="p-2 hover:bg-accent rounded-md" 
                    title="View Details"
                  >
                    <Eye class="h-4 w-4" />
                  </button>
                  <button 
                    v-if="!tool.is_builtin"
                    @click="deleteTool(tool)" 
                    class="p-2 hover:bg-accent rounded-md text-destructive"
                    title="Delete"
                  >
                    <Trash2 class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick">
      <div class="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Create Tool</h3>
          <button @click="closeCreateModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <form @submit.prevent="createTool" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Name</label>
              <input 
                v-model="form.name" 
                required 
                placeholder="my_tool" 
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
              />
              <p class="text-xs text-muted-foreground">Lowercase letters, numbers, underscores only</p>
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Category</label>
              <input 
                v-model="form.category" 
                placeholder="utility" 
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
              />
            </div>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Description</label>
            <textarea 
              v-model="form.description" 
              required 
              rows="2"
              placeholder="What does this tool do? This helps the AI decide when to use it."
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            ></textarea>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Python Code</label>
            <textarea 
              v-model="form.function_code" 
              required 
              rows="12" 
              spellcheck="false"
              class="flex w-full rounded-md border border-input bg-[#1e1e1e] text-[#d4d4d4] px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 font-mono"
            ></textarea>
            <p class="text-xs text-muted-foreground">
              Define a <code class="bg-muted px-1 rounded">main(args)</code> function as the entry point
            </p>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button 
              type="button" 
              @click="showCreateModal = false" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              Create Tool
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>


