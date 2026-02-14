import apiClient from './client'
import { User, UserPermissions } from './auth'

export interface StaffCreate {
  email: string
}

export interface UserUpdate {
  permissions?: UserPermissions
  is_active?: boolean
}

export const staffApi = {
  getAll: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>('/staff/')
    return response.data
  },

  create: async (data: StaffCreate): Promise<User> => {
    const response = await apiClient.post<User>('/staff/', data)
    return response.data
  },

  update: async (id: number, data: UserUpdate): Promise<User> => {
    const response = await apiClient.put<User>(`/staff/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/staff/${id}`)
  },

  resendPasswordReset: async (id: number): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/staff/${id}/resend-password-reset`)
    return response.data
  },
}
