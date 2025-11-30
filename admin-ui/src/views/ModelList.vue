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
  active: boolean
  enabled: boolean
  base_model?: string
  rag_settings?: RagSettings | null
  tool_names?: string[]
  model_params?: Record<string, any> | null
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
const tableColspan = computed(() => 2 + selectedColumnsCount.value)

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

    <div v-if="displayedError" class="alert" role="alert">{{ displayedError }}</div>

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
          <router-link :to="`/edit/${model.id}`" class="icon-button icon-button-secondary" aria-label="Edit model"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3.5 11.5v1.5h1.5l6-6-1.5-1.5-6 6z" /><path d="M10.75 4l1.25 1.25" /></svg><span class="sr-only">Edit</span></router-link>

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
          <tr v-for="model in filteredModels" :key="model.id">
            <td>{{ model.name }}</td>
            <td><span :class="['status-badge', getStatusClass(model)]">{{ getStatusLabel(model) }}</span></td>
            <td v-if="selectedColumns.base">{{ model.base_model || 'Default' }}</td>
            <td v-if="selectedColumns.rag">{{ formatRagSettings(model.rag_settings) }}</td>
            <td v-if="selectedColumns.tools">{{ formatTools(model.tool_names) }}</td>
            <td v-if="selectedColumns.params">{{ formatParams(model.model_params) }}</td>
            <td class="actions-cell">
              <router-link :to="`/edit/${model.id}`" class="icon-button icon-button-secondary" aria-label="Edit model"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3.5 11.5v1.5h1.5l6-6-1.5-1.5-6 6z" /><path d="M10.75 4l1.25 1.25" /></svg></router-link>
              <button v-if="!model.active" class="icon-button icon-button-success" :disabled="activationLoading === model.id" @click="onActivate(model)" type="button" aria-label="Activate model"><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 4v8" /><path d="M4 8h8" /></svg></button>
              <button v-else class="icon-button icon-button-warning" :disabled="deactivationLoading === model.id" @click="onDeactivate(model)" type="button" aria-label="Deactivate model"><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 8h8" /></svg></button>
              <button class="icon-button icon-button-danger" :disabled="deleteLoading === model.id" @click="onDelete(model)" type="button" aria-label="Delete model"><svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 5h8" /><path d="M6.5 5V3.5h3V5" /><path d="M5.5 7v6" /><path d="M10.5 7v6" /></svg></button>
            </td>
          </tr>
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
.page-header { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; }
.page-header h1 { margin:0; font-size:1.5rem }
.subtitle { margin:4px 0 0; color:#6c757d; font-size:0.9rem }

.toolbar { display:flex; justify-content:space-between; gap:1rem; align-items:center; flex-wrap:wrap }
.tools-left { display:flex; gap:0.75rem; align-items:center }
.tools-right { display:flex; gap:0.5rem; align-items:center }
.form-input { padding:0.5rem 0.75rem; border:1px solid #ced4da; border-radius:6px }
.form-select { padding:0.45rem 0.6rem; border:1px solid #ced4da; border-radius:6px }

.card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem }
.model-card { background:#fff; border:1px solid #e6e9ee; border-radius:10px; display:flex; flex-direction:column; overflow:hidden }
.card-header { display:flex; justify-content:space-between; align-items:center; padding:0.9rem 1rem; border-bottom:1px solid #f1f5f9 }
.card-body{ padding:0.9rem 1rem }
.card-actions{ display:flex; gap:0.5rem; justify-content:flex-end; padding:0.75rem 1rem; background:#fafbfc }
.model-name{ margin:0; font-weight:600 }
.model-meta{ font-size:0.85rem; color:#6b7280 }
.status-badge{ padding:0.18rem 0.6rem; border-radius:999px; font-weight:600; font-size:0.75rem }
.status-active{ background:#dcfce7; color:#15803d }
.status-enabled{ background:#dbeafe; color:#1d4ed8 }
.status-disabled{ background:#eef2f6; color:#475569 }

.model-table{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #e6e9ee; border-radius:8px; overflow:hidden }
.model-table th,.model-table td{ padding:0.6rem 0.85rem; border-bottom:1px solid #eef2f6 }
.model-table th{ background:#f7fafc; text-align:left }
.actions-cell{ display:flex; gap:0.5rem; justify-content:flex-end }

.icon-button{ width:36px; height:36px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; border:none; background:#fff }
.icon-button svg{ width:16px; height:16px }
.icon-button-success{ background:#e6f5ec; color:#0f9d58 }
.icon-button-warning{ background:#fff4e6; color:#c2410c }
.icon-button-danger{ background:#fee2e2; color:#bb1e1e }

.btn-primary{ background:#212529; color:#fff; padding:0.5rem 0.9rem; border-radius:6px }
.btn-secondary{ background:#eef2f6; padding:0.45rem 0.8rem; border-radius:6px }

.empty-state{ padding:1.25rem; text-align:center; color:#6b7280 }
.alert{ background:#fcebea; color:#9f3a38; padding:0.75rem; border-radius:8px }
.loading-indicator{ padding:1rem; border:1px solid #eef2f6; border-radius:8px; display:flex; gap:0.5rem; align-items:center }
.spinner{ width:16px; height:16px; border:2px solid #e6e9ee; border-top-color:#212529; border-radius:50%; animation:spin 0.8s linear infinite }
.spinner-small{ width:12px; height:12px; border:2px solid transparent; border-top-color:currentColor; border-radius:50%; animation:spin 0.8s linear infinite }

.sr-only{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0 }

@keyframes spin{ to{ transform:rotate(360deg) } }

@media (max-width:720px){ .tools-left{ flex-direction:column; align-items:flex-start; gap:0.5rem } .actions-cell{ justify-content:flex-start } }
</style>
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.status-active {
  background: #dcfce7;
  color: #16a34a;
}

.status-enabled {
  background: #dbeafe;
  color: #2563eb;
}

.status-disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.card-body {
  padding: 1rem;
}

.model-details {
  margin: 0;
}

.detail-row {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f3f4f6;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row dt {
  font-weight: 500;
  color: #6b7280;
  min-width: 100px;
  font-size: 0.875rem;
}

.detail-row dd {
  margin: 0;
  color: #111827;
  font-size: 0.875rem;
  word-break: break-word;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  flex-wrap: wrap;
}

/* Table */
.table-container {
  overflow-x: auto;
}

.model-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.model-table th,
.model-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}

.model-table th {
  background: #f9fafb;
  font-weight: 600;
  font-size: 0.875rem;
  color: #374151;
}

.model-table td {
  font-size: 0.875rem;
  color: #111827;
}

.model-table tbody tr:hover {
  background: #f9fafb;
}

.actions-cell {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background-color 0.2s, opacity 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon-button {
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: #f3f4f6;
  color: #374151;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  text-decoration: none;
}

.icon-button svg {
  width: 18px;
  height: 18px;
}

.icon-button:hover:not(:disabled) {
  background: #e5e7eb;
}

.icon-button:focus-visible {
  outline: 2px solid #111827;
  outline-offset: 2px;
}

.icon-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon-button-secondary {
  background: #fff;
  color: #374151;
}

.icon-button-success {
  background: #e6f5ec;
  color: #0f9d58;
}

.icon-button-warning {
  background: #fff4e6;
  color: #a855f7;
}

.icon-button-danger {
  background: #fee2e2;
  color: #b91c1c;
}

.btn-small {
  padding: 0.375rem 0.75rem;
  font-size: 0.8125rem;
}

.btn-primary {
  background: #007bff;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-success {
  background: #28a745;
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background: #1e7e34;
}

.btn-warning {
  background: #ffc107;
  color: #212529;
}

.btn-warning:hover:not(:disabled) {
  background: #d39e00;
}

.btn-danger {
  background: #dc3545;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #bd2130;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
  font-size: 1rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
