<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import { Plus, Trash2, Power, PowerOff, Settings, Upload, RefreshCw, Eye } from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const router = useRouter()
const toast = useToast()

const models = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const showSyncModal = ref(false)
const syncing = ref(false)

const form = ref({
  name: '',
  version: '1.0.0',
  base_model: '',
  enable_rag: true,
  tool_names: [],
  temperature: 0.7,
  max_tokens: 2048
})

const syncForm = ref({
  configYaml: '',
  dryRun: true,
  deleteMissing: false
})

const syncResults = ref(null)

const availableTools = ref([])

const fetchModels = async () => {
  loading.value = true
  try {
    const response = await api.getModels()
    models.value = response.data
  } catch (error) {
    console.error('Error fetching models:', error)
  } finally {
    loading.value = false
  }
}

const fetchTools = async () => {
  try {
    const response = await api.getTools(false) // simple list
    availableTools.value = response.data
  } catch (error) {
    console.error('Error fetching tools:', error)
  }
}

const openCreateModal = () => {
  form.value = {
    name: '',
    version: '1.0.0',
    base_model: '',
    enable_rag: true,
    tool_names: [],
    temperature: 0.7,
    max_tokens: 2048
  }
  showCreateModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const openSyncModal = () => {
  syncForm.value = {
    configYaml: `models:
  - name: example-model
    version: "1.0.0"
    enabled: true
    base_model: gpt-4
    rag_settings:
      enabled: false
    tool_names: []
    model_params:
      temperature: 0.7
      max_tokens: 2048`,
    dryRun: true,
    deleteMissing: false
  }
  syncResults.value = null
  showSyncModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const syncModels = async () => {
  syncing.value = true
  syncResults.value = null
  try {
    const response = await api.syncModels(syncForm.value.configYaml, {
      dry_run: syncForm.value.dryRun,
      delete_missing: syncForm.value.deleteMissing
    })
    syncResults.value = response.data
    if (!syncForm.value.dryRun) {
      toast.success('Models synced successfully!')
      await fetchModels()
    }
  } catch (error) {
    console.error('Error syncing models:', error)
    toast.error('Failed to sync models: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncing.value = false
  }
}

const createModel = async () => {
  try {
    const payload = {
      name: form.value.name,
      version: form.value.version,
      enabled: true,
      rag_settings: { enabled: form.value.enable_rag },
      tool_names: form.value.tool_names,
      base_model: form.value.base_model,
      model_params: {
        temperature: form.value.temperature,
        max_tokens: form.value.max_tokens
      }
    }
    await api.createModel(payload)
    closeCreateModal()
    fetchModels()
  } catch (error) {
    console.error('Error creating model:', error)
    toast.error('Failed to create model')
  }
}

const closeCreateModal = () => {
  showCreateModal.value = false
  form.value = {
    name: '',
    version: '1.0.0',
    base_model: '',
    enable_rag: true,
    tool_names: [],
    temperature: 0.7,
    max_tokens: 2048
  }

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const closeSyncModal = () => {
  showSyncModal.value = false
  syncForm.value = {
    configYaml: '',
    dryRun: true,
    deleteMissing: false
  }
  syncResults.value = null

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event) => {
  if (event.key === 'Escape') {
    if (showCreateModal.value) {
      closeCreateModal()
    } else if (showSyncModal.value) {
      closeSyncModal()
    }
  }
}

const handleBackdropClick = (event, modalType) => {
  if (event.target === event.currentTarget) {
    if (modalType === 'create') {
      closeCreateModal()
    } else if (modalType === 'sync') {
      closeSyncModal()
    }
  }
}

const deleteModel = async (id) => {
  if (!confirm('Are you sure you want to delete this model?')) return
  try {
    await api.deleteModel(id)
    fetchModels()
  } catch (error) {
    console.error('Error deleting model:', error)
  }
}

const toggleActive = async (model) => {
  try {
    if (model.active) {
      await api.deactivateModel(model.id)
    } else {
      await api.activateModel(model.id)
    }
    fetchModels()
  } catch (error) {
    console.error('Error toggling model status:', error)
  }
}

const viewModelDetails = (model) => {
  router.push(`/models/${model.id}`)
}

onMounted(() => {
  fetchModels()
  fetchTools()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <Breadcrumbs />
      <div class="flex gap-2">
        <button 
          @click="openSyncModal"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
        >
          <Upload class="mr-2 h-4 w-4" />
          Sync Config
        </button>
        <button 
          @click="openCreateModal"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
        >
          <Plus class="mr-2 h-4 w-4" />
          Create Model
        </button>
      </div>
    </div>

    <div class="rounded-md border bg-card">
      <div class="relative w-full overflow-auto">
        <table class="w-full caption-bottom text-sm">
          <thead class="[&_tr]:border-b">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Name</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Version</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Status</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">RAG</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Tools</th>
              <th class="h-8 px-3 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="6" class="px-3 py-2 text-center">Loading...</td>
            </tr>
            <tr v-else-if="models.length === 0">
              <td colspan="6" class="px-3 py-2 text-center">No models found</td>
            </tr>
            <tr v-else v-for="model in models" :key="model.id" class="border-b transition-colors hover:bg-muted/50 cursor-pointer" @click="viewModelDetails(model)">
              <td class="px-3 py-2 align-middle font-medium">{{ model.name }}</td>
              <td class="px-3 py-2 align-middle">{{ model.version }}</td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                  :class="{
                    'border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100': model.active,
                    'border-transparent bg-secondary text-secondary-foreground': !model.active
                  }"
                >
                  {{ model.active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                  :class="{
                    'border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100': model.rag_settings?.enabled,
                    'border-transparent bg-secondary text-secondary-foreground': !model.rag_settings?.enabled
                  }"
                >
                  {{ model.rag_settings?.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle">
                <div class="flex flex-wrap gap-1">
                  <span v-for="tool in model.tool_names.slice(0, 2)" :key="tool" class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                    {{ tool }}
                  </span>
                  <span v-if="model.tool_names.length > 2" class="text-xs text-muted-foreground">+{{ model.tool_names.length - 2 }}</span>
                </div>
              </td>
              <td class="px-3 py-2 align-middle text-right" @click.stop>
                <div class="flex justify-end gap-2">
                  <button @click="viewModelDetails(model)" class="p-2 hover:bg-accent rounded-md" title="View Details">
                    <Eye class="h-4 w-4" />
                  </button>
                  <button @click="toggleActive(model)" class="p-2 hover:bg-accent rounded-md" :title="model.active ? 'Deactivate' : 'Activate'">
                    <PowerOff v-if="model.active" class="h-4 w-4" />
                    <Power v-else class="h-4 w-4" />
                  </button>
                  <button @click="deleteModel(model.id)" class="p-2 hover:bg-accent rounded-md text-destructive" title="Delete">
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
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'create')">
      <div class="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Create Model</h3>
          <button @click="closeCreateModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <form @submit.prevent="createModel" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Name</label>
              <input v-model="form.name" required class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Version</label>
              <input v-model="form.version" required class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Base Model</label>
            <input v-model="form.base_model" placeholder="e.g. gpt-4" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
          </div>

          <div class="flex items-center space-x-2">
            <input type="checkbox" v-model="form.enable_rag" id="rag" class="h-4 w-4 rounded border-primary text-primary ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />
            <label for="rag" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">Enable RAG</label>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Tools</label>
            <select multiple v-model="form.tool_names" class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
              <option v-for="tool in availableTools" :key="tool" :value="tool">{{ tool }}</option>
            </select>
            <p class="text-xs text-muted-foreground">Hold Ctrl/Cmd to select multiple</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Temperature</label>
              <input type="number" step="0.1" v-model="form.temperature" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium leading-none">Max Tokens</label>
              <input type="number" v-model="form.max_tokens" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
            </div>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="showCreateModal = false" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
              Cancel
            </button>
            <button type="submit" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
              Create
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Sync Modal -->
    <div v-if="showSyncModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'sync')">
      <div class="w-full max-w-4xl rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Sync Models from Config</h3>
          <button @click="closeSyncModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Config YAML</label>
            <textarea 
              v-model="syncForm.configYaml" 
              rows="15" 
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 font-mono"
              placeholder="Paste your YAML configuration here..."
            ></textarea>
          </div>

          <div class="flex items-center gap-6">
            <div class="flex items-center space-x-2">
              <input type="checkbox" v-model="syncForm.dryRun" id="dryRun" class="h-4 w-4 rounded border-primary text-primary ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />
              <label for="dryRun" class="text-sm font-medium leading-none">Dry Run (preview changes)</label>
            </div>
            <div class="flex items-center space-x-2">
              <input type="checkbox" v-model="syncForm.deleteMissing" id="deleteMissing" class="h-4 w-4 rounded border-primary text-primary ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />
              <label for="deleteMissing" class="text-sm font-medium leading-none text-destructive">Delete missing models</label>
            </div>
          </div>

          <!-- Sync Results -->
          <div v-if="syncResults" class="rounded-md border p-4 space-y-2">
            <h4 class="font-medium">{{ syncForm.dryRun ? 'Preview Results' : 'Sync Results' }}</h4>
            <div class="grid grid-cols-3 gap-4 text-sm">
              <div class="text-center p-2 rounded bg-green-100 dark:bg-green-900">
                <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ syncResults.created || 0 }}</div>
                <div class="text-muted-foreground">{{ syncForm.dryRun ? 'Would Create' : 'Created' }}</div>
              </div>
              <div class="text-center p-2 rounded bg-blue-100 dark:bg-blue-900">
                <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{{ syncResults.updated || 0 }}</div>
                <div class="text-muted-foreground">{{ syncForm.dryRun ? 'Would Update' : 'Updated' }}</div>
              </div>
              <div class="text-center p-2 rounded bg-red-100 dark:bg-red-900">
                <div class="text-2xl font-bold text-red-600 dark:text-red-400">{{ syncResults.deleted || 0 }}</div>
                <div class="text-muted-foreground">{{ syncForm.dryRun ? 'Would Delete' : 'Deleted' }}</div>
              </div>
            </div>
            <div v-if="syncResults.details && syncResults.details.length > 0" class="mt-3 text-sm">
              <h5 class="font-medium mb-1">Details:</h5>
              <ul class="list-disc list-inside text-muted-foreground">
                <li v-for="(detail, idx) in syncResults.details" :key="idx">{{ detail }}</li>
              </ul>
            </div>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="showSyncModal = false" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
              Cancel
            </button>
            <button 
              @click="syncModels" 
              :disabled="syncing"
              class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              <RefreshCw v-if="syncing" class="mr-2 h-4 w-4 animate-spin" />
              {{ syncing ? 'Syncing...' : (syncForm.dryRun ? 'Preview Sync' : 'Sync Models') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
