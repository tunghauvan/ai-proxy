<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import {
  Save,
  Play,
  Settings,
  BarChart3,
  History,
  Zap,
  Database,
  Wrench,
  TestTube,
  Eye,
  Edit3
} from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const model = ref(null)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const activeTab = ref('overview')
const checked = ref(false)

const form = ref({
  // Basic settings
  name: '',
  version: '',
  base_model: '',
  enabled: true,

  // Model parameters
  model_params: {
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    stop_sequences: []
  },

  // RAG settings
  rag_settings: {
    enabled: false,
    chunk_size: 1000,
    chunk_overlap: 200,
    similarity_threshold: 0.7,
    max_documents: 5,
    embedding_model: 'text-embedding-ada-002'
  },

  // Tool settings
  tool_names: [],
  tool_configs: {}
})

const availableTools = ref([])
const availableBaseModels = ref([])
const testPrompt = ref('Hello, can you help me with a simple task?')
const testResponse = ref('')
const modelStats = ref(null)
const versionHistory = ref([])
const showToolDialog = ref(false)
const selectedTool = ref('')
const toolCode = ref('')

// Watch for changes in checked to update form.enabled
watch(checked, (newValue) => {
  form.value.enabled = newValue
})

// Watch for changes in form.enabled to update checked
watch(() => form.value.enabled, (newValue) => {
  checked.value = newValue
})

const fetchModel = async () => {
  loading.value = true
  try {
    const response = await api.getModel(route.params.id)
    model.value = response.data

    // Populate form with model data
    form.value = {
      name: model.value.name,
      version: model.value.version,
      base_model: model.value.base_model || '',
      enabled: model.value.enabled,
      model_params: {
        temperature: model.value.model_params?.temperature || 0.7,
        max_tokens: model.value.model_params?.max_tokens || 2048,
        top_p: model.value.model_params?.top_p || 1.0,
        frequency_penalty: model.value.model_params?.frequency_penalty || 0.0,
        presence_penalty: model.value.model_params?.presence_penalty || 0.0,
        stop_sequences: model.value.model_params?.stop_sequences || []
      },
      rag_settings: {
        enabled: model.value.rag_settings?.enabled || false,
        chunk_size: model.value.rag_settings?.chunk_size || 1000,
        chunk_overlap: model.value.rag_settings?.chunk_overlap || 200,
        similarity_threshold: model.value.rag_settings?.similarity_threshold || 0.7,
        max_documents: model.value.rag_settings?.top_k || 5,
        embedding_model: model.value.rag_settings?.embedding_model || 'text-embedding-ada-002',
        collection: model.value.rag_settings?.collection || 'knowledge_base'
      },
      tool_names: [...model.value.tool_names],
      tool_configs: model.value.tool_configs || {}
    }

    // Sync checked with form.enabled
    checked.value = form.value.enabled

    // Fetch additional data
    await Promise.all([
      fetchModelStats(),
      fetchVersionHistory()
    ])
  } catch (error) {
    console.error('Error fetching model:', error)
  } finally {
    loading.value = false
  }
}

const fetchTools = async () => {
  try {
    const response = await api.getTools(true) // Get detailed tool info
    availableTools.value = response.data
  } catch (error) {
    console.error('Error fetching tools:', error)
    // Fallback to basic tool names if detailed API fails
    availableTools.value = ['calculator', 'weather', 'text_analyzer', 'unit_converter', 'random_tools']
  }
}

