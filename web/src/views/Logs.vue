<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api/client'
import { Eye, Trash2, RefreshCw } from 'lucide-vue-next'

const logs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const limit = 20
const showDetailsModal = ref(false)
const currentLog = ref(null)

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
  try {
    const response = await api.getLog(id)
    currentLog.value = response.data
    showDetailsModal.value = true
  } catch (error) {
    console.error('Error fetching log details:', error)
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
  if (!confirm('Are you sure you want to clear ALL logs?')) return
  try {
    await api.clearLogs()
    fetchLogs()
  } catch (error) {
    console.error('Error clearing logs:', error)
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
      <h2 class="text-3xl font-bold tracking-tight">Logs</h2>
      <button 
        @click="clearLogs"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 text-destructive hover:text-destructive"
      >
        <Trash2 class="mr-2 h-4 w-4" />
        Clear All Logs
      </button>
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
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Time</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Model</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Status</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Latency</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Tokens</th>
              <th class="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="6" class="p-4 text-center">Loading...</td>
            </tr>
            <tr v-else-if="logs.length === 0">
              <td colspan="6" class="p-4 text-center">No logs found</td>
            </tr>
            <tr v-else v-for="log in logs" :key="log.id" class="border-b transition-colors hover:bg-muted/50">
              <td class="p-4 align-middle whitespace-nowrap">{{ new Date(log.created_at).toLocaleString() }}</td>
              <td class="p-4 align-middle">{{ log.model_name }}</td>
              <td class="p-4 align-middle">
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
              <td class="p-4 align-middle">{{ log.latency_ms ? `${log.latency_ms}ms` : '-' }}</td>
              <td class="p-4 align-middle">{{ log.total_tokens || '-' }}</td>
              <td class="p-4 align-middle text-right">
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

    <div class="flex items-center justify-end space-x-2 py-4">
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

    <!-- Details Modal -->
    <div v-if="showDetailsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div class="w-full max-w-3xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Log Details</h3>
          <button @click="showDetailsModal = false" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div v-if="currentLog" class="space-y-6">
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="font-semibold">ID:</span> {{ currentLog.id }}
            </div>
            <div>
              <span class="font-semibold">Chat ID:</span> {{ currentLog.chat_id }}
            </div>
            <div>
              <span class="font-semibold">Model:</span> {{ currentLog.model_name }}
            </div>
            <div>
              <span class="font-semibold">Created:</span> {{ new Date(currentLog.created_at).toLocaleString() }}
            </div>
            <div>
              <span class="font-semibold">Latency:</span> {{ currentLog.latency_ms }}ms
            </div>
            <div>
              <span class="font-semibold">Total Tokens:</span> {{ currentLog.total_tokens }}
            </div>
          </div>

          <div class="space-y-2">
            <h4 class="font-semibold text-sm">User Message</h4>
            <div class="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">{{ currentLog.user_message }}</div>
          </div>

          <div class="space-y-2">
            <h4 class="font-semibold text-sm">Response</h4>
            <div class="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap">{{ currentLog.response_content }}</div>
          </div>

          <div v-if="currentLog.tools_used && currentLog.tools_used.length > 0" class="space-y-2">
            <h4 class="font-semibold text-sm">Tools Used</h4>
            <div class="flex flex-wrap gap-2">
              <span v-for="tool in currentLog.tools_used" :key="tool" class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground">
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
      </div>
    </div>
  </div>
</template>
