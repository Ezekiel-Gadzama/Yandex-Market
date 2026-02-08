import apiClient from './client'

export interface ProductTemplate {
  id: number
  name: string
  template_data: Record<string, any>
  created_at: string
  updated_at?: string
}

export interface ProductTemplateCreate {
  name: string
  template_data: Record<string, any>
}

export interface ProductTemplateUpdate {
  name?: string
  template_data?: Record<string, any>
}

export const productTemplatesApi = {
  getAll: async () => {
    const response = await apiClient.get<ProductTemplate[]>('/product-templates/')
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<ProductTemplate>(`/product-templates/${id}`)
    return response.data
  },
  
  create: async (data: ProductTemplateCreate) => {
    const response = await apiClient.post<ProductTemplate>('/product-templates/', data)
    return response.data
  },
  
  update: async (id: number, data: ProductTemplateUpdate) => {
    const response = await apiClient.put<ProductTemplate>(`/product-templates/${id}`, data)
    return response.data
  },
  
  delete: async (id: number) => {
    await apiClient.delete(`/product-templates/${id}`)
  },
}
