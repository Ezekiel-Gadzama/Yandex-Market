import apiClient from './client'

export interface SyncResult {
  success: boolean
  products_synced: number
  products_created: number
  products_updated: number
  errors: string[]
}

export const syncApi = {
  syncAll: async (force: boolean = false) => {
    const response = await apiClient.post<SyncResult>('/sync/', null, {
      params: { force }
    })
    return response.data
  },
  
  syncProducts: async (force: boolean = false) => {
    const response = await apiClient.post<SyncResult>('/sync/products', null, {
      params: { force }
    })
    return response.data
  },
  
  syncOrders: async () => {
    const response = await apiClient.post('/sync/orders')
    return response.data
  },
}
