import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi, Product, ProductCreate } from '../api/products'
import { productTemplatesApi, ProductTemplate } from '../api/productTemplates'
import { productVariantsApi, ProductVariant } from '../api/productVariants'
import { reviewsApi } from '../api/reviews'
import { mediaApi } from '../api/media'
import { Eye, Trash2, Plus, X, FileText, Star } from 'lucide-react'

export default function Products() {
  const [viewingProduct, setViewingProduct] = useState<Product | null>(null)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ProductTemplate | null>(null)
  const [useTemplateDefaults, setUseTemplateDefaults] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [templateName, setTemplateName] = useState('')
  const queryClient = useQueryClient()

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
  })

  const { data: templates } = useQuery({
    queryKey: ['product-templates'],
    queryFn: () => productTemplatesApi.getAll(),
  })

  const { isLoading: fullDetailsLoading } = useQuery({
    queryKey: ['product-full', viewingProduct?.id],
    queryFn: () => productsApi.getFullDetails(viewingProduct!.id),
    enabled: !!viewingProduct && showViewModal,
  })

  const createMutation = useMutation({
    mutationFn: (data: ProductCreate) => productsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      setShowAddModal(false)
      resetForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })

  const createTemplateMutation = useMutation({
    mutationFn: (data: { name: string; template_data: Record<string, any> }) =>
      productTemplatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-templates'] })
      setShowTemplateModal(false)
      setTemplateName('')
      alert('Template created successfully!')
    },
  })

  const filteredProducts = products?.filter((p) =>
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleViewProduct = async (product: Product) => {
    setViewingProduct(product)
    setShowViewModal(true)
  }

  const handleCreateTemplate = () => {
    if (!viewingProduct || !templateName.trim()) {
      alert('Please enter a template name')
      return
    }
    
    // Create template from current product
    const templateData: Record<string, any> = {
      name: viewingProduct.name,
      description: viewingProduct.description,
      product_type: viewingProduct.product_type,
      cost_price: viewingProduct.cost_price,
      selling_price: viewingProduct.selling_price,
      supplier_url: viewingProduct.supplier_url,
      supplier_name: viewingProduct.supplier_name,
      yandex_model: viewingProduct.yandex_model,
      yandex_category_id: viewingProduct.yandex_category_id,
      yandex_category_path: viewingProduct.yandex_category_path,
      yandex_brand: viewingProduct.yandex_brand,
      yandex_platform: viewingProduct.yandex_platform,
      yandex_localization: viewingProduct.yandex_localization,
      yandex_publication_type: viewingProduct.yandex_publication_type,
      yandex_activation_territory: viewingProduct.yandex_activation_territory,
      yandex_edition: viewingProduct.yandex_edition,
      yandex_series: viewingProduct.yandex_series,
      yandex_age_restriction: viewingProduct.yandex_age_restriction,
      yandex_activation_instructions: viewingProduct.yandex_activation_instructions,
      original_price: viewingProduct.original_price,
      discount_percentage: viewingProduct.discount_percentage,
      yandex_images: viewingProduct.yandex_images || [],
      yandex_videos: viewingProduct.yandex_videos || [],
    }
    
    createTemplateMutation.mutate({
      name: templateName,
      template_data: templateData,
    })
  }

  const handleSelectTemplate = (template: ProductTemplate | null) => {
    setSelectedTemplate(template)
  }

  const resetForm = () => {
    setSelectedTemplate(null)
    setUseTemplateDefaults(true)
  }

  const handleAddProduct = () => {
    resetForm()
    setShowAddModal(true)
  }

  if (productsLoading) {
    return <div className="text-center py-12">Loading products...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>
        <button
          onClick={handleAddProduct}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Product
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search products..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
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
                Price
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredProducts && filteredProducts.length > 0 ? (
              filteredProducts.map((product) => (
                <tr key={product.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{product.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-500 capitalize">{product.product_type}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">₽{product.selling_price.toLocaleString('ru-RU')}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      product.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {product.is_active ? 'Active' : 'Inactive'}
                    </span>
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
                      <button
                        onClick={() => {
                          if (confirm('Are you sure you want to delete this product?')) {
                            deleteMutation.mutate(product.id)
                          }
                        }}
                        className="text-red-600 hover:text-red-900"
                        title="Delete"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                  No products found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* View Product Modal */}
      {showViewModal && viewingProduct && (
        <ProductViewModal
          product={viewingProduct}
          isLoading={fullDetailsLoading}
          onClose={() => {
            setShowViewModal(false)
            setViewingProduct(null)
          }}
          onCreateTemplate={() => setShowTemplateModal(true)}
        />
      )}

      {/* Create Template Modal */}
      {showTemplateModal && viewingProduct && (
        <CreateTemplateModal
          product={viewingProduct}
          templateName={templateName}
          onTemplateNameChange={setTemplateName}
          onCreate={handleCreateTemplate}
          onClose={() => {
            setShowTemplateModal(false)
            setTemplateName('')
          }}
          isLoading={createTemplateMutation.isPending}
        />
      )}

      {/* Add Product Modal */}
      {showAddModal && (
        <AddProductModal
          templates={templates || []}
          selectedTemplate={selectedTemplate}
          useTemplateDefaults={useTemplateDefaults}
          onTemplateSelect={handleSelectTemplate}
          onUseDefaultsChange={setUseTemplateDefaults}
          onSubmit={(data) => createMutation.mutate(data)}
          onClose={() => {
            setShowAddModal(false)
            resetForm()
          }}
          isLoading={createMutation.isPending}
        />
      )}
    </div>
  )
}

// Product View Modal Component
function ProductViewModal({
  product,
  isLoading,
  onClose,
  onCreateTemplate,
}: {
  product: Product
  isLoading: boolean
  onClose: () => void
  onCreateTemplate: () => void
}) {
  const [activeTab, setActiveTab] = useState<'details' | 'variants' | 'reviews'>('details')
  
  const { data: variants } = useQuery({
    queryKey: ['product-variants', product.id],
    queryFn: () => productVariantsApi.getProductVariants(product.id),
    enabled: !!product.id,
  })
  
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
      <div className="relative top-10 mx-auto p-5 border w-full max-w-5xl shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-2xl font-bold text-gray-900">Product Details</h3>
          <div className="flex space-x-2">
            <button
              onClick={onCreateTemplate}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              <FileText className="h-4 w-4 mr-2" />
              Create Template
            </button>
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
              onClick={() => setActiveTab('variants')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'variants'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Variants ({variants?.length || 0})
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
          <div className="space-y-6">
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
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <p className="mt-1 text-sm text-gray-900">{product.description || 'N/A'}</p>
                </div>
              </div>
            </div>

            {/* Pricing */}
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Pricing</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Cost Price</label>
                  <p className="mt-1 text-sm text-gray-900">₽{product.cost_price.toLocaleString('ru-RU')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Selling Price</label>
                  <p className="mt-1 text-sm text-gray-900">₽{product.selling_price.toLocaleString('ru-RU')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Profit</label>
                  <p className="mt-1 text-sm text-green-600">₽{product.profit.toLocaleString('ru-RU')} ({product.profit_percentage.toFixed(2)}%)</p>
                </div>
                {product.original_price && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Original Price / Discount</label>
                    <p className="mt-1 text-sm text-gray-900">
                      ₽{product.original_price.toLocaleString('ru-RU')} 
                      {product.discount_percentage ? ` (-${product.discount_percentage.toFixed(0)}%)` : ''}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Yandex Market Details */}
            <div>
              <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Yandex Market Details</h4>
              <div className="grid grid-cols-2 gap-4">
                {product.yandex_brand && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Brand</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_brand}</p>
                  </div>
                )}
                {product.yandex_platform && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Platform</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_platform}</p>
                  </div>
                )}
                {product.yandex_category_path && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Category</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_category_path}</p>
                  </div>
                )}
                {product.yandex_localization && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Localization</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_localization}</p>
                  </div>
                )}
                {product.yandex_edition && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Edition</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_edition}</p>
                  </div>
                )}
                {product.yandex_series && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Series</label>
                    <p className="mt-1 text-sm text-gray-900">{product.yandex_series}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Media */}
            {(product.yandex_images && product.yandex_images.length > 0) || 
             (product.yandex_videos && product.yandex_videos.length > 0) ? (
              <div>
                <h4 className="text-lg font-semibold text-gray-800 mb-3 border-b pb-2">Media</h4>
                {product.yandex_images && product.yandex_images.length > 0 && (
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Images</label>
                    <div className="grid grid-cols-4 gap-2">
                      {product.yandex_images.map((img, idx) => (
                        <img
                          key={idx}
                          src={mediaApi.getMediaUrl(img)}
                          alt={`Product image ${idx + 1}`}
                          className="w-full h-32 object-cover rounded border"
                        />
                      ))}
                    </div>
                  </div>
                )}
                {product.yandex_videos && product.yandex_videos.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Videos</label>
                    <div className="grid grid-cols-4 gap-2">
                      {product.yandex_videos.map((vid, idx) => (
                        <video
                          key={idx}
                          src={mediaApi.getMediaUrl(vid)}
                          className="w-full h-32 object-cover rounded border"
                          controls
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
              </>
            )}
            
            {activeTab === 'variants' && (
              <ProductVariantsTab productId={product.id} variants={variants || []} />
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

// Product Variants Tab Component
function ProductVariantsTab({ productId, variants }: { productId: number; variants: ProductVariant[] }) {
  const [showAddVariant, setShowAddVariant] = useState(false)
  const queryClient = useQueryClient()
  
  const createVariantMutation = useMutation({
    mutationFn: (data: any) => productVariantsApi.createVariant(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-variants', productId] })
      setShowAddVariant(false)
    },
  })
  
  const deleteVariantMutation = useMutation({
    mutationFn: (variantId: number) => productVariantsApi.deleteVariant(variantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product-variants', productId] })
    },
  })
  
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-lg font-semibold text-gray-800">Product Variants</h4>
        <button
          onClick={() => setShowAddVariant(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Variant
        </button>
      </div>
      
      {variants.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Variant Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Platform</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Territory</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {variants.map((variant) => (
                <tr key={variant.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {variant.variant_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {variant.platform || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {variant.activation_territory || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₽{variant.selling_price.toLocaleString('ru-RU')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      variant.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {variant.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this variant?')) {
                          deleteVariantMutation.mutate(variant.id)
                        }
                      }}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No variants found. Click "Add Variant" to create one.
        </div>
      )}
      
      {showAddVariant && (
        <AddVariantModal
          productId={productId}
          onSubmit={(data) => createVariantMutation.mutate(data)}
          onClose={() => setShowAddVariant(false)}
          isLoading={createVariantMutation.isPending}
        />
      )}
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
  
  const replyMutation = useMutation({
    mutationFn: ({ reviewId, text }: { reviewId: string; text: string }) =>
      reviewsApi.replyToProductReview(reviewId, text),
    onSuccess: () => {
      setReplyingTo(null)
      setReplyText('')
      // Refresh reviews
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

// Add Variant Modal Component
function AddVariantModal({
  productId: _productId,
  onSubmit,
  onClose,
  isLoading,
}: {
  productId: number
  onSubmit: (data: any) => void
  onClose: () => void
  isLoading: boolean
}) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const data = {
      variant_name: formData.get('variant_name') as string,
      edition: formData.get('edition') as string || undefined,
      platform: formData.get('platform') as string || undefined,
      activation_territory: formData.get('activation_territory') as string || undefined,
      localization: formData.get('localization') as string || undefined,
      selling_price: parseFloat(formData.get('selling_price') as string),
      original_price: formData.get('original_price') ? parseFloat(formData.get('original_price') as string) : undefined,
      cost_price: parseFloat(formData.get('cost_price') as string),
      stock_quantity: parseInt(formData.get('stock_quantity') as string) || 0,
      is_active: (formData.get('is_active') as string) === 'true',
    }
    
    onSubmit(data)
  }
  
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Add Product Variant</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-6 w-6" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Variant Name *</label>
            <input
              type="text"
              name="variant_name"
              required
              placeholder="e.g., Enhanced Edition•Kazakhstan•PC"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Edition</label>
              <input
                type="text"
                name="edition"
                placeholder="e.g., Enhanced Edition"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
              <input
                type="text"
                name="platform"
                placeholder="e.g., PC, PlayStation 4, PlayStation 5"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Activation Territory</label>
              <input
                type="text"
                name="activation_territory"
                placeholder="e.g., Kazakhstan, all countries"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Localization</label>
              <input
                type="text"
                name="localization"
                placeholder="e.g., Russian subtitles and interface"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Selling Price (₽) *</label>
              <input
                type="number"
                name="selling_price"
                step="0.01"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cost Price (₽) *</label>
              <input
                type="number"
                name="cost_price"
                step="0.01"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Original Price (₽)</label>
              <input
                type="number"
                name="original_price"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Stock Quantity</label>
              <input
                type="number"
                name="stock_quantity"
                defaultValue={0}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                name="is_active"
                value="true"
                defaultChecked
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Active</span>
            </label>
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Variant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Create Template Modal Component
function CreateTemplateModal({
  product,
  templateName,
  onTemplateNameChange,
  onCreate,
  onClose,
  isLoading,
}: {
  product: Product
  templateName: string
  onTemplateNameChange: (name: string) => void
  onCreate: () => void
  onClose: () => void
  isLoading: boolean
}) {
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Create Template from Product</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-6 w-6" />
          </button>
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Template Name</label>
          <input
            type="text"
            value={templateName}
            onChange={(e) => onTemplateNameChange(e.target.value)}
            placeholder="Enter template name..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="text-sm text-gray-600 mb-4">
          This will create a template based on "{product.name}" with all its current settings.
        </div>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onCreate}
            disabled={!templateName.trim() || isLoading}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create Template'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Add Product Modal Component
function AddProductModal({
  templates,
  selectedTemplate,
  useTemplateDefaults,
  onTemplateSelect,
  onUseDefaultsChange,
  onSubmit,
  onClose,
  isLoading,
}: {
  templates: ProductTemplate[]
  selectedTemplate: ProductTemplate | null
  useTemplateDefaults: boolean
  onTemplateSelect: (template: ProductTemplate | null) => void
  onUseDefaultsChange: (use: boolean) => void
  onSubmit: (data: ProductCreate) => void
  onClose: () => void
  isLoading: boolean
}) {
  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Add Product</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-6 w-6" />
          </button>
        </div>
        
        {/* Template Selection */}
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <label className="block text-sm font-medium text-gray-700 mb-2">Use Template (Optional)</label>
          <select
            value={selectedTemplate?.id || ''}
            onChange={(e) => {
              const template = templates.find(t => t.id === parseInt(e.target.value))
              onTemplateSelect(template || null)
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">No Template</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
          
          {selectedTemplate && (
            <div className="mt-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={useTemplateDefaults}
                  onChange={(e) => onUseDefaultsChange(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Auto-fill with template defaults</span>
              </label>
              {!useTemplateDefaults && (
                <p className="text-xs text-gray-500 mt-1">
                  Unchecked: Template fields will be cleared. You can manually fill them.
                </p>
              )}
            </div>
          )}
        </div>

        <form onSubmit={(e) => {
          e.preventDefault()
          const formData = new FormData(e.currentTarget)
          const data: ProductCreate = {
            name: formData.get('name') as string,
            description: formData.get('description') as string || undefined,
            product_type: (formData.get('product_type') as 'digital' | 'physical') || 'digital',
            cost_price: parseFloat(formData.get('cost_price') as string),
            selling_price: parseFloat(formData.get('selling_price') as string),
            supplier_url: formData.get('supplier_url') as string || undefined,
            supplier_name: formData.get('supplier_name') as string || undefined,
            yandex_model: formData.get('yandex_model') as string || 'DBS',
            yandex_category_id: formData.get('yandex_category_id') as string || undefined,
            yandex_category_path: formData.get('yandex_category_path') as string || undefined,
            yandex_brand: formData.get('yandex_brand') as string || undefined,
            yandex_platform: formData.get('yandex_platform') as string || undefined,
            yandex_localization: formData.get('yandex_localization') as string || undefined,
            yandex_publication_type: formData.get('yandex_publication_type') as string || undefined,
            yandex_activation_territory: formData.get('yandex_activation_territory') as string || 'all countries',
            yandex_edition: formData.get('yandex_edition') as string || undefined,
            yandex_series: formData.get('yandex_series') as string || undefined,
            yandex_age_restriction: formData.get('yandex_age_restriction') as string || undefined,
            original_price: formData.get('original_price') ? parseFloat(formData.get('original_price') as string) : undefined,
            discount_percentage: formData.get('discount_percentage') ? parseFloat(formData.get('discount_percentage') as string) : undefined,
            is_active: (formData.get('is_active') as string) === 'true',
          }
          onSubmit(data)
        }} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1">Basic Information</h4>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Name *</label>
              <input
                type="text"
                name="name"
                required
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.name : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Type *</label>
              <select
                name="product_type"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.product_type || 'digital' : 'digital'}
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
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.description : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            
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
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.cost_price : ''}
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
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.selling_price : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Original Price (₽)</label>
              <input
                type="number"
                name="original_price"
                step="0.01"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.original_price : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Discount (%)</label>
              <input
                type="number"
                name="discount_percentage"
                step="0.01"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.discount_percentage : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            
            <div className="md:col-span-2">
              <h4 className="text-md font-semibold text-gray-800 mb-2 border-b pb-1 mt-4">Yandex Market Details</h4>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Model *</label>
              <input
                type="text"
                name="yandex_model"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_model || 'DBS' : 'DBS'}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Brand</label>
              <input
                type="text"
                name="yandex_brand"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_brand : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Platform</label>
              <input
                type="text"
                name="yandex_platform"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_platform : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Localization</label>
              <input
                type="text"
                name="yandex_localization"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_localization : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Edition</label>
              <input
                type="text"
                name="yandex_edition"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_edition : ''}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Activation Territory</label>
              <input
                type="text"
                name="yandex_activation_territory"
                defaultValue={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.yandex_activation_territory || 'all countries' : 'all countries'}
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div className="md:col-span-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="is_active"
                  value="true"
                  defaultChecked={selectedTemplate && useTemplateDefaults ? selectedTemplate.template_data?.is_active !== false : true}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Active</span>
              </label>
            </div>
          </div>
          
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
