import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clientsApi, ClientCreate, ClientUpdate } from '../api/clients'
import { productsApi } from '../api/products'
import { UserPlus, Edit2, Trash2, X } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

export default function Clients() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [selectedClient, setSelectedClient] = useState<any>(null)
  const [selectedProducts, setSelectedProducts] = useState<number[]>([])
  const [filterProductId, setFilterProductId] = useState<number | undefined>(undefined)
  const [searchTerm, setSearchTerm] = useState('')
  const [productSearchTerm, setProductSearchTerm] = useState('')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [formValid, setFormValid] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; clientId: number | null }>({ isOpen: false, clientId: null })
  const [incrementConfirm, setIncrementConfirm] = useState<{ isOpen: boolean; clientId: number | null; productId: number | null }>({ isOpen: false, clientId: null, productId: null })
  const addClientFormRef = useRef<HTMLFormElement>(null)
  const queryClient = useQueryClient()
  
  const checkFormValidity = () => {
    if (addClientFormRef.current) {
      setFormValid(addClientFormRef.current.checkValidity())
    }
  }

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['clients', filterProductId, searchTerm, startDate, endDate],
    queryFn: () => clientsApi.getAll({
      product_id: filterProductId,
      search: searchTerm || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
  })

  const { data: products = [] } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
  })

  const createMutation = useMutation({
    mutationFn: (data: ClientCreate) => clientsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setIsAddModalOpen(false)
      setSelectedProducts([])
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ClientUpdate }) =>
      clientsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setIsEditModalOpen(false)
      setSelectedClient(null)
      setSelectedProducts([])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => clientsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })

  const incrementMutation = useMutation({
    mutationFn: ({ clientId, productId }: { clientId: number; productId: number }) =>
      clientsApi.incrementPurchase(clientId, productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })

  const handleAdd = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      name: formData.get('name') as string,
      email: formData.get('email') as string,
      purchased_product_ids: selectedProducts,
    })
    setSelectedProducts([])
    setProductSearchTerm('')
  }

  const handleEdit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    updateMutation.mutate({
      id: selectedClient.id,
      data: {
        name: formData.get('name') as string,
        email: formData.get('email') as string,
        purchased_product_ids: selectedProducts,
      },
    })
    setSelectedProducts([])
  }

  const toggleProduct = (productId: number) => {
    setSelectedProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    )
  }

  const handleDelete = (id: number) => {
    setDeleteConfirm({ isOpen: true, clientId: id })
  }

  const handleIncrement = (clientId: number, productId: number) => {
    setIncrementConfirm({ isOpen: true, clientId, productId })
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Clients</h1>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <UserPlus className="h-5 w-5 mr-2" />
          Add Client
        </button>
      </div>

      {/* Filters */}
      <div className="mb-4 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <input
              id="search"
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="w-full sm:w-64">
            <label htmlFor="product-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Filter by Product
            </label>
            <select
              id="product-filter"
              value={filterProductId || ''}
              onChange={(e) => setFilterProductId(e.target.value ? parseInt(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Clients</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Created From</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Created To</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading clients...</div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Products
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created At
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {clients.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No clients yet. Add your first client to get started.
                  </td>
                </tr>
              ) : (
                clients.map((client) => (
                  <tr key={client.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {client.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {client.email}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {client.purchased_product_ids && client.purchased_product_ids.length > 0 ? (
                        <div className="space-y-1">
                          {products
                            .filter(p => client.purchased_product_ids.includes(p.id))
                            .map((product) => (
                              <div key={product.id} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                                <span className="text-xs">{product.name}</span>
                                <button
                                  onClick={() => handleIncrement(client.id, product.id)}
                                  disabled={incrementMutation.isPending}
                                  className="ml-2 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                                  title="Increment purchase count"
                                >
                                  +1
                                </button>
                              </div>
                            ))}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">No purchases</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(client.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => {
                          setSelectedClient(client)
                          setSelectedProducts(client.purchased_product_ids || [])
                          setProductSearchTerm('')
                          setIsEditModalOpen(true)
                        }}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(client.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Client Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] flex flex-col p-6">
            {/* Sticky Header */}
            <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
              <h2 className="text-xl font-bold text-gray-900">Add Client</h2>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form 
              id="add-client-form" 
              ref={addClientFormRef}
              onSubmit={handleAdd} 
              onInput={checkFormValidity}
              onChange={checkFormValidity}
              className="space-y-4 flex-1 overflow-y-auto"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  name="email"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Products Purchased (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Search by product name or ID..."
                  value={productSearchTerm}
                  onChange={(e) => setProductSearchTerm(e.target.value)}
                  className="w-full mb-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="border border-gray-300 rounded-md max-h-48 overflow-y-auto p-2">
                  {products.length === 0 ? (
                    <p className="text-sm text-gray-500 p-2">No products available</p>
                  ) : (
                    products
                      .filter((product) => {
                        if (!productSearchTerm) return true
                        const search = productSearchTerm.toLowerCase()
                        return (
                          product.name.toLowerCase().includes(search) ||
                          product.id.toString().includes(search)
                        )
                      })
                      .map((product) => (
                        <label key={product.id} className="flex items-center p-2 hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedProducts.includes(product.id)}
                            onChange={() => toggleProduct(product.id)}
                            className="mr-2"
                          />
                          <span className="text-sm">{product.name} (ID: {product.id})</span>
                        </label>
                      ))
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Select products this client has purchased
                </p>
              </div>
            </form>
            {/* Sticky Footer */}
            <div className="flex justify-end space-x-3 pt-4 border-t sticky bottom-0 bg-white mt-4">
              <button
                type="button"
              onClick={() => {
                setIsAddModalOpen(false)
                setFormValid(false)
                setProductSearchTerm('')
              }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="add-client-form"
                disabled={createMutation.isPending || !formValid}
                className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed ${
                  formValid && !createMutation.isPending 
                    ? 'bg-blue-600 hover:bg-blue-700' 
                    : 'bg-gray-400 cursor-not-allowed'
                }`}
              >
                {createMutation.isPending ? 'Adding...' : 'Add Client'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Client Modal */}
      {isEditModalOpen && selectedClient && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Edit Client</h2>
              <button
                onClick={() => {
                  setIsEditModalOpen(false)
                  setSelectedClient(null)
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  defaultValue={selectedClient.name}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  name="email"
                  required
                  defaultValue={selectedClient.email}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Products Purchased (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Search by product name or ID..."
                  value={productSearchTerm}
                  onChange={(e) => setProductSearchTerm(e.target.value)}
                  className="w-full mb-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <div className="border border-gray-300 rounded-md max-h-48 overflow-y-auto p-2">
                  {products.length === 0 ? (
                    <p className="text-sm text-gray-500 p-2">No products available</p>
                  ) : (
                    products
                      .filter((product) => {
                        if (!productSearchTerm) return true
                        const search = productSearchTerm.toLowerCase()
                        return (
                          product.name.toLowerCase().includes(search) ||
                          product.id.toString().includes(search)
                        )
                      })
                      .map((product) => (
                        <label key={product.id} className="flex items-center p-2 hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedProducts.includes(product.id)}
                            onChange={() => toggleProduct(product.id)}
                            className="mr-2"
                          />
                          <span className="text-sm">{product.name} (ID: {product.id})</span>
                        </label>
                      ))
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Select products this client has purchased
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditModalOpen(false)
                    setSelectedClient(null)
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteConfirm.isOpen}
        title="Delete Client"
        message="Are you sure you want to delete this client? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => {
          if (deleteConfirm.clientId) {
            deleteMutation.mutate(deleteConfirm.clientId)
          }
          setDeleteConfirm({ isOpen: false, clientId: null })
        }}
        onCancel={() => setDeleteConfirm({ isOpen: false, clientId: null })}
      />

      {/* Increment Confirmation Modal */}
      <ConfirmationModal
        isOpen={incrementConfirm.isOpen}
        title="Increment Purchase Count"
        message="Increment purchase count for this product?"
        confirmText="Increment"
        cancelText="Cancel"
        variant="info"
        onConfirm={() => {
          if (incrementConfirm.clientId && incrementConfirm.productId) {
            incrementMutation.mutate({ clientId: incrementConfirm.clientId, productId: incrementConfirm.productId })
          }
          setIncrementConfirm({ isOpen: false, clientId: null, productId: null })
        }}
        onCancel={() => setIncrementConfirm({ isOpen: false, clientId: null, productId: null })}
      />
    </div>
  )
}
