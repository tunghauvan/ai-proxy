<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useModelsStore } from '../store'

// Types
interface RagSettings {
  enabled?: boolean
  knowledge_base?: string
  chunk_size?: number
  top_k?: number
}

interface Model {
  id: string
  name: string
  version?: string
  active: boolean
  enabled: boolean
  base_model?: string
  rag_settings?: RagSettings | null
  tool_names?: string[]
  model_params?: Record<string, any> | null
  created_at?: string
  updated_at?: string
  active_versions?: string[]
  version_count?: number
}

const store = useModelsStore()

// Persistence key
const VIEW_MODE_KEY = 'modelListViewMode'
function getInitialViewMode(): 'card' | 'table' {
  if (typeof window === 'undefined') return 'card'
  const v = window.localStorage.getItem(VIEW_MODE_KEY)
  return v === 'table' ? 'table' : 'card'
}

// Local state
const viewMode = ref<'card' | 'table'>(getInitialViewMode())
const activationLoading = ref<string | null>(null)
const deactivationLoading = ref<string | null>(null)
const deleteLoading = ref<string | null>(null)
const actionError = ref<string | null>(null)
const selectedColumns = ref({ base: true, rag: true, tools: true, params: true })
const columnDropdownOpen = ref(false)

// Tools bar state
const searchQuery = ref('')
const statusFilter = ref<'all' | 'active' | 'enabled' | 'disabled'>('all')

watch(viewMode, (v) => {
  if (typeof window !== 'undefined') window.localStorage.setItem(VIEW_MODE_KEY, v)
})

const displayedError = computed(() => actionError.value || store.error)

// Helpers
function getStatusLabel(model: Model) {
  if (model.active) return 'Active'
  if (model.enabled) return 'Enabled'
  return 'Disabled'
}

function getStatusClass(model: Model) {
  if (model.active) return 'status-active'
  if (model.enabled) return 'status-enabled'
  return 'status-disabled'
}

function formatParams(params: Record<string, any> | null | undefined): string {
  if (!params || Object.keys(params).length === 0) return 'Defaults'
  return Object.entries(params).map(([k, v]) => `${k}: ${v}`).join(', ')
}

function formatRagSettings(rag: RagSettings | null | undefined): string {
  if (!rag) return 'Not configured'
  if (!rag.enabled) return 'Disabled'
  const parts: string[] = ['Enabled']
  if (rag.knowledge_base) parts.push(`KB: ${rag.knowledge_base}`)
  if (rag.chunk_size) parts.push(`Chunk: ${rag.chunk_size}`)
  if (rag.top_k) parts.push(`Top-K: ${rag.top_k}`)
  return parts.join(', ')
}

function formatTools(tools: string[] | null | undefined): string {
  if (!tools || tools.length === 0) return 'None'
  return tools.join(', ')
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

// Actions
async function onActivate(m: Model) {
  activationLoading.value = m.id
  actionError.value = null
  try {
    await store.activateModel(m.id)
  } catch (e: any) {
    actionError.value = e.message || 'Failed to activate model'
  } finally {
    activationLoading.value = null
  }
}

async function onDeactivate(m: Model) {
  deactivationLoading.value = m.id
  actionError.value = null
  try {
    await store.deactivateModel(m.id)
  } catch (e: any) {
    actionError.value = e.message || 'Failed to deactivate model'
  } finally {
    deactivationLoading.value = null
  }
}

async function onDelete(m: Model) {
  if (!window.confirm('Are you sure you want to delete this model?')) return
  deleteLoading.value = m.id
  actionError.value = null
  try {
    await store.deleteModel(m.id)
  } catch (e: any) {
    actionError.value = e.message || 'Failed to delete model'
  } finally {
    deleteLoading.value = null
  }
}

function setViewMode(mode: 'card' | 'table') {
  viewMode.value = mode
}

function toggleColumnDropdown() { columnDropdownOpen.value = !columnDropdownOpen.value }
function closeColumnDropdown() { columnDropdownOpen.value = false }

function refreshModels() {
  actionError.value = null
  store.fetchModels()
}

// Filtering
const filteredModels = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return (store.models || [])
    .filter((m: Model) => {
      if (statusFilter.value === 'active' && !m.active) return false
      if (statusFilter.value === 'enabled' && !m.enabled) return false
      if (statusFilter.value === 'disabled' && (m.active || m.enabled)) return false
      if (!q) return true
      return (
        (m.name || '').toLowerCase().includes(q) ||
        (m.base_model || '').toLowerCase().includes(q) ||
        (m.tool_names || []).join(' ').toLowerCase().includes(q)
      )
    })
})

