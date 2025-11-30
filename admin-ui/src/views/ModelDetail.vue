<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useModelsStore } from '../store'
import { Cog6ToothIcon } from '@heroicons/vue/24/outline'

const store = useModelsStore()
const router = useRouter()
const route = useRoute()

// State
const loading = ref(true)
const model = ref(null)
const versions = ref([])
const versionsLoading = ref(false)
const editMode = ref(false)
const error = ref('')
const settingsDropdownOpen = ref(false)

// Edit form state
const editForm = reactive({
  name: '',
  baseModel: '',
  modelParams: '',
  enabled: true,
  ragEnabled: true,
  topK: 3,
  collection: 'knowledge_base',
  tools: [],
})

const editError = ref('')
const editSubmitting = ref(false)

const MODEL_NAME_PATTERN = /^[a-z][a-z0-9_-]*$/
const VERSION_PATTERN = /^\d+\.\d+\.\d+$/

// Available base models for dropdown
const AVAILABLE_BASE_MODELS = [
  { value: 'gpt-oss:20b-cloud', label: 'GPT-OSS 20B Cloud' },
  { value: 'gpt-oss:120b-cloud', label: 'GPT-OSS 120B Cloud' },
]

const availableTools = computed(() => store.tools)

function formatDate(dateStr) {
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

function formatRagSettings(rag) {
  if (!rag) return 'Not configured'
  if (!rag.enabled) return 'Disabled'
  const parts = ['Enabled']
  if (rag.top_k) parts.push(`Top-K: ${rag.top_k}`)
  if (rag.collection) parts.push(`Collection: ${rag.collection}`)
  return parts.join(', ')
}

function formatTools(tools) {
  if (!tools || tools.length === 0) return 'None'
  return tools.join(', ')
}

function formatParams(params) {
  if (!params || Object.keys(params).length === 0) return 'Defaults'
  return Object.entries(params).map(([k, v]) => `${k}: ${v}`).join(', ')
}

async function loadModel() {
  loading.value = true
  error.value = ''
  try {
    model.value = await store.getModel(route.params.id)
    await loadVersions()
  } catch (e) {
    error.value = e.message || 'Failed to load model'
  } finally {
    loading.value = false
  }
}

async function loadVersions() {
  versionsLoading.value = true
  try {
    const res = await fetch(`/v1/admin/models/${route.params.id}/versions`)
    if (!res.ok) throw new Error(await res.text())
    versions.value = await res.json()
  } catch (e) {
    error.value = e.message || 'Failed to load version history'
  } finally {
    versionsLoading.value = false
  }
}

function enterEditMode() {
  editForm.name = model.value.name || ''
  editForm.baseModel = model.value.base_model || ''
  editForm.modelParams = model.value.model_params ? JSON.stringify(model.value.model_params, null, 2) : ''
  editForm.enabled = model.value.enabled !== false
  editForm.ragEnabled = model.value.rag_settings?.enabled ?? true
  editForm.topK = model.value.rag_settings?.top_k ?? 3
  editForm.collection = model.value.rag_settings?.collection ?? 'knowledge_base'
  editForm.tools = model.value.tool_names || []
  editError.value = ''
  editMode.value = true
}

function exitEditMode() {
  editMode.value = false
  editError.value = ''
}

async function saveChanges() {
  editSubmitting.value = true
  editError.value = ''
  try {
    // Parse model params JSON
    let modelParams = null
    if (editForm.modelParams.trim()) {
      try {
        modelParams = JSON.parse(editForm.modelParams)
      } catch (e) {
        throw new Error('Invalid JSON for Model Parameters')
      }
    }

    await store.updateModel(route.params.id, {
      name: editForm.name.trim().toLowerCase(),
      base_model: editForm.baseModel.trim() || null,
      model_params: modelParams,
      enabled: editForm.enabled,
      rag_settings: {
        enabled: editForm.ragEnabled,
        top_k: editForm.topK,
        collection: editForm.collection,
      },
      tool_names: editForm.tools.length ? editForm.tools : [],
    })
    
    await loadModel()
    editMode.value = false
  } catch (e) {
    editError.value = e.message
  } finally {
    editSubmitting.value = false
  }
}

async function activateVersion(version) {
  try {
    await fetch(`/v1/admin/models/${route.params.id}/versions/${version}/activate`, { method: 'POST' })
    await loadVersions()
    await store.fetchModels()
  } catch (e) {
    error.value = e.message || 'Failed to activate version'
  }
}

async function deactivateVersion(version) {
  try {
    const res = await fetch(`/v1/admin/models/${route.params.id}/versions/${version}/deactivate`, { method: 'POST' })
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Failed to deactivate version')
    }
    await loadVersions()
    await store.fetchModels()
  } catch (e) {
    error.value = e.message || 'Failed to deactivate version'
  }
}

