<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import {
  ArrowLeft,
  Save,
  Play,
  Code,
  Settings,
  Wrench,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const tool = ref(null)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const activeTab = ref('code')

const form = ref({
  name: '',
  description: '',
  category: '',
  enabled: true,
  function_code: '',
  parameters: []
})

// Test form - generate placeholder based on tool parameters
const testArgs = ref('{}')
const testResult = ref(null)
const testError = ref(null)

// Generate placeholder JSON based on tool parameters
const generatePlaceholderArgs = () => {
  const params = form.value.parameters || []
  if (params.length === 0) {
    // Default placeholder for tools without parameters
    if (tool.value?.name === 'get_datetime') {
      testArgs.value = '{}'
    } else if (tool.value?.name === 'search_knowledge_base') {
      testArgs.value = JSON.stringify({ query: "example search query" }, null, 2)
    } else {
      testArgs.value = JSON.stringify({
        example_param: "example_value"
      }, null, 2)
    }
    return
  }
  
  const placeholder = {}
  params.forEach(param => {
    switch (param.type) {
      case 'string':
        placeholder[param.name] = param.default || `example_${param.name}`
        break
      case 'number':
        placeholder[param.name] = param.default || 0
        break
      case 'boolean':
        placeholder[param.name] = param.default || false
        break
      case 'array':
        placeholder[param.name] = param.default || []
        break
      case 'object':
        placeholder[param.name] = param.default || {}
        break
      default:
        placeholder[param.name] = param.default || `example_${param.name}`
    }
  })
  testArgs.value = JSON.stringify(placeholder, null, 2)
}

const fetchTool = async () => {
  loading.value = true
  try {
    const response = await api.getTool(route.params.id)
    tool.value = response.data
    
    // Populate form with tool data
    form.value = {
      name: tool.value.name,
      description: tool.value.description || '',
      category: tool.value.category || '',
      enabled: tool.value.enabled,
      function_code: tool.value.function_code || '',
      parameters: tool.value.parameters || []
    }
    
    // Generate placeholder test arguments
    generatePlaceholderArgs()
  } catch (error) {
    console.error('Error fetching tool:', error)
    toast.error('Failed to load tool details')
  } finally {
    loading.value = false
  }
}

const saveTool = async () => {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      category: form.value.category,
      enabled: form.value.enabled,
      function_code: form.value.function_code,
      parameters: form.value.parameters
    }

    await api.updateTool(route.params.id, payload)
    await fetchTool()
    toast.success('Tool updated successfully!')
  } catch (error) {
    console.error('Error saving tool:', error)
    toast.error(error.response?.data?.detail || 'Failed to save tool')
  } finally {
    saving.value = false
  }
}

const testTool = async () => {
  testing.value = true
  testResult.value = null
  testError.value = null

  try {
    // Parse test arguments
    let args = {}
    try {
      args = JSON.parse(testArgs.value)
    } catch (e) {
      testError.value = 'Invalid JSON in test arguments'
      testing.value = false
      return
    }

    const response = await api.testTool(route.params.id, args)
    testResult.value = response.data
  } catch (error) {
    console.error('Error testing tool:', error)
    testError.value = error.response?.data?.detail || error.message || 'Test failed'
  } finally {
    testing.value = false
  }
}

const addParameter = () => {
  form.value.parameters.push({
    name: '',
    type: 'string',
    description: '',
    required: true,
    default: null
  })
}

const removeParameter = (index) => {
  form.value.parameters.splice(index, 1)
}

const isBuiltin = computed(() => tool.value?.is_builtin === true)

const tabs = [
  { id: 'code', label: 'Code Editor', icon: Code },
  { id: 'parameters', label: 'Parameters', icon: Settings },
  { id: 'testing', label: 'Testing', icon: Play }
]

// Computed breadcrumb items including current tab
const breadcrumbItems = computed(() => {
  const items = []
  
  // Add tool name
  if (tool.value) {
    items.push({
      label: tool.value.name,
      path: null
    })
  }
  
  // Add current tab
  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (currentTab) {
    items.push({
      label: currentTab.label,
      onClick: null
    })
  }
  
  return items
})

