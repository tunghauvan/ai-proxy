<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import api from '../api/client'
import { useToast } from 'vue-toastification'
import { Eye, Trash2, RefreshCw, BarChart3, Clock, CheckCircle, XCircle, Wrench } from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const toast = useToast()

const logs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const limit = 20
const showDetailsModal = ref(false)
const showStatsModal = ref(false)
const currentLog = ref(null)
const stats = ref(null)
const loadingStats = ref(false)

const filters = ref({
  tool_name: '',
  status: ''
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      limit,
      offset: (page.value - 1) * limit,
      ...filters.value
    }
    // Remove empty filters
    Object.keys(params).forEach(key => params[key] === '' && delete params[key])
    
    const response = await api.getToolLogs(params)
    logs.value = response.data.logs || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('Error fetching tool logs:', error)
    toast.error('Failed to fetch tool logs')
  } finally {
    loading.value = false
  }
}

const viewLog = async (id) => {
  try {
    const response = await api.getToolLog(id)
    currentLog.value = response.data
    showDetailsModal.value = true

    // Add keyboard event listener for Escape key
    document.addEventListener('keydown', handleKeyDown)
  } catch (error) {
    console.error('Error fetching log details:', error)
    toast.error('Failed to fetch log details')
  }
}

const deleteLog = async (id) => {
  if (!confirm('Are you sure you want to delete this tool log?')) return
  try {
    await api.deleteToolLog(id)
    toast.success('Log deleted')
    fetchLogs()
  } catch (error) {
    console.error('Error deleting log:', error)
    toast.error('Failed to delete log')
  }
}

const clearLogs = async () => {
  if (!confirm('Are you sure you want to clear ALL tool execution logs?')) return
  try {
    await api.clearToolLogs()
    toast.success('All tool logs cleared')
    fetchLogs()
  } catch (error) {
    console.error('Error clearing logs:', error)
    toast.error('Failed to clear logs')
  }
}

const fetchStats = async () => {
  loadingStats.value = true
  try {
    const response = await api.getToolLogStats()
    stats.value = response.data
    showStatsModal.value = true

    // Add keyboard event listener for Escape key
    document.addEventListener('keydown', handleKeyDown)
  } catch (error) {
    console.error('Error fetching stats:', error)
    toast.error('Failed to fetch statistics')
  } finally {
    loadingStats.value = false
  }
}