async function removeModel() {
  if (!window.confirm('Are you sure you want to permanently delete this model? This action cannot be undone.')) return
  
  try {
    await store.deleteModel(route.params.id)
    router.push('/')
  } catch (e) {
    error.value = e.message || 'Failed to delete model'
  }
}

async function disableModel() {
  try {
    await store.updateModel(route.params.id, { enabled: false })
    await loadModel()
  } catch (e) {
    error.value = e.message || 'Failed to disable model'
  }
}

function toggleSettingsDropdown() {
  settingsDropdownOpen.value = !settingsDropdownOpen.value
}

function closeSettingsDropdown() {
  settingsDropdownOpen.value = false
}

// Click outside handler
onMounted(async () => {
  await store.fetchTools()
  await loadModel()

  // Add click outside handler
  const handleClickOutside = (event) => {
    const dropdown = document.querySelector('.settings-dropdown')
    if (dropdown && !dropdown.contains(event.target)) {
      closeSettingsDropdown()
    }
  }

  document.addEventListener('click', handleClickOutside)

  // Cleanup on unmount
  onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside)
  })
})
</script>

<template>
  <div class="model-detail">
    <!-- Back Navigation -->
    <div class="back-navigation">
      <router-link to="/" class="back-link">← Back to Models</router-link>
    </div>

    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1 v-if="!editMode" class="page-title">{{ model?.name }}</h1>
        <div v-if="!editMode" class="header-meta">
          v{{ model?.version }} · {{ model?.base_model || 'Default' }} · Active: {{ model?.active ? 'Yes' : 'No' }}
        </div>
      </div>
      <div class="header-actions">
        <div class="settings-dropdown" v-if="!editMode">
          <button 
            class="settings-button" 
            @click="toggleSettingsDropdown"
            :aria-expanded="settingsDropdownOpen"
            aria-haspopup="true"
          >
            <Cog6ToothIcon class="w-5 h-5" />
          </button>
          <div v-if="settingsDropdownOpen" class="settings-menu" @mouseleave="closeSettingsDropdown">
            <button class="settings-item" @click="enterEditMode(); closeSettingsDropdown()">
              <span>Edit</span>
            </button>
            <button class="settings-item settings-item-warning" @click="disableModel(); closeSettingsDropdown()">
              <span>Disable</span>
            </button>
            <button class="settings-item settings-item-danger" @click="removeModel(); closeSettingsDropdown()">
              <span>Remove</span>
            </button>
          </div>
        </div>
        <button v-else class="btn btn-secondary" @click="exitEditMode">Cancel</button>
      </div>
    </div>

    <div v-if="error" class="error-message" role="alert">{{ error }}</div>

    <div v-if="loading" class="loading-indicator">
      <span class="spinner"></span> Loading model details...
    </div>

    <div v-else-if="model" class="detail-container">
      <!-- Model Information Box - Read Mode -->
      <div v-if="!editMode" class="info-box">
        <div class="info-section">
          <h2 class="section-title">Configuration</h2>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">Model Name</span>
              <span class="value">{{ model.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">Version</span>
              <span class="value">v{{ model.version }}</span>
            </div>
            <div class="info-item">
              <span class="label">Status</span>
              <span :class="['status-badge', model.enabled ? 'status-enabled' : 'status-disabled']">
                {{ model.enabled ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">Active</span>
              <span :class="['status-badge', model.active ? 'status-active' : 'status-inactive']">
                {{ model.active ? 'Active' : 'Inactive' }}
              </span>
            </div>
          </div>
        </div>

        <div class="info-section">
          <h3 class="section-title">LLM Configuration</h3>
          <div class="info-grid">
            <div class="info-item full-width">
              <span class="label">Base Model</span>
              <span class="value">{{ model.base_model || 'Default' }}</span>
            </div>
            <div class="info-item full-width">
              <span class="label">Model Parameters</span>
              <span class="value">{{ formatParams(model.model_params) }}</span>
            </div>
          </div>
        </div>

        <div class="info-section">
          <h3 class="section-title">RAG Settings</h3>
          <div class="info-grid">
            <div class="info-item full-width">
              <span class="label">Configuration</span>
              <span class="value">{{ formatRagSettings(model.rag_settings) }}</span>
            </div>
          </div>
        </div>

        <div class="info-section">
          <h3 class="section-title">Tools</h3>
          <div class="info-grid">
            <div class="info-item full-width">
              <span class="label">Available Tools</span>
              <span class="value">{{ formatTools(model.tool_names) }}</span>
            </div>
          </div>
        </div>

        <div class="info-section meta">
          <div class="info-item">
            <span class="label">Created</span>
            <span class="value">{{ formatDate(model.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="label">Updated</span>
            <span class="value">{{ formatDate(model.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Model Information Box - Edit Mode -->
      <form v-else class="edit-box" @submit.prevent="saveChanges">
        <div class="form-section">
          <h3 class="section-title">Edit Configuration</h3>
          
          <div class="form-group">
            <label class="form-label">Model Name</label>
            <input 
              v-model="editForm.name" 
              type="text"
              class="form-input"
              placeholder="e.g. my-model"
              required 
            />
          </div>

          <div class="form-group">
            <label class="form-label">Base Model</label>
            <select 
              v-model="editForm.baseModel" 
              class="form-select"
            >
              <option value="">Select a base model (optional)</option>
              <option 
                v-for="model in AVAILABLE_BASE_MODELS" 
                :key="model.value" 
                :value="model.value"
              >
                {{ model.label }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Model Parameters (JSON)</label>
            <textarea 
              v-model="editForm.modelParams" 
              class="form-textarea"
              rows="3"
              placeholder='{"temperature": 0.7}'
            ></textarea>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editForm.enabled" />
              <span>Model Enabled</span>
            </label>
          </div>
        </div>

        <div class="form-section">
          <h3 class="section-title">RAG Settings</h3>
          
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="editForm.ragEnabled" />
              <span>Enable RAG</span>
            </label>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Top K</label>
              <input 
                type="number" 
                v-model.number="editForm.topK" 
                min="1" 
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Collection</label>
              <input 
                v-model="editForm.collection" 
                type="text"
                class="form-input"
              />
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3 class="section-title">Tools</h3>
          <div class="tools-grid">
            <label v-for="t in availableTools" :key="t" class="checkbox-label">
              <input type="checkbox" :value="t" v-model="editForm.tools" />
              <span>{{ t }}</span>
            </label>
          </div>
        </div>

        <div v-if="editError" class="error-message">{{ editError }}</div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="exitEditMode">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="editSubmitting">
            {{ editSubmitting ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>

      <!-- Version History Table -->
      <div class="versions-section">
        <h2 class="section-title">Version History</h2>
        
        <div v-if="versionsLoading" class="loading-indicator">
          <span class="spinner-small"></span> Loading versions...
        </div>

        <div v-else-if="versions.length > 0" class="table-container">
          <table class="versions-table">
            <thead>
              <tr>
                <th scope="col">Version</th>
                <th scope="col">Status</th>
                <th scope="col">Created</th>
                <th scope="col">Description</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ver in versions" :key="ver.version" :class="{ 'current-version': ver.version === model.version }">
                <td>
                  <strong>v{{ ver.version }}</strong>
                  <span v-if="ver.version === model.version" class="current-badge">Current</span>
                </td>
                <td>
                  <span :class="['version-status', ver.active ? 'version-active' : 'version-inactive']">
                    {{ ver.active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td>{{ formatDate(ver.created_at) }}</td>
                <td>{{ ver.description || '-' }}</td>
                <td class="actions-cell">
                  <button 
                    v-if="!ver.active" 
                    class="btn btn-sm btn-success"
                    @click="activateVersion(ver.version)"
                    :disabled="editMode"
                  >
                    Activate
                  </button>
                  <button 
                    v-else 
                    class="btn btn-sm btn-warning"
                    @click="deactivateVersion(ver.version)"
                    :disabled="editMode || versions.filter(v => v.active).length === 1"
                    :title="versions.filter(v => v.active).length === 1 ? 'Cannot deactivate only active version' : ''"
                  >
                    Deactivate
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state">
          No version history available
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.model-detail {
  width: 100%;
  padding: 1.25rem;
}

/* Back Navigation */
.back-navigation {
  margin-bottom: 1rem;
}

.back-link {
  color: #0066cc;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: color 0.2s;
}

.back-link:hover {
  color: #0052a3;
}

/* Header */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.header-content {
  flex: 1;
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #212529;
}

.header-meta {
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

/* Info Box */
.info-box {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
}

.edit-box {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 2rem;
  margin-bottom: 2rem;
}

.info-section {
  margin-bottom: 2rem;
}

.info-section:last-child {
  margin-bottom: 0;
}

.info-section.meta {
  padding-top: 2rem;
  border-top: 1px solid #e9ecef;
  margin-bottom: 0;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #212529;
  margin: 0 0 1rem 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.value {
  font-size: 0.95rem;
  color: #212529;
  word-break: break-word;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8125rem;
  font-weight: 500;
  width: fit-content;
}

.status-enabled {
  background: #d4edda;
  color: #155724;
}

.status-active {
  background: #cce5ff;
  color: #004085;
}

.status-inactive {
  background: #f8d7da;
  color: #721c24;
}

.status-disabled {
  background: #e9ecef;
  color: #6c757d;
}

/* Form Styles */
.form-section {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #212529;
  margin-bottom: 0.5rem;
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 6px;
  font-size: 0.875rem;
  font-family: inherit;
  background: #fff;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.form-textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
  user-select: none;
}

.checkbox-label input {
  cursor: pointer;
}

.tools-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

/* Versions Section */
.versions-section {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 2rem;
}

.table-container {
  overflow-x: auto;
}

.versions-table {
  width: 100%;
  border-collapse: collapse;
}

.versions-table th,
.versions-table td {
  padding: 1rem;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
  font-size: 0.875rem;
}

.versions-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.versions-table tbody tr:last-child td {
  border-bottom: none;
}

.versions-table tbody tr.current-version {
  background: #f0f7ff;
}

.current-badge {
  display: inline-block;
  background: #cce5ff;
  color: #004085;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  margin-left: 0.5rem;
}

.version-status {
  display: inline-flex;
  align-items: center;
  padding: 0.375rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8125rem;
  font-weight: 500;
}

.version-active {
  background: #d4edda;
  color: #155724;
}

.version-inactive {
  background: #f8d7da;
  color: #721c24;
}

.actions-cell {
  display: flex;
  gap: 0.5rem;
}

/* Settings Dropdown */
.settings-dropdown {
  position: relative;
}

.settings-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid #ced4da;
  border-radius: 6px;
  background: #fff;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.2s;
}

.settings-button:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
  color: #495057;
}

.settings-button:focus {
  outline: none;
  border-color: #0066cc;
  box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
}

.settings-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 10;
  width: 160px;
  background: #fff;
  border: 1px solid #ced4da;
  border-radius: 6px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  margin-top: 0.25rem;
}

.settings-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  background: none;
  color: #212529;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  text-align: left;
}

.settings-item:hover {
  background: #f8f9fa;
}

.settings-item:first-child {
  border-radius: 6px 6px 0 0;
}

.settings-item:last-child {
  border-radius: 0 0 6px 6px;
}

.settings-item:only-child {
  border-radius: 6px;
}

.settings-item-warning {
  color: #856404;
}

.settings-item-warning:hover {
  background: #fff3cd;
}

.settings-item-danger {
  color: #721c24;
}

.settings-item-danger:hover {
  background: #f8d7da;
}

/* States */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem;
  color: #6c757d;
  text-align: center;
  justify-content: center;
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
  margin-bottom: 1rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px dashed #ced4da;
}
</style>
