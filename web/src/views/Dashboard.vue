<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { Activity, CheckCircle, AlertCircle, Clock, Hash, ArrowDown, ArrowUp } from 'lucide-vue-next'

const stats = ref({
  total_logs: 0,
  success_count: 0,
  error_count: 0,
  pending_count: 0,
  avg_latency_ms: 0,
  total_tokens: 0,
  input_tokens: 0,
  output_tokens: 0,
  models_used: {},
  tools_used: {}
})

const loading = ref(true)

const fetchStats = async () => {
  try {
    const response = await api.getLogStats()
    stats.value = response.data
  } catch (error) {
    console.error('Error fetching stats:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<template>
  <div class="space-y-6">
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading dashboard...</div>
    </div>
    
    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Total Requests</h3>
          <Activity class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ stats.total_logs }}</div>
      </div>
      
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Success Rate</h3>
          <CheckCircle class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">
          {{ stats.total_logs ? Math.round((stats.success_count / stats.total_logs) * 100) : 0 }}%
        </div>
        <p class="text-xs text-muted-foreground">{{ stats.success_count }} successful</p>
      </div>
      
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Errors</h3>
          <AlertCircle class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ stats.error_count }}</div>
      </div>
      
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Avg Latency</h3>
          <Clock class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ stats.avg_latency_ms ? stats.avg_latency_ms.toFixed(0) : 0 }}ms</div>
      </div>

      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Input Tokens</h3>
          <ArrowDown class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ stats.input_tokens.toLocaleString() }}</div>
      </div>

      <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
        <div class="flex flex-row items-center justify-between space-y-0 pb-2">
          <h3 class="tracking-tight text-sm font-medium">Output Tokens</h3>
          <ArrowUp class="h-4 w-4 text-muted-foreground" />
        </div>
        <div class="text-2xl font-bold">{{ stats.output_tokens.toLocaleString() }}</div>
      </div>
    </div>

    <div class="grid gap-6 md:grid-cols-2">
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm">
        <div class="flex flex-col space-y-1.5 p-6">
          <h3 class="font-semibold leading-none tracking-tight">Models Used</h3>
        </div>
        <div class="p-6 pt-0">
          <div v-if="Object.keys(stats.models_used).length === 0" class="text-sm text-muted-foreground">
            No data available
          </div>
          <div v-else class="space-y-4">
            <div v-for="(count, model) in stats.models_used" :key="model" class="flex items-center">
              <div class="w-full flex-1 text-sm font-medium truncate">{{ model }}</div>
              <div class="text-sm text-muted-foreground">{{ count }} req</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="rounded-xl border bg-card text-card-foreground shadow-sm">
        <div class="flex flex-col space-y-1.5 p-6">
          <h3 class="font-semibold leading-none tracking-tight">Tools Used</h3>
        </div>
        <div class="p-6 pt-0">
          <div v-if="Object.keys(stats.tools_used).length === 0" class="text-sm text-muted-foreground">
            No data available
          </div>
          <div v-else class="space-y-4">
            <div v-for="(count, tool) in stats.tools_used" :key="tool" class="flex items-center">
              <div class="w-full flex-1 text-sm font-medium truncate">{{ tool }}</div>
              <div class="text-sm text-muted-foreground">{{ count }} calls</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
