import apiClient from './client'

export interface User {
  id: number
  email: string
  name?: string | null
  is_admin: boolean
  created_by_id: number | null
  permissions: UserPermissions
  is_active: boolean
  business_name?: string | null
  business_username?: string | null
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
  business_name?: string
  business_username?: string  // e.g. @Goal_sale
}

export interface UserLogin {
  business_identifier: string  // Admin email OR business username (e.g. @Goal_sale)
  email: string
  password: string
}

export interface ChangePassword {
  previous_password: string
  new_password: string
}

export interface PasswordResetRequest {
  identifier: string  // Admin email OR business username (e.g. @Goal_sale)
}

export interface PasswordReset {
  token: string
  new_password: string
}

export interface PasswordResetWithPrevious {
  business_identifier: string  // Admin email OR business username (e.g. @Goal_sale)
  staff_email: string
  previous_password: string
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

  resetPasswordWithPrevious: async (data: PasswordResetWithPrevious): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/reset-password-with-previous', data)
    return response.data
  },

  changePassword: async (data: ChangePassword): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/auth/change-password', data)
    return response.data
  },
}
