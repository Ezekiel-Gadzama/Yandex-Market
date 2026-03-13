import apiClient from './client'

export interface ChatMessage {
  id: string
  text: string
  author: 'SELLER' | 'CUSTOMER' | 'SYSTEM'
  created_at?: string
  order_id?: string
  attachments?: {
    url: string
    type: 'image' | 'video' | 'file'
    name: string
  }[]
}

export interface ChatListItem {
  chatId: number
  type: 'CHAT' | 'ARBITRAGE'
  status: string
  createdAt?: string
  updatedAt?: string
  orderId?: number
  returnId?: number
  context?: any
}

export const chatApi = {
  getOrderMessages: async (orderId: string) => {
    const response = await apiClient.get<ChatMessage[]>(`chat/orders/${orderId}/messages`)
    return response.data
  },
  
  sendOrderMessage: async (orderId: string, text: string, attachments?: { url: string; type: string; name: string }[]) => {
    const payload: any = { text }
    if (attachments && attachments.length > 0) {
      payload.attachments = attachments
    }
    const response = await apiClient.post(`chat/orders/${orderId}/messages`, payload)
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

  listChats: async (limit: number = 20, pageToken?: string) => {
    const params: any = { limit }
    if (pageToken) params.page_token = pageToken
    const response = await apiClient.get<{ chats: ChatListItem[]; nextPageToken?: string }>(`chat/chats`, { params })
    return response.data
  },

  getChatMessages: async (chatId: number, limit: number = 100, pageToken?: string) => {
    const params: any = { limit }
    if (pageToken) params.page_token = pageToken
    const response = await apiClient.get<{ context: any; messages: ChatMessage[]; nextPageToken?: string }>(
      `chat/chats/${chatId}/messages`,
      { params }
    )
    return response.data
  },

  sendChatMessage: async (chatId: number, text: string) => {
    const response = await apiClient.post(`chat/chats/${chatId}/messages`, { text })
    return response.data
  },
}
