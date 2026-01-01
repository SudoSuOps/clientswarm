import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// Auth
export const getNonce = () => api.get('/auth/nonce')
export const login = (message: string, signature: string) =>
  api.post('/auth/login', { message, signature })
export const register = (message: string, signature: string, ens_subdomain: string) =>
  api.post('/auth/register', { message, signature, ens_subdomain })
export const getMe = () => api.get('/auth/me')

// Jobs
export const submitJob = (model: string, input_cid: string, name?: string) =>
  api.post('/jobs/submit', { model, input_cid, name })
export const listJobs = (page = 1, status?: string) =>
  api.get('/jobs', { params: { page, status } })
export const getJob = (jobId: string) => api.get(`/jobs/${jobId}`)
export const refreshJob = (jobId: string) => api.post(`/jobs/${jobId}/refresh`)

// Upload
export const uploadFile = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload/file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const uploadFiles = async (files: File[]) => {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  return api.post('/upload/files', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Stats
export const getDashboardStats = () => api.get('/stats/dashboard')

// Settings
export const getProfile = () => api.get('/settings/profile')
export const updateProfile = (data: any) => api.patch('/settings/profile', data)
export const getBilling = () => api.get('/settings/billing')
export const addFunds = (amount: number, payment_method: string) =>
  api.post('/settings/billing/add-funds', { amount, payment_method })
export const generateApiKey = () => api.post('/settings/api-keys/generate')
export const listApiKeys = () => api.get('/settings/api-keys')

export default api
