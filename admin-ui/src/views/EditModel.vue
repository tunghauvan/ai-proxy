<template>
  <div class="edit-model">
    <div class="page-header">
      <h1>Edit Model</h1>
      <p class="subtitle">Update model configuration or create a new version</p>
    </div>

    <div v-if="loading" class="loading-state">Loading model...</div>

    <form v-else @submit.prevent="submit">
      <div class="form-section">
        <div class="form-group">
          <label class="form-label" for="model-name">Model Name *</label>
          <input 
            id="model-name"
            v-model="form.name" 
            type="text"
            class="form-input"
            :class="{ 'input-error': nameError }"
            placeholder="e.g. my-model-v1"
            @input="validateName"
            required 
          />
          <span v-if="nameError" class="form-error">{{ nameError }}</span>
          <span v-else class="form-hint">Only lowercase letters (a-z), numbers (0-9), underscores (_), hyphens (-). Must start with a letter.</span>
        </div>
        <div class="form-group">
          <label class="form-label" for="model-version">Current Version</label>
          <input 
            id="model-version"
            v-model="form.version" 
            type="text"
            class="form-input"
            placeholder="1.0.0"
            disabled
          />
          <span class="form-hint">To create a new version, use "Create New Version" below</span>
        </div>
      </div>

      <div class="form-section">
        <h3 class="section-title">LLM Configuration</h3>
        <div class="form-group">
          <label class="form-label" for="base-model">Base Model</label>
          <input 
            id="base-model"
            v-model="form.baseModel" 
            type="text"
            class="form-input"
            placeholder="e.g. qwen3:8b, gpt-4o (optional)"
          />
          <span class="form-hint">Leave empty to use default from environment</span>
        </div>
        <div class="form-group">
          <label class="form-label" for="model-params">Model Parameters (JSON)</label>
          <textarea 
            id="model-params"
            v-model="form.modelParams" 
            class="form-textarea"
            rows="3"
            placeholder='{"temperature": 0.7, "max_tokens": 1024}'
          ></textarea>
          <span class="form-hint">Allowed: temperature, max_tokens, top_p, frequency_penalty, presence_penalty</span>
        </div>
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.enabled" />
            <span>Model Enabled</span>
          </label>
        </div>
      </div>

      <div class="form-section">
        <h3 class="section-title">RAG Settings</h3>
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.ragEnabled" />
            <span>Enable RAG</span>
          </label>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label" for="top-k">Top K</label>
            <input 
              id="top-k"
              type="number" 
              v-model.number="form.topK" 
              min="1" 
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label class="form-label" for="collection">Collection</label>
            <input 
              id="collection"
              v-model="form.collection" 
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
            <input type="checkbox" :value="t" v-model="form.tools" />
            <span>{{ t }}</span>
          </label>
        </div>
      </div>

      <div v-if="errorMsg" class="error-message">{{ errorMsg }}</div>

      <div class="form-actions">
        <router-link to="/" class="btn btn-secondary">Cancel</router-link>
        <button type="submit" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>
    </form>

    <!-- Create New Version Section -->
    <div v-if="!loading" class="version-section">
      <h2 class="section-title">Create New Version</h2>
      <p class="section-description">
        Create a new version of this model. The current configuration will be used as a base. 
        New version must be greater than current version ({{ form.version }}).
      </p>
      
      <div class="new-version-form">
        <div class="form-row-inline">
          <div class="form-group">
            <label class="form-label" for="new-version">New Version</label>
            <input 
              id="new-version"
              v-model="newVersion" 
              type="text"
              class="form-input"
              :class="{ 'input-error': newVersionError }"
              :placeholder="suggestedVersion"
              @input="validateNewVersion"
            />
            <span v-if="newVersionError" class="form-error">{{ newVersionError }}</span>
          </div>
          <div class="form-group">
            <label class="form-label" for="version-description">Description (optional)</label>
            <input 
              id="version-description"
              v-model="newVersionDescription" 
              type="text"
              class="form-input"
              placeholder="e.g. Added new tool support"
            />
          </div>
        </div>
        <button 
          type="button" 
          class="btn btn-success" 
          :disabled="creatingVersion || newVersionError"
          @click="createNewVersion"
        >
          {{ creatingVersion ? 'Creating...' : 'Create Version' }}
        </button>
      </div>
      
      <div v-if="versionSuccessMsg" class="success-message">{{ versionSuccessMsg }}</div>
      <div v-if="versionErrorMsg" class="error-message">{{ versionErrorMsg }}</div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useModelsStore } from '../store'

const store = useModelsStore()
const router = useRouter()
const route = useRoute()

// Model name validation regex
const MODEL_NAME_PATTERN = /^[a-z][a-z0-9_-]*$/
const VERSION_PATTERN = /^\d+\.\d+\.\d+$/

const form = reactive({
  name: '',
  version: '1.0.0',
  baseModel: '',
  modelParams: '',
  enabled: true,
  ragEnabled: true,
  topK: 3,
  collection: 'knowledge_base',
  tools: [],
})

const loading = ref(true)
const submitting = ref(false)
const errorMsg = ref('')
const nameError = ref('')

// New version state
const newVersion = ref('')
const newVersionDescription = ref('')
const newVersionError = ref('')
const creatingVersion = ref(false)
const versionSuccessMsg = ref('')
const versionErrorMsg = ref('')

const availableTools = computed(() => store.tools)

