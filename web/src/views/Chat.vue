<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import api, { axiosInstance } from '../api/client'
import { Send, Bot, User, Loader2, Settings2, Trash2, MessageSquare } from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const models = ref([])
const selectedModel = ref('')
const kbs = ref([])
const selectedKB = ref('')
const messagesContainer = ref(null)
const streamingEnabled = ref(true)
const showSettings = ref(false)
const systemMessage = ref('')
const currentStreamingMessage = ref('')

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

const clearChat = () => {
  messages.value = []
  currentStreamingMessage.value = ''
}

const sendMessage = async () => {
  if (!input.value.trim() || loading.value) return

  const userMessage = input.value
  messages.value.push({ role: 'user', content: userMessage })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    // Build messages array for API
    const apiMessages = []
    if (systemMessage.value.trim()) {
      apiMessages.push({ role: 'system', content: systemMessage.value })
    }
    apiMessages.push(...messages.value.map(m => ({
      role: m.role,
      content: m.content
    })))

    const payload = {
      model: selectedModel.value,
      messages: apiMessages,
      stream: streamingEnabled.value
    }

    // Build headers
    const headers = {}
    if (selectedKB.value) {
      headers['X-KB-ID'] = selectedKB.value
    }

    if (streamingEnabled.value) {
      // Handle streaming response
      currentStreamingMessage.value = ''
      messages.value.push({ role: 'assistant', content: '', streaming: true })
      
      const response = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: JSON.stringify(payload)
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              // Finalize the streaming message
              const lastMessage = messages.value[messages.value.length - 1]
              lastMessage.streaming = false
              break
            }
            try {
              const parsed = JSON.parse(data)
              const content = parsed.choices?.[0]?.delta?.content || ''
              if (content) {
                currentStreamingMessage.value += content
                const lastMessage = messages.value[messages.value.length - 1]
                lastMessage.content = currentStreamingMessage.value
                scrollToBottom()
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } else {
      // Handle non-streaming response
      const response = await api.chatCompletion(payload, { headers })
      const assistantMessage = response.data.choices[0].message.content
      messages.value.push({ role: 'assistant', content: assistantMessage })
    }
  } catch (error) {
    console.error('Error sending message:', error)
    messages.value.push({ role: 'assistant', content: 'Error: Failed to get response.' })
  } finally {
    loading.value = false
    currentStreamingMessage.value = ''
    scrollToBottom()
  }
}

onMounted(() => {
  fetchModels()
  fetchKBs()
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-10rem)] max-w-5xl mx-auto w-full">
    <div class="flex items-center justify-between mb-6">
      <Breadcrumbs />
      <div class="flex gap-3 items-center">
        <!-- Settings Toggle -->
        <button 
          @click="showSettings = !showSettings"
          class="p-2 hover:bg-accent rounded-md"
          :class="showSettings ? 'bg-accent' : ''"
          title="Chat Settings"
        >
          <Settings2 class="h-5 w-5" />
        </button>
        
        <!-- Clear Chat -->
        <button 
          @click="clearChat"
          class="p-2 hover:bg-accent rounded-md text-muted-foreground hover:text-destructive"
          title="Clear Chat"
          :disabled="messages.length === 0"
        >
          <Trash2 class="h-5 w-5" />
        </button>

        <!-- KB Selection -->
        <div class="relative">
          <select v-model="selectedKB" class="h-9 w-[200px] rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
            <option value="">No Knowledge Base</option>
            <option v-for="kb in kbs" :key="kb.id" :value="kb.id">{{ kb.name }}</option>
          </select>
        </div>
        
        <!-- Model Selection -->
        <div class="relative">
          <select v-model="selectedModel" class="h-9 w-[200px] rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
            <option v-for="model in models" :key="model.id" :value="model.name">{{ model.name }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Settings Panel -->
    <div v-if="showSettings" class="mb-4 p-4 rounded-lg border bg-card space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="font-medium">Chat Settings</h3>
        <div class="flex items-center space-x-2">
          <input type="checkbox" v-model="streamingEnabled" id="streaming" class="h-4 w-4 rounded border-primary text-primary" />
          <label for="streaming" class="text-sm font-medium">Enable Streaming</label>
        </div>
      </div>
      <div class="space-y-2">
        <label class="text-sm font-medium">System Message</label>
        <textarea 
          v-model="systemMessage" 
          placeholder="Enter a system message to set the AI's behavior..."
          rows="2"
          class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        ></textarea>
      </div>
    </div>

    <div class="flex-1 rounded-xl border bg-card shadow-sm flex flex-col overflow-hidden">
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-6">
        <div v-if="messages.length === 0" class="flex h-full flex-col items-center justify-center text-muted-foreground space-y-4">
          <div class="p-4 rounded-full bg-muted/50">
            <MessageSquare class="h-8 w-8" />
          </div>
          <p>Start a conversation with the AI assistant</p>
          <p v-if="selectedKB" class="text-xs">Using Knowledge Base: {{ kbs.find(k => k.id === selectedKB)?.name }}</p>
        </div>
        <div v-for="(msg, index) in messages" :key="index" class="flex gap-4" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
          <div class="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow-sm" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'">
            <User v-if="msg.role === 'user'" class="h-4 w-4" />
            <Bot v-else class="h-4 w-4" />
          </div>
          <div class="rounded-lg px-4 py-3 text-sm max-w-[80%] shadow-sm" :class="msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted/50 border'">
            <p class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</p>
            <span v-if="msg.streaming" class="inline-block w-2 h-4 bg-current animate-pulse ml-1"></span>
          </div>
        </div>
        <div v-if="loading && !streamingEnabled" class="flex gap-4">
          <div class="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow-sm bg-muted">
            <Bot class="h-4 w-4" />
          </div>
          <div class="rounded-lg px-4 py-3 text-sm bg-muted/50 border flex items-center">
            <Loader2 class="h-4 w-4 animate-spin" />
          </div>
        </div>
      </div>

      <div class="p-4 border-t bg-background/50 backdrop-blur supports-[backdrop-filter]:bg-background/50">
        <form @submit.prevent="sendMessage" class="flex gap-3 max-w-4xl mx-auto">
          <input 
            v-model="input" 
            placeholder="Type your message..." 
            class="flex h-11 w-full rounded-md border border-input bg-background px-4 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 shadow-sm"
            :disabled="loading"
          />
          <button 
            type="submit" 
            class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-11 px-6 shadow-sm"
            :disabled="loading || !input.trim()"
          >
            <Send class="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
