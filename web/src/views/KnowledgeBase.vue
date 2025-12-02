<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { Plus, Trash2, FileText, RefreshCw, Search } from 'lucide-vue-next'

const kbs = ref([])
const loading = ref(true)
const showCreateModal = ref(false)
const showDocsModal = ref(false)
const currentKB = ref(null)
const documents = ref([])
const docsLoading = ref(false)

const form = ref({
  name: '',
  description: '',
  collection: ''
})

const fetchKBs = async () => {
  loading.value = true
  try {
    const response = await api.getKBs()
    kbs.value = response.data
  } catch (error) {
    console.error('Error fetching KBs:', error)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  form.value = {
    name: '',
    description: '',
    collection: ''
  }
  showCreateModal.value = true
}

const createKB = async () => {
  try {
    await api.createKB(form.value)
    showCreateModal.value = false
    fetchKBs()
  } catch (error) {
    console.error('Error creating KB:', error)
    alert('Failed to create Knowledge Base')
  }
}

const deleteKB = async (id) => {
  if (!confirm('Are you sure you want to delete this Knowledge Base?')) return
  try {
    await api.deleteKB(id)
    fetchKBs()
  } catch (error) {
    console.error('Error deleting KB:', error)
  }
}

const clearKB = async (id) => {
  if (!confirm('Are you sure you want to clear all documents from this Knowledge Base?')) return
  try {
    await api.clearKB(id)
    alert('Knowledge Base cleared')
  } catch (error) {
    console.error('Error clearing KB:', error)
  }
}

const viewDocuments = async (kb) => {
  currentKB.value = kb
  showDocsModal.value = true
  docsLoading.value = true
  documents.value = []
  try {
    const response = await api.getKBDocuments(kb.id)
    documents.value = response.data.documents || []
  } catch (error) {
    console.error('Error fetching documents:', error)
  } finally {
    docsLoading.value = false
  }
}

onMounted(() => {
  fetchKBs()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-3xl font-bold tracking-tight">Knowledge Base</h2>
      <button 
        @click="openCreateModal"
        class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
      >
        <Plus class="mr-2 h-4 w-4" />
        Create KB
      </button>
    </div>

    <div class="rounded-md border bg-card">
      <div class="relative w-full overflow-auto">
        <table class="w-full caption-bottom text-sm">
          <thead class="[&_tr]:border-b">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Name</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Collection</th>
              <th class="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Description</th>
              <th class="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr v-if="loading">
              <td colspan="4" class="p-4 text-center">Loading...</td>
            </tr>
            <tr v-else-if="kbs.length === 0">
              <td colspan="4" class="p-4 text-center">No knowledge bases found</td>
            </tr>
            <tr v-else v-for="kb in kbs" :key="kb.id" class="border-b transition-colors hover:bg-muted/50">
              <td class="p-4 align-middle font-medium">{{ kb.name }}</td>
              <td class="p-4 align-middle font-mono text-xs">{{ kb.collection }}</td>
              <td class="p-4 align-middle text-muted-foreground">{{ kb.description }}</td>
              <td class="p-4 align-middle text-right">
                <div class="flex justify-end gap-2">
                  <button @click="viewDocuments(kb)" class="p-2 hover:bg-accent rounded-md" title="View Documents">
                    <FileText class="h-4 w-4" />
                  </button>
                  <button @click="clearKB(kb.id)" class="p-2 hover:bg-accent rounded-md" title="Clear Documents">
                    <RefreshCw class="h-4 w-4" />
                  </button>
                  <button @click="deleteKB(kb.id)" class="p-2 hover:bg-accent rounded-md text-destructive" title="Delete KB">
                    <Trash2 class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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
            <label class="text-sm font-medium leading-none">Name</label>
            <input v-model="form.name" required placeholder="My Knowledge Base" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
          </div>
          
          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Collection Name (Optional)</label>
            <input v-model="form.collection" placeholder="Auto-generated if empty" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium leading-none">Description</label>
            <input v-model="form.description" placeholder="Description of the knowledge base" class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50" />
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="showCreateModal = false" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
              Cancel
            </button>
            <button type="submit" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2">
              Create
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Documents Modal -->
    <div v-if="showDocsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div class="w-full max-w-4xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Documents: {{ currentKB?.name }}</h3>
          <button @click="showDocsModal = false" class="p-1 hover:bg-accent rounded-md">
            <span class="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
        
        <div class="flex-1 overflow-auto border rounded-md">
          <div v-if="docsLoading" class="p-8 text-center">Loading documents...</div>
          <div v-else-if="documents.length === 0" class="p-8 text-center">No documents found in this knowledge base.</div>
          <div v-else class="divide-y">
            <div v-for="doc in documents" :key="doc.id" class="p-4 hover:bg-muted/50">
              <div class="flex justify-between items-start mb-2">
                <span class="font-medium text-sm">{{ doc.source }}</span>
                <span class="text-xs text-muted-foreground font-mono">{{ doc.id.substring(0, 8) }}...</span>
              </div>
              <p class="text-sm text-muted-foreground line-clamp-3">{{ doc.content }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