const selectedColumnsCount = computed(() => Object.values(selectedColumns.value).filter(Boolean).length)
const tableColspan = computed(() => 3 + selectedColumnsCount.value)

onMounted(() => {
  store.fetchModels()
})
</script>

<template>
  <div class="model-list full-width">
    <header class="page-header">
      <div>
        <h1>Model List</h1>
        <p class="subtitle">Review and manage configured AI models.</p>
      </div>
      <router-link to="/create" class="btn btn-primary">+ Create Model</router-link>
    </header>

    <!-- Tools bar -->
    <div class="toolbar">
      <div class="tools-left">
        <div class="search">
          <input type="search" v-model="searchQuery" placeholder="Search models, base model or tools..." class="form-input" aria-label="Search models" />
        </div>

        <div class="status-filter">
          <label>
            <select v-model="statusFilter" class="form-select" aria-label="Filter by status">
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </label>
        </div>

        <div class="column-selector" v-if="viewMode === 'table'">
          <button class="dropdown-toggle" @click="toggleColumnDropdown" type="button" :aria-expanded="columnDropdownOpen" aria-haspopup="true">Columns ▾</button>
          <div v-if="columnDropdownOpen" class="dropdown-menu" @mouseleave="closeColumnDropdown">
            <label class="dropdown-item"><input type="checkbox" v-model="selectedColumns.base" /> Base</label>
            <label class="dropdown-item"><input type="checkbox" v-model="selectedColumns.rag" /> RAG</label>
            <label class="dropdown-item"><input type="checkbox" v-model="selectedColumns.tools" /> Tools</label>
            <label class="dropdown-item"><input type="checkbox" v-model="selectedColumns.params" /> Params</label>
          </div>
        </div>
      </div>

      <div class="tools-right">
        <button class="btn btn-secondary" @click="refreshModels" type="button" aria-label="Refresh models">Refresh</button>
        <div class="view-toggle" role="group" aria-label="View mode">
          <button type="button" class="view-pill" :class="{ active: viewMode === 'card' }" @click="setViewMode('card')" :aria-pressed="viewMode === 'card'"><span class="view-icon">▦</span><span class="view-label">Card</span></button>
          <button type="button" class="view-pill" :class="{ active: viewMode === 'table' }" @click="setViewMode('table')" :aria-pressed="viewMode === 'table'"><span class="view-icon">≡</span><span class="view-label">Table</span></button>
        </div>
      </div>
    </div>

    <div v-if="displayedError" class="error-message" role="alert">{{ displayedError }}</div>

    <div v-if="store.loading" class="loading-indicator" aria-live="polite"><span class="spinner" aria-hidden="true"></span> Loading models...</div>

    <!-- Card view -->
    <div v-else-if="viewMode === 'card'" class="card-grid">
      <article v-for="model in filteredModels" :key="model.id" class="model-card">
        <header class="card-header">
          <div>
            <h2 class="model-name">{{ model.name }}</h2>
            <div class="model-meta">{{ model.base_model || 'Default' }} · {{ (model.tool_names || []).length }} tools</div>
          </div>
          <span :class="['status-badge', getStatusClass(model)]">{{ getStatusLabel(model) }}</span>
        </header>

        <div class="card-body">
          <div class="model-details">
            <div class="detail-row"><dt>RAG</dt><dd>{{ formatRagSettings(model.rag_settings) }}</dd></div>
            <div class="detail-row"><dt>Tools</dt><dd>{{ formatTools(model.tool_names) }}</dd></div>
            <div class="detail-row"><dt>Parameters</dt><dd>{{ formatParams(model.model_params) }}</dd></div>
          </div>
        </div>

        <footer class="card-actions">
          <router-link :to="`/models/${model.id}`" class="icon-button icon-button-secondary" aria-label="View model details" title="View Details"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 3l6 5-6 5" /></svg><span class="sr-only">View</span></router-link>

          <button v-if="!model.active" class="icon-button icon-button-success" :disabled="activationLoading === model.id" @click="onActivate(model)" type="button" aria-label="Activate model">
            <span v-if="activationLoading === model.id" class="spinner-small" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 4v8" /><path d="M4 8h8" /></svg>
          </button>

          <button v-else class="icon-button icon-button-warning" :disabled="deactivationLoading === model.id" @click="onDeactivate(model)" type="button" aria-label="Deactivate model">
            <span v-if="deactivationLoading === model.id" class="spinner-small" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 8h8" /></svg>
          </button>

          <button class="icon-button icon-button-danger" :disabled="deleteLoading === model.id" @click="onDelete(model)" type="button" aria-label="Delete model">
            <span v-if="deleteLoading === model.id" class="spinner-small" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 5h8" /><path d="M6.5 5V3.5h3V5" /><path d="M5.5 7v6" /><path d="M10.5 7v6" /></svg>
          </button>
        </footer>
      </article>

      <div v-if="filteredModels.length === 0" class="empty-state">No models found.</div>
    </div>

    <!-- Table view -->
    <div v-else class="table-container">
      <table class="model-table" aria-label="Model list table">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Status</th>
            <th v-if="selectedColumns.base" scope="col">Base Model</th>
            <th v-if="selectedColumns.rag" scope="col">RAG</th>
            <th v-if="selectedColumns.tools" scope="col">Tools</th>
            <th v-if="selectedColumns.params" scope="col">Params</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="model in filteredModels" :key="model.id">
            <tr>
              <td>{{ model.name }}</td>
              <td><span :class="['status-badge', getStatusClass(model)]">{{ getStatusLabel(model) }}</span></td>
              <td v-if="selectedColumns.base">{{ model.base_model || 'Default' }}</td>
              <td v-if="selectedColumns.rag">{{ formatRagSettings(model.rag_settings) }}</td>
              <td v-if="selectedColumns.tools">{{ formatTools(model.tool_names) }}</td>
              <td v-if="selectedColumns.params">{{ formatParams(model.model_params) }}</td>
              <td class="actions-cell">
                <router-link :to="`/models/${model.id}`" class="icon-button icon-button-secondary" aria-label="View model details" title="View Details"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 3l6 5-6 5" /></svg></router-link>
                <button v-if="!model.active" class="icon-button icon-button-success" :disabled="activationLoading === model.id" @click="onActivate(model)" type="button" aria-label="Activate model"><span v-if="activationLoading === model.id" class="spinner-small" aria-hidden="true"></span><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 4v8" /><path d="M4 8h8" /></svg></button>
                <button v-else class="icon-button icon-button-warning" :disabled="deactivationLoading === model.id" @click="onDeactivate(model)" type="button" aria-label="Deactivate model"><span v-if="deactivationLoading === model.id" class="spinner-small" aria-hidden="true"></span><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 8h8" /></svg></button>
                <button class="icon-button icon-button-danger" :disabled="deleteLoading === model.id" @click="onDelete(model)" type="button" aria-label="Delete model"><span v-if="deleteLoading === model.id" class="spinner-small" aria-hidden="true"></span><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 5h8" /><path d="M6.5 5V3.5h3V5" /><path d="M5.5 7v6" /><path d="M10.5 7v6" /></svg></button>
              </td>
            </tr>
          </template>
          <tr v-if="filteredModels.length === 0">
            <td :colspan="tableColspan" class="empty-state">No models found.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
