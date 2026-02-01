import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi, Product, ProductCreate } from '../api/products'
import { mediaApi } from '../api/media'
import { Plus, Edit, Trash2, Upload, Key, Search, X, Image, Video } from 'lucide-react'

export default function Products() {
  const [showModal, setShowModal] = useState(false)
  const [editingProduct, setEditingProduct] = useState<Product | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [uploadedVideos, setUploadedVideos] = useState<string[]>([])
  const [imageFiles, setImageFiles] = useState<File[]>([])
  const [videoFiles, setVideoFiles] = useState<File[]>([])
  const imageInputRef = useRef<HTMLInputElement>(null)
  const videoInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: products, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
  })

  const createMutation = useMutation({
    mutationFn: (data: ProductCreate) => productsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setShowModal(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ProductCreate> }) =>
      productsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setShowModal(false)
      setEditingProduct(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (id: number) => productsApi.uploadToYandex(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  const generateKeysMutation = useMutation({
    mutationFn: ({ id, count }: { id: number; count: number }) =>
      productsApi.generateKeys(id, count),
    onSuccess: () => {
      alert('Activation keys generated successfully!')
    },
  })

  const uploadImagesMutation = useMutation({
    mutationFn: (files: File[]) => mediaApi.uploadImages(files),
    onSuccess: (paths) => {
      setUploadedImages(prev => [...prev, ...paths])
      setImageFiles([])
    },
  })

  const uploadVideosMutation = useMutation({
    mutationFn: (files: File[]) => mediaApi.uploadVideos(files),
    onSuccess: (paths) => {
      setUploadedVideos(prev => [...prev, ...paths])
      setVideoFiles([])
    },
  })

  const filteredProducts = products?.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleImageUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const fileArray = Array.from(files)
    setImageFiles(prev => [...prev, ...fileArray])
    uploadImagesMutation.mutate(fileArray)
  }

  const handleVideoUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const fileArray = Array.from(files)
    setVideoFiles(prev => [...prev, ...fileArray])
    uploadVideosMutation.mutate(fileArray)
  }

  const removeImage = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const removeVideo = (index: number) => {
    setUploadedVideos(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    // Combine uploaded files with any URL inputs
    const imagesStr = formData.get('yandex_images_urls') as string
    const videosStr = formData.get('yandex_videos_urls') as string
    const urlImages = imagesStr ? imagesStr.split(',').map(url => url.trim()).filter(url => url) : []
    const urlVideos = videosStr ? videosStr.split(',').map(url => url.trim()).filter(url => url) : []
    
    // Combine uploaded paths with URLs
    const images = [...uploadedImages, ...urlImages].filter(Boolean)
    const videos = [...uploadedVideos, ...urlVideos].filter(Boolean)
    
    const data: ProductCreate = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      product_type: (formData.get('product_type') as 'digital' | 'physical') || 'digital',
      cost_price: parseFloat(formData.get('cost_price') as string),
      selling_price: parseFloat(formData.get('selling_price') as string),
      supplier_url: formData.get('supplier_url') as string || undefined,
      supplier_name: formData.get('supplier_name') as string || undefined,
      // Yandex Market fields
      yandex_model: formData.get('yandex_model') as string || (formData.get('product_type') === 'digital' ? 'DBS' : undefined),
      yandex_category_id: formData.get('yandex_category_id') as string || undefined,
      yandex_category_path: formData.get('yandex_category_path') as string || undefined,
      yandex_brand: formData.get('yandex_brand') as string || undefined,
      yandex_platform: formData.get('yandex_platform') as string || undefined,
      yandex_localization: formData.get('yandex_localization') as string || undefined,
      yandex_publication_type: formData.get('yandex_publication_type') as string || undefined,
      yandex_activation_territory: formData.get('yandex_activation_territory') as string || undefined,
      yandex_edition: formData.get('yandex_edition') as string || undefined,
      yandex_series: formData.get('yandex_series') as string || undefined,
      yandex_age_restriction: formData.get('yandex_age_restriction') as string || undefined,
      yandex_activation_instructions: formData.get('yandex_activation_instructions') === 'on',
      original_price: formData.get('original_price') ? parseFloat(formData.get('original_price') as string) : undefined,
      discount_percentage: formData.get('discount_percentage') ? parseFloat(formData.get('discount_percentage') as string) : undefined,
      yandex_images: images.length > 0 ? images : undefined,
      yandex_videos: videos.length > 0 ? videos : undefined,
    }

    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, data })
    } else {
      createMutation.mutate(data)
    }
    
    // Reset uploads after submit
    setUploadedImages([])
    setUploadedVideos([])
    setImageFiles([])
    setVideoFiles([])
  }

  // Initialize uploaded media when editing
  const handleEdit = (product: Product) => {
    setEditingProduct(product)
    // Extract local paths from URLs (remove /api/media/files/ prefix)
    const imagePaths = (product.yandex_images || []).map(url => {
      if (url.includes('/api/media/files/')) {
        return url.replace('/api/media/files/', '')
      }
      return url
    })
    const videoPaths = (product.yandex_videos || []).map(url => {
      if (url.includes('/api/media/files/')) {
        return url.replace('/api/media/files/', '')
      }
      return url
    })
    setUploadedImages(imagePaths)
    setUploadedVideos(videoPaths)
    setShowModal(true)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingProduct(null)
    setUploadedImages([])
    setUploadedVideos([])
    setImageFiles([])
    setVideoFiles([])
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>
        <button
          onClick={() => {
            setEditingProduct(null)
            setUploadedImages([])
            setUploadedVideos([])
            setImageFiles([])
            setVideoFiles([])
            setShowModal(true)
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Product
        </button>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search products..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full max-w-md"
          />
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Profit
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center">Loading...</td>
              </tr>
            ) : filteredProducts && filteredProducts.length > 0 ? (
              filteredProducts.map((product) => (
                <tr key={product.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{product.name}</div>
                    {product.description && (
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {product.description}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                      {product.product_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₽{product.cost_price.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₽{product.selling_price.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-green-600">
                      ₽{product.profit.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-xs text-gray-500">
                      {product.profit_percentage.toFixed(1)}%
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      product.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {product.is_synced && (
                      <span className="ml-2 px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        Synced
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end space-x-2">
                      {product.product_type === 'digital' && !product.is_synced && (
                        <button
                          onClick={() => uploadMutation.mutate(product.id)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Upload to Yandex"
                        >
                          <Upload className="h-5 w-5" />
                        </button>
                      )}
                      {product.product_type === 'digital' && (
                        <button
                          onClick={() => generateKeysMutation.mutate({ id: product.id, count: 10 })}
                          className="text-purple-600 hover:text-purple-900"
                          title="Generate Keys"
                        >
                          <Key className="h-5 w-5" />
                        </button>
                      )}
                      <button
                        onClick={() => handleEdit(product)}
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        <Edit className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Are you sure you want to delete this product?')) {
                            deleteMutation.mutate(product.id)
                          }
                        }}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  No products found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {editingProduct ? 'Edit Product' : 'Add Product'}
            </h3>
            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Basic Information */}
                <div className="md:col-span-2">
                  <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1">Basic Information</h4>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name *</label>
                  <input
                    type="text"
                    name="name"
                    required
                    defaultValue={editingProduct?.name}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Type *</label>
                  <select
                    name="product_type"
                    defaultValue={editingProduct?.product_type || 'digital'}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="digital">Digital</option>
                    <option value="physical">Physical</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    name="description"
                    rows={3}
                    defaultValue={editingProduct?.description}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>

                {/* Pricing */}
                <div className="md:col-span-2">
                  <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1 mt-4">Pricing</h4>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cost Price (₽) *</label>
                  <input
                    type="number"
                    name="cost_price"
                    step="0.01"
                    required
                    defaultValue={editingProduct?.cost_price}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Selling Price (₽) *</label>
                  <input
                    type="number"
                    name="selling_price"
                    step="0.01"
                    required
                    defaultValue={editingProduct?.selling_price}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Original Price (₽) - for discount</label>
                  <input
                    type="number"
                    name="original_price"
                    step="0.01"
                    defaultValue={editingProduct?.original_price}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Discount Percentage (%)</label>
                  <input
                    type="number"
                    name="discount_percentage"
                    step="0.01"
                    defaultValue={editingProduct?.discount_percentage}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>

                {/* Supplier Information */}
                <div className="md:col-span-2">
                  <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1 mt-4">Supplier Information</h4>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Supplier URL</label>
                  <input
                    type="url"
                    name="supplier_url"
                    defaultValue={editingProduct?.supplier_url}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Supplier Name</label>
                  <input
                    type="text"
                    name="supplier_name"
                    defaultValue={editingProduct?.supplier_name}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>

                {/* Yandex Market Details */}
                <div className="md:col-span-2">
                  <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1 mt-4">Yandex Market Details</h4>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Model (DBS for digital) *</label>
                  <input
                    type="text"
                    name="yandex_model"
                    defaultValue={editingProduct?.yandex_model || 'DBS'}
                    placeholder="DBS"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Category ID</label>
                  <input
                    type="text"
                    name="yandex_category_id"
                    defaultValue={editingProduct?.yandex_category_id}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Category Path</label>
                  <input
                    type="text"
                    name="yandex_category_path"
                    defaultValue={editingProduct?.yandex_category_path}
                    placeholder="Electronics > Gaming > Games"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Brand</label>
                  <input
                    type="text"
                    name="yandex_brand"
                    defaultValue={editingProduct?.yandex_brand}
                    placeholder="e.g., Sony"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Platform</label>
                  <input
                    type="text"
                    name="yandex_platform"
                    defaultValue={editingProduct?.yandex_platform}
                    placeholder="e.g., PlayStation 4, PlayStation 5"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Localization</label>
                  <input
                    type="text"
                    name="yandex_localization"
                    defaultValue={editingProduct?.yandex_localization}
                    placeholder="e.g., Russian subtitles"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Publication Type</label>
                  <input
                    type="text"
                    name="yandex_publication_type"
                    defaultValue={editingProduct?.yandex_publication_type}
                    placeholder="e.g., complete"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Activation Territory</label>
                  <input
                    type="text"
                    name="yandex_activation_territory"
                    defaultValue={editingProduct?.yandex_activation_territory || 'all countries'}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Edition</label>
                  <input
                    type="text"
                    name="yandex_edition"
                    defaultValue={editingProduct?.yandex_edition}
                    placeholder="e.g., The Trilogy"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Series</label>
                  <input
                    type="text"
                    name="yandex_series"
                    defaultValue={editingProduct?.yandex_series}
                    placeholder="e.g., PlayStation"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Age Restriction</label>
                  <input
                    type="text"
                    name="yandex_age_restriction"
                    defaultValue={editingProduct?.yandex_age_restriction}
                    placeholder="e.g., 18+"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      name="yandex_activation_instructions"
                      defaultChecked={editingProduct?.yandex_activation_instructions !== false}
                      className="mr-2"
                    />
                    <span className="text-sm font-medium text-gray-700">Has Activation Instructions</span>
                  </label>
                </div>

                {/* Media */}
                <div className="md:col-span-2">
                  <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1 mt-4">Media (Images & Videos)</h4>
                </div>
                
                {/* Image Upload */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Images</label>
                  <div className="space-y-2">
                    <div
                      className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 cursor-pointer transition-colors"
                      onClick={() => imageInputRef.current?.click()}
                      onDragOver={(e) => {
                        e.preventDefault()
                        e.currentTarget.classList.add('border-blue-400')
                      }}
                      onDragLeave={(e) => {
                        e.currentTarget.classList.remove('border-blue-400')
                      }}
                      onDrop={(e) => {
                        e.preventDefault()
                        e.currentTarget.classList.remove('border-blue-400')
                        handleImageUpload(e.dataTransfer.files)
                      }}
                    >
                      <Image className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="mt-4">
                        <label className="cursor-pointer">
                          <span className="mt-2 block text-sm font-medium text-gray-900">
                            Drop images here or click to upload
                          </span>
                          <input
                            ref={imageInputRef}
                            type="file"
                            multiple
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => handleImageUpload(e.target.files)}
                          />
                        </label>
                        <p className="mt-1 text-xs text-gray-500">PNG, JPG, GIF up to 10MB</p>
                      </div>
                    </div>
                    
                    {/* Uploaded Images Preview */}
                    {uploadedImages.length > 0 && (
                      <div className="grid grid-cols-4 gap-2 mt-4">
                        {uploadedImages.map((path, idx) => (
                          <div key={idx} className="relative group">
                            <img
                              src={mediaApi.getMediaUrl(path)}
                              alt={`Upload ${idx + 1}`}
                              className="w-full h-24 object-cover rounded border"
                            />
                            <button
                              type="button"
                              onClick={() => removeImage(idx)}
                              className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Pending Uploads */}
                    {imageFiles.length > 0 && (
                      <div className="mt-2 text-sm text-gray-600">
                        Uploading {imageFiles.length} file(s)...
                      </div>
                    )}
                  </div>
                  
                  {/* URL Input for external images */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Or enter image URLs (comma-separated)</label>
                    <textarea
                      name="yandex_images_urls"
                      rows={2}
                      placeholder="https://example.com/image1.jpg, https://example.com/image2.jpg"
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                
                {/* Video Upload */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Videos</label>
                  <div className="space-y-2">
                    <div
                      className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 cursor-pointer transition-colors"
                      onClick={() => videoInputRef.current?.click()}
                      onDragOver={(e) => {
                        e.preventDefault()
                        e.currentTarget.classList.add('border-blue-400')
                      }}
                      onDragLeave={(e) => {
                        e.currentTarget.classList.remove('border-blue-400')
                      }}
                      onDrop={(e) => {
                        e.preventDefault()
                        e.currentTarget.classList.remove('border-blue-400')
                        handleVideoUpload(e.dataTransfer.files)
                      }}
                    >
                      <Video className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="mt-4">
                        <label className="cursor-pointer">
                          <span className="mt-2 block text-sm font-medium text-gray-900">
                            Drop videos here or click to upload
                          </span>
                          <input
                            ref={videoInputRef}
                            type="file"
                            multiple
                            accept="video/*"
                            className="hidden"
                            onChange={(e) => handleVideoUpload(e.target.files)}
                          />
                        </label>
                        <p className="mt-1 text-xs text-gray-500">MP4, MOV, AVI up to 100MB</p>
                      </div>
                    </div>
                    
                    {/* Uploaded Videos Preview */}
                    {uploadedVideos.length > 0 && (
                      <div className="grid grid-cols-4 gap-2 mt-4">
                        {uploadedVideos.map((path, idx) => (
                          <div key={idx} className="relative group">
                            <video
                              src={mediaApi.getMediaUrl(path)}
                              className="w-full h-24 object-cover rounded border"
                              controls={false}
                            />
                            <button
                              type="button"
                              onClick={() => removeVideo(idx)}
                              className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Pending Uploads */}
                    {videoFiles.length > 0 && (
                      <div className="mt-2 text-sm text-gray-600">
                        Uploading {videoFiles.length} file(s)...
                      </div>
                    )}
                  </div>
                  
                  {/* URL Input for external videos */}
                  <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Or enter video URLs (comma-separated)</label>
                    <textarea
                      name="yandex_videos_urls"
                      rows={2}
                      placeholder="https://example.com/video1.mp4, https://example.com/video2.mp4"
                      className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  {editingProduct ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
