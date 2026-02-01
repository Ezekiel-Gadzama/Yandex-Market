import apiClient from './client'

export interface Order {
  id: number
  yandex_order_id: string
  product_id: number
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  quantity: number
  total_amount: number
  status: 'pending' | 'processing' | 'completed' | 'cancelled' | 'failed'
  activation_code_sent: boolean
  activation_code_sent_at?: string
  profit: number
  created_at: string
  updated_at?: string
  completed_at?: string
}

export const ordersApi = {
  getAll: async (params?: { status?: string }) => {
    const response = await apiClient.get<Order[]>('/orders', { params })
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
  
  sendActivationEmail: async (id: number) => {
    const response = await apiClient.post(`/orders/${id}/send-activation-email`)
    return response.data
  },
  
  complete: async (id: number) => {
    const response = await apiClient.post(`/orders/${id}/complete`)
    return response.data
  },
}