const fetchBaseModels = async () => {
  try {
    const response = await api.getBaseModels()
    availableBaseModels.value = response.data.data.map(model => model.id)
  } catch (error) {
    console.error('Error fetching base models:', error)
    // Fallback to some common models
    availableBaseModels.value = ['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'llama-2-70b']
  }
}

const fetchModelStats = async () => {
  try {
    // This would need a new API endpoint for model-specific stats
    // For now, we'll use placeholder data
    modelStats.value = {
      total_requests: 0,
      success_rate: 0,
      avg_latency: 0,
      total_tokens: 0,
      input_tokens: 0,
      output_tokens: 0
    }
  } catch (error) {
    console.error('Error fetching model stats:', error)
  }
}

const fetchVersionHistory = async () => {
  try {
    const response = await api.getModelVersions(route.params.id)
    versionHistory.value = response.data || []
  } catch (error) {
    console.error('Error fetching version history:', error)
    // Fallback to current version
    if (model.value) {
      versionHistory.value = [
        {
          version: model.value.version,
          created_at: model.value.created_at,
          enabled: model.value.enabled,
          active: model.value.active,
          rag_settings: model.value.rag_settings,
          tool_names: model.value.tool_names
        }
      ]
    }
  }
}

// Version management functions
const showCreateVersionModal = ref(false)
const newVersion = ref({
  version: '',
  description: '',
  enable_rag: false,
  tool_names: []
})
const creatingVersion = ref(false)

const openCreateVersionModal = () => {
  newVersion.value = {
    version: '',
    description: '',
    enable_rag: form.value.rag_settings?.enabled || false,
    tool_names: [...(form.value.tool_names || [])]
  }
  showCreateVersionModal.value = true
}

const createVersion = async () => {
  if (!newVersion.value.version) {
    toast.error('Version number is required')
    return
  }
  creatingVersion.value = true
  try {
    const payload = {
      version: newVersion.value.version,
      description: newVersion.value.description,
      rag_settings: { enabled: newVersion.value.enable_rag },
      tool_names: newVersion.value.tool_names
    }
    await api.createModelVersion(route.params.id, payload)
    toast.success(`Version ${newVersion.value.version} created successfully!`)
    showCreateVersionModal.value = false
    await fetchVersionHistory()
  } catch (error) {
    console.error('Error creating version:', error)
    toast.error('Failed to create version')
  } finally {
    creatingVersion.value = false
  }
}

const activateVersion = async (version) => {
  try {
    await api.activateModelVersion(route.params.id, version)
    toast.success(`Version ${version} activated!`)
    await fetchVersionHistory()
    await fetchModel()
  } catch (error) {
    console.error('Error activating version:', error)
    toast.error('Failed to activate version')
  }
}

const deactivateVersion = async (version) => {
  try {
    await api.deactivateModelVersion(route.params.id, version)
    toast.success(`Version ${version} deactivated!`)
    await fetchVersionHistory()
    await fetchModel()
  } catch (error) {
    console.error('Error deactivating version:', error)
    toast.error('Failed to deactivate version')
  }
}

const saveModel = async () => {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      version: form.value.version,
      base_model: form.value.base_model,
      enabled: form.value.enabled,
      model_params: form.value.model_params,
      rag_settings: {
        enabled: form.value.rag_settings.enabled,
        top_k: form.value.rag_settings.max_documents || 3,
        collection: form.value.rag_settings.collection || 'knowledge_base'
      },
      tool_names: form.value.tool_names
      // Remove tool_configs as it's not expected by the server
    }

    await api.updateModel(route.params.id, payload)
    await fetchModel() // Refresh data
    toast.success('Model updated successfully!')
  } catch (error) {
    console.error('Error saving model:', error)
    toast.error('Failed to save model')
  } finally {
    saving.value = false
  }
}

const testModel = async () => {
  testing.value = true
  testResponse.value = ''

  try {
    const payload = {
      model: `${form.value.name}@${form.value.version}`,
      messages: [
        {
          role: 'user',
          content: testPrompt.value
        }
      ],
      stream: false
    }

    const response = await api.chatCompletion(payload)
    testResponse.value = response.data.choices[0].message.content
  } catch (error) {
    console.error('Error testing model:', error)
    testResponse.value = `Error: ${error.response?.data?.detail || error.message}`
  } finally {
    testing.value = false
  }
}

