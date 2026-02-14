import apiClient from './client'

export interface Client {
  id: number
  name: string
  email: string
  purchased_product_ids: number[]
  product_quantities?: { [productId: number]: number }
  order_ids: string[]
  created_at: string
  updated_at?: string
}

export interface ClientCreate {
  name: string
  email: string
  purchased_product_ids?: number[]
}

export interface ClientUpdate {
  name?: string
  email?: string
  purchased_product_ids?: number[]
}

export const clientsApi = {
  getAll: async (params?: { product_id?: number; search?: string; start_date?: string; end_date?: string }): Promise<Client[]> => {
    const response = await apiClient.get('clients/', { params })
    return response.data
  },

  create: async (data: ClientCreate): Promise<Client> => {
    const response = await apiClient.post('clients/', data)
    return response.data
  },

  update: async (id: number, data: ClientUpdate): Promise<Client> => {
    const response = await apiClient.put(`clients/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`clients/${id}`)
  },

  incrementPurchase: async (clientId: number, productId: number): Promise<{ message: string; new_quantity: number; last_purchase_date?: string }> => {
    const response = await apiClient.post(`clients/${clientId}/increment-purchase/${productId}`)
    return response.data
  },

  decrementPurchase: async (clientId: number, productId: number): Promise<{ message: string; new_quantity: number; previous_last_purchase_date?: string }> => {
    const response = await apiClient.post(`clients/${clientId}/decrement-purchase/${productId}`)
    return response.data
  },

  createFromOrder: async (orderId: string, email?: string, name?: string): Promise<Client> => {
    const payload: any = {
      order_id: orderId,
    }
    // Only include email if it's provided and not empty
    if (email !== undefined && email !== null && email !== '') {
      payload.email = email
    }
    // Only include name if it's provided and not empty
    if (name !== undefined && name !== null && name !== '') {
      payload.name = name
    }
    const response = await apiClient.post('clients/create-from-order', payload)
    return response.data
  },
}