/* Full width layout */
.model-list.full-width { width: 100%; padding: 1.25rem; }

.toolbar { display:flex; justify-content:space-between; gap:1rem; align-items:center; flex-wrap:wrap; margin-bottom: 1.5rem; }
.tools-left { display:flex; gap:0.75rem; align-items:center }
.tools-right { display:flex; gap:0.5rem; align-items:center }

/* View Toggle */
.view-toggle {
  display: flex;
  background: #e9ecef;
  padding: 0.25rem;
  border-radius: 6px;
  gap: 0.25rem;
}

.view-pill {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border: none;
  background: transparent;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.15s;
}

.view-pill:hover {
  color: #212529;
}

.view-pill.active {
  background: #fff;
  color: #212529;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.view-icon { font-size: 1rem; line-height: 1; }

/* Column Selector */
.column-selector { position: relative; }
.dropdown-toggle {
  background: #fff;
  border: 1px solid #ced4da;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  color: #495057;
}
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.25rem;
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  padding: 0.5rem;
  z-index: 10;
  min-width: 150px;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
  border-radius: 4px;
}
.dropdown-item:hover { background: #f8f9fa; }

/* Card Grid */
.card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:1.5rem }
.model-card { background:#fff; border:1px solid #e9ecef; border-radius:8px; display:flex; flex-direction:column; overflow:hidden; transition: box-shadow 0.2s; }
.model-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-color: #dee2e6; }

.card-header { display:flex; justify-content:space-between; align-items:flex-start; padding:1.25rem; border-bottom:1px solid #f8f9fa }
.card-body{ padding:1.25rem; flex: 1; }
.card-actions{ display:flex; gap:0.5rem; justify-content:flex-end; padding:1rem 1.25rem; background:#f8f9fa; border-top: 1px solid #e9ecef; }

.model-name{ margin:0 0 0.25rem 0; font-weight:600; font-size: 1.125rem; color: #212529; }
.model-meta{ font-size:0.875rem; color:#6c757d }

.model-details { display: flex; flex-direction: column; gap: 0.75rem; }
.detail-row { display: flex; gap: 0.75rem; font-size: 0.875rem; border-bottom: 1px solid #f8f9fa; padding-bottom: 0.75rem; }
.detail-row:last-child { border-bottom: none; padding-bottom: 0; }
.detail-row dt { font-weight: 500; color: #6c757d; min-width: 80px; }
.detail-row dd { margin: 0; color: #212529; word-break: break-word; }

/* Version Badge */
.version-badge {
  display: inline-block;
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
  margin-left: 0.5rem;
  cursor: pointer;
  transition: background 0.2s;
}
.version-badge:hover {
  background: #bbdefb;
}

/* Version History Panel */
.version-history-panel {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}
.version-history-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  margin: 0 0 0.75rem 0;
}
.version-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.version-item {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 0.75rem;
}
.version-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.version-number {
  font-weight: 600;
  color: #212529;
}
.version-status {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 10px;
}
.version-active {
  background: #d4edda;
  color: #155724;
}
.version-inactive {
  background: #f8d7da;
  color: #721c24;
}
/* Table */
.table-container { overflow-x: auto; border: 1px solid #e9ecef; border-radius: 8px; }
.model-table{ width:100%; border-collapse:collapse; background:#fff; }
.model-table th,.model-table td{ padding:0.75rem 1rem; border-bottom:1px solid #e9ecef; text-align: left; font-size: 0.875rem; }
.model-table th{ background:#f8f9fa; font-weight: 600; color: #495057; white-space: nowrap; }
.model-table tr:last-child td { border-bottom: none; }
.actions-cell{ display:flex; gap:0.5rem; justify-content:flex-end }

/* Small buttons */
.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 4px;
}
.btn-success {
  background: #28a745;
  color: #fff;
  border: none;
  cursor: pointer;
}
.btn-success:hover {
  background: #218838;
}
.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-warning {
  background: #ffc107;
  color: #212529;
  border: none;
  cursor: pointer;
}
.btn-warning:hover {
  background: #e0a800;
}
.btn-warning:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Icon button info */
.icon-button-info {
  color: #17a2b8;
}
.icon-button-info:hover {
  background: rgba(23, 162, 184, 0.1);
}

.loading-indicator{ padding:2rem; text-align: center; color: #6c757d; display:flex; gap:0.75rem; align-items:center; justify-content: center; }
.empty-state{ padding:3rem; text-align:center; color:#6c757d; background: #f8f9fa; border-radius: 8px; border: 1px dashed #ced4da; }

@media (max-width:768px){ 
  .tools-left{ flex-direction:column; align-items:stretch; gap:0.75rem; width: 100%; } 
  .tools-right { width: 100%; justify-content: space-between; margin-top: 0.75rem; }
  .search input { width: 100%; }
  .actions-cell{ justify-content:flex-start } 
}
</style>
