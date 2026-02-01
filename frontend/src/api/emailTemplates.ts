import apiClient from './client'

export interface EmailTemplate {
  id: number
  name: string
  subject: string
  body: string
  created_at: string
  updated_at?: string
}

export interface EmailTemplateCreate {
  name: string
  subject: string
  body: string
}

export interface EmailTemplateUpdate {
  name?: string
  subject?: string
  body?: string
}

export const emailTemplatesApi = {
  getAll: async () => {
    const response = await apiClient.get<EmailTemplate[]>('/email-templates')
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<EmailTemplate>(`/email-templates/${id}`)
    return response.data
  },
  
  create: async (data: EmailTemplateCreate) => {
    const response = await apiClient.post<EmailTemplate>('/email-templates', data)
    return response.data
  },
  
  update: async (id: number, data: EmailTemplateUpdate) => {
    const response = await apiClient.put<EmailTemplate>(`/email-templates/${id}`, data)
    return response.data
  },
  
  delete: async (id: number) => {
    await apiClient.delete(`/email-templates/${id}`)
  },
}
