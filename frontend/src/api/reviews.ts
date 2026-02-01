import apiClient from './client'

export interface Review {
  id: string
  rating: number
  text: string
  author: {
    name: string
    id?: string
  }
  created_at?: string
  product?: {
    name: string
    id?: string
  }
}

export interface ReviewResponse {
  reviews: Review[]
  average_rating: number
  total_reviews: number
  rating_breakdown: {
    5: number
    4: number
    3: number
    2: number
    1: number
  }
}

export interface RatingSummary {
  average_rating: number
  total_reviews: number
  rating_breakdown: {
    5: number
    4: number
    3: number
    2: number
    1: number
  }
}

export const reviewsApi = {
  getProductReviews: async (productId?: string, limit: number = 50) => {
    const response = await apiClient.get<ReviewResponse>('/reviews/products', {
      params: { product_id: productId, limit }
    })
    return response.data
  },
  
  getProductRating: async (productId: string) => {
    const response = await apiClient.get<RatingSummary>(`/reviews/products/${productId}/rating`)
    return response.data
  },
  
  replyToProductReview: async (reviewId: string, text: string) => {
    const response = await apiClient.post(`/reviews/products/${reviewId}/reply`, { text })
    return response.data
  },
  
  getShopReviews: async (limit: number = 50) => {
    const response = await apiClient.get<ReviewResponse>('/reviews/shop', { params: { limit } })
    return response.data
  },
  
  getShopRating: async () => {
    const response = await apiClient.get<RatingSummary>('/reviews/shop/rating')
    return response.data
  },
  
  replyToShopReview: async (reviewId: string, text: string) => {
    const response = await apiClient.post(`/reviews/shop/${reviewId}/reply`, { text })
    return response.data
  },
}
