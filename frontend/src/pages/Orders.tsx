import React, { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordersApi } from '../api/orders'
import { productsApi } from '../api/products'
import { documentationsApi } from '../api/documentations'
import { chatApi, ChatMessage } from '../api/chat'
import { activationTemplatesApi } from '../api/activationTemplates'
import { clientsApi } from '../api/clients'
import { mediaApi } from '../api/media'
import { CheckCircle, Mail, RefreshCw, Search, FileText, MessageCircle, X, Send, AlertCircle, ChevronDown, ChevronRight, UserPlus, Paperclip, CheckCheck } from 'lucide-react'
import { useTimeZone } from '../contexts/TimeZoneContext'
import CopyButton from '../components/CopyButton'
import FeedbackButton from '../components/FeedbackButton'
import ConfirmationModal from '../components/ConfirmationModal'

export default function Orders() {
  const { formatDateTime } = useTimeZone()
  const [activeTab, setActiveTab] = useState<'digital' | 'physical'>('digital')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState('')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [page, setPage] = useState(0)
  const pageSize = 15
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null)
  const [showOrderChat, setShowOrderChat] = useState(false)
  const [showStoreChat, setShowStoreChat] = useState(false)
  const [completeConfirm, setCompleteConfirm] = useState<{ isOpen: boolean; orderId: number | null }>({ isOpen: false, orderId: null })
  const [sendActivationConfirm, setSendActivationConfirm] = useState<{ isOpen: boolean; orderId: number | null }>({ isOpen: false, orderId: null })
  const [manualActivationModal, setManualActivationModal] = useState<{ isOpen: boolean; orderId: number | null; orderItems: any[] | null }>({ isOpen: false, orderId: null, orderItems: null })
  const [markFinishedConfirm, setMarkFinishedConfirm] = useState<{ isOpen: boolean; orderId: number | null }>({ isOpen: false, orderId: null })
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
  const [docViewerModal, setDocViewerModal] = useState<{ isOpen: boolean; productId: number | null }>({ isOpen: false, productId: null })
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  const [refreshSuccess, setRefreshSuccess] = useState(false)
  const [createClientModal, setCreateClientModal] = useState<{ isOpen: boolean; orderId: string | null; customerName: string | null }>({ isOpen: false, orderId: null, customerName: null })
  const queryClient = useQueryClient()
  
  const toggleOrderExpansion = (yandexOrderId: string) => {
    setExpandedOrders(prev => {
      const newSet = new Set(prev)
      if (newSet.has(yandexOrderId)) {
        newSet.delete(yandexOrderId)
      } else {
        newSet.add(yandexOrderId)
      }
      return newSet
    })
  }

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ isOpen: true, type, message })
    // Auto-close after 4 seconds
    setTimeout(() => setNotification(prev => ({ ...prev, isOpen: false })), 4000)
  }

  useEffect(() => {
    // Reset paging when switching Digital/Physical tabs
    setPage(0)
  }, [activeTab])

  useEffect(() => {
    // Reset paging when filters change
    setPage(0)
  }, [statusFilter, startDate, endDate])

  const { data: pendingCounts } = useQuery({
    queryKey: ['orders', 'pending-counts'],
    queryFn: () => ordersApi.getPendingCounts(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })

  const { data: orders, isLoading, refetch } = useQuery({
    queryKey: ['orders', activeTab, page, pageSize, statusFilter, startDate, endDate],
    queryFn: () => {
      // Cast to avoid TS stale type mismatch in some environments
      const params = {
        is_digital: activeTab === 'digital',
        skip: page * pageSize,
        limit: pageSize,
        refresh_status: page === 0,
        status: statusFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      } as any
      return ordersApi.getAll(params)
    },
    staleTime: 0, // Always refetch on mount
    gcTime: 0, // Don't cache (gcTime replaces cacheTime in React Query v5)
    refetchInterval: 30000, // Refetch every 30 seconds to get latest data after sync
  })

  // Fetch all activation templates to check random_key
  const { data: allTemplates } = useQuery({
    queryKey: ['activation-templates'],
    queryFn: () => activationTemplatesApi.getAll(undefined, { skip: 0, limit: 2000 }),
  })

  const fulfillMutation = useMutation({
    mutationFn: (id: number) => ordersApi.fulfill(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      showNotification('success', 'Order fulfilled successfully!')
    },
    onError: (error: any) => {
      showNotification('error', error?.response?.data?.detail || 'Failed to fulfill order')
    },
  })

  // Send Activation now calls the complete endpoint to deliver digital goods to Yandex Market
  const sendActivationMutation = useMutation({
    mutationFn: ({ id, activationKeys }: { id: number; activationKeys?: Record<number, string> }) => 
      ordersApi.complete(id, activationKeys),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      showNotification('success', 'Activation sent successfully! Order completed on Yandex Market.')
      setManualActivationModal({ isOpen: false, orderId: null, orderItems: null })
    },
    onError: (error: any) => {
      showNotification('error', error?.response?.data?.detail || 'Failed to send activation')
    },
  })

  const completeMutation = useMutation({
    mutationFn: (id: number) => ordersApi.complete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      showNotification('success', 'Order completed!')
    },
    onError: (error: any) => {
      showNotification('error', error?.response?.data?.detail || 'Failed to complete order')
    },
  })

  const filteredOrders = orders?.filter((order) => {
    // Filter by search term (client-side)
    if (!searchTerm) return true

    const searchLower = searchTerm.toLowerCase()

    const matchesOrderId = order.yandex_order_id.toLowerCase().includes(searchLower)
    const matchesCustomerName = order.customer_name?.toLowerCase().includes(searchLower)
    const matchesCustomerEmail = order.customer_email?.toLowerCase().includes(searchLower)
    const matchesProductName =
      order.items?.some((item: any) => item.product_name?.toLowerCase().includes(searchLower)) || false

    return matchesOrderId || matchesCustomerName || matchesCustomerEmail || matchesProductName
  })

  const handleOpenOrderChat = (orderId: string) => {
    setSelectedOrderId(orderId)
    setShowOrderChat(true)
  }

  const handleOpenStoreChat = () => {
    setShowStoreChat(true)
  }

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Orders</h1>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={async () => {
              setRefreshSuccess(false)
              await refetch()
              setRefreshSuccess(true)
              setTimeout(() => setRefreshSuccess(false), 2000)
            }}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            title="Refresh orders"
          >
            {refreshSuccess ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                <span className="text-green-600">✓</span>
              </>
            ) : (
              <>
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </>
            )}
          </button>
        <button
          onClick={handleOpenStoreChat}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          <MessageCircle className="h-4 w-4 mr-2" />
          Store Chat
        </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('digital')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'digital'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <span className="inline-flex items-center">
              Digital Orders
              {(pendingCounts?.digital ?? 0) > 0 && (
                <span className="ml-2 inline-flex items-center justify-center h-5 min-w-5 px-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold">
                  {pendingCounts!.digital > 99 ? '99+' : pendingCounts!.digital}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('physical')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'physical'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <span className="inline-flex items-center">
              Physical Orders
              {(pendingCounts?.physical ?? 0) > 0 && (
                <span className="ml-2 inline-flex items-center justify-center h-5 min-w-5 px-1 rounded-full bg-red-100 text-red-700 text-xs font-semibold">
                  {pendingCounts!.physical > 99 ? '99+' : pendingCounts!.physical}
                </span>
              )}
            </span>
          </button>
        </nav>
      </div>

      {/* Order Status Counts */}
      {orders && (
        <div className="mb-6 grid grid-cols-2 md:grid-cols-5 gap-4">
          {(() => {
            const counts = {
              pending: orders.filter(o => o.status === 'pending').length,
              processing: orders.filter(o => o.status === 'processing').length,
              completed: orders.filter(o => o.status === 'completed').length,
              cancelled: orders.filter(o => o.status === 'cancelled').length,
              finished: orders.filter(o => o.status === 'finished').length,
            }
            
            return (
              <>
                <div className="bg-white p-4 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Pending</div>
                  <div className="text-2xl font-bold text-yellow-600">{counts.pending}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Processing</div>
                  <div className="text-2xl font-bold text-blue-600">{counts.processing}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Completed</div>
                  <div className="text-2xl font-bold text-green-600">{counts.completed}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Cancelled</div>
                  <div className="text-2xl font-bold text-red-600">{counts.cancelled}</div>
                </div>
                <div className="bg-white p-4 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Finished</div>
                  <div className="text-2xl font-bold text-purple-600">{counts.finished}</div>
                </div>
              </>
            )
          })()}
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 space-y-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search orders..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md w-full"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md"
          >
            <option value="">All Statuses</option>
            <option value="unfinished">Unfinished</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="finished">Finished</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
      </div>

      {/* Pagination */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="text-sm text-gray-600">
          Page <span className="font-semibold">{page + 1}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isLoading}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((p) => p + 1)}
            disabled={isLoading || (orders ? orders.length < pageSize : true)}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      {/* Orders Table: horizontal scroll on mobile with hint */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <p className="md:hidden px-4 py-2 text-xs text-gray-500 bg-gray-50 border-b">Swipe left to see more columns</p>
        <div className="overflow-x-auto overflow-y-visible" style={{ WebkitOverflowScrolling: 'touch' }}>
          <table className="min-w-full divide-y divide-gray-200" style={{ minWidth: '900px' }}>
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Order ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Product
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Customer
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              {activeTab === 'digital' && (
                <>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Activation Sent
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Activation Template
                  </th>
                </>
              )}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Documentation
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {isLoading ? (
              <tr>
                <td colSpan={activeTab === 'digital' ? 10 : 8} className="px-6 py-4 text-center">Loading...</td>
              </tr>
            ) : filteredOrders && filteredOrders.length > 0 ? (
              filteredOrders.map((order) => {
                const isExpanded = expandedOrders.has(order.yandex_order_id)
                
                // If order doesn't have items array, create one from the single product (backward compatibility)
                let orderItems = order.items
                if (!orderItems || orderItems.length === 0) {
                  // Create a single item from the order's product data
                  orderItems = [{
                    product_id: order.product_id,
                    product_name: order.product_name || 'Unknown Product',
                    quantity: order.quantity || 1,
                    item_price: order.total_amount / (order.quantity || 1),
                    item_total: order.total_amount,
                    activation_code_sent: order.activation_code_sent,
                    email_template_id: null, // Will be fetched by OrderActivationTemplate component
                    documentation_id: null, // Will be fetched by OrderDocumentationButton component
                  }]
                }
                
                // Always show expand button for all orders, even single-product ones
                const hasItems = orderItems && orderItems.length > 0
                const hasMultipleItems = orderItems && orderItems.length > 1
                
                // Check if ALL products in the order have activation templates
                const allProductsHaveTemplates = orderItems 
                  ? orderItems.every(item => item.email_template_id != null)
                  : true  // Fallback if no items array
                
                // Check if ALL products have templates with random_key checked
                const allProductsHaveRandomKey = orderItems && allTemplates
                  ? orderItems.every(item => {
                      if (!item.email_template_id) return false
                      const template = allTemplates.find(t => t.id === item.email_template_id)
                      return template?.random_key === true
                    })
                  : true  // Fallback if no items or templates
                
                return (
                  <>
                    {/* Main order row */}
                    <tr key={order.id} className="bg-gray-50 hover:bg-gray-100 cursor-pointer" onClick={() => toggleOrderExpansion(order.yandex_order_id)}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        <div className="flex items-center gap-2">
                          {/* Always show expand/collapse button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleOrderExpansion(order.yandex_order_id)
                            }}
                            className="text-gray-500 hover:text-gray-700"
                          >
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                          {order.yandex_order_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                        <div className="font-medium">
                          {order.items_count || orderItems.length} product{(order.items_count || orderItems.length) !== 1 ? 's' : ''}
                        </div>
                      </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{order.customer_name || 'N/A'}</div>
                    <div className="text-sm text-gray-500">{order.customer_email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₽{order.total_amount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {order.status === 'completed' ? (
                      <button
                        onClick={() => setMarkFinishedConfirm({ isOpen: true, orderId: order.id })}
                        className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 hover:bg-green-200 cursor-pointer transition-colors"
                        title="Click to mark as finished"
                      >
                        {order.status} (Click to finish)
                      </button>
                    ) : (
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        order.status === 'finished' ? 'bg-purple-100 text-purple-800' :
                        order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        order.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {order.status}
                      </span>
                    )}
                  </td>
                  {activeTab === 'digital' && (
                    <>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {order.activation_code_sent ? (
                          <span className="inline-flex items-center text-green-600">
                            <CheckCircle className="h-5 w-5 mr-1" />
                            Sent
                          </span>
                        ) : (
                          <span className="text-gray-400">Not sent</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {hasMultipleItems ? (
                          <span className="text-gray-400 text-xs">See products below</span>
                        ) : hasItems ? (
                          <span className="text-gray-400 text-xs">See product below</span>
                        ) : (
                          <OrderActivationTemplate 
                            productId={order.product_id} 
                            activationCodeSent={order.activation_code_sent}
                          />
                        )}
                      </td>
                    </>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDateTime(order.order_created_at || order.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    {hasMultipleItems ? (
                      <span className="text-gray-400 text-xs">See products below</span>
                    ) : hasItems ? (
                      <span className="text-gray-400 text-xs">See product below</span>
                    ) : (
                      <OrderDocumentationButton
                        productId={order.product_id}
                        onViewDocs={() => setDocViewerModal({ isOpen: true, productId: order.product_id })}
                      />
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end space-x-2" onClick={(e) => e.stopPropagation()}>
                      {order.status === 'pending' && (
                        <button
                          onClick={() => fulfillMutation.mutate(order.id)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Fulfill Order"
                        >
                          <RefreshCw className="h-5 w-5" />
                        </button>
                      )}
                      {/* Show Send Activation button at order level - whenever activation not yet sent */}
                      {activeTab === 'digital' && 
                       order.status === 'processing' && 
                       !order.activation_code_sent && (
                        <button
                          onClick={() => {
                            if (!allProductsHaveTemplates) {
                              showNotification('error', 'Cannot send activation: Some products are missing activation templates. Please attach templates to all products first.')
                              return
                            }
                            
                            // If all products have random_key checked, send automatically
                            if (allProductsHaveRandomKey) {
                              setSendActivationConfirm({ isOpen: true, orderId: order.id })
                            } else {
                              // Show manual activation key entry modal
                              setManualActivationModal({ isOpen: true, orderId: order.id, orderItems: orderItems || [] })
                            }
                          }}
                          className={allProductsHaveTemplates 
                            ? "text-purple-600 hover:text-purple-900" 
                            : "text-gray-400 cursor-not-allowed opacity-50"}
                          title={allProductsHaveTemplates 
                            ? (allProductsHaveRandomKey 
                                ? "Send Activation for all products" 
                                : "Enter activation keys manually")
                            : "Cannot send: Some products are missing activation templates"}
                        >
                          <Mail className="h-5 w-5" />
                        </button>
                      )}
                      {order.status === 'processing' && order.activation_code_sent && (
                        <button
                          onClick={() => {
                            setCompleteConfirm({ isOpen: true, orderId: order.id })
                          }}
                          className="text-green-600 hover:text-green-900"
                          title="Complete Order"
                        >
                          <CheckCircle className="h-5 w-5" />
                        </button>
                      )}
                      {order.status === 'finished' && !order.has_client && (
                        <button
                          onClick={async () => {
                            // Check if client already exists by buyer_id (auto-append)
                            try {
                              // Try to auto-append if buyer_id exists (pass undefined for email, not empty string)
                              await clientsApi.createFromOrder(order.yandex_order_id, undefined, order.customer_name || undefined)
                              showNotification('success', 'Order appended to existing client automatically!')
                              // Immediately invalidate queries to update UI
                              await queryClient.invalidateQueries({ queryKey: ['orders'] })
                              await queryClient.invalidateQueries({ queryKey: ['clients'] })
                              // Refetch orders to get updated has_client flag
                              refetch()
                            } catch (error: any) {
                              // If auto-append fails (no buyer_id match), show modal for email input
                              if (error.response?.status === 400 && error.response?.data?.detail?.includes('Email is required')) {
                                setCreateClientModal({ 
                                  isOpen: true, 
                                  orderId: order.yandex_order_id,
                                  customerName: order.customer_name || null
                                })
                              } else if (error.response?.status === 400 && error.response?.data?.detail?.includes('already exists')) {
                                // Client already exists - refresh to update has_client flag
                                showNotification('success', error.response?.data?.detail || 'Client already exists for this order')
                                await queryClient.invalidateQueries({ queryKey: ['orders'] })
                                refetch()
                              } else {
                                showNotification('error', error.response?.data?.detail || 'Failed to create client')
                              }
                            }
                          }}
                          className="text-blue-600 hover:text-blue-900"
                          title="Create Client"
                        >
                          <UserPlus className="h-5 w-5" />
                        </button>
                      )}
                      <OrderChatButton orderId={order.yandex_order_id} onOpenChat={handleOpenOrderChat} />
                    </div>
                  </td>
                </tr>
                
                {/* Expanded product rows - show for ALL orders when expanded */}
                {isExpanded && hasItems && orderItems && orderItems.map((item, idx) => (
                  <tr key={`${order.id}-item-${idx}`} className="bg-white border-l-4 border-blue-200" onClick={(e) => e.stopPropagation()}>
                    <td className="px-6 py-3 text-sm text-gray-500">
                      {/* Empty for alignment */}
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-900">
                      <div className="font-medium">{item.product_name}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Qty: {item.quantity} × ₽{item.item_price.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} = ₽{item.item_total.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                      </div>
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-500">
                      {/* Empty for alignment */}
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-900">
                      ₽{item.item_total.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-500">
                      {/* Empty for alignment */}
                    </td>
                    {activeTab === 'digital' && (
                      <>
                        <td className="px-6 py-3 text-sm text-gray-500">
                          {/* Empty - activation status shown at order level */}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-500">
                          <OrderActivationTemplate 
                            productId={item.product_id} 
                            activationCodeSent={item.activation_code_sent ?? order.activation_code_sent}
                          />
                        </td>
                      </>
                    )}
                    <td className="px-6 py-3 text-sm text-gray-500">
                      {/* Empty for alignment */}
                    </td>
                    <td className="px-6 py-3 text-sm font-medium">
                      <OrderDocumentationButton
                        productId={item.product_id}
                        onViewDocs={() => setDocViewerModal({ isOpen: true, productId: item.product_id })}
                      />
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-500">
                      {/* Empty for alignment */}
                    </td>
                  </tr>
                ))}
                  </>
                )
              })
            ) : (
              <tr>
                <td colSpan={activeTab === 'digital' ? 10 : 8} className="px-6 py-4 text-center text-gray-500">
                  No orders found
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Order Chat Modal */}
      {showOrderChat && selectedOrderId && (
        <OrderChatModal
          orderId={selectedOrderId}
          onClose={() => {
            setShowOrderChat(false)
            setSelectedOrderId(null)
          }}
        />
      )}

      {/* Store Chat Modal */}
      {showStoreChat && (
        <StoreChatModal
          onClose={() => setShowStoreChat(false)}
        />
      )}

      {/* Send Activation Confirmation Modal */}
      <ConfirmationModal
        isOpen={sendActivationConfirm.isOpen}
        title="Send Activation"
        message="Send the activation codes and instructions to Yandex Market for all products in this order? This will deliver the digital goods to the customer and complete the order."
        confirmText="Send Activation"
        cancelText="Cancel"
        variant="info"
        onConfirm={() => {
          if (sendActivationConfirm.orderId) {
            sendActivationMutation.mutate({ id: sendActivationConfirm.orderId })
          }
          setSendActivationConfirm({ isOpen: false, orderId: null })
        }}
        onCancel={() => setSendActivationConfirm({ isOpen: false, orderId: null })}
      />

      {/* Manual Activation Key Entry Modal */}
      {manualActivationModal.isOpen && manualActivationModal.orderId && manualActivationModal.orderItems && (
        <ManualActivationModal
          orderItems={manualActivationModal.orderItems}
          allTemplates={allTemplates || []}
          onClose={() => setManualActivationModal({ isOpen: false, orderId: null, orderItems: null })}
          onConfirm={(activationKeys) => {
            if (manualActivationModal.orderId) {
              sendActivationMutation.mutate({ id: manualActivationModal.orderId, activationKeys })
            }
          }}
          isLoading={sendActivationMutation.isPending}
        />
      )}

      {/* Mark Finished Confirmation Modal */}
      <ConfirmationModal
        isOpen={markFinishedConfirm.isOpen}
        title="Mark Order as Finished"
        message="Mark this order as finished? This indicates you have completed all interactions with the buyer."
        confirmText="Mark as Finished"
        cancelText="Cancel"
        variant="info"
        onConfirm={() => {
          if (markFinishedConfirm.orderId) {
            ordersApi.markFinished(markFinishedConfirm.orderId).then(() => {
              queryClient.invalidateQueries({ queryKey: ['orders'] })
              showNotification('success', 'Order marked as finished!')
            }).catch((error: any) => {
              showNotification('error', error?.response?.data?.detail || 'Failed to mark order as finished')
            })
          }
          setMarkFinishedConfirm({ isOpen: false, orderId: null })
        }}
        onCancel={() => setMarkFinishedConfirm({ isOpen: false, orderId: null })}
      />

      {/* Complete Order Confirmation Modal */}
      <ConfirmationModal
        isOpen={completeConfirm.isOpen}
        title="Complete Order"
        message="Mark this order as completed?"
        confirmText="Complete"
        cancelText="Cancel"
        variant="info"
        onConfirm={() => {
          if (completeConfirm.orderId) {
            completeMutation.mutate(completeConfirm.orderId)
          }
          setCompleteConfirm({ isOpen: false, orderId: null })
        }}
        onCancel={() => setCompleteConfirm({ isOpen: false, orderId: null })}
      />

      {/* Documentation Viewer Modal */}
      {docViewerModal.isOpen && docViewerModal.productId !== null && docViewerModal.productId !== undefined && (
        <DocumentationViewerModal
          productId={docViewerModal.productId}
          onClose={() => setDocViewerModal({ isOpen: false, productId: null })}
        />
      )}

      {/* Create Client Modal */}
      {createClientModal.isOpen && createClientModal.orderId && (
        <CreateClientFromOrderModal
          orderId={createClientModal.orderId}
          customerName={createClientModal.customerName}
          onClose={() => setCreateClientModal({ isOpen: false, orderId: null, customerName: null })}
          onSuccess={async () => {
            setCreateClientModal({ isOpen: false, orderId: null, customerName: null })
            showNotification('success', 'Client created successfully!')
            // Immediately invalidate and refetch to update UI
            await queryClient.invalidateQueries({ queryKey: ['orders'] })
            await queryClient.invalidateQueries({ queryKey: ['clients'] })
            refetch()
          }}
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

// Order Chat Button Component with Unread Count Badge
function OrderChatButton({ orderId, onOpenChat }: { orderId: string; onOpenChat: (orderId: string) => void }) {
  const { data: unreadCount } = useQuery({
    queryKey: ['order-chat-unread', orderId],
    queryFn: () => chatApi.getUnreadCount(orderId),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const handleClick = () => {
    // Open the chat modal immediately (don't block on network)
    onOpenChat(orderId)
  }

  return (
    <button
      onClick={handleClick}
      className="relative text-indigo-600 hover:text-indigo-900"
      title="View Chat"
    >
      <MessageCircle className="h-5 w-5" />
      {unreadCount && unreadCount > 0 && (
        <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </button>
  )
}

// Order Chat Modal Component
function OrderChatModal({ orderId, onClose }: { orderId: string; onClose: () => void }) {
  const { formatDateTime } = useTimeZone()
  const [messageText, setMessageText] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [attachedFiles, setAttachedFiles] = useState<{ url: string; name: string }[]>([])
  const queryClient = useQueryClient()
  const messagesScrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)
  const initialAutoScrollDoneRef = useRef(false)
  const openedLastSeenRef = useRef<string | null>(null)
  const autoMarkedReadRef = useRef(false)
  const [markingRead, setMarkingRead] = useState(false)

  const { data: messages, isLoading, isFetching } = useQuery({
    queryKey: ['order-chat', orderId],
    queryFn: () => chatApi.getOrderMessages(orderId),
    refetchInterval: 5000, // Refresh every 5 seconds
    placeholderData: (prev) => prev,
  })

  // Copy UI handled by shared CopyButton component

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setUploadError(null)
    setIsUploading(true)
    try {
      const fileArray = Array.from(files)
      const uploaded = await mediaApi.uploadFiles(fileArray, 'documentation')
      setAttachedFiles(prev => [
        ...prev,
        ...uploaded.map(f => ({
          url: mediaApi.encodeFileUrl(f.url),
          name: mediaApi.decodeFileName(f.url),
        })),
      ])
      // Clear the input so the same file can be selected again if needed
      event.target.value = ''
    } catch (error: any) {
      console.error('Failed to upload chat attachments:', error)
      setUploadError(error?.response?.data?.detail || 'Failed to upload files')
    } finally {
      setIsUploading(false)
    }
  }

  // On open: capture last seen. Do NOT auto-mark as read (user may already have read in Yandex).
  React.useEffect(() => {
    initialAutoScrollDoneRef.current = false
    autoMarkedReadRef.current = false
    openedLastSeenRef.current = localStorage.getItem(`order_chat_last_seen_${orderId}`)
  }, [orderId, queryClient])

  useEffect(() => {
    const el = messagesScrollRef.current
    if (!el) return
    if (!messages || messages.length === 0) return

    if (!initialAutoScrollDoneRef.current) {
      const lastSeen = openedLastSeenRef.current
      let didScrollToUnread = false
      if (lastSeen) {
        const lastSeenMs = new Date(lastSeen).getTime()
        if (!Number.isNaN(lastSeenMs)) {
          const firstUnread = messages.find((m) => {
            if (!m.created_at) return false
            const ms = new Date(m.created_at).getTime()
            return !Number.isNaN(ms) && ms > lastSeenMs
          })
          if (firstUnread) {
            const node = el.querySelector(`[data-message-id="${firstUnread.id}"]`) as HTMLElement | null
            if (node) {
              node.scrollIntoView({ block: 'center' })
              didScrollToUnread = true
            }
          }
        }
      }

      if (!didScrollToUnread) {
        el.scrollTop = el.scrollHeight
      }
      initialAutoScrollDoneRef.current = true
    }

    if (stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight
    }
  }, [orderId, messages?.length])

  const markOrderChatAsRead = async () => {
    if (!messages || messages.length === 0) return
    const latest = [...messages]
      .map((m) => m.created_at)
      .filter(Boolean)
      .sort()
      .slice(-1)[0] as string | undefined
    if (latest) localStorage.setItem(`order_chat_last_seen_${orderId}`, latest)
    setMarkingRead(true)
    try {
      queryClient.setQueryData(['order-chat-unread', orderId], 0)
      await chatApi.markAsRead(orderId)
    } catch (e) {
      console.error('Failed to mark chat as read:', e)
    } finally {
      setMarkingRead(false)
      queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderId] })
    }
  }

  const sendMessageMutation = useMutation({
    mutationFn: (text: string) => chatApi.sendOrderMessage(orderId, text),
    onSuccess: () => {
      setMessageText('')
      setAttachedFiles([])
      queryClient.invalidateQueries({ queryKey: ['order-chat', orderId] })
      queryClient.invalidateQueries({ queryKey: ['order-chat-unread', orderId] })
    },
    onError: () => {
      // Still clear the input field even on error since message was sent
      setMessageText('')
      queryClient.invalidateQueries({ queryKey: ['order-chat', orderId] })
    },
  })

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    const baseText = messageText.trim()
    const hasFiles = attachedFiles.length > 0
    if (!baseText && !hasFiles) return

    // Build message text with file links appended on new lines
    let finalText = baseText
    if (hasFiles) {
      const filesBlock = attachedFiles
        .map((file) => `📎 ${file.name}: ${file.url}`)
        .join('\n')
      finalText = finalText ? `${finalText}\n\n${filesBlock}` : filesBlock
    }

    sendMessageMutation.mutate(finalText)
  }

  const extractAttachmentsFromMessage = (text: string | undefined) => {
    if (!text) return { body: text, attachments: [] as { url: string; name: string }[] }
    const lines = text.split('\n')
    const attachmentLines: string[] = []
    const bodyLines: string[] = []

    for (const line of lines) {
      if (line.trim().startsWith('📎 ')) {
        attachmentLines.push(line.trim())
      } else {
        bodyLines.push(line)
      }
    }

    const attachments = attachmentLines
      .map((line) => {
        // Format: 📎 name: url
        const withoutIcon = line.replace(/^📎\s*/, '')
        const parts = withoutIcon.split(':')
        if (parts.length < 2) return null
        const name = parts[0].trim()
        const url = parts.slice(1).join(':').trim()
        if (!url) return null
        return { url, name: name || url }
      })
      .filter((x): x is { url: string; name: string } => !!x)

    return { body: bodyLines.join('\n').trim(), attachments }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4 gap-3">
          <h3 className="text-xl font-bold text-gray-900">Order Chat - {orderId}</h3>
          <div className="flex items-center gap-2">
            <FeedbackButton
              onAction={markOrderChatAsRead}
              disabled={markingRead}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
              title="Mark chat as read (use if you already read in Yandex)"
              label="Mark as read"
              successLabel="Marked as read"
              successClassName="border-green-300 bg-green-50 text-green-800 hover:bg-green-100"
              errorLabel="Failed"
              errorClassName="border-red-300 bg-red-50 text-red-800 hover:bg-red-100"
              successChildren={
                <>
                  <CheckCheck className="h-4 w-4" />
                  Marked
                </>
              }
            >
              <>
                <CheckCheck className={`h-4 w-4 ${markingRead ? 'animate-pulse' : ''}`} />
                Mark as read
              </>
            </FeedbackButton>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={messagesScrollRef}
          onScroll={() => {
            const el = messagesScrollRef.current
            if (!el) return
            const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
            stickToBottomRef.current = distanceFromBottom < 120
            if (distanceFromBottom < 30 && messages && messages.length > 0) {
              const latest = [...messages]
                .map((m) => m.created_at)
                .filter(Boolean)
                .sort()
                .slice(-1)[0] as string | undefined
              if (latest) {
                localStorage.setItem(`order_chat_last_seen_${orderId}`, latest)
                if (!autoMarkedReadRef.current) {
                  autoMarkedReadRef.current = true
                  queryClient.setQueryData(['order-chat-unread', orderId], 0)
                  chatApi
                    .markAsRead(orderId)
                    .then(() => queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderId] }))
                    .catch(() => queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderId] }))
                } else {
                  queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderId] })
                }
              }
            }
          }}
          className="flex-1 overflow-y-auto mb-4 space-y-3 border border-gray-200 rounded-lg p-4 bg-gray-50"
        >
          {isLoading ? (
            <div className="text-center py-4 text-gray-500">Loading messages...</div>
          ) : messages && messages.length > 0 ? (
            messages.map((message: ChatMessage) => (
              <div
                key={message.id}
                data-message-id={message.id}
                className={`flex ${message.author === 'SELLER' ? 'justify-end' : 'justify-start'}`}
              >
                {(() => {
                  const { body, attachments } = extractAttachmentsFromMessage(message.text)
                  return (
                <div
                  className={`relative max-w-xs lg:max-w-md px-4 py-2 rounded-lg break-words whitespace-pre-wrap ${
                    message.author === 'SELLER'
                      ? 'bg-blue-600 text-white'
                      : message.author === 'CUSTOMER'
                      ? 'bg-white text-gray-900 border border-gray-200'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                >
                  <div className="text-xs mb-1 opacity-75">
                    {message.author === 'SELLER' ? 'You' : message.author === 'CUSTOMER' ? 'Customer' : 'System'}
                  </div>
                  {body && (
                    <div className="text-sm break-words whitespace-pre-wrap">{body}</div>
                  )}
                  {attachments.length > 0 && (
                    <div className="mt-2 space-y-1 text-xs">
                      {attachments.map((file, idx) => (
                        <a
                          key={`${file.url}-${idx}`}
                          href={file.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 underline decoration-dotted hover:decoration-solid break-all"
                        >
                          <FileText className="h-3 w-3" />
                          <span>{file.name}</span>
                        </a>
                      ))}
                    </div>
                  )}
                  <div className="absolute top-2 right-2">
                    <CopyButton
                      text={message.text}
                      title="Copy message"
                      className="inline-flex items-center gap-1 rounded-full bg-black/10 px-2 py-0.5 text-[10px] font-medium hover:bg-black/20 text-inherit"
                      copiedLabel="Copied"
                      label="Copy"
                    />
                  </div>
                  {message.created_at && (
                    <div className="text-xs mt-1 opacity-75">
                      {formatDateTime(message.created_at)}
                    </div>
                  )}
                </div>
                  )
                })()}
              </div>
            ))
          ) : (
            <div className="text-center py-4 text-gray-500">No messages yet. Start the conversation!</div>
          )}
          {!isLoading && isFetching && (
            <div className="text-center pt-2 text-xs text-gray-400">Refreshing…</div>
          )}
        </div>

        {/* Attachments & Message Input */}
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <label className="inline-flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-md text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer">
                <Paperclip className="h-4 w-4" />
                <span>Attach files</span>
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileChange}
                  disabled={isUploading || sendMessageMutation.isPending}
                />
              </label>
              {isUploading && (
                <span className="text-xs text-gray-500">Uploading…</span>
              )}
            </div>
            {uploadError && (
              <span className="text-xs text-red-600 truncate">{uploadError}</span>
            )}
          </div>

          {attachedFiles.length > 0 && (
            <div className="max-h-20 overflow-y-auto rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2">
              <div className="text-[11px] font-medium text-gray-600 mb-1">Attached files (will be sent as links):</div>
              <ul className="space-y-0.5 text-[11px] text-gray-700">
                {attachedFiles.map((file, idx) => (
                  <li key={`${file.url}-${idx}`} className="flex items-center gap-1">
                    <span className="text-gray-500">•</span>
                    <a
                      href={file.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline break-all"
                    >
                      {file.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <form onSubmit={handleSend} className="flex space-x-2">
            <input
              type="text"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={sendMessageMutation.isPending}
            />
            <button
              type="submit"
              disabled={sendMessageMutation.isPending || (!messageText.trim() && attachedFiles.length === 0)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

// Store Chat Modal Component (General store-wide chat)
function StoreChatModal({ onClose }: { onClose: () => void }) {
  const [messageText, setMessageText] = useState('')

  // For store chat, we'll use a general endpoint or show a message
  // Since Yandex API might not have a general store chat, we'll show a placeholder
  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (messageText.trim()) {
      // TODO: Implement general store chat API endpoint
      setMessageText('')
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-gray-900">Store Chat</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-3 border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="text-center py-8 text-gray-500">
            <MessageCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>General store chat is coming soon!</p>
            <p className="text-sm mt-2">For now, please use order-specific chats by clicking the chat icon on any order.</p>
          </div>
        </div>

        {/* Message Input */}
        <form onSubmit={handleSend} className="flex space-x-2">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder="General store chat coming soon..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled
          />
          <button
            type="submit"
            disabled
            className="px-4 py-2 bg-gray-400 text-white rounded-md cursor-not-allowed flex items-center"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  )
}

function OrderActivationTemplate({ 
  productId, 
  showButton = false,
  orderStatus,
  activationCodeSent,
  autoActivationEnabled,
  onSendActivation
}: { 
  productId: number | null | undefined
  showButton?: boolean
  orderStatus?: string
  activationCodeSent?: boolean
  autoActivationEnabled?: boolean
  onSendActivation?: () => void
}) {
  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsApi.getById(productId!),
    enabled: !!productId,
  })

  // Fetch all activation templates to check random_key
  const { data: allTemplates } = useQuery({
    queryKey: ['activation-templates'],
    queryFn: () => activationTemplatesApi.getAll(undefined, { skip: 0, limit: 2000 }),
  })

  // If product not in database
  if (!productId) {
    if (showButton) {
      return null
    }
    return <span className="text-gray-400 text-xs">Product not in database</span>
  }

  // If showButton is true, show the Send Activation button (for Actions column)
  if (showButton) {
    if (orderStatus === 'processing' && 
        !activationCodeSent && 
        product?.email_template_id &&
        !autoActivationEnabled) {
      return (
        <button
          onClick={onSendActivation}
          className="text-purple-600 hover:text-purple-900"
          title="Send Activation"
        >
          <Mail className="h-5 w-5" />
        </button>
      )
    }
    return null
  }

  // Otherwise, show the activation template status (for Activation Template column)
  if (!product?.email_template_id) {
    return <span className="text-red-600">✗ Not attached</span>
  }

  // Check if template requires manual activation key
  const template = allTemplates?.find(t => t.id === product.email_template_id)
  const requiresManualKey = template && !template.random_key

  return (
    <div className="flex flex-col">
      <span className="text-green-600">✓ Attached</span>
      {requiresManualKey && !activationCodeSent && (
        <span className="text-xs text-orange-600 mt-1">Requires activation key</span>
      )}
    </div>
  )
}

function OrderDocumentationButton({ productId, onViewDocs }: { productId: number | null | undefined; onViewDocs: () => void }) {
  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsApi.getById(productId!),
    enabled: !!productId,
  })

  if (!productId) {
    return <span className="text-gray-400 text-xs">Product not in database</span>
  }

  if (!product?.documentation_id) {
    return <span className="text-gray-400 text-xs">No documentation</span>
  }

  return (
    <button
      onClick={onViewDocs}
      className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
      title="View documentation"
    >
      <FileText className="h-4 w-4 mr-1" />
      View Docs
    </button>
  )
}

// Documentation Viewer Modal
function DocumentationViewerModal({ productId, onClose }: { productId: number | null | undefined; onClose: () => void }) {
  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsApi.getById(productId!),
    enabled: !!productId,
  })

  const { data: documentation, isLoading } = useQuery({
    queryKey: ['documentation', product?.documentation_id],
    queryFn: () => documentationsApi.get(product!.documentation_id!),
    enabled: !!product?.documentation_id,
  })

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div className="relative bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {documentation?.name || 'Documentation'}
            </h3>
            {documentation?.description && (
              <p className="text-sm text-gray-500 mt-1">{documentation.description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">Loading documentation...</div>
          ) : !documentation ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No documentation found for this product.</p>
            </div>
          ) : documentation.type === 'text' && documentation.content ? (
            <div
              className="prose max-w-none"
              dangerouslySetInnerHTML={{ __html: documentation.content }}
            />
          ) : documentation.type === 'file' && documentation.file_url ? (
            <div className="text-center py-8">
              <FileText className="h-16 w-16 mx-auto mb-4 text-blue-500" />
              <p className="text-gray-700 mb-4">This documentation is a file attachment.</p>
              <a
                href={mediaApi.encodeFileUrl(documentation.file_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <FileText className="h-4 w-4 mr-2" />
                Open File
              </a>
            </div>
          ) : documentation.type === 'link' && documentation.link_url ? (
            <div className="text-center py-8">
              <FileText className="h-16 w-16 mx-auto mb-4 text-blue-500" />
              <p className="text-gray-700 mb-4">This documentation is an external link.</p>
              <a
                href={documentation.link_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <FileText className="h-4 w-4 mr-2" />
                Open Link
              </a>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <p>No content available for this documentation.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-3 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// Manual Activation Key Entry Modal
function ManualActivationModal({
  orderItems,
  allTemplates,
  onClose,
  onConfirm,
  isLoading,
}: {
  orderItems: any[]
  allTemplates: any[]
  onClose: () => void
  onConfirm: (activationKeys: Record<number, string>) => void
  isLoading: boolean
}) {
  const [activationKeys, setActivationKeys] = useState<Record<number, string>>({})

  // Filter items that need manual activation keys (templates without random_key)
  const itemsNeedingKeys = orderItems.filter(item => {
    if (!item.email_template_id) return false
    const template = allTemplates.find(t => t.id === item.email_template_id)
    return template && template.random_key === false
  })

  const handleKeyChange = (productId: number, key: string) => {
    setActivationKeys(prev => ({
      ...prev,
      [productId]: key
    }))
  }

  const handleConfirm = () => {
    // Validate that all required keys are entered
    const missingKeys = itemsNeedingKeys.filter(item => !activationKeys[item.product_id]?.trim())
    if (missingKeys.length > 0) {
      alert(`Please enter activation keys for all products:\n${missingKeys.map(item => `- ${item.product_name}`).join('\n')}`)
      return
    }
    onConfirm(activationKeys)
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-gray-900">Enter Activation Keys</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isLoading}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-4">
            This order contains products with activation templates that require manual activation keys. 
            Please enter the activation key for each product below.
          </p>
        </div>

        <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
          {itemsNeedingKeys.map((item) => {
            const template = allTemplates.find(t => t.id === item.email_template_id)
            return (
              <div key={item.product_id} className="border border-gray-200 rounded-lg p-4">
                <div className="mb-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {item.product_name}
                    {item.quantity > 1 && <span className="text-gray-500 ml-2">(Qty: {item.quantity})</span>}
                  </label>
                  {template && (
                    <p className="text-xs text-gray-500 mb-2">
                      Template: {template.name} (Random Key: {template.random_key ? 'Yes' : 'No'})
                    </p>
                  )}
                </div>
                <input
                  type="text"
                  value={activationKeys[item.product_id] || ''}
                  onChange={(e) => handleKeyChange(item.product_id, e.target.value)}
                  placeholder="Enter activation key..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                />
              </div>
            )
          })}
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-100"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading || itemsNeedingKeys.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Sending...' : 'Send Activation'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Create Client From Order Modal Component
function CreateClientFromOrderModal({
  orderId,
  customerName,
  onClose,
  onSuccess,
}: {
  orderId: string
  customerName: string | null
  onClose: () => void
  onSuccess: () => void
}) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState(customerName || '')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) {
      alert('Please enter an email address')
      return
    }

    setIsLoading(true)
    try {
      await clientsApi.createFromOrder(orderId, email.trim(), name.trim() || undefined)
      onSuccess()
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message
      if (errorMsg.includes('already exists')) {
        alert('Client already exists for this order. The order has been appended to the existing client.')
        onSuccess() // Refresh anyway
      } else {
        alert('Failed to create client: ' + errorMsg)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-900">Create Client from Order</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isLoading}
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={customerName || 'Enter client name'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <p className="mt-1 text-xs text-gray-500">
              {customerName ? `Default: ${customerName}` : 'Leave empty to use order customer name'}
            </p>
          </div>
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !email.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Creating...' : 'Create Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
