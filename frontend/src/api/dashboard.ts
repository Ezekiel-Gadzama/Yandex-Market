import apiClient from './client'
import { Order } from './orders'

export interface DashboardStats {
  total_products: number
  active_products: number
  total_orders: number
  pending_orders: number
  processing_orders: number
  completed_orders: number
  cancelled_orders: number
  finished_orders: number
  successful_orders: number
  total_revenue: number
  total_profit: number
  total_cost: number
  profit_margin: number
}

export interface TopProduct {
  product_id: number
  product_name: string
  total_sales: number
  total_revenue: number
  total_profit: number
}

export interface ExtraCost {
  id: number
  business_id: number
  description: string
  amount: number
  date: string
  created_at: string
}

export interface DashboardData {
  stats: DashboardStats
  top_products: TopProduct[]
  recent_orders: Order[]
  extra_costs: ExtraCost[]
}

export interface DateRange {
  startDate?: string
  endDate?: string
}

export const dashboardApi = {
  getStats: async (period?: string, dateRange?: DateRange) => {
    const params: any = {}
    if (period && period !== 'custom') {
      params.period = period
    }
    if (dateRange?.startDate && dateRange?.endDate) {
      params.start_date = dateRange.startDate
      params.end_date = dateRange.endDate
    }
    const response = await apiClient.get<DashboardStats>('/dashboard/stats', { params })
    return response.data
  },
  
  getTopProducts: async (limit: number = 10, period?: string, dateRange?: DateRange) => {
    const params: any = { limit }
    if (period && period !== 'custom') {
      params.period = period
    }
    if (dateRange?.startDate && dateRange?.endDate) {
      params.start_date = dateRange.startDate
      params.end_date = dateRange.endDate
    }
    const response = await apiClient.get<TopProduct[]>('/dashboard/top-products', { params })
    return response.data
  },
  
  getRecentOrders: async (limit: number = 10) => {
    const response = await apiClient.get<Order[]>('/dashboard/recent-orders', {
      params: { limit }
    })
    return response.data
  },
  
  getData: async (period?: string, dateRange?: DateRange) => {
    const params: any = {}
    if (period && period !== 'custom') {
      params.period = period
    }
    if (dateRange?.startDate && dateRange?.endDate) {
      params.start_date = dateRange.startDate
      params.end_date = dateRange.endDate
    }
    const response = await apiClient.get<DashboardData>('/dashboard/data', { params })
    return response.data
  },

  createExtraCost: async (payload: { description: string; amount: number; date: string }) => {
    const response = await apiClient.post<ExtraCost>('/dashboard/extra-costs', payload)
    return response.data
  },

  updateExtraCost: async (id: number, payload: { description?: string; amount?: number; date?: string }) => {
    const response = await apiClient.patch<ExtraCost>(`/dashboard/extra-costs/${id}`, payload)
    return response.data
  },

  deleteExtraCost: async (id: number) => {
    await apiClient.delete(`/dashboard/extra-costs/${id}`)
  },
}
