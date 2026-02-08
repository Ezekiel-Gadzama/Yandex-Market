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
}