const nextPage = () => {
  if ((page.value * limit) < total.value) {
    page.value++
    fetchLogs()
  }
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  currentLog.value = null

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const closeStatsModal = () => {
  showStatsModal.value = false
  stats.value = null

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event) => {
  if (event.key === 'Escape') {
    if (showDetailsModal.value) {
      closeDetailsModal()
    } else if (showStatsModal.value) {
      closeStatsModal()
    }
  }
}

const handleBackdropClick = (event, modalType) => {
  if (event.target === event.currentTarget) {
    if (modalType === 'details') {
      closeDetailsModal()
    } else if (modalType === 'stats') {
      closeStatsModal()
    }
  }
}

const prevPage = () => {
  if (page.value > 1) {
    page.value--
    fetchLogs()
  }
}

const uniqueTools = computed(() => {
  const tools = new Set(logs.value.map(l => l.tool_name))
  return Array.from(tools).sort()
})

watch(filters, () => {
  page.value = 1
  fetchLogs()
}, { deep: true })

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <Breadcrumbs />
      <div class="flex gap-2">
        <button 
          @click="fetchStats"
          :disabled="loadingStats"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
        >
          <BarChart3 class="mr-2 h-4 w-4" />
          Statistics
        </button>
        <button 
          @click="clearLogs"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 text-destructive hover:text-destructive"
        >
          <Trash2 class="mr-2 h-4 w-4" />
          Clear All
        </button>
      </div>
    </div>

    <div class="flex gap-4 items-center">
      <input 
        v-model="filters.tool_name" 
        placeholder="Filter by tool name..."
        class="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-[200px]"
      />
      <select v-model="filters.status" class="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-[150px]">
        <option value="">All Status</option>
        <option value="success">Success</option>
        <option value="error">Error</option>
      </select>
      <button @click="fetchLogs" class="p-2 hover:bg-accent rounded-md" title="Refresh">
        <RefreshCw class="h-4 w-4" />
      </button>
    </div>

    <div class="rounded-md border bg-card">
      <div class="relative w-full overflow-auto">
        <table class="w-full caption-bottom text-sm">
          <thead class="[&_tr]:border-b">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Time</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Tool</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Status</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Execution Time</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Type</th>
              <th class="h-8 px-3 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="6" class="px-3 py-2 text-center">Loading...</td>
            </tr>
            <tr v-else-if="logs.length === 0">
              <td colspan="6" class="px-3 py-2 text-center">No tool execution logs found</td>
            </tr>
            <tr v-else v-for="log in logs" :key="log.id" class="border-b transition-colors hover:bg-muted/50 cursor-pointer" @click="viewLog(log.id)">
              <td class="px-3 py-2 align-middle whitespace-nowrap">{{ new Date(log.created_at).toLocaleString() }}</td>
              <td class="px-3 py-2 align-middle font-medium">{{ log.tool_name }}</td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                  :class="{
                    'border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100': log.status === 'success',
                    'border-transparent bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100': log.status === 'error'
                  }"
                >
                  {{ log.status }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle">{{ log.execution_time_ms ? `${log.execution_time_ms}ms` : '-' }}</td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                  :class="{
                    'border-transparent bg-primary/10 text-primary': log.is_builtin,
                    'border-transparent bg-secondary text-secondary-foreground': !log.is_builtin
                  }"
                >
                  {{ log.is_builtin ? 'Built-in' : 'Custom' }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle text-right" @click.stop>
                <div class="flex justify-end gap-2">
                  <button @click="viewLog(log.id)" class="p-2 hover:bg-accent rounded-md" title="View Details">
                    <Eye class="h-4 w-4" />
                  </button>
                  <button @click="deleteLog(log.id)" class="p-2 hover:bg-accent rounded-md text-destructive" title="Delete Log">
                    <Trash2 class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="flex items-center justify-between py-4">
      <span class="text-sm text-muted-foreground">Total: {{ total }} logs</span>
      <div class="flex items-center space-x-2">
        <button 
          @click="prevPage" 
          :disabled="page === 1"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2"
        >
          Previous
        </button>
        <span class="text-sm text-muted-foreground">Page {{ page }}</span>
        <button 
          @click="nextPage" 
          :disabled="(page * limit) >= total"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2"
        >
          Next
        </button>
      </div>
    </div>

    <!-- Details Modal -->
    <div v-if="showDetailsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'details')">
      <div class="w-full max-w-3xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Tool Execution Details</h3>
          <button @click="closeDetailsModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div v-if="currentLog" class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="font-semibold">Tool Name:</span> 
              <span class="ml-2 font-mono">{{ currentLog.tool_name }}</span>
            </div>
            <div>
              <span class="font-semibold">Status:</span>
              <span 
                class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold"
                :class="currentLog.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
              >
                {{ currentLog.status }}
              </span>
            </div>
            <div>
              <span class="font-semibold">Execution Time:</span> {{ currentLog.execution_time_ms }}ms
            </div>
            <div>
              <span class="font-semibold">Type:</span> {{ currentLog.is_builtin ? 'Built-in' : 'Custom' }}
            </div>
            <div>
              <span class="font-semibold">Created:</span> {{ new Date(currentLog.created_at).toLocaleString() }}
            </div>
            <div v-if="currentLog.chat_log_id">
              <span class="font-semibold">Chat Log ID:</span> 
              <span class="ml-2 font-mono text-xs">{{ currentLog.chat_log_id }}</span>
            </div>
          </div>

          <div class="space-y-2">
            <h4 class="font-semibold text-sm">Input Arguments</h4>
            <div class="rounded-md bg-muted p-3 text-sm font-mono whitespace-pre-wrap overflow-x-auto">{{ JSON.stringify(currentLog.input_args, null, 2) || '(none)' }}</div>
          </div>

          <div class="space-y-2">
            <h4 class="font-semibold text-sm">Output Result</h4>
            <div class="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap max-h-[200px] overflow-y-auto">{{ currentLog.output_result || '(none)' }}</div>
          </div>

          <div v-if="currentLog.headers_forwarded && Object.keys(currentLog.headers_forwarded).length > 0" class="space-y-2">
            <h4 class="font-semibold text-sm">Headers Forwarded</h4>
            <div class="rounded-md bg-muted p-3 text-sm font-mono whitespace-pre-wrap">{{ JSON.stringify(currentLog.headers_forwarded, null, 2) }}</div>
          </div>

          <div v-if="currentLog.error_message" class="space-y-2">
            <h4 class="font-semibold text-sm text-destructive">Error</h4>
            <div class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              <p>{{ currentLog.error_message }}</p>
              <pre v-if="currentLog.error_traceback" class="mt-2 text-xs whitespace-pre-wrap">{{ currentLog.error_traceback }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Statistics Modal -->
    <div v-if="showStatsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'stats')">
      <div class="w-full max-w-2xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Tool Execution Statistics</h3>
          <button @click="closeStatsModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div v-if="stats" class="space-y-6">
          <!-- Overview -->
          <div class="grid grid-cols-4 gap-4">
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold">{{ stats.total_executions }}</div>
              <div class="text-sm text-muted-foreground">Total Executions</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold text-green-600">{{ stats.total_successes }}</div>
              <div class="text-sm text-muted-foreground">Successful</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold text-red-600">{{ stats.total_errors }}</div>
              <div class="text-sm text-muted-foreground">Errors</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold">{{ stats.success_rate }}%</div>
              <div class="text-sm text-muted-foreground">Success Rate</div>
            </div>
          </div>

          <!-- Per-Tool Stats -->
          <div v-if="stats.tools && stats.tools.length > 0" class="space-y-2">
            <h4 class="font-semibold">Per-Tool Statistics</h4>
            <div class="rounded-md border">
              <table class="w-full text-sm">
                <thead class="border-b bg-muted/50">
                  <tr>
                    <th class="p-3 text-left font-medium">Tool</th>
                    <th class="p-3 text-center font-medium">Executions</th>
                    <th class="p-3 text-center font-medium">Success</th>
                    <th class="p-3 text-center font-medium">Errors</th>
                    <th class="p-3 text-right font-medium">Avg Time</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="tool in stats.tools" :key="tool.tool_name" class="border-b last:border-0">
                    <td class="p-3 font-medium">{{ tool.tool_name }}</td>
                    <td class="p-3 text-center">{{ tool.execution_count }}</td>
                    <td class="p-3 text-center text-green-600">{{ tool.success_count }}</td>
                    <td class="p-3 text-center text-red-600">{{ tool.error_count }}</td>
                    <td class="p-3 text-right">{{ tool.avg_execution_time_ms ? `${tool.avg_execution_time_ms.toFixed(1)}ms` : '-' }}</td>
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
