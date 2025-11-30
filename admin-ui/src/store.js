import { defineStore } from 'pinia'
import { ref } from 'vue'

const API_BASE = '/v1/admin'
const CHAT_API = '/v1/chat/completions'

export const useModelsStore = defineStore('models', () => {
  const models = ref([])
  const tools = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchModels() {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/models`)
      if (!res.ok) throw new Error(await res.text())
      models.value = await res.json()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTools() {
    try {
      const res = await fetch(`${API_BASE}/tools`)
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      tools.value = data.tools || []
    } catch (e) {
      console.error('Failed to fetch tools', e)
    }
  }

  async function createModel(payload) {
    const res = await fetch(`${API_BASE}/models`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(await res.text())
    const created = await res.json()
    models.value.push(created)
    return created
  }

  async function activateModel(modelId) {
    const res = await fetch(`${API_BASE}/models/${modelId}/activate`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    await fetchModels()
  }

  async function deactivateModel(modelId) {
    const res = await fetch(`${API_BASE}/models/${modelId}/deactivate`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    await fetchModels()
  }

  async function getModel(modelId) {
    const res = await fetch(`${API_BASE}/models/${modelId}`)
    if (!res.ok) throw new Error(await res.text())
    return await res.json()
  }

  async function updateModel(modelId, payload) {
    const res = await fetch(`${API_BASE}/models/${modelId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(await res.text())
    const updated = await res.json()
    const idx = models.value.findIndex(m => m.id === modelId)
    if (idx !== -1) models.value[idx] = updated
    return updated
  }

  async function deleteModel(modelId) {
    const res = await fetch(`${API_BASE}/models/${modelId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    models.value = models.value.filter(m => m.id !== modelId)
  }

  return { models, tools, loading, error, fetchModels, fetchTools, createModel, activateModel, deactivateModel, getModel, updateModel, deleteModel }
})

export const useChatStore = defineStore('chat', () => {
  // State
  const selectedModelName = ref('')
  const messages = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  // Actions
  function selectModel(name) {
    selectedModelName.value = name
  }

  async function sendMessage(content) {
    if (!content.trim() || isLoading.value) return

    // Add user message
    const userMessage = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString()
    }
    messages.value.push(userMessage)

    isLoading.value = true
    error.value = null

    try {
      // Build the messages array for the API (include conversation history)
      const apiMessages = messages.value.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const res = await fetch(CHAT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModelName.value,
          messages: apiMessages
        })
      })

      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(errorText || `Request failed with status ${res.status}`)
      }

      const data = await res.json()
      
      // Extract assistant message from response
      if (data.choices && data.choices.length > 0) {
        const assistantMessage = {
          role: 'assistant',
          content: data.choices[0].message.content,
          timestamp: new Date().toISOString()
        }
        messages.value.push(assistantMessage)
      }
    } catch (e) {
      error.value = e.message || 'Failed to send message'
      // Remove the user message if the request failed
      messages.value.pop()
    } finally {
      isLoading.value = false
    }
  }

  function clearChat() {
    messages.value = []
    error.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    selectedModelName,
    messages,
    isLoading,
    error,
    selectModel,
    sendMessage,
    clearChat,
    clearError
  }
})
