import apiClient from './client'

export const mediaApi = {
  uploadImages: async (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    const response = await apiClient.post<string[]>('/media/upload/images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  uploadVideos: async (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    const response = await apiClient.post<string[]>('/media/upload/videos', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  getMediaUrl: (path: string) => {
    // If it's already a full URL, return as is
    if (path.startsWith('http')) {
      return path
    }
    // If it starts with /, it's already a path
    if (path.startsWith('/')) {
      return path
    }
    // Otherwise, prepend the media API path
    return `/api/media/files/${path}`
  },
}
