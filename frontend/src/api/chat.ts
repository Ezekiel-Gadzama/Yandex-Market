import apiClient from './client'

export interface ChatMessage {
  id: string
  text: string
  author: 'SELLER' | 'CUSTOMER' | 'SYSTEM'
  created_at?: string
  order_id?: string
}

export const chatApi = {
  getOrderMessages: async (orderId: string) => {
    const response = await apiClient.get<ChatMessage[]>(`chat/orders/${orderId}/messages`)
    return response.data
  },
  
  sendOrderMessage: async (orderId: string, text: string) => {
    const response = await apiClient.post(`chat/orders/${orderId}/messages`, { text })
    return response.data
  },
  
  getUnreadCount: async (orderId: string) => {
    const response = await apiClient.get<{ unread_count: number }>(`chat/orders/${orderId}/unread-count`)
    return response.data.unread_count
  },
  
  markAsRead: async (orderId: string) => {
    const response = await apiClient.post(`chat/orders/${orderId}/mark-read`)
    return response.data
  },
}
