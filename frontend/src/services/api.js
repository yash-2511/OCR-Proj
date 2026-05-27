import axios from 'axios'
import useDocumentStore from '../store/useDocumentStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 100000,
})

const AUTH_TOKEN_KEY = 'ocr-proj-auth-token'

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY)
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

async function request(config) {
  try {
    const response = await api.request(config)
    return response.data
  } catch (error) {
    const message = error?.response?.data?.error || error.message || 'Request failed'
    throw new Error(message)
  }
}

export function setAuthToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY)
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

// Default (network) implementations
const networkImpl = {
  signupUser: (payload) => request({ method: 'POST', url: '/api/auth/signup', data: payload }),
  loginUser: (payload) => request({ method: 'POST', url: '/api/auth/login', data: payload }),
  getCurrentUser: () => request({ method: 'GET', url: '/api/auth/me' }),
  logoutUser: () => request({ method: 'POST', url: '/api/auth/logout' }),
  uploadDocument: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request({ method: 'POST', url: '/api/upload', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
  },
  uploadBatch: (files) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return request({ method: 'POST', url: '/api/upload/batch', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
  },
  classifyDocument: (documentId) => request({ method: 'POST', url: '/api/classify', data: { document_id: documentId } }),
  extractDocument: (documentId) => request({ method: 'POST', url: '/api/extract', data: { document_id: documentId } }),
  listDocuments: (params = {}) => request({ method: 'GET', url: '/api/documents', params }),
  getDocument: (documentId) => request({ method: 'GET', url: `/api/documents/${documentId}` }),
  getDocumentInsights: (documentId) => request({ method: 'GET', url: `/api/documents/${documentId}/insights` }),
  updateDocumentFields: (documentId, fields) => request({ method: 'PUT', url: `/api/documents/${documentId}/fields`, data: { fields } }),
  updateDocumentStatus: (documentId, status) => request({ method: 'PATCH', url: `/api/documents/${documentId}/status`, data: { status } }),
  deleteDocument: (documentId) => request({ method: 'DELETE', url: `/api/documents/${documentId}` }),
  getStats: () => request({ method: 'GET', url: '/api/stats' }),
  exportDocument: (documentId, format = 'json') => api.post('/api/export', { document_id: documentId, format }, { responseType: 'blob' }),
  exportBatch: (batchId) => api.post(`/api/export/batch/${batchId}`, {}, { responseType: 'blob' }),
  healthCheck: () => request({ method: 'GET', url: '/api/health' }),
}

// Mock mode support
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const mockStore = useDocumentStore

// Mock implementations that call the store
const mockImpl = {
  healthCheck: async () => ({ status: 'ok' }),
  getCurrentUser: async () => ({ data: { user: { username: 'Demo User', role: 'Admin' } } }),
  listDocuments: async (params = {}) => {
    const docs = mockStore?.getState().documents || []
    return { data: docs }
  },
  getDocument: async (id) => {
    const d = mockStore?.getState().getDocument(id)
    if (!d) throw new Error('Not found')
    return { data: d }
  },
  getDocumentInsights: async (id) => {
    const document = mockStore?.getState().getDocument(id)
    if (!document) throw new Error('Not found')

    const sourceFields = document.fields && typeof document.fields === 'object' ? document.fields : document.extractedFields || {}
    const fields = Object.entries(sourceFields).map(([field_name, field_value]) => ({ field_name, field_value }))
    const highlights = fields.slice(0, 5).map((field) => `${field.field_name}: ${field.field_value}`)
    const summaryBits = []
    if (document.type) summaryBits.push(`This appears to be a ${String(document.type).toLowerCase()} document.`)
    if (document.text) summaryBits.push(document.text.split('\n').slice(0, 2).join(' '))
    if (document.extractedFields?.ADDRESS) summaryBits.push(`It includes address details such as ${document.extractedFields.ADDRESS}.`)
    if (document.extractedFields?.TOTAL) summaryBits.push(`A monetary total of ${document.extractedFields.TOTAL} is present.`)
    if (document.extractedFields?.DATE) summaryBits.push(`The document includes date information like ${document.extractedFields.DATE}.`)

    return {
      data: {
        extracted_text: document.text || Object.values(sourceFields).join('\n') || 'No OCR text could be recovered from this document.',
        summary: summaryBits.length ? summaryBits.join(' ') : 'This document contains structured information and appears ready for review.',
        highlights,
        document_type: document.type || document.doc_type || 'document',
      },
    }
  },
  extractDocument: (id) => mockStore?.getState().simulateExtract(id),
  getStats: async () => {
    const state = mockStore?.getState()
    return {
      data: {
        documents: state?.documents?.length || 0,
        batches: state?.batches?.length || 0,
      },
    }
  },
  uploadDocument: async (file, docType) => {
    const id = String(Date.now())
    const newDoc = { id, filename: file.name || 'uploaded_file', type: docType || 'Unknown', status: 'QUEUED', confidence: 0, pageCount: 1, uploadedAt: new Date().toISOString(), extractedFields: {}, tables: [], bboxes: [] }
    mockStore?.getState().addDocument(newDoc)
    return { data: newDoc }
  },
  signupUser: async (payload) => ({ data: { user: { username: payload.username }, token: 'mock-token' } }),
  loginUser: async (payload) => ({ data: { user: { username: payload.username }, token: 'mock-token' } }),
  logoutUser: async () => ({}),
}

// Exported functions that delegate to mock or network implementations
export const signupUser = (...args) => (USE_MOCK ? mockImpl.signupUser(...args) : networkImpl.signupUser(...args))
export const loginUser = (...args) => (USE_MOCK ? mockImpl.loginUser(...args) : networkImpl.loginUser(...args))
export const getCurrentUser = (...args) => (USE_MOCK ? mockImpl.getCurrentUser(...args) : networkImpl.getCurrentUser(...args))
export const logoutUser = (...args) => (USE_MOCK ? mockImpl.logoutUser(...args) : networkImpl.logoutUser(...args))
export const uploadDocument = (...args) => (USE_MOCK ? mockImpl.uploadDocument(...args) : networkImpl.uploadDocument(...args))
export const uploadBatch = (...args) => (USE_MOCK ? mockImpl.uploadBatch?.(...args) ?? Promise.resolve() : networkImpl.uploadBatch(...args))
export const classifyDocument = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.classifyDocument(...args))
export const extractDocument = (...args) => (USE_MOCK ? mockImpl.extractDocument(...args) : networkImpl.extractDocument(...args))
export const listDocuments = (...args) => (USE_MOCK ? mockImpl.listDocuments(...args) : networkImpl.listDocuments(...args))
export const getDocument = (...args) => (USE_MOCK ? mockImpl.getDocument(...args) : networkImpl.getDocument(...args))
export const getDocumentInsights = (...args) => (USE_MOCK ? mockImpl.getDocumentInsights(...args) : networkImpl.getDocumentInsights(...args))
export const updateDocumentFields = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.updateDocumentFields(...args))
export const updateDocumentStatus = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.updateDocumentStatus(...args))
export const deleteDocument = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.deleteDocument(...args))
export const getStats = (...args) => (USE_MOCK ? mockImpl.getStats(...args) : networkImpl.getStats(...args))
export const exportDocument = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.exportDocument(...args))
export const exportBatch = (...args) => (USE_MOCK ? Promise.resolve() : networkImpl.exportBatch(...args))
export const healthCheck = (...args) => (USE_MOCK ? mockImpl.healthCheck(...args) : networkImpl.healthCheck(...args))

export default api
