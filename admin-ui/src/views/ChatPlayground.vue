<template>
  <div class="playground">
    <div class="page-header">
      <div class="header-content">
        <h1>Playground</h1>
        <p class="subtitle">Test your models with interactive chat</p>
      </div>
      <div class="model-selector">
        <label for="model-select">Model</label>
        <select 
          id="model-select" 
          v-model="selectedModel" 
          class="form-select"
          :disabled="isLoading"
          @change="onModelChange"
        >
          <option v-for="model in models" :key="model.id" :value="model.name">
            {{ model.name }}{{ model.active ? ' (active)' : '' }}
          </option>
        </select>
        <span v-if="selectedModelInfo" class="model-meta" :title="modelTooltip">
          RAG: {{ selectedModelInfo.rag_settings.enabled ? 'On' : 'Off' }} · 
          {{ selectedModelInfo.tool_names.length }} tools
        </span>
      </div>
    </div>

    <div v-if="error" class="error-message">
      <span>{{ error }}</span>
      <button @click="clearError" class="close-btn">Dismiss</button>
    </div>

    <div class="chat-container" ref="chatContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <p>Start a conversation by typing a message below.</p>
      </div>
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        :class="['message', msg.role]"
      >
        <div class="message-label">{{ msg.role === 'user' ? 'You' : 'Assistant' }}</div>
        <div class="message-bubble">
          <div class="message-content">{{ msg.content }}</div>
          <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>
      <div v-if="isLoading" class="message assistant">
        <div class="message-label">Assistant</div>
        <div class="message-bubble typing">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    </div>

    <div class="chat-input-container">
      <textarea
        v-model="inputMessage"
        class="form-textarea"
        @keydown.enter.exact.prevent="sendMessage"
        :disabled="isLoading"
        placeholder="Type your message... (Enter to send)"
        rows="3"
        ref="inputField"
      ></textarea>
      <div class="input-actions">
        <button 
          @click="clearChat" 
          :disabled="messages.length === 0 || isLoading"
          class="btn btn-secondary"
        >
          Clear
        </button>
        <button 
          @click="sendMessage" 
          :disabled="!inputMessage.trim() || isLoading"
          class="btn btn-primary"
        >
          {{ isLoading ? 'Sending...' : 'Send' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useModelsStore, useChatStore } from '../store'

const modelsStore = useModelsStore()
const chatStore = useChatStore()

const { models } = storeToRefs(modelsStore)
const { messages, isLoading, error, selectedModelName } = storeToRefs(chatStore)

const inputMessage = ref('')
const chatContainer = ref(null)
const inputField = ref(null)

// Local selected model that syncs with store
const selectedModel = computed({
  get: () => selectedModelName.value,
  set: (val) => chatStore.selectModel(val)
})

// Get the full model info for the selected model
const selectedModelInfo = computed(() => {
  return models.value.find(m => m.name === selectedModel.value)
})

// Tooltip with model details
const modelTooltip = computed(() => {
  const info = selectedModelInfo.value
  if (!info) return ''
  return `RAG: ${info.rag_settings.enabled ? 'Enabled' : 'Disabled'}
Top K: ${info.rag_settings.top_k}
Collection: ${info.rag_settings.collection}
Tools: ${info.tool_names.join(', ') || 'None'}`
})

onMounted(async () => {
  await modelsStore.fetchModels()
  // Set default model to the active one if not already set
  if (!selectedModelName.value && models.value.length > 0) {
    const activeModel = models.value.find(m => m.active)
    chatStore.selectModel(activeModel ? activeModel.name : models.value[0].name)
  }
  focusInput()
})

// Auto-scroll to bottom when new messages arrive
watch(messages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

watch(isLoading, async (loading) => {
  if (loading) {
    await nextTick()
    scrollToBottom()
  }
})

function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function focusInput() {
  if (inputField.value) {
    inputField.value.focus()
  }
}

function onModelChange() {
  // Clear chat when model changes (optional, can be removed)
  // chatStore.clearChat()
  focusInput()
}

async function sendMessage() {
  const content = inputMessage.value.trim()
  if (!content || isLoading.value) return
  
  inputMessage.value = ''
  await chatStore.sendMessage(content)
  focusInput()
}

function clearChat() {
  chatStore.clearChat()
  focusInput()
}

function clearError() {
  chatStore.clearError()
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.playground {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  min-height: 400px;
}

.header-content h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 0.25rem 0;
  color: #212529;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.model-selector label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #495057;
}

.model-selector select {
  min-width: 180px;
}

.model-meta {
  font-size: 0.75rem;
  color: #6c757d;
  cursor: help;
}

.error-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.close-btn {
  background: none;
  border: none;
  font-size: 0.8125rem;
  cursor: pointer;
  color: #842029;
  padding: 0.25rem 0.5rem;
  font-weight: 600;
}

.close-btn:hover {
  text-decoration: underline;
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1.5rem;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6c757d;
  font-size: 0.875rem;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 0.375rem;
}

.message.user .message-label {
  text-align: right;
}

.message-bubble {
  padding: 0.875rem 1rem;
  border-radius: 8px;
  position: relative;
}

.message.user .message-bubble {
  background: #212529;
  color: #fff;
}

.message.assistant .message-bubble {
  background: #fff;
  border: 1px solid #e9ecef;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.875rem;
  line-height: 1.5;
}

.message-time {
  font-size: 0.6875rem;
  opacity: 0.6;
  margin-top: 0.5rem;
}

.message.user .message-time {
  text-align: right;
}

.message.assistant .message-time {
  color: #6c757d;
}

.typing {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.875rem 1rem;
}

.typing .dot {
  width: 6px;
  height: 6px;
  background: #6c757d;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing .dot:nth-child(1) { animation-delay: -0.32s; }
.typing .dot:nth-child(2) { animation-delay: -0.16s; }
.typing .dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-input-container {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

@media (max-width: 640px) {
  .playground {
    height: calc(100vh - 160px);
  }
  
  .page-header {
    flex-direction: column;
  }
  
  .model-selector {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .model-selector select {
    flex: 1;
    min-width: 0;
  }
  
  .message {
    max-width: 85%;
  }
}
</style>