onMounted(() => {
  fetchTool()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="flex items-center space-x-2 ml-4">
          <span v-if="isBuiltin" class="inline-flex items-center rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-semibold">
            Built-in
          </span>
          <span v-else class="inline-flex items-center rounded-full bg-secondary text-secondary-foreground px-2.5 py-0.5 text-xs font-semibold">
            Custom
          </span>
          <span v-if="tool?.category" class="text-muted-foreground text-sm">
            • {{ tool.category }}
          </span>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <button
          v-if="!isBuiltin"
          @click="saveTool"
          :disabled="saving"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
        >
          <Save class="mr-2 h-4 w-4" />
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading tool details...</div>
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
        <!-- Code Editor Tab -->
        <div v-if="activeTab === 'code'" class="space-y-6">
          <!-- Tool Info -->
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Tool Information</h3>
            <div class="grid gap-4 md:grid-cols-2">
              <div>
                <label class="text-sm font-medium">Name</label>
                <input 
                  v-model="form.name" 
                  :disabled="isBuiltin"
                  class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50 disabled:cursor-not-allowed" 
                />
              </div>
              <div>
                <label class="text-sm font-medium">Category</label>
                <input 
                  v-model="form.category" 
                  :disabled="isBuiltin"
                  placeholder="e.g., utility, search, math"
                  class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50 disabled:cursor-not-allowed" 
                />
              </div>
              <div class="md:col-span-2">
                <label class="text-sm font-medium">Description</label>
                <textarea 
                  v-model="form.description" 
                  :disabled="isBuiltin"
                  rows="2"
                  class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50 disabled:cursor-not-allowed"
                ></textarea>
              </div>
              <div class="flex items-center space-x-2">
                <input 
                  type="checkbox" 
                  v-model="form.enabled" 
                  :disabled="isBuiltin"
                  id="enabled" 
                  class="h-4 w-4" 
                />
                <label for="enabled" class="text-sm font-medium">Enabled</label>
              </div>
            </div>
          </div>

          <!-- Code Editor -->
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">Python Code</h3>
              <div class="flex items-center space-x-2">
                <Code class="h-4 w-4 text-muted-foreground" />
                <span class="text-sm text-muted-foreground">Python 3.11+</span>
              </div>
            </div>
            
            <div v-if="isBuiltin" class="mb-4 p-3 rounded-md bg-muted">
              <div class="flex items-center space-x-2 text-sm text-muted-foreground">
                <AlertCircle class="h-4 w-4" />
                <span>Built-in tools cannot be edited. The code is implemented in the server.</span>
              </div>
            </div>

            <div class="relative">
              <textarea 
                v-model="form.function_code" 
                :disabled="isBuiltin"
                rows="20"
                spellcheck="false"
                class="flex w-full rounded-md border border-input bg-[#1e1e1e] text-[#d4d4d4] px-4 py-3 text-sm font-mono leading-relaxed disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="def main(args):
    # Tool entry point
    return 'Hello World'"
              ></textarea>
            </div>
            
            <div class="mt-4 text-sm text-muted-foreground">
              <p class="font-medium mb-2">Function Requirements:</p>
              <ul class="list-disc list-inside space-y-1">
                <li>Must define a <code class="bg-muted px-1 rounded">main(args)</code> function as the entry point</li>
                <li>The <code class="bg-muted px-1 rounded">args</code> parameter is a dictionary containing input values</li>
                <li>Return value should be a string or JSON-serializable object</li>
                <li>You can import standard library modules at the top of the code</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Parameters Tab -->
        <div v-if="activeTab === 'parameters'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">Function Parameters</h3>
              <button 
                v-if="!isBuiltin"
                @click="addParameter"
                class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-8 px-3 py-1"
              >
                Add Parameter
              </button>
            </div>

            <div v-if="form.parameters.length === 0" class="text-center py-8 text-muted-foreground">
              <Wrench class="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No parameters defined</p>
              <p class="text-sm">Parameters define what input the tool expects</p>
            </div>

            <div v-else class="space-y-4">
              <div 
                v-for="(param, index) in form.parameters" 
                :key="index"
                class="p-4 border rounded-lg space-y-3"
              >
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium">Parameter {{ index + 1 }}</span>
                  <button 
                    v-if="!isBuiltin"
                    @click="removeParameter(index)"
                    class="text-destructive hover:text-destructive/80"
                  >
                    <XCircle class="h-4 w-4" />
                  </button>
                </div>
                
                <div class="grid gap-3 md:grid-cols-2">
                  <div>
                    <label class="text-sm font-medium">Name</label>
                    <input 
                      v-model="param.name" 
                      :disabled="isBuiltin"
                      placeholder="parameter_name"
                      class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50" 
                    />
                  </div>
                  <div>
                    <label class="text-sm font-medium">Type</label>
                    <select 
                      v-model="param.type" 
                      :disabled="isBuiltin"
                      class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50"
                    >
                      <option value="string">String</option>
                      <option value="number">Number</option>
                      <option value="boolean">Boolean</option>
                      <option value="array">Array</option>
                      <option value="object">Object</option>
                    </select>
                  </div>
                  <div class="md:col-span-2">
                    <label class="text-sm font-medium">Description</label>
                    <input 
                      v-model="param.description" 
                      :disabled="isBuiltin"
                      placeholder="What does this parameter do?"
                      class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50" 
                    />
                  </div>
                  <div class="flex items-center space-x-2">
                    <input 
                      type="checkbox" 
                      v-model="param.required" 
                      :disabled="isBuiltin"
                      :id="`required-${index}`" 
                      class="h-4 w-4" 
                    />
                    <label :for="`required-${index}`" class="text-sm">Required</label>
                  </div>
                  <div v-if="!param.required">
                    <label class="text-sm font-medium">Default Value</label>
                    <input 
                      v-model="param.default" 
                      :disabled="isBuiltin"
                      placeholder="Default value"
                      class="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1 disabled:opacity-50" 
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Testing Tab -->
        <div v-if="activeTab === 'testing'" class="space-y-6">
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Test Tool</h3>
            
            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between">
                  <label class="text-sm font-medium">Input Arguments (JSON)</label>
                  <button 
                    type="button"
                    @click="generatePlaceholderArgs"
                    class="text-xs text-primary hover:underline"
                  >
                    Reset to placeholder
                  </button>
                </div>
                <textarea 
                  v-model="testArgs" 
                  rows="8"
                  spellcheck="false"
                  placeholder='{"key": "value"}'
                  class="flex w-full rounded-md border border-input bg-[#1e1e1e] text-[#d4d4d4] px-3 py-2 text-sm mt-1 font-mono"
                ></textarea>
                <p class="text-xs text-muted-foreground mt-1">
                  Provide the input arguments as a JSON object. The placeholder is generated based on tool parameters.
                </p>
              </div>

              <button 
                @click="testTool" 
                :disabled="testing"
                class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
              >
                <Play class="mr-2 h-4 w-4" />
                {{ testing ? 'Running...' : 'Run Test' }}
              </button>

              <!-- Test Result -->
              <div v-if="testResult !== null || testError" class="mt-4">
                <label class="text-sm font-medium">Result</label>
                
                <!-- Success -->
                <div v-if="testResult !== null && !testError" class="mt-2">
                  <div class="flex items-center space-x-2 text-green-600 mb-2">
                    <CheckCircle class="h-4 w-4" />
                    <span class="text-sm font-medium">Success</span>
                  </div>
                  <pre class="p-4 bg-muted rounded-md text-sm overflow-x-auto whitespace-pre-wrap">{{ typeof testResult === 'object' ? JSON.stringify(testResult, null, 2) : testResult }}</pre>
                </div>

                <!-- Error -->
                <div v-if="testError" class="mt-2">
                  <div class="flex items-center space-x-2 text-destructive mb-2">
                    <XCircle class="h-4 w-4" />
                    <span class="text-sm font-medium">Error</span>
                  </div>
                  <pre class="p-4 bg-destructive/10 text-destructive rounded-md text-sm overflow-x-auto whitespace-pre-wrap">{{ testError }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- Example Arguments -->
          <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
            <h3 class="text-lg font-semibold mb-4">Parameter Reference</h3>
            
            <div v-if="form.parameters.length === 0" class="text-muted-foreground text-sm">
              This tool has no defined parameters. You can still test it with an empty object <code class="bg-muted px-1 rounded">{}</code>.
            </div>

            <div v-else class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b">
                    <th class="text-left p-2 font-medium">Parameter</th>
                    <th class="text-left p-2 font-medium">Type</th>
                    <th class="text-left p-2 font-medium">Required</th>
                    <th class="text-left p-2 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="param in form.parameters" :key="param.name" class="border-b">
                    <td class="p-2 font-mono">{{ param.name }}</td>
                    <td class="p-2">{{ param.type }}</td>
                    <td class="p-2">
                      <span :class="param.required ? 'text-destructive' : 'text-muted-foreground'">
                        {{ param.required ? 'Yes' : 'No' }}
                      </span>
                    </td>
                    <td class="p-2 text-muted-foreground">{{ param.description || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
