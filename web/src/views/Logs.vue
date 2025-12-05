<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/client'
import { Eye, Trash2, RefreshCw, BarChart3, Clock, CheckCircle, XCircle, Wrench, Bot, Database, Zap } from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const logs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const limit = 20
const showDetailsModal = ref(false)
const showStatsModal = ref(false)
const currentLog = ref(null)
const agentEvents = ref([])
const toolLogs = ref([])
const loadingDetails = ref(false)
const stats = ref(null)
const loadingStats = ref(false)
const activeDetailTab = ref('overview')

const filters = ref({
  status: '',
  model: ''
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
    
    const response = await api.getLogs(params)
    logs.value = response.data.logs
    total.value = response.data.total
  } catch (error) {
    console.error('Error fetching logs:', error)
  } finally {
    loading.value = false
  }
}

const viewLog = async (id) => {
  loadingDetails.value = true
  activeDetailTab.value = 'overview'
  agentEvents.value = []
  toolLogs.value = []
  
  try {
    // Fetch log details
    const response = await api.getLog(id)
    currentLog.value = response.data
    showDetailsModal.value = true

    // Add keyboard event listener for Escape key
    document.addEventListener('keydown', handleKeyDown)
    
    // Fetch agent events and tool logs in parallel
    try {
      const [eventsRes, toolLogsRes] = await Promise.all([
        api.getAgentEvents(id).catch(() => ({ data: { events: [] } })),
        api.getToolLogsByChat(id).catch(() => ({ data: { logs: [] } }))
      ])
      agentEvents.value = eventsRes.data?.events || []
      toolLogs.value = toolLogsRes.data?.logs || []
    } catch (e) {
      console.log('Could not fetch additional details:', e)
    }
  } catch (error) {
    console.error('Error fetching log details:', error)
  } finally {
    loadingDetails.value = false
  }
}

const fetchStats = async () => {
  loadingStats.value = true
  try {
    const response = await api.getLogStats()
    stats.value = response.data
    showStatsModal.value = true

    // Add keyboard event listener for Escape key
    document.addEventListener('keydown', handleKeyDown)
  } catch (error) {
    console.error('Error fetching stats:', error)
  } finally {
    loadingStats.value = false
  }
}

const deleteLog = async (id) => {
  if (!confirm('Are you sure you want to delete this log?')) return
  try {
    await api.deleteLog(id)
    fetchLogs()
  } catch (error) {
    console.error('Error deleting log:', error)
  }
}

