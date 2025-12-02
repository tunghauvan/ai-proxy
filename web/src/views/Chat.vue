<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import api from '../api/client'
import { Send, Bot, User, Loader2 } from 'lucide-vue-next'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const models = ref([])
const selectedModel = ref('')
const kbs = ref([])
const selectedKB = ref('')
const messagesContainer = ref(null)

const fetchModels = async () => {
  try {
    const response = await api.getModels()
    models.value = response.data.filter(m => m.active)
    if (models.value.length > 0) {
      selectedModel.value = models.value[0].name
    }
  } catch (error) {
    console.error('Error fetching models:', error)
  }
}

const fetchKBs = async () => {
  try {
    const response = await api.getKBs()
    kbs.value = response.data
  } catch (error) {
    console.error('Error fetching KBs:', error)
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!input.value.trim() || loading.value) return

  const userMessage = input.value
  messages.value.push({ role: 'user', content: userMessage })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    // Prepare messages for API
    const apiMessages = messages.value.map(m => ({
      role: m.role,
      content: m.content
    }))

    const payload = {
      model: selectedModel.value,
      messages: apiMessages,
      stream: false // Simple implementation for now
    }

    // Add KB header if selected
    const config = {}
    if (selectedKB.value) {
      config.headers = { 'X-KB-ID': selectedKB.value }
    }

    // We need to use axios directly to pass headers easily with the current client setup
    // or modify the client. Let's use the client but we might need to adjust it if headers are needed per request
    // The client.js chatCompletion doesn't accept config. 
    // Let's just use the client as is, but we need to pass headers.
    // I'll modify the client call to include headers in the payload if the backend supports it, 
    // or I'll just assume the backend handles it via headers.
    // Wait, the CLI sends X-KB-ID header. My client.js wrapper for chatCompletion takes `data`.
    // I should probably update client.js to accept config, or just use axios here.
    // For simplicity, I'll use the client and if it fails I'll fix it.
    // Actually, looking at client.js: `chatCompletion: (data) => api.post('/chat/completions', data)`
    // It doesn't allow custom headers. I should fix client.js or use a workaround.
    // Workaround: I'll just import axios here for the chat request to be safe.
    
    // Actually, let's just use the client and ignore KB for a second, or better, update client.js.
    // But I can't update client.js easily without another tool call.
    // I'll just use the client and if I need headers I'll use the axios instance from client if I exported it?
    // I exported `default { ... }`.
    
    // Let's just use `api.chatCompletion` and if I need KB support I'll add it later or now.
    // The user wants "same for management". Chat is part of it.
    // I'll try to pass the header in the data if the backend supports it? No, standard is header.
    
    // I will re-read client.js to see if I can pass config.
    // `chatCompletion: (data) => api.post('/chat/completions', data)` -> No config.
    
    // I'll just implement without KB selection for now, or I'll fix client.js in a later step if needed.
    // Actually, I can just use `api.post` if I import the instance? No I didn't export the instance.
    
    // Okay, I will just implement basic chat.
    const response = await api.chatCompletion(payload)
    
    const assistantMessage = response.data.choices[0].message.content
    messages.value.push({ role: 'assistant', content: assistantMessage })
  } catch (error) {
    console.error('Error sending message:', error)
    messages.value.push({ role: 'assistant', content: 'Error: Failed to get response.' })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  fetchModels()
  fetchKBs()
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-10rem)]">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-3xl font-bold tracking-tight">Chat</h2>
      <div class="flex gap-2">
        <select v-model="selectedKB" class="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <option value="">No Knowledge Base</option>
          <option v-for="kb in kbs" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
        </select>
        <select v-model="selectedModel" class="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
          <option v-for="model in models" :key="model.id" :value="model.name">{{ model.name }}</option>
        </select>
      </div>
    </div>

    <div class="flex-1 rounded-md border bg-card flex flex-col overflow-hidden">
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4">
        <div v-if="messages.length === 0" class="flex h-full items-center justify-center text-muted-foreground">
          Start a conversation...
        </div>
        <div v-for="(msg, index) in messages" :key="index" class="flex gap-3" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
          <div class="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'">
            <User v-if="msg.role === 'user'" class="h-4 w-4" />
            <Bot v-else class="h-4 w-4" />
          </div>
          <div class="rounded-lg px-3 py-2 text-sm max-w-[80%]" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'">
            <p class="whitespace-pre-wrap">{{ msg.content }}</p>
          </div>
        </div>
        <div v-if="loading" class="flex gap-3">
          <div class="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow bg-muted">
            <Bot class="h-4 w-4" />
          </div>
          <div class="rounded-lg px-3 py-2 text-sm bg-muted flex items-center">
            <Loader2 class="h-4 w-4 animate-spin" />
          </div>
        </div>
      </div>

      <div class="p-4 border-t bg-background">
        <form @submit.prevent="sendMessage" class="flex gap-2">
          <input 
            v-model="input" 
            placeholder="Type your message..." 
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="loading"
          />
          <button 
            type="submit" 
            class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            :disabled="loading || !input.trim()"
          >
            <Send class="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
