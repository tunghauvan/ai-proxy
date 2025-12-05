<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import api from '../api/client'
import {
  ArrowLeft,
  Database,
  FileText,
  Upload,
  Search,
  RefreshCw,
  Trash2,
  File,
  Plus,
  BarChart3,
  X
} from 'lucide-vue-next'
import { Breadcrumbs } from '../components'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const kb = ref(null)
const loading = ref(true)
const stats = ref(null)
const activeTab = ref('documents')

// Documents state
const documents = ref([])
const docsLoading = ref(false)
const docsPagination = ref({ limit: 50, offset: 0, total: 0 })

// Search state
const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const searchTopK = ref(5)

// Import state
const showImportModal = ref(false)
const importType = ref('text') // 'text' or 'documents'
const importText = ref('')
const importSource = ref('')
const importDocuments = ref([{ content: '', source: '' }])
const importing = ref(false)

// Folder Sync state
const showSyncModal = ref(false)
const syncForm = ref({
  folderPath: '',
  extensions: 'txt,md,pdf',
  recursive: true,
  clearBefore: false
})
const syncing = ref(false)
const syncResults = ref(null)

// Document Detail state
const showDocumentModal = ref(false)
const selectedDocument = ref(null)

const tabs = [
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'search', label: 'Search Test', icon: Search },
  { id: 'import', label: 'Import', icon: Upload },
  { id: 'stats', label: 'Statistics', icon: BarChart3 }
]

// Computed breadcrumb items including current tab
const breadcrumbItems = computed(() => {
  const items = []
  
  // Add KB name
  if (kb.value) {
    items.push({
      label: kb.value.name,
      path: null
    })
  }
  
  // Add current tab
  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (currentTab) {
    items.push({
      label: currentTab.label,
      onClick: null
    })
  }
  
  return items
})

const fetchKB = async () => {
  loading.value = true
  try {
    const response = await api.getKB(route.params.id)
    kb.value = response.data
    await Promise.all([fetchStats(), fetchDocuments()])
  } catch (error) {
    console.error('Error fetching KB:', error)
    toast.error('Failed to fetch Knowledge Base')
    router.push('/kb')
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const response = await api.getKBStats(route.params.id)
    stats.value = response.data
  } catch (error) {
    console.error('Error fetching stats:', error)
  }
}

const fetchDocuments = async () => {
  docsLoading.value = true
  try {
    const response = await api.getKBDocuments(
      route.params.id, 
      docsPagination.value.limit, 
      docsPagination.value.offset
    )
    documents.value = response.data.documents || []
    docsPagination.value.total = response.data.total_count || 0
  } catch (error) {
    console.error('Error fetching documents:', error)
  } finally {
    docsLoading.value = false
  }
}

const loadMoreDocuments = () => {
  docsPagination.value.offset += docsPagination.value.limit
  fetchDocuments()
}

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    toast.warning('Please enter a search query')
    return
  }
  
  searchLoading.value = true
  searchResults.value = []
  try {
    const response = await api.searchKB(route.params.id, searchQuery.value, searchTopK.value)
    searchResults.value = response.data.results || []
    if (searchResults.value.length === 0) {
      toast.info('No results found')
    }
  } catch (error) {
    console.error('Error searching:', error)
    toast.error('Search failed')
  } finally {
    searchLoading.value = false
  }
}

