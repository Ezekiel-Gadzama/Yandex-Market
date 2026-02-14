import apiClient from './client'

export interface Product {
  // Essential local fields
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
  documentation_id?: number
  yandex_purchase_link?: string
  usage_period?: number
  is_active: boolean
  is_synced: boolean
  profit: number
  profit_percentage: number
  created_at: string
  updated_at?: string
  // Full Yandex JSON data (all Yandex fields are stored here)
  yandex_full_data?: Record<string, any>
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
  documentation_id?: number
  is_active?: boolean
  yandex_full_data?: Record<string, any>  // For parameterValues and other Yandex fields
}

export interface ProductUpdate {
  // Essential local-only fields
  cost_price?: number
  supplier_url?: string
  supplier_name?: string
  email_template_id?: number | null
  documentation_id?: number | null
  yandex_purchase_link?: string | null
  usage_period?: number | null
  is_active?: boolean
  // Dynamic field updates from Yandex JSON (all Yandex fields are edited here)
  yandex_field_updates?: Record<string, any>
}

export const productsApi = {
  getAll: async (params?: { is_active?: boolean; product_type?: string; search?: string }) => {
    const response = await apiClient.get<Product[]>('/products/', { params })
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<Product>(`/products/${id}`)
    return response.data
  },
  
  create: async (data: ProductCreate) => {
    const response = await apiClient.post<Product>('/products/', data)
    return response.data
  },
  
  update: async (id: number, data: ProductUpdate) => {
    const response = await apiClient.put<Product>(`/products/${id}`, data)
    return response.data
  },
  
  // uploadToYandex removed - products can only be synced from Yandex Market
  
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
