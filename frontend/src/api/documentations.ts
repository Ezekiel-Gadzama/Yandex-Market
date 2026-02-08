import apiClient from './client'

export interface Documentation {
  id: number
  name: string
  description?: string
  file_url?: string
  link_url?: string
  content?: string
  type: 'file' | 'link' | 'text'
  created_at: string
  updated_at?: string
}

export interface DocumentationCreate {
  name: string
  description?: string
  file_url?: string
  link_url?: string
  content?: string
  type: 'file' | 'link' | 'text'
}

export interface DocumentationUpdate {
  name?: string
  description?: string
  file_url?: string
  link_url?: string
  content?: string
  type?: 'file' | 'link' | 'text'
}

export const documentationsApi = {
  getAll: async (search?: string): Promise<Documentation[]> => {
    const params = search ? { search } : {}
    const response = await apiClient.get('/documentations/', { params })
    return response.data
  },

  get: async (id: number): Promise<Documentation> => {
    const response = await apiClient.get(`/documentations/${id}`)
    return response.data
  },

  create: async (data: DocumentationCreate): Promise<Documentation> => {
    const response = await apiClient.post('/documentations/', data)
    return response.data
  },

  update: async (id: number, data: DocumentationUpdate): Promise<Documentation> => {
    const response = await apiClient.put(`/documentations/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/documentations/${id}`)
  },

  uploadFile: async (file: File): Promise<{ file_url: string; filename: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/documentations/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}
