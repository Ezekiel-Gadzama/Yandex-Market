import apiClient from './client'

export interface UploadedFile {
  url: string
  type: 'image' | 'video' | 'file'
  name: string
}

export const mediaApi = {
  // Unified upload function - accepts any file type
  uploadFiles: async (files: File[]): Promise<UploadedFile[]> => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    const response = await apiClient.post<UploadedFile[]>('/media/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  
  // Legacy functions for backward compatibility (deprecated - use uploadFiles)
  uploadImages: async (files: File[]) => {
    const result = await mediaApi.uploadFiles(files)
    return result.map(f => f.url)
  },
  
  uploadVideos: async (files: File[]) => {
    const result = await mediaApi.uploadFiles(files)
    return result.map(f => f.url)
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
