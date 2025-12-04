<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import { Plus, Trash2, RefreshCw, Settings, Database } from 'lucide-vue-next'

const router = useRouter()
const toast = useToast()

const kbs = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingKB = ref(null)

const form = ref({
  name: '',
  description: '',
  collection: '',
  embedding_model: ''
})

const fetchKBs = async () => {
  loading.value = true
  try {
    const response = await api.getKBs()
    kbs.value = response.data
  } catch (error) {
    console.error('Error fetching KBs:', error)
    toast.error('Failed to fetch knowledge bases')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  form.value = {
    name: '',
    description: '',
    collection: '',
    embedding_model: ''
  }
  showCreateModal.value = true
}

const openEditModal = (kb) => {
  editingKB.value = kb
  form.value = {
    name: kb.name,
    description: kb.description || '',
    collection: kb.collection || '',
    embedding_model: kb.embedding_model || ''
  }
  showEditModal.value = true
}

const createKB = async () => {
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description || null,
      collection: form.value.collection || null,
      embedding_model: form.value.embedding_model || null
    }
    await api.createKB(payload)
    showCreateModal.value = false
    toast.success('Knowledge Base created successfully')
    fetchKBs()
  } catch (error) {
    console.error('Error creating KB:', error)
    toast.error(error.response?.data?.detail || 'Failed to create Knowledge Base')
  }
}

const updateKB = async () => {
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description || null,
      collection: form.value.collection || null,
      embedding_model: form.value.embedding_model || null
    }
    await api.updateKB(editingKB.value.id, payload)
    showEditModal.value = false
    editingKB.value = null
    toast.success('Knowledge Base updated successfully')
    fetchKBs()
  } catch (error) {
    console.error('Error updating KB:', error)
    toast.error(error.response?.data?.detail || 'Failed to update Knowledge Base')
  }
}

const deleteKB = async (kb) => {
  if (!confirm(`Are you sure you want to delete "${kb.name}"? This will also delete all documents.`)) return
  try {
    await api.deleteKB(kb.id)
    toast.success('Knowledge Base deleted')
    fetchKBs()
  } catch (error) {
    console.error('Error deleting KB:', error)
    toast.error(error.response?.data?.detail || 'Failed to delete Knowledge Base')
  }
}

const clearKB = async (kb) => {
  if (!confirm(`Are you sure you want to clear all documents from "${kb.name}"?`)) return
  try {
    await api.clearKB(kb.id)
    toast.success('Knowledge Base cleared')
  } catch (error) {
    console.error('Error clearing KB:', error)
    toast.error('Failed to clear Knowledge Base')
  }
}

const viewKBDetail = (kb) => {
  router.push(`/kb/${kb.id}`)
}

onMounted(() => {
  fetchKBs()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">Knowledge Base</h2>
        <p class="text-muted-foreground">Manage your RAG knowledge bases and documents</p>
      </div>
      <button 
        @click="openCreateModal"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <Plus class="mr-2 h-4 w-4" />
        Create Knowledge Base
      </button>
    </div>

    <!-- KB Cards Grid -->
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading knowledge bases...</div>
    </div>

    <div v-else-if="kbs.length === 0" class="text-center py-12 border rounded-lg bg-card">
      <Database class="mx-auto h-12 w-12 text-muted-foreground mb-4" />
      <h3 class="text-lg font-semibold mb-2">No Knowledge Bases</h3>
      <p class="text-muted-foreground mb-4">Create your first knowledge base to start storing documents.</p>
      <button 
        @click="openCreateModal"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <Plus class="mr-2 h-4 w-4" />
        Create Knowledge Base
      </button>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div 
        v-for="kb in kbs" 
        :key="kb.id" 
        class="rounded-xl border bg-card text-card-foreground shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        @click="viewKBDetail(kb)"
      >
        <div class="p-6">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center space-x-3">
              <div class="p-2 bg-primary/10 rounded-lg">
                <Database class="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 class="font-semibold">{{ kb.name }}</h3>
                <p class="text-xs text-muted-foreground font-mono">{{ kb.collection }}</p>
              </div>
            </div>
          </div>
          
          <p v-if="kb.description" class="text-sm text-muted-foreground mb-4 line-clamp-2">
            {{ kb.description }}
          </p>
          <p v-else class="text-sm text-muted-foreground mb-4 italic">No description</p>
          
          <div class="flex items-center justify-between pt-4 border-t">
            <span class="text-xs text-muted-foreground">
              {{ kb.embedding_model || 'Default embedding' }}
            </span>
            <div class="flex gap-1" @click.stop>
              <button 
                @click="openEditModal(kb)" 
                class="p-2 hover:bg-accent rounded-md" 
                title="Edit"
              >
                <Settings class="h-4 w-4" />
              </button>
              <button 
                @click="clearKB(kb)" 
                class="p-2 hover:bg-accent rounded-md" 
                title="Clear Documents"
              >
                <RefreshCw class="h-4 w-4" />
              </button>
              <button 
                @click="deleteKB(kb)" 
                class="p-2 hover:bg-accent rounded-md text-destructive" 
                title="Delete"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Create Knowledge Base</h3>
          <button @click="showCreateModal = false" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <form @submit.prevent="createKB" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Name *</label>
            <input 
              v-model="form.name" 
              required 
              placeholder="my-knowledge-base" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
            <p class="text-xs text-muted-foreground">Lowercase letters, numbers, underscores, hyphens only</p>
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Collection Name</label>
            <input 
              v-model="form.collection" 
              placeholder="Auto-generated if empty" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
            <p class="text-xs text-muted-foreground">Qdrant collection name</p>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Description</label>
            <textarea 
              v-model="form.description" 
              rows="2"
              placeholder="Description of the knowledge base" 
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            ></textarea>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Embedding Model</label>
            <input 
              v-model="form.embedding_model" 
              placeholder="Default model if empty" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button 
              type="button" 
              @click="showCreateModal = false" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Edit Knowledge Base</h3>
          <button @click="showEditModal = false; editingKB = null" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <form @submit.prevent="updateKB" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Name *</label>
            <input 
              v-model="form.name" 
              required 
              placeholder="my-knowledge-base" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Collection Name</label>
            <input 
              v-model="form.collection" 
              placeholder="Qdrant collection name" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Description</label>
            <textarea 
              v-model="form.description" 
              rows="2"
              placeholder="Description of the knowledge base" 
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            ></textarea>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Embedding Model</label>
            <input 
              v-model="form.embedding_model" 
              placeholder="Default model if empty" 
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" 
            />
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button 
              type="button" 
              @click="showEditModal = false; editingKB = null" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
            >
              Cancel
            </button>
            <button 
              type="submit" 
              class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
