import apiClient from './client'

export interface User {
  id: number
  email: string
  is_admin: boolean
  created_by_id: number | null
  permissions: UserPermissions
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface UserPermissions {
  view_staff: boolean
  view_settings: boolean
  client_right: boolean
  view_marketing_emails: boolean
  dashboard_right: boolean
  view_product_prices: boolean
}

export interface Token {
  access_token: string
  token_type: string
  user: User
}

export interface UserSignup {
  email: string
  password: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordReset {
  token: string
  new_password: string
}

export const authApi = {
  signup: async (data: UserSignup): Promise<Token> => {
    const response = await apiClient.post<Token>('/auth/signup', data)
    return response.data
  },

  login: async (data: UserLogin): Promise<Token> => {
    const response = await apiClient.post<Token>('/auth/login', data)
    return response.data
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  requestPasswordReset: async (data: PasswordResetRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/request-password-reset', data)
    return response.data
  },

  resetPassword: async (data: PasswordReset): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/reset-password', data)
    return response.data
  },
}
