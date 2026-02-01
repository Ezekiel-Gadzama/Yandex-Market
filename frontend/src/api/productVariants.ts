import apiClient from './client'

export interface ProductVariant {
  id: number
  product_id: number
  variant_name: string
  variant_sku?: string
  edition?: string
  platform?: string
  activation_territory?: string
  localization?: string
  selling_price: number
  original_price?: number
  cost_price: number
  is_active: boolean
  stock_quantity: number
  yandex_market_id?: string
  yandex_market_sku?: string
  is_synced: boolean
  profit: number
  profit_percentage: number
  created_at: string
  updated_at?: string
}

export interface ProductVariantCreate {
  variant_name: string
  variant_sku?: string
  edition?: string
  platform?: string
  activation_territory?: string
  localization?: string
  selling_price: number
  original_price?: number
  cost_price: number
  is_active?: boolean
  stock_quantity?: number
}

export interface ProductVariantUpdate {
  variant_name?: string
  variant_sku?: string
  edition?: string
  platform?: string
  activation_territory?: string
  localization?: string
  selling_price?: number
  original_price?: number
  cost_price?: number
  is_active?: boolean
  stock_quantity?: number
}

export const productVariantsApi = {
  getProductVariants: async (productId: number) => {
    const response = await apiClient.get<ProductVariant[]>(`/products/${productId}/variants`)
    return response.data
  },
  
  createVariant: async (productId: number, data: ProductVariantCreate) => {
    const response = await apiClient.post<ProductVariant>(`/products/${productId}/variants`, data)
    return response.data
  },
  
  updateVariant: async (variantId: number, data: ProductVariantUpdate) => {
    const response = await apiClient.put<ProductVariant>(`/variants/${variantId}`, data)
    return response.data
  },
  
  deleteVariant: async (variantId: number) => {
    await apiClient.delete(`/variants/${variantId}`)
  },
  
  syncVariantToYandex: async (variantId: number) => {
    const response = await apiClient.post(`/variants/${variantId}/sync-to-yandex`)
    return response.data
  },
}