const suggestedVersion = computed(() => {
  const parts = form.version.split('.')
  if (parts.length === 3) {
    const patch = parseInt(parts[2]) + 1
    return `${parts[0]}.${parts[1]}.${patch}`
  }
  return '1.0.1'
})

function validateName() {
  const name = form.name.trim().toLowerCase()
  nameError.value = ''
  
  if (!name) {
    return
  }
  
  if (name.length < 2) {
    nameError.value = 'Name must be at least 2 characters'
    return
  }
  
  if (name.length > 64) {
    nameError.value = 'Name must be at most 64 characters'
    return
  }
  
  if (!MODEL_NAME_PATTERN.test(name)) {
    nameError.value = 'Invalid format. Use lowercase letters, numbers, underscores, hyphens. Must start with a letter.'
    return
  }
}

function validateNewVersion() {
  const version = newVersion.value.trim()
  newVersionError.value = ''
  
  if (!version) {
    return
  }
  
  if (!VERSION_PATTERN.test(version)) {
    newVersionError.value = 'Version must follow format: X.Y.Z (e.g., 1.0.0, 2.1.3)'
    return
  }
  
  // Compare with current version
  const currentParts = form.version.split('.').map(Number)
  const newParts = version.split('.').map(Number)
  
  let isGreater = false
  for (let i = 0; i < 3; i++) {
    if (newParts[i] > currentParts[i]) {
      isGreater = true
      break
    } else if (newParts[i] < currentParts[i]) {
      break
    }
  }
  
  if (!isGreater) {
    newVersionError.value = `New version must be greater than current version (${form.version})`
  }
}

async function createNewVersion() {
  validateNewVersion()
  if (newVersionError.value || !newVersion.value.trim()) {
    versionErrorMsg.value = 'Please enter a valid version number'
    return
  }
  
  creatingVersion.value = true
  versionSuccessMsg.value = ''
  versionErrorMsg.value = ''
  
  try {
    // Parse model params JSON
    let modelParams = null
    if (form.modelParams.trim()) {
      try {
        modelParams = JSON.parse(form.modelParams)
      } catch (e) {
        throw new Error('Invalid JSON for Model Parameters')
      }
    }
    
    const res = await fetch(`/v1/admin/models/${route.params.id}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        version: newVersion.value.trim(),
        enabled: form.enabled,
        rag_settings: {
          enabled: form.ragEnabled,
          top_k: form.topK,
          collection: form.collection,
        },
        tool_names: form.tools.length ? form.tools : [],
        base_model: form.baseModel.trim() || null,
        model_params: modelParams,
        description: newVersionDescription.value.trim() || null,
      })
    })
    
    if (!res.ok) {
      const errText = await res.text()
      throw new Error(errText || 'Failed to create version')
    }
    
    versionSuccessMsg.value = `Version ${newVersion.value} created successfully!`
    
    // Update current version display
    form.version = newVersion.value
    newVersion.value = ''
    newVersionDescription.value = ''
    
    // Refresh models in store
    await store.fetchModels()
  } catch (e) {
    versionErrorMsg.value = e.message
  } finally {
    creatingVersion.value = false
  }
}

onMounted(async () => {
  await store.fetchTools()
  
  try {
    const model = await store.getModel(route.params.id)
    form.name = model.name || ''
    form.version = model.version || '1.0.0'
    form.baseModel = model.base_model || ''
    form.modelParams = model.model_params ? JSON.stringify(model.model_params, null, 2) : ''
    form.enabled = model.enabled !== false
    form.ragEnabled = model.rag_settings?.enabled ?? true
    form.topK = model.rag_settings?.top_k ?? 3
    form.collection = model.rag_settings?.collection ?? 'knowledge_base'
    form.tools = model.tool_names || []
  } catch (e) {
    errorMsg.value = 'Failed to load model: ' + e.message
  } finally {
    loading.value = false
  }
})

async function submit() {
  // Validate name before submit
  validateName()
  if (nameError.value) {
    errorMsg.value = 'Please fix the model name'
    return
  }
  
  submitting.value = true
  errorMsg.value = ''
  try {
    // Parse model params JSON
    let modelParams = null
    if (form.modelParams.trim()) {
      try {
        modelParams = JSON.parse(form.modelParams)
      } catch (e) {
        throw new Error('Invalid JSON for Model Parameters')
      }
    }

    await store.updateModel(route.params.id, {
      name: form.name.trim().toLowerCase(),
      base_model: form.baseModel.trim() || null,
      model_params: modelParams,
      enabled: form.enabled,
      rag_settings: {
        enabled: form.ragEnabled,
        top_k: form.topK,
        collection: form.collection,
      },
      tool_names: form.tools.length ? form.tools : [],
    })
    router.push('/')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.edit-model {
  max-width: 640px;
}

.loading-state {
  color: #6c757d;
  padding: 2rem 0;
}

form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
}

.form-row-inline {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.tools-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.form-error {
  color: #dc3545;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.input-error {
  border-color: #dc3545 !important;
}

.input-error:focus {
  box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.15) !important;
}

/* Version Section */
.version-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid #e9ecef;
}

.section-description {
  color: #6c757d;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.new-version-form {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.success-message {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #d4edda;
  color: #155724;
  border-radius: 6px;
  font-size: 0.875rem;
}

.btn-success {
  background: #28a745;
  color: #fff;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-success:hover {
  background: #218838;
}

.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
