import apiClient from './client'

export interface ActivationTemplate {
  id: number
  name: string
  body: string
  random_key: boolean
  required_login: boolean
  activate_till_days?: number
  created_at: string
  updated_at?: string
}

export interface ActivationTemplateCreate {
  name: string
  body: string
  random_key?: boolean
  required_login?: boolean
  activate_till_days?: number
}

export interface ActivationTemplateUpdate {
  name?: string
  body?: string
  random_key?: boolean
  required_login?: boolean
  activate_till_days?: number
}

export const activationTemplatesApi = {
  getAll: async (search?: string) => {
    const params = search ? { search } : {}
    const response = await apiClient.get<ActivationTemplate[]>('activation-templates/', { params })
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<ActivationTemplate>(`activation-templates/${id}`)
    return response.data
  },
  
  create: async (data: ActivationTemplateCreate) => {
    const response = await apiClient.post<ActivationTemplate>('activation-templates/', data)
    return response.data
  },
  
  update: async (id: number, data: ActivationTemplateUpdate) => {
    const response = await apiClient.put<ActivationTemplate>(`activation-templates/${id}`, data)
    return response.data
  },
  
  delete: async (id: number) => {
    await apiClient.delete(`activation-templates/${id}`)
  },

  /** Export template as TXT or PDF; triggers browser download */
  export: async (id: number, format: 'txt' | 'pdf'): Promise<void> => {
    const response = await apiClient.get(`activation-templates/${id}/export`, {
      params: { format },
      responseType: 'blob',
    })
    const disposition = response.headers['content-disposition']
    const match = disposition && disposition.match(/filename="?([^";]+)"?/)
    const filename = match ? match[1] : `activation-template.${format}`
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const a = document.createElement('a')
    a.href = url
    a.setAttribute('download', filename)
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  },

  /** Create template from uploaded TXT or PDF file */
  createFromFile: async (file: File): Promise<ActivationTemplate> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('activation-templates/from-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}
