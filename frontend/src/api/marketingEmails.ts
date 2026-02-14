import apiClient from './client'

export interface Attachment {
  url: string
  type: 'image' | 'video' | 'file'
  name: string
}

export interface MarketingEmailTemplate {
  id: number
  name: string
  subject: string
  body: string
  attachments?: Attachment[]
  frequency_days?: number
  auto_broadcast_enabled: boolean
  is_default: boolean
  created_at: string
  updated_at?: string
}

export interface MarketingEmailTemplateCreate {
  name: string
  subject: string
  body: string
  attachments?: Attachment[]
  frequency_days?: number
  auto_broadcast_enabled?: boolean
  is_default?: boolean
}

export interface MarketingEmailTemplateUpdate {
  name?: string
  subject?: string
  body?: string
  attachments?: Attachment[]
  frequency_days?: number
  auto_broadcast_enabled?: boolean
  is_default?: boolean
}

export interface BroadcastFilters {
  product_ids?: number[]
  date_filter?: 'last_month' | 'last_3_months' | 'last_6_months' | 'last_year' | 'custom' | null
  custom_start_date?: string
  custom_end_date?: string
  min_product_quantity?: number
  min_total_products?: number
}

export interface BroadcastResponse {
  message: string
  sent_count: number
  template_id: number
  template_name: string
  filters_applied: string[]
}

export const marketingEmailsApi = {
  getAll: async (search?: string): Promise<MarketingEmailTemplate[]> => {
    const params = search ? { search } : {}
    const response = await apiClient.get('marketing-emails/', { params })
    return response.data
  },

  create: async (data: MarketingEmailTemplateCreate): Promise<MarketingEmailTemplate> => {
    const response = await apiClient.post('marketing-emails/', data)
    return response.data
  },

  update: async (id: number, data: MarketingEmailTemplateUpdate): Promise<MarketingEmailTemplate> => {
    const response = await apiClient.put(`marketing-emails/${id}`, data)
    return response.data
  },

  getById: async (id: number): Promise<MarketingEmailTemplate> => {
    const response = await apiClient.get(`marketing-emails/${id}`)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`marketing-emails/${id}`)
  },

  broadcast: async (id: number, filters: BroadcastFilters): Promise<BroadcastResponse> => {
    const response = await apiClient.post(`marketing-emails/${id}/broadcast`, filters)
    return response.data
  },
}
