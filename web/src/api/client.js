import axios from 'axios'

const api = axios.create({
  baseURL: '/v1', // Proxy will handle this
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  deleteKB: (id) => api.delete(`/admin/knowledge-bases/${id}`),
  getKBDocuments: (id, limit = 20, offset = 0) => api.get(`/rag/documents`, { params: { kb_id: id, limit, offset } }),
  clearKB: (id) => api.delete(`/rag/clear`, { params: { kb_id: id } }),
  
  // Chat
  chatCompletion: (data) => api.post('/chat/completions', data),

  // Logs
  getLogs: (params) => api.get('/admin/logs', { params }),
  getLog: (id) => api.get(`/admin/logs/${id}`),
  getLogStats: () => api.get('/admin/logs/stats'),
  deleteLog: (id) => api.delete(`/admin/logs/${id}`),
  clearLogs: (params) => api.delete('/admin/logs', { params }),
}
