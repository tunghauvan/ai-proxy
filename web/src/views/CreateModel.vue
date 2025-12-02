<template>
  <div class="create-model">
    <div class="page-header">
      <h1>Create Model</h1>
      <p class="subtitle">Configure a new custom model with RAG and tools</p>
    </div>

    <form @submit.prevent="submit">
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
          <label class="form-label" for="model-version">Version</label>
          <input 
            id="model-version"
            v-model="form.version" 
            type="text"
            class="form-input"
            placeholder="1.0.0"
          />
          <span class="form-hint">Semantic version (e.g., 1.0.0, 2.1.0)</span>
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
          {{ submitting ? 'Creating...' : 'Create Model' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useModelsStore } from '../store'

const store = useModelsStore()
const router = useRouter()

// Model name validation regex
const MODEL_NAME_PATTERN = /^[a-z][a-z0-9_-]*$/

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

const submitting = ref(false)
const errorMsg = ref('')
const nameError = ref('')

const availableTools = computed(() => store.tools)

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

onMounted(() => {
  store.fetchTools()
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

    await store.createModel({
      name: form.name.trim().toLowerCase(),
      version: form.version.trim() || '1.0.0',
      base_model: form.baseModel.trim() || null,
      model_params: modelParams,
      enabled: form.enabled,
      rag_settings: {
        enabled: form.ragEnabled,
        top_k: form.topK,
        collection: form.collection,
      },
      tool_names: form.tools.length ? form.tools : undefined,
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
.create-model {
  max-width: 560px;
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
</style>
