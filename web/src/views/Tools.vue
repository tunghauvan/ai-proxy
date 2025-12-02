<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { Plus, Trash2, Code } from 'lucide-vue-next'

const tools = ref([])
const loading = ref(true)
const showCreateModal = ref(false)

const form = ref({
  name: '',
  description: '',
  category: '',
  function_code: ''
})

const fetchTools = async () => {
  loading.value = true
  try {
    const response = await api.getTools(true) // detailed list
    tools.value = response.data
  } catch (error) {
    console.error('Error fetching tools:', error)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  form.value = {
    name: '',
    description: '',
    category: '',
    function_code: 'def main(args):\n    """Tool entry point"""\n    return "Hello World"'
  }
  showCreateModal.value = true
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
    showCreateModal.value = false
    fetchTools()
  } catch (error) {
    console.error('Error creating tool:', error)
    alert('Failed to create tool')
  }
}

const deleteTool = async (id) => {
  if (!confirm('Are you sure you want to delete this tool?')) return
  try {
    await api.deleteTool(id)
    fetchTools()
  } catch (error) {
    console.error('Error deleting tool:', error)
  }
}

onMounted(() => {
  fetchTools()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-3xl font-bold tracking-tight">Tools</h2>
      <button 
        @click="openCreateModal"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <Plus class="mr-2 h-4 w-4" />
        Create Tool
      </button>
    </div>

    <div class="rounded-md border bg-card">
      <div class="relative w-full overflow-auto">
        <table class="w-full caption-bottom text-sm">
          <thead class="[&_tr]:border-b">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Name</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Category</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Type</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Description</th>
              <th class="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="5" class="p-4 text-center">Loading...</td>
            </tr>
            <tr v-else-if="tools.length === 0">
              <td colspan="5" class="p-4 text-center">No tools found</td>
            </tr>
            <tr v-else v-for="tool in tools" :key="tool.id" class="border-b transition-colors hover:bg-muted/50">
              <td class="p-4 align-middle font-medium">{{ tool.name }}</td>
              <td class="p-4 align-middle">
                <span v-if="tool.category" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                  {{ tool.category }}
                </span>
                <span v-else class="text-muted-foreground">-</span>
              </td>
              <td class="p-4 align-middle">
                <span v-if="tool.is_builtin" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary/10 text-primary hover:bg-primary/20">
                  Built-in
                </span>
                <span v-else class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                  Custom
                </span>
              </td>
              <td class="p-4 align-middle text-muted-foreground truncate max-w-[300px]">
                {{ tool.description }}
              </td>
              <td class="p-4 align-middle text-right">
                <button 
                  v-if="!tool.is_builtin"
                  @click="deleteTool(tool.id)" 
                  class="p-2 hover:bg-accent rounded-md text-destructive"
                >
                  <Trash2 class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div class="w-full max-w-2xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Create Custom Tool</h3>
          <button @click="showCreateModal = false" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <form @submit.prevent="createTool" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Name</label>
              <input v-model="form.name" required placeholder="my_tool" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Category</label>
              <input v-model="form.category" placeholder="utility" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Description</label>
            <input v-model="form.description" required placeholder="What does this tool do?" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Python Code</label>
            <textarea v-model="form.function_code" required rows="10" class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"></textarea>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="showCreateModal = false" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
              Cancel
            </button>
            <button type="submit" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
              Create Tool
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