const addStopSequence = () => {
  form.value.model_params.stop_sequences.push('')
}

const removeStopSequence = (index) => {
  form.value.model_params.stop_sequences.splice(index, 1)
}

const toggleTool = (toolName) => {
  const index = form.value.tool_names.indexOf(toolName)
  if (index > -1) {
    form.value.tool_names.splice(index, 1)
    delete form.value.tool_configs[toolName]
  } else {
    form.value.tool_names.push(toolName)
    form.value.tool_configs[toolName] = {}
  }
}

const isToolSelected = (toolName) => {
  return form.value.tool_names.includes(toolName)
}

const viewToolCode = async (toolId) => {
  // Find the tool object to get the name
  const tool = availableTools.value.find(t => t.id === toolId || t.name === toolId)
  selectedTool.value = tool ? tool.name : toolId
  showToolDialog.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)

  try {
    const response = await api.getTool(toolId)
    toolCode.value = response.data.function_code || 'No code available'
  } catch (error) {
    console.error('Error fetching tool code:', error)
    toolCode.value = 'Error loading tool code'
  }
}

const closeToolDialog = () => {
  showToolDialog.value = false
  selectedTool.value = ''
  toolCode.value = ''

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event) => {
  if (event.key === 'Escape' && showToolDialog.value) {
    closeToolDialog()
  }
}

const handleBackdropClick = (event) => {
  if (event.target === event.currentTarget) {
    closeToolDialog()
  }
}

const tabs = [
  { id: 'overview', label: 'Overview', icon: Eye },
  { id: 'parameters', label: 'Parameters', icon: Settings },
  { id: 'rag', label: 'RAG Settings', icon: Database },
  { id: 'tools', label: 'Tools', icon: Wrench },
  { id: 'versions', label: 'Versions', icon: History },
  { id: 'testing', label: 'Testing', icon: TestTube },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 }
]

// Computed breadcrumb items including current tab
const breadcrumbItems = computed(() => {
  const items = []
  
  // Add model name
  if (model.value) {
    items.push({
      label: model.value.name,
      path: null // Current page, not clickable to navigate away
    })
  }
  
  // Add current tab
  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (currentTab) {
    items.push({
      label: currentTab.label,
      onClick: null // Current tab
    })
  }
  
  return items
})

onMounted(() => {
  fetchModel()
  fetchTools()
  fetchBaseModels()
})

