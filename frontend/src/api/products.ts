import apiClient from './client'

export interface Product {
  id: number
  name: string
  description?: string
  product_type: 'digital' | 'physical'
  cost_price: number
  selling_price: number
  supplier_url?: string
  supplier_name?: string
  yandex_market_id?: string
  yandex_market_sku?: string
  email_template_id?: number
  is_active: boolean
  is_synced: boolean
  profit: number
  profit_percentage: number
  created_at: string
  updated_at?: string
  // Yandex Market fields
  yandex_model?: string
  yandex_category_id?: string
  yandex_category_path?: string
  yandex_brand?: string
  yandex_platform?: string
  yandex_localization?: string
  yandex_publication_type?: string
  yandex_activation_territory?: string
  yandex_edition?: string
  yandex_series?: string
  yandex_age_restriction?: string
  yandex_activation_instructions?: boolean
  original_price?: number
  discount_percentage?: number
  yandex_images?: string[]
  yandex_videos?: string[]
}

export interface ProductCreate {
  name: string
  description?: string
  product_type: 'digital' | 'physical'
  cost_price: number
  selling_price: number
  supplier_url?: string
  supplier_name?: string
  yandex_market_id?: string
  yandex_market_sku?: string
  email_template_id?: number
  is_active?: boolean
  // Yandex Market fields
  yandex_model?: string
  yandex_category_id?: string
  yandex_category_path?: string
  yandex_brand?: string
  yandex_platform?: string
  yandex_localization?: string
  yandex_publication_type?: string
  yandex_activation_territory?: string
  yandex_edition?: string
  yandex_series?: string
  yandex_age_restriction?: string
  yandex_activation_instructions?: boolean
  original_price?: number
  discount_percentage?: number
  yandex_images?: string[]
  yandex_videos?: string[]
}

export interface ProductUpdate {
  name?: string
  description?: string
  product_type?: 'digital' | 'physical'
  cost_price?: number
  selling_price?: number
  supplier_url?: string
  supplier_name?: string
  email_template_id?: number
  is_active?: boolean
  // Yandex Market fields
  yandex_model?: string
  yandex_category_id?: string
  yandex_category_path?: string
  yandex_brand?: string
  yandex_platform?: string
  yandex_localization?: string
  yandex_publication_type?: string
  yandex_activation_territory?: string
  yandex_edition?: string
  yandex_series?: string
  yandex_age_restriction?: string
  yandex_activation_instructions?: boolean
  original_price?: number
  discount_percentage?: number
  yandex_images?: string[]
  yandex_videos?: string[]
}

export const productsApi = {
  getAll: async (params?: { is_active?: boolean; product_type?: string }) => {
    const response = await apiClient.get<Product[]>('/products', { params })
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<Product>(`/products/${id}`)
    return response.data
  },
  
  create: async (data: ProductCreate) => {
    const response = await apiClient.post<Product>('/products', data)
    return response.data
  },
  
  update: async (id: number, data: ProductUpdate) => {
    const response = await apiClient.put<Product>(`/products/${id}`, data)
    return response.data
  },
  
  delete: async (id: number) => {
    await apiClient.delete(`/products/${id}`)
  },
  
  uploadToYandex: async (id: number) => {
    const response = await apiClient.post(`/products/${id}/upload-to-yandex`)
    return response.data
  },
  
  generateKeys: async (id: number, count: number = 10) => {
    const response = await apiClient.post(`/products/${id}/generate-keys`, null, {
      params: { count }
    })
    return response.data
  },
  
  getFullDetails: async (id: number) => {
    const response = await apiClient.get(`/products/${id}/full`)
    return response.data
  },
}
