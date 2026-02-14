import apiClient from './client'

export interface OrderItem {
  product_id: number
  product_name: string
  quantity: number
  item_price: number
  item_total: number
  yandex_item_id?: number | null
  yandex_offer_id?: string | null
  activation_code_sent: boolean
  activation_key_id?: number | null
  email_template_id?: number | null
  documentation_id?: number | null
}

export interface Order {
  id: number
  yandex_order_id: string
  product_id: number
  product_name?: string
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  quantity: number
  total_amount: number
  status: 'pending' | 'processing' | 'completed' | 'finished' | 'cancelled' | 'failed'
  activation_code_sent: boolean
  activation_code_sent_at?: string
  profit: number
  items?: OrderItem[]  // All products/items in this order
  items_count?: number  // Number of products in this order
  delivery_type?: 'DIGITAL' | 'DELIVERY' | null  // Delivery type from Yandex API
  has_client?: boolean  // Whether a client already exists for this order
  created_at: string
  updated_at?: string
  completed_at?: string
  order_created_at?: string  // Actual order creation date from Yandex API
}

export const ordersApi = {
  getAll: async (params?: { status?: string; start_date?: string; end_date?: string }) => {
    const response = await apiClient.get<Order[]>('/orders/', { params })
    return response.data
  },
  
  getById: async (id: number) => {
    const response = await apiClient.get<Order>(`/orders/${id}`)
    return response.data
  },
  
  fulfill: async (id: number) => {
    const response = await apiClient.post(`/orders/${id}/fulfill`)
    return response.data
  },
  
  complete: async (id: number, activationKeys?: Record<number, string>) => {
    const response = await apiClient.post(`/orders/${id}/complete`, activationKeys ? { activation_keys: activationKeys } : undefined)
    return response.data
  },
  
  markFinished: async (id: number) => {
    const response = await apiClient.post(`/orders/${id}/mark-finished`)
    return response.data
  },
}
