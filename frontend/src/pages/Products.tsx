import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi, Product, ProductUpdate } from '../api/products'
import { activationTemplatesApi } from '../api/activationTemplates'
import { documentationsApi } from '../api/documentations'
import { reviewsApi } from '../api/reviews'
import { mediaApi } from '../api/media'
import { useAuth } from '../contexts/AuthContext'
import { Eye, X, Star, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'

export default function Products() {
  const { user } = useAuth()
  const canViewPrices = user?.is_admin || user?.permissions.view_product_prices
  const [viewingProduct, setViewingProduct] = useState<Product | null>(null)
  const [showViewModal, setShowViewModal] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [viewingDoc, setViewingDoc] = useState<number | null>(null)
  const [viewingTemplate, setViewingTemplate] = useState<number | null>(null)
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
  const [refreshSuccess, setRefreshSuccess] = useState(false)
  const queryClient = useQueryClient()

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ isOpen: true, type, message })
    // Auto-close after 4 seconds
    setTimeout(() => setNotification(prev => ({ ...prev, isOpen: false })), 4000)
  }

  const { data: products, isLoading: productsLoading, refetch: refetchProducts } = useQuery({
    queryKey: ['products', statusFilter, searchTerm],
    queryFn: () => productsApi.getAll({
      is_active: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
      search: searchTerm || undefined,
    }),
  })

  // Fetch all documentations and templates for the table
  const { data: allDocumentations } = useQuery({
    queryKey: ['documentations'],
    queryFn: () => documentationsApi.getAll(),
  })

  const { data: allTemplates } = useQuery({
    queryKey: ['activation-templates'],
    queryFn: () => activationTemplatesApi.getAll(),
  })
  

  const updateProductMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdate }) => productsApi.update(id, data),
    onSuccess: (updatedProduct) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['product-full', viewingProduct?.id] })
      // Update viewingProduct state with the updated product data
      if (viewingProduct && viewingProduct.id === updatedProduct.id) {
        setViewingProduct(updatedProduct)
      }
      showNotification('success', 'Product updated successfully on Yandex Market!')
    },
    onError: (error: any) => {
      showNotification('error', 'Failed to update product: ' + (error?.response?.data?.detail || error.message))
    },
  })

  const { data: fullProductDetails, isLoading: fullDetailsLoading } = useQuery({
    queryKey: ['product-full', viewingProduct?.id],
    queryFn: async () => {
      const data = await productsApi.getFullDetails(viewingProduct!.id)
      console.log('=== FULL PRODUCT API RESPONSE (PROCESSED - includes local DB fields) ===')
      console.log(JSON.stringify(data, null, 3))
      console.log('=== RAW YANDEX DATA ONLY (from yandex_full_data field) ===')
      if (data.yandex_full_data) {
        console.log(JSON.stringify(data.yandex_full_data, null, 2))
      } else {
        console.log('No yandex_full_data found - check backend logs for raw Yandex API response')
      }
      console.log('=== END OF API RESPONSE ===')
      console.log('NOTE: Check backend terminal/logs for the actual raw Yandex API response')
      return data
    },
    enabled: !!viewingProduct && showViewModal && viewingProduct.id > 0, // Only fetch if product ID is valid
  })



  // Products are already filtered by backend, no need for additional filtering
  const filteredProducts = products

  const handleViewProduct = async (product: Product) => {
    setViewingProduct(product)
    setShowViewModal(true)
  }



  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>
        <div className="flex gap-2">
          <button
            onClick={async () => {
              setRefreshSuccess(false)
              await refetchProducts()
              setRefreshSuccess(true)
              setTimeout(() => setRefreshSuccess(false), 2000)
            }}
            disabled={productsLoading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            title="Refresh products"
          >
            {refreshSuccess ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                <span className="text-green-600">✓</span>
              </>
            ) : (
              <>
                <RefreshCw className={`h-4 w-4 mr-2 ${productsLoading ? 'animate-spin' : ''}`} />
                Refresh
              </>
            )}
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search products by name, description, or activation key..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {/* Products Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
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
                Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Docs
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Activation
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {productsLoading ? (
              <tr>
                <td colSpan={8} className="px-6 py-4 text-center">Loading...</td>
              </tr>
            ) : filteredProducts && filteredProducts.length > 0 ? (
              filteredProducts.map((product) => (
                <tr key={product.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{product.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-500 capitalize">{product.product_type}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {canViewPrices ? (
                        `₽${(() => {
                          // Try to get price from Yandex data first
                          const yandexPrice = product.yandex_full_data?.basicPrice?.value || 
                                            product.yandex_full_data?.campaignPrice?.value ||
                                            product.yandex_full_data?.price
                          return (yandexPrice || product.selling_price || 0).toLocaleString('ru-RU')
                        })()}`
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {canViewPrices ? (
                        product.cost_price && product.cost_price > 0 ? (
                          `₽${product.cost_price.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        ) : (
                          <span className="text-gray-400">—</span>
                        )
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      product.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {product.documentation_id ? (
                      <button
                        onClick={() => setViewingDoc(product.documentation_id!)}
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        {allDocumentations?.find(d => d.id === product.documentation_id)?.name || `Doc #${product.documentation_id}`}
                      </button>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {product.email_template_id ? (
                      <button
                        onClick={() => setViewingTemplate(product.email_template_id!)}
                        className="text-blue-600 hover:text-blue-800 underline"
                      >
                        {allTemplates?.find(t => t.id === product.email_template_id)?.name || `Template #${product.email_template_id}`}
                      </button>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleViewProduct(product)}
                        className="text-indigo-600 hover:text-indigo-900"
                        title="View Details"
                      >
                        <Eye className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="px-6 py-4 text-center text-gray-500">
                  No products found
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* View Product Modal */}
      {showViewModal && viewingProduct && (
        <ProductViewModal
          product={viewingProduct}
          fullDetails={fullProductDetails}
          isLoading={fullDetailsLoading}
          onClose={() => {
            setShowViewModal(false)
            setViewingProduct(null)
          }}
          onUpdateProduct={(id, data) => updateProductMutation.mutate({ id, data })}
        />
      )}


      {/* Documentation View Modal */}
      {viewingDoc && (
        <DocumentationViewModal
          docId={viewingDoc}
          onClose={() => setViewingDoc(null)}
        />
      )}

      {/* Activation Template View Modal */}
      {viewingTemplate && (
        <ActivationTemplateViewModal
          templateId={viewingTemplate}
          onClose={() => setViewingTemplate(null)}
        />
      )}

      {/* Notification Popup */}
      {notification.isOpen && (
        <div className="fixed top-4 right-4 z-[60] animate-in slide-in-from-top">
          <div className={`flex items-center gap-3 px-5 py-4 rounded-lg shadow-lg border ${
            notification.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            {notification.type === 'success' ? (
              <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            )}
            <span className="text-sm font-medium">{notification.message}</span>
            <button
              onClick={() => setNotification(prev => ({ ...prev, isOpen: false }))}
              className="ml-2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// Product View Modal Component
function ProductViewModal({
  product,
  fullDetails,
  isLoading,
  onClose,
  onUpdateProduct,
}: {
  product: Product
  fullDetails?: any
  isLoading: boolean
  onClose: () => void
  onUpdateProduct: (id: number, data: ProductUpdate) => void
}) {
  const { user } = useAuth()
  const canViewPrices = user?.is_admin || user?.permissions.view_product_prices
  const [activeTab, setActiveTab] = useState<'details' | 'reviews'>('details')
  
  // Extract medias from yandex_full_data
  const getMedias = () => {
    const pictures = fullDetails?.yandex_full_data?.pictures || fullDetails?.yandex_full_data?.images || []
    const videos = fullDetails?.yandex_full_data?.videos || []
    
    // Combine into unified medias array with type indicator
    const medias: Array<{url: string, type: 'image' | 'video'}> = []
    if (Array.isArray(pictures)) {
      pictures.forEach((url: string) => {
        if (url) medias.push({ url, type: 'image' })
      })
    }
    if (Array.isArray(videos)) {
      videos.forEach((url: string) => {
        if (url) medias.push({ url, type: 'video' })
      })
    }
    return medias
  }
  
  const medias = getMedias()
  
  const { data: reviewsData } = useQuery({
    queryKey: ['product-reviews', product.yandex_market_id],
    queryFn: () => reviewsApi.getProductReviews(product.yandex_market_id),
    enabled: !!product.yandex_market_id,
  })
  
  const { data: ratingData } = useQuery({
    queryKey: ['product-rating', product.yandex_market_id],
    queryFn: () => reviewsApi.getProductRating(product.yandex_market_id!),
    enabled: !!product.yandex_market_id,
  })
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-5xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        {/* Sticky Header */}
        <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
          <h3 className="text-2xl font-bold text-gray-900">Product Details</h3>
          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-4">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('details')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'details'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Details
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'reviews'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Reviews & Ratings
              {ratingData && (
                <span className="ml-2 inline-flex items-center">
                  <Star className="h-4 w-4 text-yellow-400 fill-yellow-400 mr-1" />
                  {ratingData.average_rating.toFixed(1)}
                </span>
              )}
            </button>
          </nav>
        </div>

        {isLoading ? (
          <div className="text-center py-8">Loading full details...</div>
        ) : (
          <div className="space-y-6 flex-1 overflow-y-auto">
            {activeTab === 'details' && (
              <>
            {/* Basic Information */}
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Basic Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <p className="mt-1 text-sm text-gray-900">{product.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Type</label>
                  <p className="mt-1 text-sm text-gray-900 capitalize">{product.product_type}</p>
                </div>
                {product.product_type === 'digital' && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Activation Template</label>
                    <EmailTemplateSelector
                      productId={product.id}
                      currentTemplateId={product.email_template_id}
                      onUpdate={(templateId) => {
                        onUpdateProduct(product.id, { email_template_id: templateId ?? null })
                      }}
                    />
                  </div>
                )}
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Documentation</label>
                  <DocumentationSelector
                    productId={product.id}
                    currentDocumentationId={product.documentation_id}
                    onUpdate={(documentationId) => {
                      onUpdateProduct(product.id, { documentation_id: documentationId ?? null })
                    }}
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Yandex Purchase Link (Optional)</label>
                  <input
                    type="url"
                    defaultValue={product.yandex_purchase_link || ''}
                    onChange={(e) => {
                      onUpdateProduct(product.id, { yandex_purchase_link: e.target.value || null })
                    }}
                    placeholder="https://market.yandex.ru/..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Link to purchase this product on Yandex Market
                  </p>
                </div>
                {product.product_type === 'physical' && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Usage Period (Days) (Optional)</label>
                    <input
                      type="number"
                      min="1"
                      defaultValue={product.usage_period || ''}
                      onChange={(e) => {
                        const value = e.target.value ? parseInt(e.target.value) : null
                        onUpdateProduct(product.id, { usage_period: value })
                      }}
                      placeholder="30"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Number of days the product can be used (used instead of activation template period for physical products)
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Pricing */}
            {canViewPrices && (
              <div>
                <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Pricing</h4>
                <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Cost Price (₽)</label>
                  <input
                    type="number"
                    step="0.01"
                    defaultValue={product.cost_price}
                    onChange={(e) => {
                      const newCostPrice = parseFloat(e.target.value) || 0
                      onUpdateProduct(product.id, { cost_price: newCostPrice })
                    }}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Selling Price</label>
                  <p className="mt-1 text-sm text-gray-900">
                    ₽{(() => {
                      const yandexPrice = fullDetails?.yandex_full_data?.basicPrice?.value || 
                                        fullDetails?.yandex_full_data?.campaignPrice?.value ||
                                        fullDetails?.yandex_full_data?.price
                      return (yandexPrice || product.selling_price || 0).toLocaleString('ru-RU')
                    })()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Profit</label>
                  <p className="mt-1 text-sm text-green-600">
                    {(() => {
                      // Calculate profit using actual selling price from Yandex data
                      const actualSellingPrice = fullDetails?.yandex_full_data?.basicPrice?.value || 
                                                fullDetails?.yandex_full_data?.campaignPrice?.value ||
                                                fullDetails?.yandex_full_data?.price ||
                                                product.selling_price || 0
                      const actualCostPrice = product.cost_price || 0
                      const actualProfit = actualSellingPrice - actualCostPrice
                      const actualProfitPercentage = actualCostPrice > 0 
                        ? (actualProfit / actualCostPrice) * 100 
                        : (actualSellingPrice > 0 ? 100 : 0)
                      return `₽${actualProfit.toLocaleString('ru-RU')} (${actualProfitPercentage.toFixed(2)}%)`
                    })()}
                  </p>
                </div>
                {(fullDetails?.yandex_full_data?.oldPrice || fullDetails?.yandex_full_data?.original_price) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Original Price / Discount</label>
                    <p className="mt-1 text-sm text-gray-900">
                      ₽{(fullDetails.yandex_full_data.oldPrice || fullDetails.yandex_full_data.original_price).toLocaleString('ru-RU')} 
                      {fullDetails.yandex_full_data.discount_percentage ? ` (-${fullDetails.yandex_full_data.discount_percentage.toFixed(0)}%)` : ''}
                    </p>
                  </div>
                )}
              </div>
            </div>
            )}

            {/* Media Section */}
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Media</h4>
              {medias.length > 0 ? (
                <div className="grid grid-cols-4 gap-4">
                  {medias.map((media, idx) => (
                    <div key={idx} className="relative group">
                      {media.type === 'image' ? (
                        <img
                          src={media.url.startsWith('http') ? media.url : mediaApi.getMediaUrl(media.url)}
                          alt={`Product media ${idx + 1}`}
                          className="w-full h-32 object-cover rounded border"
                        />
                      ) : (
                        <video
                          src={media.url.startsWith('http') ? media.url : mediaApi.getMediaUrl(media.url)}
                          className="w-full h-32 object-cover rounded border"
                          controls
                        />
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">No media available</p>
              )}
            </div>

            {/* Product Parameters */}
            {fullDetails?.yandex_full_data?.parameterValues && Array.isArray(fullDetails.yandex_full_data.parameterValues) && (
              <div>
                <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Product Parameters</h4>
                <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                  {fullDetails.yandex_full_data.parameterValues.map((param: any, idx: number) => {
                    // Create readable field names based on parameterId and value
                    const getFieldName = (paramId: number, value: string): string => {
                      // Map common parameter IDs to readable names
                      const paramNameMap: Record<number, string> = {
                        7351754: 'Usage Terms',
                        16382542: 'Activation Instructions',
                        17942745: 'Physical Delivery Required',
                        24915630: 'Platform Compatibility',
                        27140631: 'Not Applicable',
                        33453610: 'Supported Devices',
                        33663230: 'Quantity',
                        37693330: 'Product Type',
                        37810090: 'Count',
                        37821410: 'Duration (Months)',
                        37919770: 'Auto-renewal',
                        37919810: 'Region',
                        37948770: 'Online Cinema',
                        37949750: 'Available Countries',
                        37951450: 'Age Rating',
                        37972050: 'Service Name',
                        37978150: 'Subscription Period',
                        37978250: 'Payment Type',
                        50882075: 'Brand/Service',
                        57046341: 'Plan Details',
                        200: 'Category',
                      }
                      
                      // Check if value contains specific keywords for better naming
                      if (value && typeof value === 'string') {
                        const lowerValue = value.toLowerCase()
                        if (lowerValue.includes('online cinema')) return 'Online Cinema'
                        if (lowerValue.includes('mobile device')) return 'Mobile Devices'
                        if (lowerValue.includes('pc')) return 'PC Compatibility'
                        if (lowerValue.includes('smart tv')) return 'Smart TV Support'
                        if (lowerValue.includes('android')) return 'Android Support'
                        if (lowerValue.includes('ios')) return 'iOS Support'
                        if (lowerValue.includes('windows')) return 'Windows Support'
                        if (lowerValue.includes('macos')) return 'macOS Support'
                        if (lowerValue.includes('electronic key')) return 'Product Type'
                        if (lowerValue.includes('month')) return 'Subscription Duration'
                        if (lowerValue.includes('countries')) return 'Available Countries'
                        if (lowerValue.includes('age') || lowerValue.includes('rating')) return 'Age Rating'
                      }
                      
                      return paramNameMap[paramId] || `Parameter ${paramId}`
                    }
                    
                    const fieldName = getFieldName(param.parameterId, param.value)
                    const displayValue = param.value || (param.valueId ? `ID: ${param.valueId}` : 'N/A')
                    
                    return (
                      <div key={idx} className="bg-white p-3 rounded border border-gray-200">
                        <div className="font-medium text-sm text-gray-700 mb-1">{fieldName}</div>
                        <div className="text-sm text-gray-900">{displayValue}</div>
                        {param.valueId && (
                          <div className="text-xs text-gray-500 mt-1">Value ID: {param.valueId}</div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Yandex Market Fields */}
            {fullDetails?.yandex_full_data && (
              <div>
                <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Yandex Market Fields</h4>
                <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                  {Object.entries(fullDetails.yandex_full_data).map(([key, value]) => {
                    // Skip already displayed fields and parameterValues (shown in Product Parameters section)
                    const displayedFields = ['name', 'description', 'price', 'availability', 'id', 'sku', 'parameterValues']
                    if (displayedFields.includes(key)) return null
                    
                    // Handle nested objects (like basicPrice, campaignPrice)
                    if (value && typeof value === 'object' && !Array.isArray(value) && value !== null) {
                      return (
                        <div key={key} className="border-b border-gray-200 pb-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="font-medium text-sm text-gray-700 capitalize">
                              {key.replace(/_/g, ' ')}:
                            </div>
                          </div>
                          <div className="ml-4 space-y-2 bg-white p-3 rounded border">
                            {Object.entries(value as Record<string, any>).map(([subKey, subValue]) => {
                              return (
                                <div key={subKey} className="flex items-start gap-2">
                                  <div className="w-1/3 font-medium text-xs text-gray-600 capitalize pt-1">
                                    {subKey.replace(/_/g, ' ')}:
                                  </div>
                                  <div className="w-2/3">
                                    <div className="text-sm text-gray-900 break-words">
                                      {typeof subValue === 'object' && subValue !== null ? (
                                        <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-32">
                                          {JSON.stringify(subValue, null, 2)}
                                        </pre>
                                      ) : (
                                        <span>{String(subValue || 'N/A')}</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    }
                    
                    // Handle simple values (read-only)
                    return (
                      <div key={key} className="flex items-start gap-2 border-b border-gray-200 pb-3">
                        <div className="w-1/3 font-medium text-sm text-gray-700 capitalize pt-2">
                          {key.replace(/_/g, ' ')}:
                        </div>
                        <div className="w-2/3">
                          <div className="flex-1 text-sm text-gray-900 break-words">
                            {typeof value === 'object' && value !== null ? (
                              <pre className="text-xs bg-white p-2 rounded border overflow-auto max-h-32">
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : (
                              <span>{String(value || 'N/A')}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
              </>
            )}
            
            {activeTab === 'reviews' && (
              <ProductReviewsTab 
                productId={product.yandex_market_id} 
                reviewsData={reviewsData}
                ratingData={ratingData}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Product Reviews Tab Component
function ProductReviewsTab({ 
  productId, 
  reviewsData, 
  ratingData 
}: { 
  productId?: string
  reviewsData?: any
  ratingData?: any
}) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const [replyText, setReplyText] = useState('')
  
  const queryClient = useQueryClient()
  
  const replyMutation = useMutation({
    mutationFn: ({ reviewId, text }: { reviewId: string; text: string }) =>
      reviewsApi.replyToProductReview(reviewId, text),
    onSuccess: () => {
      setReplyingTo(null)
      setReplyText('')
      // Refresh reviews and rating
      queryClient.invalidateQueries({ queryKey: ['product-reviews', productId] })
      queryClient.invalidateQueries({ queryKey: ['product-rating', productId] })
    },
  })
  
  if (!productId) {
    return (
      <div className="text-center py-8 text-gray-500">
        Product not synced with Yandex Market. Reviews are only available for synced products.
      </div>
    )
  }
  
  return (
    <div>
      {/* Rating Summary */}
      {ratingData && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="flex items-center">
                <Star className="h-8 w-8 text-yellow-400 fill-yellow-400 mr-2" />
                <span className="text-3xl font-bold text-gray-900">{ratingData.average_rating.toFixed(1)}</span>
                <span className="text-gray-500 ml-2">/ 5.0</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{ratingData.total_reviews} reviews</p>
            </div>
            <div className="text-right">
              {[5, 4, 3, 2, 1].map((stars) => (
                <div key={stars} className="flex items-center text-sm mb-1">
                  <span className="w-8">{stars}⭐</span>
                  <div className="w-32 bg-gray-200 rounded-full h-2 mx-2">
                    <div
                      className="bg-yellow-400 h-2 rounded-full"
                      style={{
                        width: `${(ratingData.rating_breakdown[stars] / ratingData.total_reviews) * 100}%`
                      }}
                    />
                  </div>
                  <span className="text-gray-600">{ratingData.rating_breakdown[stars]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* Reviews List */}
      {reviewsData && reviewsData.reviews && reviewsData.reviews.length > 0 ? (
        <div className="space-y-4">
          {reviewsData.reviews.map((review: any) => (
            <div key={review.id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center">
                  <div className="flex">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`h-4 w-4 ${
                          star <= review.rating
                            ? 'text-yellow-400 fill-yellow-400'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="ml-2 text-sm font-medium text-gray-900">
                    {review.author?.name || 'Anonymous'}
                  </span>
                </div>
                {review.created_at && (
                  <span className="text-xs text-gray-500">
                    {new Date(review.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-700 mb-3">{review.text}</p>
              
              {replyingTo === review.id ? (
                <div className="mt-3">
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Type your reply..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    rows={3}
                  />
                  <div className="flex space-x-2 mt-2">
                    <button
                      onClick={() => replyMutation.mutate({ reviewId: review.id, text: replyText })}
                      disabled={!replyText.trim() || replyMutation.isPending}
                      className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {replyMutation.isPending ? 'Sending...' : 'Send Reply'}
                    </button>
                    <button
                      onClick={() => {
                        setReplyingTo(null)
                        setReplyText('')
                      }}
                      className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setReplyingTo(review.id)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Reply
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">No reviews yet</div>
      )}
    </div>
  )
}

// Email Template Selector Component
function EmailTemplateSelector({
  productId: _productId,
  currentTemplateId,
  onUpdate,
}: {
  productId: number
  currentTemplateId?: number
  onUpdate: (templateId?: number) => void
}) {
  const { data: emailTemplates } = useQuery({
    queryKey: ['activation-templates'],
    queryFn: () => activationTemplatesApi.getAll(),
  })
  
  return (
    <>
      <select
        value={currentTemplateId || ''}
        onChange={(e) => {
          const templateId = e.target.value ? parseInt(e.target.value) : undefined
          onUpdate(templateId)
        }}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">No Template</option>
        {emailTemplates?.map((template) => (
          <option key={template.id} value={template.id}>
            {template.name}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-gray-500">
        Select an activation template to use when sending activation codes for this product
      </p>
    </>
  )
}

// Documentation Selector Component (for view mode)
function DocumentationSelector({
  productId: _productId,
  currentDocumentationId,
  onUpdate,
}: {
  productId: number
  currentDocumentationId?: number
  onUpdate: (documentationId?: number) => void
}) {
  const { data: documentations } = useQuery({
    queryKey: ['documentations'],
    queryFn: () => documentationsApi.getAll(),
  })
  
  return (
    <>
      <select
        value={currentDocumentationId || ''}
        onChange={(e) => {
          const documentationId = e.target.value ? parseInt(e.target.value) : undefined
          onUpdate(documentationId)
        }}
        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">No Documentation</option>
        {documentations?.map((doc) => (
          <option key={doc.id} value={doc.id}>
            {doc.name}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-gray-500">
        Select documentation to help staff fulfill orders for this product
      </p>
    </>
  )
}

// Documentation View Modal
function DocumentationViewModal({
  docId,
  onClose,
}: {
  docId: number
  onClose: () => void
}) {
  const { data: doc, isLoading } = useQuery({
    queryKey: ['documentation', docId],
    queryFn: () => documentationsApi.get(docId),
    enabled: !!docId,
  })

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div className="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white">
          <div className="text-center py-8">Loading...</div>
        </div>
      </div>
    )
  }

  if (!doc) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
          <h3 className="text-2xl font-bold text-gray-900">Documentation: {doc.name}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {doc.description && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <p className="text-sm text-gray-900">{doc.description}</p>
            </div>
          )}
          {doc.type === 'file' && doc.file_url && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">File</label>
              <a
                href={mediaApi.encodeFileUrl(doc.file_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {mediaApi.decodeFileName(doc.file_url) || 'View File'}
              </a>
            </div>
          )}
          {doc.type === 'link' && doc.link_url && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Link</label>
              <a
                href={doc.link_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {doc.link_url}
              </a>
            </div>
          )}
          {doc.type === 'text' && doc.content && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Content</label>
              <div className="text-sm text-gray-900 whitespace-pre-wrap bg-gray-50 p-4 rounded border">
                {doc.content}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Activation Template View Modal
function ActivationTemplateViewModal({
  templateId,
  onClose,
}: {
  templateId: number
  onClose: () => void
}) {
  const { data: template, isLoading } = useQuery({
    queryKey: ['activation-template', templateId],
    queryFn: () => activationTemplatesApi.getById(templateId),
    enabled: !!templateId,
  })

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div className="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white">
          <div className="text-center py-8">Loading...</div>
        </div>
      </div>
    )
  }

  if (!template) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
          <h3 className="text-2xl font-bold text-gray-900">Activation Template: {template.name}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Body</label>
            <div className="text-sm text-gray-900 whitespace-pre-wrap bg-gray-50 p-4 rounded border">
              {template.body}
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Settings</label>
            <div className="text-sm text-gray-900 space-y-1">
              <p>Random Key: {template.random_key ? 'Yes' : 'No'}</p>
              <p>Required Login: {template.required_login ? 'Yes' : 'No'}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Add Product Modal removed - products can only be synced from Yandex Market