onUnmounted(() => {
  // Clean up keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div class="flex items-center gap-4">
        <!-- Breadcrumbs -->
        <Breadcrumbs :items="breadcrumbItems" />

        <!-- Status Toggle -->
        <div class="flex items-center gap-2 ml-6">
          <span class="text-sm font-medium">Status:</span>
          <span :class="form.enabled ? 'text-green-600' : 'text-red-600'" class="text-sm font-medium">
            {{ form.enabled ? 'Active' : 'Inactive' }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="saveModel"
          :disabled="saving"
          class="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 h-10"
        >
          <Save class="mr-2 h-4 w-4" />
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading model details...</div>
    </div>

    <!-- Content -->
    <div v-else class="space-y-6">
      <!-- Tabs -->
      <div class="border-b">
        <nav class="flex space-x-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            ]"
          >
            <component :is="tab.icon" class="h-4 w-4" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="space-y-6">
        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="space-y-6">
          <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Status</h3>
                <Zap class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">
                <span :class="form.enabled ? 'text-green-600' : 'text-red-600'">
                  {{ form.enabled ? 'Active' : 'Inactive' }}
                </span>
              </div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Base Model</h3>
                <Settings class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ form.base_model || 'Not set' }}</div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Tools</h3>
                <Wrench class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ form.tool_names.length }}</div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">RAG</h3>
                <Database class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">
                <span :class="form.rag_settings.enabled ? 'text-green-600' : 'text-red-600'">
                  {{ form.rag_settings.enabled ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>
          </div>

          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Model Configuration</h3>
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <label class="text-sm font-medium">Name</label>
                <input v-model="form.name" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
              </div>
              <div>
                <label class="text-sm font-medium">Version</label>
                <input v-model="form.version" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
              </div>
              <div>
                <label class="text-sm font-medium">Base Model</label>
                <select v-model="form.base_model" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1">
                  <option value="">Select a base model...</option>
                  <option v-for="baseModel in availableBaseModels" :key="baseModel" :value="baseModel">
                    {{ baseModel }}
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Parameters Tab -->
        <div v-if="activeTab === 'parameters'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Model Parameters</h3>
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <label class="text-sm font-medium">Temperature</label>
                <input type="number" step="0.1" min="0" max="2" v-model="form.model_params.temperature"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Controls randomness (0-2)</p>
              </div>
              <div>
                <label class="text-sm font-medium">Max Tokens</label>
                <input type="number" min="1" v-model="form.model_params.max_tokens"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Maximum response length</p>
              </div>
              <div>
                <label class="text-sm font-medium">Top P</label>
                <input type="number" step="0.1" min="0" max="1" v-model="form.model_params.top_p"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Nucleus sampling (0-1)</p>
              </div>
              <div>
                <label class="text-sm font-medium">Frequency Penalty</label>
                <input type="number" step="0.1" min="-2" max="2" v-model="form.model_params.frequency_penalty"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Reduce repetition (-2 to 2)</p>
              </div>
              <div>
                <label class="text-sm font-medium">Presence Penalty</label>
                <input type="number" step="0.1" min="-2" max="2" v-model="form.model_params.presence_penalty"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Encourage new topics (-2 to 2)</p>
              </div>
            </div>

            <div class="mt-6">
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm font-medium">Stop Sequences</label>
                <button @click="addStopSequence" class="text-sm text-primary hover:underline">Add Sequence</button>
              </div>
              <div class="space-y-2">
                <div v-for="(sequence, index) in form.model_params.stop_sequences" :key="index" class="flex items-center space-x-2">
                  <input v-model="form.model_params.stop_sequences[index]"
                         placeholder="Enter stop sequence"
                         class="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm" />
                  <button @click="removeStopSequence(index)" class="text-red-600 hover:text-red-800">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- RAG Settings Tab -->
        <div v-if="activeTab === 'rag'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">RAG Settings</h3>
              <div class="flex items-center space-x-2">
                <input type="checkbox" v-model="form.rag_settings.enabled" id="rag-enabled" class="h-4 w-4" />
                <label for="rag-enabled" class="text-sm font-medium">Enable RAG</label>
              </div>
            </div>

            <div v-if="form.rag_settings.enabled" class="grid gap-4 md:grid-cols-2">
              <div>
                <label class="text-sm font-medium">Chunk Size</label>
                <input type="number" min="100" v-model="form.rag_settings.chunk_size"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Size of text chunks</p>
              </div>
              <div>
                <label class="text-sm font-medium">Chunk Overlap</label>
                <input type="number" min="0" v-model="form.rag_settings.chunk_overlap"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Overlap between chunks</p>
              </div>
              <div>
                <label class="text-sm font-medium">Similarity Threshold</label>
                <input type="number" step="0.1" min="0" max="1" v-model="form.rag_settings.similarity_threshold"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Minimum similarity score (0-1)</p>
              </div>
              <div>
                <label class="text-sm font-medium">Max Documents</label>
                <input type="number" min="1" v-model="form.rag_settings.max_documents"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Maximum documents to retrieve</p>
              </div>
              <div class="md:col-span-2">
                <label class="text-sm font-medium">Embedding Model</label>
                <input v-model="form.rag_settings.embedding_model"
                       placeholder="e.g. text-embedding-ada-002"
                       class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1" />
                <p class="text-xs text-muted-foreground mt-1">Model used for text embeddings</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Tools Tab -->
        <div v-if="activeTab === 'tools'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Available Tools</h3>

            <!-- Tools Table -->
            <div class="rounded-md border bg-card">
              <div class="relative w-full overflow-auto">
                <table class="w-full caption-bottom text-sm">
                  <thead class="[&_tr]:border-b">
                    <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                      <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Name</th>
                      <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Description</th>
                      <th class="h-8 px-3 text-right align-middle font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="[&_tr:last-child]:border-0">
                    <tr v-for="tool in availableTools" :key="tool.name || tool"
                        class="border-b transition-colors hover:bg-muted/50">
                      <td class="px-3 py-2 align-middle">
                        <div class="flex items-center space-x-2">
                          <input type="checkbox" :checked="isToolSelected(tool.name || tool)"
                                 @change="toggleTool(tool.name || tool)" class="h-4 w-4" />
                          <span class="font-medium">{{ tool.name || tool }}</span>
                        </div>
                      </td>
                      <td class="px-3 py-2 align-middle text-muted-foreground max-w-[300px] truncate">
                        {{ tool.description || 'No description available' }}
                      </td>
                      <td class="px-3 py-2 align-middle text-right">
                        <button @click="viewToolCode(tool.id)"
                                class="p-2 hover:bg-accent rounded-md" title="View Code">
                          <Eye class="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-if="form.tool_names.length > 0" class="mt-6">
              <h4 class="text-md font-semibold mb-4">Selected Tools ({{ form.tool_names.length }})</h4>
              <div class="flex flex-wrap gap-2">
                <span v-for="tool in form.tool_names" :key="tool"
                      class="inline-flex items-center rounded-full bg-primary/10 text-primary px-3 py-1 text-sm">
                  {{ tool }}
                  <button @click="toggleTool(tool)" class="ml-2 text-primary hover:text-primary/80">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                  </button>
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Testing Tab -->
        <div v-if="activeTab === 'testing'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Test Model</h3>

            <div class="space-y-4">
              <div>
                <label class="text-sm font-medium">Test Prompt</label>
                <textarea v-model="testPrompt" rows="4"
                          placeholder="Enter a test prompt to see how the model responds..."
                          class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"></textarea>
              </div>

              <button @click="testModel" :disabled="testing"
                      class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
                <Play class="mr-2 h-4 w-4" />
                {{ testing ? 'Testing...' : 'Test Model' }}
              </button>

              <div v-if="testResponse" class="mt-4">
                <label class="text-sm font-medium">Response</label>
                <div class="mt-1 p-4 bg-muted rounded-md">
                  <pre class="text-sm whitespace-pre-wrap">{{ testResponse }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Analytics Tab -->
        <div v-if="activeTab === 'analytics'" class="space-y-6">
          <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Total Requests</h3>
                <BarChart3 class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ modelStats?.total_requests || 0 }}</div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Success Rate</h3>
                <BarChart3 class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ modelStats?.success_rate || 0 }}%</div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Avg Latency</h3>
                <BarChart3 class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ modelStats?.avg_latency || 0 }}ms</div>
            </div>

            <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
              <div class="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 class="tracking-tight text-sm font-medium">Total Tokens</h3>
                <BarChart3 class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="text-2xl font-bold">{{ modelStats?.total_tokens || 0 }}</div>
            </div>
          </div>
        </div>

        <!-- Version History Tab -->
        <div v-if="activeTab === 'versions'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm">
            <div class="flex items-center justify-between p-6">
              <h3 class="font-semibold leading-none tracking-tight">Model Versions</h3>
              <button 
                @click="openCreateVersionModal"
                class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                New Version
              </button>
            </div>
            <div class="p-6 pt-0">
              <div v-if="versionHistory.length === 0" class="text-center py-8 text-muted-foreground">
                No versions found
              </div>
              <div v-else class="space-y-4">
                <div v-for="version in versionHistory" :key="version.version"
                     class="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
                  <div class="flex-1">
                    <div class="flex items-center gap-3">
                      <h4 class="font-medium">v{{ version.version }}</h4>
                      <span v-if="version.active" class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800 dark:bg-green-900 dark:text-green-100">
                        Active
                      </span>
                      <span v-else-if="version.enabled" class="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                        Enabled
                      </span>
                      <span v-else class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-800 dark:bg-gray-900 dark:text-gray-100">
                        Disabled
                      </span>
                    </div>
                    <div class="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span v-if="version.rag_settings?.enabled">
                        <Database class="inline h-3 w-3 mr-1" /> RAG Enabled
                      </span>
                      <span v-if="version.tool_names?.length">
                        <Wrench class="inline h-3 w-3 mr-1" /> {{ version.tool_names.length }} Tools
                      </span>
                      <span v-if="version.created_at">
                        Created: {{ new Date(version.created_at).toLocaleDateString() }}
                      </span>
                    </div>
                    <p v-if="version.description" class="text-sm text-muted-foreground mt-1">{{ version.description }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button 
                      v-if="!version.active"
                      @click="activateVersion(version.version)"
                      class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3"
                      title="Activate this version"
                    >
                      <Zap class="h-4 w-4 mr-1" /> Activate
                    </button>
                    <button 
                      v-else
                      @click="deactivateVersion(version.version)"
                      class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3"
                      title="Deactivate this version"
                    >
                      Deactivate
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Create Version Modal -->
  <div v-if="showCreateVersionModal" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
    <div class="bg-background rounded-lg shadow-lg max-w-lg w-full">
      <div class="flex items-center justify-between p-6 border-b">
        <h3 class="text-lg font-semibold">Create New Version</h3>
        <button @click="showCreateVersionModal = false" class="text-muted-foreground hover:text-foreground">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      <div class="p-6 space-y-4">
        <div class="space-y-2">
          <label class="text-sm font-medium">Version Number *</label>
          <input 
            v-model="newVersion.version" 
            placeholder="e.g., 1.1.0" 
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          />
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium">Description</label>
          <textarea 
            v-model="newVersion.description" 
            placeholder="Describe what's new in this version..."
            rows="3"
            class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          ></textarea>
        </div>
        <div class="flex items-center space-x-2">
          <input 
            type="checkbox" 
            v-model="newVersion.enable_rag" 
            id="version-rag" 
            class="h-4 w-4 rounded border-primary text-primary ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
          />
          <label for="version-rag" class="text-sm font-medium">Enable RAG</label>
        </div>
        <div class="space-y-2">
          <label class="text-sm font-medium">Tools</label>
          <select 
            multiple 
            v-model="newVersion.tool_names" 
            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <option v-for="tool in availableTools" :key="tool.id || tool.name" :value="tool.name">{{ tool.name }}</option>
          </select>
          <p class="text-xs text-muted-foreground">Hold Ctrl/Cmd to select multiple</p>
        </div>
      </div>
      <div class="flex justify-end gap-2 p-6 border-t">
        <button 
          @click="showCreateVersionModal = false"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4"
        >
          Cancel
        </button>
        <button 
          @click="createVersion"
          :disabled="creatingVersion || !newVersion.version"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4"
        >
          {{ creatingVersion ? 'Creating...' : 'Create Version' }}
        </button>
      </div>
    </div>
  </div>

  <!-- Tool Code Dialog -->
  <div v-if="showToolDialog" class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" @click="handleBackdropClick">
    <div class="bg-background rounded-lg shadow-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
      <div class="flex items-center justify-between p-6 border-b">
        <h3 class="text-lg font-semibold">Tool Code: {{ selectedTool }}</h3>
        <button @click="closeToolDialog" class="text-muted-foreground hover:text-foreground">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      <div class="p-6 overflow-auto max-h-[60vh]">
        <pre class="text-sm bg-muted p-4 rounded-md overflow-x-auto"><code>{{ toolCode }}</code></pre>
      </div>
    </div>
  </div>
</template>