import apiClient from './client'

export interface AppSettings {
  id: number
  processing_time_min: number
  processing_time_max?: number
  maximum_wait_time_value?: number
  maximum_wait_time_unit?: string
  working_hours_text?: string
  company_email?: string
  yandex_api_token?: string
  yandex_business_id?: string
  yandex_campaign_id?: string
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_email?: string
  secret_key?: string
  auto_activation_enabled: boolean
  auto_append_clients: boolean
  created_at: string
  updated_at?: string
}

export interface AppSettingsUpdate {
  processing_time_min?: number
  processing_time_max?: number
  maximum_wait_time_value?: number
  maximum_wait_time_unit?: string
  working_hours_text?: string
  company_email?: string
  yandex_api_token?: string
  yandex_business_id?: string
  yandex_campaign_id?: string
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_email?: string
  secret_key?: string
  auto_activation_enabled?: boolean
  auto_append_clients?: boolean
}

export const settingsApi = {
  get: async () => {
    const response = await apiClient.get<AppSettings>('settings/')
    return response.data
  },
  
  update: async (data: AppSettingsUpdate) => {
    const response = await apiClient.put<AppSettings>('settings/', data)
    return response.data
  },
}
