import axios from 'axios'

const api = axios.create({
  baseURL: '/v1', // Proxy will handle this
  headers: {
    'Content-Type': 'application/json',
  },
})

// Export the axios instance for custom requests
export const axiosInstance = api

export default {
  // Models
  getModels: () => api.get('/admin/models'),
  getModel: (id) => api.get(`/admin/models/${id}`),
  createModel: (data) => api.post('/admin/models', data),
  updateModel: (id, data) => api.put(`/admin/models/${id}`, data),
  deleteModel: (id) => api.delete(`/admin/models/${id}`),
  activateModel: (id) => api.post(`/admin/models/${id}/activate`),
  deactivateModel: (id) => api.post(`/admin/models/${id}/deactivate`),
  getBaseModels: () => api.get('/base-models'),
  
  // Model Versions
  getModelVersions: (modelId) => api.get(`/admin/models/${modelId}/versions`),
  createModelVersion: (modelId, data) => api.post(`/admin/models/${modelId}/versions`, data),
  activateModelVersion: (modelId, version) => api.post(`/admin/models/${modelId}/versions/${version}/activate`),
  deactivateModelVersion: (modelId, version) => api.post(`/admin/models/${modelId}/versions/${version}/deactivate`),
  
  // Model Sync
  syncModels: (config, options = {}) => api.post('/admin/models/sync', { config, ...options }),

  // Tools
  getTools: (detailed = true) => api.get(`/admin/tools/detailed`),
  getTool: (id) => api.get(`/admin/tools/${id}`),
  createTool: (data) => api.post('/admin/tools', data),
  updateTool: (id, data) => api.put(`/admin/tools/${id}`, data),
  deleteTool: (id) => api.delete(`/admin/tools/${id}`),
  testTool: (id, args) => api.post(`/admin/tools/${id}/test`, args),

  // Knowledge Base
  getKBs: () => api.get('/admin/knowledge-bases'),
  getKB: (id) => api.get(`/admin/knowledge-bases/${id}`),
  createKB: (data) => api.post('/admin/knowledge-bases', data),
  updateKB: (id, data) => api.put(`/admin/knowledge-bases/${id}`, data),
  deleteKB: (id) => api.delete(`/admin/knowledge-bases/${id}`),
  getKBDocuments: (id, limit = 50, offset = 0) => api.get(`/rag/documents`, { params: { kb_id: id, limit, offset } }),
  getKBStats: (id) => api.get(`/rag/stats`, { params: { kb_id: id } }),
  clearKB: (id) => api.delete(`/rag/clear`, { params: { kb_id: id } }),
  reloadKB: (id) => api.post(`/rag/reload`, null, { params: { kb_id: id } }),
  searchKB: (id, query, topK = 5) => api.post(`/rag/search`, { query, top_k: topK }, { params: { kb_id: id } }),
  importTexts: (id, texts, sources) => api.post(`/rag/import/texts`, { texts, sources }, { params: { kb_id: id } }),
  importDocuments: (id, documents) => api.post(`/rag/import/documents`, { documents }, { params: { kb_id: id } }),
  
  // KB Folder Sync
  syncKBFolder: (id, data) => api.post(`/rag/sync-folder`, data, { params: { kb_id: id } }),
  
  // Chat (with optional custom headers)
  chatCompletion: (data, config = {}) => api.post('/chat/completions', data, config),
  chatCompletionStream: (data, config = {}) => api.post('/chat/completions', { ...data, stream: true }, {
    ...config,
    responseType: 'stream',
  }),

  // Logs
  getLogs: (params) => api.get('/admin/logs', { params }),
  getLog: (id) => api.get(`/admin/logs/${id}`),
  getLogStats: () => api.get('/admin/logs/stats'),
  deleteLog: (id) => api.delete(`/admin/logs/${id}`),
  clearLogs: (params) => api.delete('/admin/logs', { params }),
  
  // Agent Events (for timeline)
  getAgentEvents: (logId) => api.get(`/admin/agent-events/${logId}`),
  
  // Tool Execution Logs
  getToolLogs: (params) => api.get('/admin/tool-logs', { params }),
  getToolLog: (id) => api.get(`/admin/tool-logs/${id}`),
  getToolLogsByChat: (chatLogId) => api.get(`/admin/tool-logs/chat/${chatLogId}`),
  getToolLogStats: () => api.get('/admin/tool-logs/stats'),
  deleteToolLog: (id) => api.delete(`/admin/tool-logs/${id}`),
  clearToolLogs: (params) => api.delete('/admin/tool-logs', { params }),
}