const clearLogs = async () => {
  if (!confirm('Are you sure you want to clear ALL logs? This action cannot be undone.')) return
  try {
    await api.clearLogs()
    fetchLogs()
  } catch (error) {
    console.error('Error clearing logs:', error)
  }
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  currentLog.value = null
  agentEvents.value = []
  toolLogs.value = []

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

const nextPage = () => {
  if ((page.value * limit) < total.value) {
    page.value++
    fetchLogs()
  }
}

const prevPage = () => {
  if (page.value > 1) {
    page.value--
    fetchLogs()
  }
}

const getEventIcon = (eventType) => {
  const iconMap = {
    'AGENT_START': Bot,
    'AGENT_END': Bot,
    'LLM_START': Zap,
    'LLM_END': Zap,
    'TOOL_START': Wrench,
    'TOOL_END': Wrench,
    'RETRIEVAL_START': Database,
    'RETRIEVAL_END': Database,
    'RETRIEVAL_SKIP': Database
  }
  return iconMap[eventType] || Clock
}

const getEventColor = (eventType, status) => {
  if (status === 'error') return 'text-red-500'
  if (eventType.includes('START')) return 'text-blue-500'
  if (eventType.includes('END')) return 'text-green-500'
  if (eventType.includes('SKIP')) return 'text-yellow-500'
  return 'text-muted-foreground'
}

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
          Clear All Logs
        </button>
      </div>
    </div>

    <div class="flex gap-4 items-center">
      <select v-model="filters.status" class="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 w-[150px]">
        <option value="">All Status</option>
        <option value="success">Success</option>
        <option value="error">Error</option>
        <option value="pending">Pending</option>
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
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Model</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Status</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Latency</th>
              <th class="h-8 px-3 text-left align-middle font-medium text-muted-foreground">Tokens</th>
              <th class="h-8 px-3 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="6" class="px-3 py-2 text-center">Loading...</td>
            </tr>
            <tr v-else-if="logs.length === 0">
              <td colspan="6" class="px-3 py-2 text-center">No logs found</td>
            </tr>
            <tr v-else v-for="log in logs" :key="log.id" class="border-b transition-colors hover:bg-muted/50 cursor-pointer" @click="viewLog(log.id)">
              <td class="px-3 py-2 align-middle whitespace-nowrap">{{ new Date(log.created_at).toLocaleString() }}</td>
              <td class="px-3 py-2 align-middle">{{ log.model_name }}</td>
              <td class="px-3 py-2 align-middle">
                <span 
                  class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  :class="{
                    'border-transparent bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100': log.status === 'success',
                    'border-transparent bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100': log.status === 'error',
                    'border-transparent bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100': log.status === 'pending'
                  }"
                >
                  {{ log.status }}
                </span>
              </td>
              <td class="px-3 py-2 align-middle">{{ log.latency_ms ? `${log.latency_ms}ms` : '-' }}</td>
              <td class="px-3 py-2 align-middle">{{ log.total_tokens || '-' }}</td>
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
      <div class="w-full max-w-4xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Log Details</h3>
          <button @click="closeDetailsModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <!-- Tabs -->
        <div class="border-b mb-4">
          <nav class="flex space-x-4">
            <button 
              @click="activeDetailTab = 'overview'"
              :class="activeDetailTab === 'overview' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'"
              class="py-2 px-1 border-b-2 font-medium text-sm"
            >Overview</button>
            <button 
              @click="activeDetailTab = 'timeline'"
              :class="activeDetailTab === 'timeline' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'"
              class="py-2 px-1 border-b-2 font-medium text-sm"
            >
              Timeline
              <span v-if="agentEvents.length > 0" class="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">{{ agentEvents.length }}</span>
            </button>
            <button 
              @click="activeDetailTab = 'tools'"
              :class="activeDetailTab === 'tools' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground'"
              class="py-2 px-1 border-b-2 font-medium text-sm"
            >
              Tool Executions
              <span v-if="toolLogs.length > 0" class="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">{{ toolLogs.length }}</span>
            </button>
          </nav>
        </div>
        
        <div v-if="loadingDetails" class="text-center py-8">Loading details...</div>
        
        <div v-else-if="currentLog" class="space-y-6">
          <!-- Overview Tab -->
          <div v-if="activeDetailTab === 'overview'" class="space-y-6">
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="font-semibold">ID:</span> 
                <span class="ml-2 font-mono text-xs">{{ currentLog.id }}</span>
              </div>
              <div>
                <span class="font-semibold">Chat ID:</span> 
                <span class="ml-2 font-mono text-xs">{{ currentLog.chat_id }}</span>
              </div>
              <div>
                <span class="font-semibold">Model:</span> {{ currentLog.model_name }}
              </div>
              <div>
                <span class="font-semibold">Status:</span>
                <span 
                  class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold"
                  :class="{
                    'bg-green-100 text-green-800': currentLog.status === 'success',
                    'bg-red-100 text-red-800': currentLog.status === 'error',
                    'bg-yellow-100 text-yellow-800': currentLog.status === 'pending'
                  }"
                >{{ currentLog.status }}</span>
              </div>
              <div>
                <span class="font-semibold">Created:</span> {{ new Date(currentLog.created_at).toLocaleString() }}
              </div>
              <div>
                <span class="font-semibold">Latency:</span> {{ currentLog.latency_ms }}ms
              </div>
            </div>

            <!-- Token Usage -->
            <div class="grid grid-cols-3 gap-4">
              <div class="rounded-lg border p-3 text-center">
                <div class="text-lg font-bold">{{ currentLog.prompt_tokens || 0 }}</div>
                <div class="text-xs text-muted-foreground">Prompt Tokens</div>
              </div>
              <div class="rounded-lg border p-3 text-center">
                <div class="text-lg font-bold">{{ currentLog.completion_tokens || 0 }}</div>
                <div class="text-xs text-muted-foreground">Completion Tokens</div>
              </div>
              <div class="rounded-lg border p-3 text-center">
                <div class="text-lg font-bold">{{ currentLog.total_tokens || 0 }}</div>
                <div class="text-xs text-muted-foreground">Total Tokens</div>
              </div>
            </div>

            <div class="space-y-2">
              <h4 class="font-semibold text-sm">User Message</h4>
              <div class="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap max-h-[150px] overflow-y-auto">{{ currentLog.user_message }}</div>
            </div>

            <div class="space-y-2">
              <h4 class="font-semibold text-sm">Response</h4>
              <div class="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap max-h-[200px] overflow-y-auto">{{ currentLog.response_content }}</div>
            </div>

            <div v-if="currentLog.tools_used && currentLog.tools_used.length > 0" class="space-y-2">
              <h4 class="font-semibold text-sm">Tools Used</h4>
              <div class="flex flex-wrap gap-2">
                <span v-for="tool in currentLog.tools_used" :key="tool" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold bg-secondary text-secondary-foreground">
                  <Wrench class="mr-1 h-3 w-3" />
                  {{ tool }}
                </span>
              </div>
            </div>

            <div v-if="currentLog.error_message" class="space-y-2">
              <h4 class="font-semibold text-sm text-destructive">Error</h4>
              <div class="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                <p class="font-bold">{{ currentLog.error_type }}</p>
                <p>{{ currentLog.error_message }}</p>
              </div>
            </div>
          </div>

          <!-- Timeline Tab -->
          <div v-if="activeDetailTab === 'timeline'" class="space-y-4">
            <div v-if="agentEvents.length === 0" class="text-center py-8 text-muted-foreground">
              No timeline events available for this log
            </div>
            <div v-else class="relative">
              <div class="absolute left-4 top-0 bottom-0 w-px bg-border"></div>
              <div v-for="(event, index) in agentEvents" :key="index" class="relative pl-10 pb-6 last:pb-0">
                <div 
                  class="absolute left-2 w-5 h-5 rounded-full border-2 bg-background flex items-center justify-center"
                  :class="getEventColor(event.event_type, event.status)"
                >
                  <component :is="getEventIcon(event.event_type)" class="h-3 w-3" />
                </div>
                <div class="rounded-lg border p-3">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold text-sm">{{ event.event_type }}</span>
                      <span v-if="event.sequence_number" class="text-xs text-muted-foreground">#{{ event.sequence_number }}</span>
                    </div>
                    <div class="flex items-center gap-2 text-xs text-muted-foreground">
                      <span v-if="event.duration_ms">{{ event.duration_ms }}ms</span>
                      <span 
                        v-if="event.status"
                        class="inline-flex items-center rounded-full px-1.5 py-0.5 text-xs"
                        :class="event.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                      >{{ event.status }}</span>
                    </div>
                  </div>
                  
                  <!-- Event-specific details -->
                  <div v-if="event.event_type === 'TOOL_START' || event.event_type === 'TOOL_END'" class="text-sm">
                    <span class="text-muted-foreground">Tool:</span> 
                    <span class="font-medium">{{ event.tool_name }}</span>
                    <div v-if="event.tool_input" class="mt-1 text-xs font-mono bg-muted p-2 rounded overflow-x-auto">
                      Input: {{ JSON.stringify(event.tool_input) }}
                    </div>
                    <div v-if="event.tool_output" class="mt-1 text-xs bg-muted p-2 rounded max-h-[100px] overflow-y-auto">
                      Output: {{ event.tool_output }}
                    </div>
                  </div>
                  
                  <div v-if="event.event_type === 'LLM_END' && event.event_data" class="text-sm">
                    <div v-if="event.event_data.input_tokens || event.event_data.output_tokens" class="text-xs text-muted-foreground">
                      Tokens: {{ event.event_data.input_tokens || 0 }} in / {{ event.event_data.output_tokens || 0 }} out
                    </div>
                    <div v-if="event.event_data.has_tool_calls" class="mt-1">
                      <span class="text-muted-foreground">Tool calls requested</span>
                    </div>
                  </div>
                  
                  <div v-if="event.event_type === 'RETRIEVAL_END' && event.event_data" class="text-sm">
                    <span class="text-muted-foreground">Retrieved {{ event.event_data.num_docs || 0 }} documents</span>
                  </div>
                  
                  <div v-if="event.error_message" class="mt-2 text-sm text-destructive">
                    Error: {{ event.error_message }}
                  </div>
                  
                  <div class="mt-2 text-xs text-muted-foreground">
                    {{ new Date(event.timestamp).toLocaleTimeString() }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Tool Executions Tab -->
          <div v-if="activeDetailTab === 'tools'" class="space-y-4">
            <div v-if="toolLogs.length === 0" class="text-center py-8 text-muted-foreground">
              No tool executions for this chat
            </div>
            <div v-else class="space-y-3">
              <div v-for="tlog in toolLogs" :key="tlog.id" class="rounded-lg border p-4">
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <Wrench class="h-4 w-4 text-muted-foreground" />
                    <span class="font-semibold">{{ tlog.tool_name }}</span>
                    <span 
                      class="text-xs px-1.5 py-0.5 rounded"
                      :class="tlog.is_builtin ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'"
                    >{{ tlog.is_builtin ? 'built-in' : 'custom' }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-sm text-muted-foreground">{{ tlog.execution_time_ms }}ms</span>
                    <span 
                      class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold"
                      :class="tlog.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'"
                    >
                      <CheckCircle v-if="tlog.status === 'success'" class="mr-1 h-3 w-3" />
                      <XCircle v-else class="mr-1 h-3 w-3" />
                      {{ tlog.status }}
                    </span>
                  </div>
                </div>
                <div class="space-y-2 text-sm">
                  <div>
                    <span class="text-muted-foreground">Input:</span>
                    <pre class="mt-1 text-xs font-mono bg-muted p-2 rounded overflow-x-auto">{{ JSON.stringify(tlog.input_args, null, 2) }}</pre>
                  </div>
                  <div>
                    <span class="text-muted-foreground">Output:</span>
                    <div class="mt-1 text-xs bg-muted p-2 rounded max-h-[100px] overflow-y-auto whitespace-pre-wrap">{{ tlog.output_result || '(none)' }}</div>
                  </div>
                  <div v-if="tlog.error_message" class="text-destructive">
                    <span class="font-medium">Error:</span> {{ tlog.error_message }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Statistics Modal -->
    <div v-if="showStatsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'stats')">
      <div class="w-full max-w-4xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Chat Statistics</h3>
          <button @click="closeStatsModal" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div v-if="stats" class="space-y-6">
          <!-- Overview -->
          <div class="grid grid-cols-4 gap-4">
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold">{{ stats.total_logs }}</div>
              <div class="text-sm text-muted-foreground">Total Logs</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold text-green-600">{{ stats.success_count }}</div>
              <div class="text-sm text-muted-foreground">Success</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold text-red-600">{{ stats.error_count }}</div>
              <div class="text-sm text-muted-foreground">Errors</div>
            </div>
            <div class="rounded-lg border bg-card p-4 text-center">
              <div class="text-2xl font-bold">{{ stats.avg_latency_ms ? stats.avg_latency_ms.toFixed(0) : 0 }}ms</div>
              <div class="text-sm text-muted-foreground">Avg Latency</div>
            </div>
          </div>

          <!-- Models Used -->
          <div v-if="stats.models_used && Object.keys(stats.models_used).length > 0" class="space-y-2">
            <h4 class="font-semibold">Models Used</h4>
            <div class="rounded-md border">
              <table class="w-full text-sm">
                <thead class="border-b bg-muted/50">
                  <tr>
                    <th class="p-3 text-left font-medium">Model</th>
                    <th class="p-3 text-right font-medium">Requests</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(count, model) in stats.models_used" :key="model" class="border-b last:border-0">
                    <td class="p-3 font-medium">{{ model }}</td>
                    <td class="p-3 text-right">{{ count }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Tools Used -->
          <div v-if="stats.tools_used && Object.keys(stats.tools_used).length > 0" class="space-y-2">
            <h4 class="font-semibold">Tools Used</h4>
            <div class="rounded-md border">
              <table class="w-full text-sm">
                <thead class="border-b bg-muted/50">
                  <tr>
                    <th class="p-3 text-left font-medium">Tool</th>
                    <th class="p-3 text-right font-medium">Calls</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(count, tool) in stats.tools_used" :key="tool" class="border-b last:border-0">
                    <td class="p-3 font-medium">{{ tool }}</td>
                    <td class="p-3 text-right">{{ count }}</td>
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