const openImportModal = (type) => {
  importType.value = type
  importText.value = ''
  importSource.value = ''
  importDocuments.value = [{ content: '', source: '' }]
  showImportModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const addImportDocument = () => {
  importDocuments.value.push({ content: '', source: '' })
}

const removeImportDocument = (index) => {
  if (importDocuments.value.length > 1) {
    importDocuments.value.splice(index, 1)
  }
}

const performImport = async () => {
  importing.value = true
  try {
    if (importType.value === 'text') {
      if (!importText.value.trim()) {
        toast.warning('Please enter text to import')
        return
      }
      const texts = [importText.value]
      const sources = importSource.value ? [importSource.value] : null
      await api.importTexts(route.params.id, texts, sources)
      toast.success('Text imported successfully')
    } else {
      const validDocs = importDocuments.value.filter(d => d.content.trim())
      if (validDocs.length === 0) {
        toast.warning('Please add at least one document')
        return
      }
      await api.importDocuments(route.params.id, validDocs)
      toast.success(`${validDocs.length} document(s) imported successfully`)
    }
    
    showImportModal.value = false
    await Promise.all([fetchStats(), fetchDocuments()])
  } catch (error) {
    console.error('Error importing:', error)
    toast.error(error.response?.data?.detail || 'Import failed')
  } finally {
    importing.value = false
  }
}

const clearKB = async () => {
  if (!confirm('Are you sure you want to clear all documents? This cannot be undone.')) return
  try {
    await api.clearKB(route.params.id)
    toast.success('Knowledge Base cleared')
    await Promise.all([fetchStats(), fetchDocuments()])
  } catch (error) {
    console.error('Error clearing KB:', error)
    toast.error('Failed to clear Knowledge Base')
  }
}

const reloadKB = async () => {
  try {
    await api.reloadKB(route.params.id)
    toast.success('Knowledge Base reloaded')
    await fetchStats()
  } catch (error) {
    console.error('Error reloading KB:', error)
    toast.error('Failed to reload Knowledge Base')
  }
}

// Folder Sync functions
const openSyncModal = () => {
  syncForm.value = {
    folderPath: '',
    extensions: 'txt,md,pdf',
    recursive: true,
    clearBefore: false
  }
  syncResults.value = null
  showSyncModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const performFolderSync = async () => {
  if (!syncForm.value.folderPath.trim()) {
    toast.warning('Please enter a folder path')
    return
  }
  
  syncing.value = true
  syncResults.value = null
  try {
    const response = await api.syncKBFolder(route.params.id, {
      folder_path: syncForm.value.folderPath,
      extensions: syncForm.value.extensions.split(',').map(e => e.trim()),
      recursive: syncForm.value.recursive,
      clear_before: syncForm.value.clearBefore
    })
    syncResults.value = response.data
    toast.success(`Synced ${response.data.documents_synced || 0} documents`)
    await Promise.all([fetchStats(), fetchDocuments()])
  } catch (error) {
    console.error('Error syncing folder:', error)
    toast.error(error.response?.data?.detail || 'Folder sync failed')
  } finally {
    syncing.value = false
  }
}

const hasMoreDocs = computed(() => {
  return docsPagination.value.offset + documents.value.length < docsPagination.value.total
})

const closeImportModal = () => {
  showImportModal.value = false
  importText.value = ''
  importSource.value = ''
  importDocuments.value = [{ content: '', source: '' }]

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const closeSyncModal = () => {
  showSyncModal.value = false
  syncForm.value = {
    folderPath: '',
    extensions: 'txt,md,pdf',
    recursive: true,
    clearBefore: false
  }
  syncResults.value = null

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const openDocumentModal = (doc) => {
  selectedDocument.value = doc
  showDocumentModal.value = true

  // Add keyboard event listener for Escape key
  document.addEventListener('keydown', handleKeyDown)
}

const closeDocumentModal = () => {
  showDocumentModal.value = false
  selectedDocument.value = null

  // Remove keyboard event listener
  document.removeEventListener('keydown', handleKeyDown)
}

const handleKeyDown = (event) => {
  if (event.key === 'Escape') {
    if (showImportModal.value) {
      closeImportModal()
    } else if (showSyncModal.value) {
      closeSyncModal()
    } else if (showDocumentModal.value) {
      closeDocumentModal()
    }
  }
}

const handleBackdropClick = (event, modalType) => {
  if (event.target === event.currentTarget) {
    if (modalType === 'import') {
      closeImportModal()
    } else if (modalType === 'sync') {
      closeSyncModal()
    } else if (modalType === 'document') {
      closeDocumentModal()
    }
  }
}

onMounted(() => {
  fetchKB()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <Breadcrumbs :items="breadcrumbItems" />
        <div v-if="kb" class="flex items-center space-x-2 ml-4">
          <span class="text-sm text-muted-foreground font-mono">{{ kb.collection }}</span>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="openSyncModal"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
        >
          <Upload class="mr-2 h-4 w-4" />
          Sync Folder
        </button>
        <button
          @click="reloadKB"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
        >
          <RefreshCw class="mr-2 h-4 w-4" />
          Reload
        </button>
        <button
          @click="clearKB"
          class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground h-10 px-4 py-2"
        >
          <Trash2 class="mr-2 h-4 w-4" />
          Clear All
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="text-muted-foreground">Loading...</div>
    </div>

    <!-- Content -->
    <div v-else-if="kb" class="space-y-6">
      <!-- Stats Cards -->
      <div class="grid gap-4 md:grid-cols-4">
        <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
          <div class="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 class="tracking-tight text-sm font-medium">Documents</h3>
            <FileText class="h-4 w-4 text-muted-foreground" />
          </div>
          <div class="text-2xl font-bold">{{ stats?.document_count || 0 }}</div>
        </div>
        <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
          <div class="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 class="tracking-tight text-sm font-medium">Status</h3>
            <Database class="h-4 w-4 text-muted-foreground" />
          </div>
          <div class="text-2xl font-bold capitalize">{{ stats?.status || 'unknown' }}</div>
        </div>
        <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
          <div class="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 class="tracking-tight text-sm font-medium">Collection</h3>
            <Database class="h-4 w-4 text-muted-foreground" />
          </div>
          <div class="text-lg font-bold font-mono truncate">{{ kb.collection }}</div>
        </div>
        <div class="rounded-xl border bg-card text-card-foreground shadow-sm p-6">
          <div class="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 class="tracking-tight text-sm font-medium">Embedding</h3>
            <BarChart3 class="h-4 w-4 text-muted-foreground" />
          </div>
          <div class="text-sm font-medium truncate">{{ stats?.embedding_model || kb.embedding_model || 'Default' }}</div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b">
        <nav class="flex space-x-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            ]"
          >
            <component :is="tab.icon" class="h-4 w-4" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="space-y-6">
        <!-- Documents Tab -->
        <div v-if="activeTab === 'documents'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Documents ({{ docsPagination.total }})</h3>
            <button
              @click="openImportModal('documents')"
              class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4"
            >
              <Plus class="mr-2 h-4 w-4" />
              Add Documents
            </button>
          </div>

          <div v-if="docsLoading" class="text-center py-8">
            <div class="text-muted-foreground">Loading documents...</div>
          </div>

          <div v-else-if="documents.length === 0" class="text-center py-12 border rounded-lg bg-card">
            <FileText class="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 class="text-lg font-semibold mb-2">No Documents</h3>
            <p class="text-muted-foreground mb-4">Import documents to start building your knowledge base.</p>
            <button
              @click="openImportModal('text')"
              class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4"
            >
              <Upload class="mr-2 h-4 w-4" />
              Import Content
            </button>
          </div>

          <div v-else class="space-y-2">
            <div 
              v-for="doc in documents" 
              :key="doc.id" 
              class="p-4 border rounded-lg bg-card hover:bg-muted/50 cursor-pointer"
              @click="openDocumentModal(doc)"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center space-x-2">
                  <File class="h-4 w-4 text-muted-foreground" />
                  <span class="font-medium text-sm">{{ doc.source || 'Unknown source' }}</span>
                </div>
                <span class="text-xs text-muted-foreground font-mono">
                  {{ typeof doc.id === 'string' ? doc.id.substring(0, 12) : doc.id }}...
                </span>
              </div>
              <p class="text-sm text-muted-foreground line-clamp-3">{{ doc.content }}</p>
            </div>

            <div v-if="hasMoreDocs" class="text-center pt-4">
              <button
                @click="loadMoreDocuments"
                class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-6"
              >
                Load More
              </button>
            </div>
          </div>
        </div>

        <!-- Search Tab -->
        <div v-if="activeTab === 'search'" class="space-y-4">
          <div class="rounded-xl border bg-card p-6">
            <h3 class="text-lg font-semibold mb-4">Test Search</h3>
            <p class="text-sm text-muted-foreground mb-4">
              Test the semantic search functionality of this knowledge base.
            </p>

            <div class="space-y-4">
              <div class="flex gap-4">
                <div class="flex-1">
                  <input
                    v-model="searchQuery"
                    @keyup.enter="performSearch"
                    placeholder="Enter your search query..."
                    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  />
                </div>
                <div class="w-24">
                  <select
                    v-model="searchTopK"
                    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option :value="3">Top 3</option>
                    <option :value="5">Top 5</option>
                    <option :value="10">Top 10</option>
                  </select>
                </div>
                <button
                  @click="performSearch"
                  :disabled="searchLoading"
                  class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-6 disabled:opacity-50"
                >
                  <Search class="mr-2 h-4 w-4" />
                  {{ searchLoading ? 'Searching...' : 'Search' }}
                </button>
              </div>

              <!-- Search Results -->
              <div v-if="searchResults.length > 0" class="space-y-3 mt-6">
                <h4 class="font-medium">Results ({{ searchResults.length }})</h4>
                <div 
                  v-for="(result, index) in searchResults" 
                  :key="index"
                  class="p-4 border rounded-lg bg-muted/30"
                >
                  <div class="flex justify-between items-start mb-2">
                    <span class="font-medium text-sm flex items-center">
                      <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs mr-2">
                        {{ index + 1 }}
                      </span>
                      {{ result.source || 'Unknown' }}
                    </span>
                    <span v-if="result.score" class="text-xs text-muted-foreground">
                      Score: {{ result.score.toFixed(4) }}
                    </span>
                  </div>
                  <p class="text-sm">{{ result.content }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Import Tab -->
        <div v-if="activeTab === 'import'" class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div 
              @click="openImportModal('text')"
              class="rounded-xl border bg-card p-6 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div class="flex items-center space-x-4 mb-4">
                <div class="p-3 bg-primary/10 rounded-lg">
                  <FileText class="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 class="font-semibold">Import Text</h3>
                  <p class="text-sm text-muted-foreground">Paste text content directly</p>
                </div>
              </div>
              <p class="text-sm text-muted-foreground">
                Import raw text content. The text will be automatically chunked and embedded.
              </p>
            </div>

            <div 
              @click="openImportModal('documents')"
              class="rounded-xl border bg-card p-6 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div class="flex items-center space-x-4 mb-4">
                <div class="p-3 bg-primary/10 rounded-lg">
                  <Upload class="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 class="font-semibold">Import Documents</h3>
                  <p class="text-sm text-muted-foreground">Add multiple documents with sources</p>
                </div>
              </div>
              <p class="text-sm text-muted-foreground">
                Import multiple documents with custom source labels for better organization.
              </p>
            </div>
          </div>
        </div>

        <!-- Stats Tab -->
        <div v-if="activeTab === 'stats'" class="space-y-4">
          <div class="rounded-xl border bg-card p-6">
            <h3 class="text-lg font-semibold mb-4">Knowledge Base Statistics</h3>
            
            <div class="space-y-4">
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Name</label>
                  <p class="text-lg font-medium">{{ kb.name }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Collection</label>
                  <p class="text-lg font-medium font-mono">{{ kb.collection }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Description</label>
                  <p class="text-lg">{{ kb.description || 'No description' }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Embedding Model</label>
                  <p class="text-lg font-medium">{{ stats?.embedding_model || kb.embedding_model || 'Default' }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Document Count</label>
                  <p class="text-lg font-medium">{{ stats?.document_count || 0 }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Status</label>
                  <p class="text-lg font-medium capitalize">{{ stats?.status || 'Unknown' }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Qdrant Host</label>
                  <p class="text-lg font-medium font-mono">{{ stats?.qdrant_host || 'N/A' }}:{{ stats?.qdrant_port || 'N/A' }}</p>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-muted-foreground">Created</label>
                  <p class="text-lg font-medium">{{ kb.created_at ? new Date(kb.created_at).toLocaleDateString() : 'N/A' }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Import Modal -->
    <div v-if="showImportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'import')">
      <div class="w-full max-w-2xl rounded-lg border bg-card p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">
            {{ importType === 'text' ? 'Import Text' : 'Import Documents' }}
          </h3>
          <button @click="closeImportModal" class="p-1 hover:bg-accent rounded-md">
            <X class="h-4 w-4" />
          </button>
        </div>

        <div v-if="importType === 'text'" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">Source Name (Optional)</label>
            <input
              v-model="importSource"
              placeholder="e.g., documentation, faq, manual"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium">Text Content *</label>
            <textarea
              v-model="importText"
              rows="10"
              placeholder="Paste your text content here..."
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[200px]"
            ></textarea>
          </div>
        </div>

        <div v-else class="space-y-4">
          <div v-for="(doc, index) in importDocuments" :key="index" class="p-4 border rounded-lg space-y-3">
            <div class="flex items-center justify-between">
              <span class="font-medium text-sm">Document {{ index + 1 }}</span>
              <button 
                v-if="importDocuments.length > 1"
                @click="removeImportDocument(index)"
                class="p-1 hover:bg-accent rounded-md text-destructive"
              >
                <X class="h-4 w-4" />
              </button>
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium">Source</label>
              <input
                v-model="doc.source"
                placeholder="e.g., file.pdf, manual, FAQ"
                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium">Content *</label>
              <textarea
                v-model="doc.content"
                rows="4"
                placeholder="Document content..."
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              ></textarea>
            </div>
          </div>
          
          <button
            @click="addImportDocument"
            class="w-full inline-flex items-center justify-center rounded-md text-sm font-medium border border-dashed border-input bg-background hover:bg-accent hover:text-accent-foreground h-10"
          >
            <Plus class="mr-2 h-4 w-4" />
            Add Another Document
          </button>
        </div>

        <div class="flex justify-end space-x-2 pt-4 mt-4 border-t">
          <button
            @click="showImportModal = false"
            class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4"
          >
            Cancel
          </button>
          <button
            @click="performImport"
            :disabled="importing"
            class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 disabled:opacity-50"
          >
            <Upload class="mr-2 h-4 w-4" />
            {{ importing ? 'Importing...' : 'Import' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Folder Sync Modal -->
    <div v-if="showSyncModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'sync')">
      <div class="w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Sync Folder</h3>
          <button @click="closeSyncModal" class="p-1 hover:bg-accent rounded-md">
            <X class="h-4 w-4" />
          </button>
        </div>

        <div class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-medium">Folder Path *</label>
            <input
              v-model="syncForm.folderPath"
              placeholder="/path/to/documents/folder"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <p class="text-xs text-muted-foreground">Server-side path to the folder containing documents</p>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium">File Extensions</label>
            <input
              v-model="syncForm.extensions"
              placeholder="txt,md,pdf"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <p class="text-xs text-muted-foreground">Comma-separated list of file extensions to include</p>
          </div>

          <div class="flex items-center gap-6">
            <div class="flex items-center space-x-2">
              <input type="checkbox" v-model="syncForm.recursive" id="recursive" class="h-4 w-4 rounded border-primary text-primary ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />
              <label for="recursive" class="text-sm font-medium">Recursive (include subfolders)</label>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <input type="checkbox" v-model="syncForm.clearBefore" id="clearBefore" class="h-4 w-4 rounded border-destructive text-destructive ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2" />
            <label for="clearBefore" class="text-sm font-medium text-destructive">Clear KB before sync</label>
          </div>

          <!-- Sync Results -->
          <div v-if="syncResults" class="rounded-md border p-4 space-y-2 bg-muted/50">
            <h4 class="font-medium">Sync Results</h4>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-muted-foreground">Files Found:</span>
                <span class="ml-2 font-medium">{{ syncResults.files_found || 0 }}</span>
              </div>
              <div>
                <span class="text-muted-foreground">Documents Synced:</span>
                <span class="ml-2 font-medium">{{ syncResults.documents_synced || 0 }}</span>
              </div>
              <div>
                <span class="text-muted-foreground">Chunks Created:</span>
                <span class="ml-2 font-medium">{{ syncResults.chunks_created || 0 }}</span>
              </div>
              <div v-if="syncResults.errors">
                <span class="text-destructive">Errors:</span>
                <span class="ml-2 font-medium text-destructive">{{ syncResults.errors }}</span>
              </div>
            </div>
          </div>

          <div class="flex justify-end space-x-2 pt-4 border-t">
            <button
              @click="showSyncModal = false"
              class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4"
            >
              Close
            </button>
            <button
              @click="performFolderSync"
              :disabled="syncing || !syncForm.folderPath.trim()"
              class="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 disabled:opacity-50"
            >
              <RefreshCw v-if="syncing" class="mr-2 h-4 w-4 animate-spin" />
              <Upload v-else class="mr-2 h-4 w-4" />
              {{ syncing ? 'Syncing...' : 'Start Sync' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Document Detail Modal -->
    <div v-if="showDocumentModal" class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" @click="handleBackdropClick($event, 'document')">
      <div class="w-full max-w-4xl max-h-[80vh] rounded-lg border bg-card p-6 shadow-lg overflow-hidden flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">Document Details</h3>
          <button @click="closeDocumentModal" class="p-1 hover:bg-accent rounded-md">
            <X class="h-4 w-4" />
          </button>
        </div>

        <div v-if="selectedDocument" class="flex-1 overflow-auto">
          <div class="space-y-4">
            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <label class="text-sm font-medium text-muted-foreground">Source</label>
                <p class="text-lg font-medium">{{ selectedDocument.source || 'Unknown source' }}</p>
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-muted-foreground">ID</label>
                <p class="text-lg font-medium font-mono">{{ selectedDocument.id }}</p>
              </div>
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium text-muted-foreground">Content</label>
              <div class="rounded-md border bg-muted/50 p-4 max-h-96 overflow-auto">
                <pre class="text-sm whitespace-pre-wrap">{{ selectedDocument.content }}</pre>
              </div>
            </div>
          </div>
        </div>

        <div class="flex justify-end pt-4 border-t mt-4">
          <button
            @click="closeDocumentModal"
            class="inline-flex items-center justify-center rounded-md text-sm font-medium border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
