import apiClient from './client'

export interface UploadedFile {
  url: string
  type: 'image' | 'video' | 'file'
  name: string
}

export const mediaApi = {
  // Unified upload function - accepts any file type
  // context: 'marketing' for marketing emails, 'documentation' for documentation files
  uploadFiles: async (files: File[], context: 'marketing' | 'documentation' = 'marketing'): Promise<UploadedFile[]> => {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    const response = await apiClient.post<UploadedFile[]>(`/media/upload?context=${context}`, formData, {
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
    if (path.startsWith('http')) return path
    if (path.startsWith('/')) return path
    return `/api/media/files/${path}`
  },

  // Simple function to ensure file URL is properly encoded - handles ALL special characters
  encodeFileUrl: (fileUrl: string): string => {
    if (!fileUrl) return fileUrl
    if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) {
      return fileUrl
    }
    if (fileUrl.startsWith('/api/media/files/')) {
      const pathPart = fileUrl.replace('/api/media/files/', '')
      // Decode segment by segment to handle partial encoding
      const parts = pathPart.split('/')
      const decodedParts = parts.map(p => {
        try {
          return decodeURIComponent(p)
        } catch {
          return p
        }
      })
      // Re-encode each segment - this ensures ALL special chars are encoded
      const encodedParts = decodedParts.map(p => encodeURIComponent(p))
      const result = `/api/media/files/${encodedParts.join('/')}`
      console.log('🔗 encodeFileUrl:', { input: fileUrl, output: result })
      return result
    }
    return fileUrl
  },
  
  // Simple function to get filename for display
  decodeFileName: (fileUrl: string): string => {
    try {
      const filename = fileUrl.split('/').pop() || fileUrl
      return decodeURIComponent(filename)
    } catch {
      return fileUrl.split('/').pop() || fileUrl
    }
  },
}
