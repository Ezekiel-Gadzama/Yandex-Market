import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dashboardApi, DateRange } from '../api/dashboard'
import { useAuth } from '../contexts/AuthContext'
import { settingsApi } from '../api/settings'
import { syncApi } from '../api/sync'
import { 
  Package, 
  ShoppingCart, 
  DollarSign, 
  TrendingUp,
  Calendar,
  Edit2,
  ChevronDown,
  ChevronRight,
  X,
  Trash2,
  Pencil,
  List
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useTimeZone } from '../contexts/TimeZoneContext'

export default function Dashboard() {
  const { formatDateTime } = useTimeZone()
  const { user } = useAuth()
  const hasDashboardRight = user?.is_admin || user?.permissions.dashboard_right
  const [period, setPeriod] = useState<string>('all')
  const [dateRange, setDateRange] = useState<DateRange>({})
  const [tempDateRange, setTempDateRange] = useState<DateRange>({})
  const [showDatePicker, setShowDatePicker] = useState(false)
  const datePickerRef = useRef<HTMLDivElement>(null)
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  const [recentOrdersFilter, setRecentOrdersFilter] = useState<'all' | 'digital' | 'physical'>('all')
  const hasCheckedSyncRef = useRef(false)
  const [extraCostDescription, setExtraCostDescription] = useState('')
  const [extraCostAmount, setExtraCostAmount] = useState('')
  const [extraCostDate, setExtraCostDate] = useState('')
  const [showExtraCostsModal, setShowExtraCostsModal] = useState(false)
  const [editingCostId, setEditingCostId] = useState<number | null>(null)
  const [editDescription, setEditDescription] = useState('')
  const [editAmount, setEditAmount] = useState('')
  const [editDate, setEditDate] = useState('')
  const queryClient = useQueryClient()

  const resetExtraCostsModalInputs = () => {
    setExtraCostDescription('')
    setExtraCostAmount('')
    setExtraCostDate('')
    setEditingCostId(null)
    setEditDescription('')
    setEditAmount('')
    setEditDate('')
  }

  const closeExtraCostsModal = () => {
    setShowExtraCostsModal(false)
    resetExtraCostsModalInputs()
  }

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
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', period, dateRange],
    queryFn: () => dashboardApi.getData(period, dateRange),
  })
  const todayStr = format(new Date(), 'yyyy-MM-dd')

  const createExtraCostMutation = useMutation({
    mutationFn: (payload: { description: string; amount: number; date: string }) =>
      dashboardApi.createExtraCost(payload),
    onSuccess: () => {
      setExtraCostDescription('')
      setExtraCostAmount('')
      setExtraCostDate('')
      queryClient.invalidateQueries({ queryKey: ['dashboard', period, dateRange] })
    },
  })

  const updateExtraCostMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { description: string; amount: number; date: string } }) =>
      dashboardApi.updateExtraCost(id, payload),
    onSuccess: () => {
      setEditingCostId(null)
      queryClient.invalidateQueries({ queryKey: ['dashboard', period, dateRange] })
    },
  })

  const deleteExtraCostMutation = useMutation({
    mutationFn: (id: number) => dashboardApi.deleteExtraCost(id),
    onSuccess: () => {
      setEditingCostId(null)
      queryClient.invalidateQueries({ queryKey: ['dashboard', period, dateRange] })
    },
  })

  const startEditingCost = (cost: { id: number; description: string; amount: number; date: string }) => {
    setEditingCostId(cost.id)
    setEditDescription(cost.description)
    setEditAmount(String(cost.amount))
    setEditDate(cost.date)
  }

  const cancelEditingCost = () => {
    setEditingCostId(null)
  }

  const saveEditingCost = () => {
    if (editingCostId == null) return
    const amountNum = Number(editAmount)
    if (!editDescription.trim() || !editDate || !Number.isFinite(amountNum) || amountNum <= 0) return
    if (editDate > todayStr) return
    updateExtraCostMutation.mutate({
      id: editingCostId,
      payload: { description: editDescription.trim(), amount: amountNum, date: editDate },
    })
  }

  // Check settings on mount and trigger sync if Yandex API is configured
  useEffect(() => {
    if (!user || !user.is_admin || hasCheckedSyncRef.current) return
    
    const checkAndSync = async () => {
      hasCheckedSyncRef.current = true
      
      try {
        const settings = await settingsApi.get()
        const hasYandexConfig = settings.yandex_api_token && 
          (settings.yandex_business_id || settings.yandex_campaign_id)
        
        if (hasYandexConfig) {
          // Trigger sync in background (don't wait for it)
          syncApi.syncAll(false).catch((error) => {
            // Silently fail - sync will happen when user manually triggers it
            console.log('Auto-sync on login:', error?.response?.data?.detail || error.message)
          })
        }
      } catch (error) {
        // Silently fail - settings might not be loaded yet
        console.log('Could not check settings for auto-sync on login')
      }
    }
    
    // Small delay to ensure user is fully loaded
    const timeoutId = setTimeout(checkAndSync, 1000)
    return () => clearTimeout(timeoutId)
  }, [user])
  
  // Close date picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setShowDatePicker(false)
        // Reset temp date range to current applied range when closing without applying
        setTempDateRange(dateRange)
      }
    }
    
    if (showDatePicker) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showDatePicker, dateRange])
  
  const handlePeriodChange = (newPeriod: string) => {
    if (newPeriod === 'custom') {
      setPeriod(newPeriod)
      // Initialize temp date range with current date range when opening picker
      setTempDateRange(dateRange)
      setShowDatePicker(true)
    } else {
      setPeriod(newPeriod)
      setShowDatePicker(false)
      setDateRange({})
      setTempDateRange({})
    }
  }
  
  const handleDateRangeApply = () => {
    if (tempDateRange.startDate && tempDateRange.endDate) {
      setDateRange(tempDateRange)
      setShowDatePicker(false)
    }
  }
  
  const handleDateRangeCancel = () => {
    setShowDatePicker(false)
    // Reset temp date range to current applied range
    setTempDateRange(dateRange)
  }
  
  const getPeriodLabel = () => {
    if (period === 'custom' && dateRange.startDate && dateRange.endDate) {
      return `${format(new Date(dateRange.startDate), 'MMM d, yyyy')} - ${format(new Date(dateRange.endDate), 'MMM d, yyyy')}`
    }
    const labels: Record<string, string> = {
      'today': 'Today',
      'week': 'This Week',
      'month': 'This Month',
      'all': 'All Time',
      'custom': 'Custom Range'
    }
    return labels[period] || 'All Time'
  }

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (error) {
    const errorMessage = (error as any)?.response?.data?.detail?.message || 
                         (error as any)?.response?.data?.detail || 
                         (error as any)?.message || 
                         'Error loading dashboard. Please try again or contact your administrator.'
    return (
      <div className="text-center py-12">
        <div className="text-red-600 font-medium mb-2">Error loading dashboard</div>
        <div className="text-gray-600 text-sm">{errorMessage}</div>
      </div>
    )
  }

  if (!data) return null

  const { stats, top_products, recent_orders, extra_costs = [] } = data

  const visibleRecentOrders =
    recentOrdersFilter === 'all'
      ? recent_orders
      : recent_orders.filter((o: any) => {
          const isDigital = o?.delivery_type === 'DIGITAL'
          return recentOrdersFilter === 'digital' ? isDigital : !isDigital
        })

  const totalExtraCost = extra_costs.reduce((sum, cost) => sum + cost.amount, 0)
  const adjustedProfit = stats.total_profit - totalExtraCost
  const adjustedProfitMargin =
    stats.total_revenue > 0 ? (adjustedProfit / stats.total_revenue) * 100 : 0

  const handleAddExtraCost = () => {
    const amountNumber = Number(extraCostAmount)
    if (!extraCostDescription.trim() || !extraCostDate || !Number.isFinite(amountNumber) || amountNumber <= 0) {
      return
    }
    if (extraCostDate > todayStr) return
    createExtraCostMutation.mutate({
      description: extraCostDescription.trim(),
      amount: amountNumber,
      date: extraCostDate,
    })
  }

  const chartData = top_products.slice(0, 5).map(p => ({
    name: p.product_name.length > 20 ? p.product_name.substring(0, 20) + '...' : p.product_name,
    revenue: p.total_revenue,
    profit: p.total_profit,
  }))

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex items-center gap-2 relative">
          <div className="relative">
            <select
              value={period}
              onChange={(e) => handlePeriodChange(e.target.value)}
              className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none pr-8"
            >
              <option value="today">Today</option>
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="all">All Time</option>
              <option value="custom">Custom Date Range</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
              <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
              </svg>
            </div>
          </div>
          
          {/* Edit button to reopen date picker when in custom mode */}
          {period === 'custom' && (
            <button
              onClick={() => {
                // Initialize temp date range with current date range when opening picker
                setTempDateRange(dateRange)
                setShowDatePicker(true)
              }}
              className="p-2 text-gray-600 hover:text-blue-600 hover:bg-gray-100 rounded-md transition-colors"
              title="Edit date range"
            >
              <Edit2 className="h-4 w-4" />
            </button>
          )}
          
          {/* Date Range Picker */}
          {showDatePicker && (
            <div ref={datePickerRef} className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-10 p-4">
              <div className="flex items-center mb-3">
                <Calendar className="h-5 w-5 text-gray-400 mr-2" />
                <h3 className="text-sm font-medium text-gray-900">Select Date Range</h3>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">From Date</label>
                  <input
                    type="date"
                    value={tempDateRange.startDate || ''}
                    onChange={(e) => setTempDateRange({ ...tempDateRange, startDate: e.target.value })}
                    max={tempDateRange.endDate || undefined}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">To Date</label>
                  <input
                    type="date"
                    value={tempDateRange.endDate || ''}
                    onChange={(e) => setTempDateRange({ ...tempDateRange, endDate: e.target.value })}
                    min={tempDateRange.startDate || undefined}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex space-x-2 pt-2">
                  <button
                    onClick={handleDateRangeApply}
                    disabled={!tempDateRange.startDate || !tempDateRange.endDate}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Apply
                  </button>
                  <button
                    onClick={handleDateRangeCancel}
                    className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Period Label Display */}
          {period === 'custom' && dateRange.startDate && dateRange.endDate && !showDatePicker && (
            <div 
              className="mt-2 text-sm text-gray-600 cursor-pointer hover:text-blue-600"
              onClick={() => {
                // Initialize temp date range with current date range when opening picker
                setTempDateRange(dateRange)
                setShowDatePicker(true)
              }}
              title="Click to change date range"
            >
              {getPeriodLabel()}
            </div>
          )}
          
          {/* Show clickable label when in custom mode but no dates selected */}
          {period === 'custom' && (!dateRange.startDate || !dateRange.endDate) && !showDatePicker && (
            <div 
              className="mt-2 text-sm text-gray-500 cursor-pointer hover:text-blue-600"
              onClick={() => {
                // Initialize temp date range with current date range when opening picker
                setTempDateRange(dateRange)
                setShowDatePicker(true)
              }}
              title="Click to select date range"
            >
              Click to select date range
            </div>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Package className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Products</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.total_products}</dd>
                  <dd className="text-sm text-gray-500">{stats.active_products} active</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ShoppingCart className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Orders</dt>
                  <dd className="text-lg font-medium text-gray-900">{stats.total_orders}</dd>
                  <dd className="text-sm text-gray-500 space-y-1">
                    <div>{stats.pending_orders} pending</div>
                    <div>{stats.processing_orders} processing</div>
                    <div>{stats.completed_orders} completed</div>
                    <div>{stats.cancelled_orders} cancelled</div>
                    <div>{stats.finished_orders} finished</div>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {hasDashboardRight && (
          <>
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <DollarSign className="h-6 w-6 text-gray-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Revenue</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        ₽{stats.total_revenue.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                      </dd>
                      <dd className="text-sm text-gray-500">
                        ₽{stats.total_profit.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} profit
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <TrendingUp className="h-6 w-6 text-gray-400" />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Profit Margin</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {adjustedProfitMargin.toFixed(2)}%
                      </dd>
                      <dd className="text-sm text-gray-500">
                        {stats.successful_orders} successful
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg lg:col-span-2">
              <div className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-900">Extra Costs (Current Period)</h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Total extra cost:{' '}
                    <span className="font-semibold text-red-600">
                      -₽{totalExtraCost.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                    </span>
                    {' · '}
                    Adjusted profit:{' '}
                    <span className="font-semibold text-gray-900">
                      ₽{adjustedProfit.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                    </span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setEditingCostId(null)
                    setShowExtraCostsModal(true)
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <List className="h-4 w-4" />
                  View & manage extra costs
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Products Chart */}
        {hasDashboardRight && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Top Products (Revenue & Profit Chart)</h2>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="revenue" fill="#3b82f6" name="Revenue" />
                  <Bar dataKey="profit" fill="#10b981" name="Profit" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8">No sales data yet</p>
            )}
          </div>
        )}

        {/* Top Products List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Top Selling Products (Sales Count)</h2>
          {top_products.length > 0 ? (
            <div className="space-y-4">
              {top_products.slice(0, 5).map((product) => (
                <div key={product.product_id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{product.product_name}</p>
                    <p className="text-sm text-gray-500">{product.total_sales} sales</p>
                  </div>
                  {hasDashboardRight && (
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        ₽{product.total_revenue.toLocaleString('ru-RU')}
                      </p>
                      <p className="text-sm text-green-600">
                        ₽{product.total_profit.toLocaleString('ru-RU')} profit
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No products sold yet</p>
          )}
        </div>
      </div>

      {/* Recent Orders */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 sm:px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-medium text-gray-900">Recent Orders</h2>
            <select
              value={recentOrdersFilter}
              onChange={(e) => setRecentOrdersFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 bg-white"
              title="Filter by type"
            >
              <option value="all">All</option>
              <option value="digital">Digital</option>
              <option value="physical">Physical</option>
            </select>
          </div>
        </div>
        <p className="md:hidden px-4 py-2 text-xs text-gray-500 bg-gray-50 border-b">Swipe left to see more columns</p>
        <div className="overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
          <table className="min-w-full divide-y divide-gray-200" style={{ minWidth: '700px' }}>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {visibleRecentOrders.length > 0 ? (
                visibleRecentOrders.map((order) => {
                  const isExpanded = expandedOrders.has(order.yandex_order_id)
                  
                  // If order doesn't have items array, create one from the single product (backward compatibility)
                  let orderItems: any[] | undefined = order.items
                  if (!orderItems || orderItems.length === 0) {
                    orderItems = [{
                      product_id: order.product_id,
                      product_name: order.product_name || 'Unknown Product',
                      quantity: order.quantity || 1,
                      item_price: order.total_amount / (order.quantity || 1),
                      item_total: order.total_amount,
                      activation_code_sent: order.activation_code_sent || false,
                      yandex_item_id: null,
                      yandex_offer_id: null,
                      activation_key_id: null,
                      email_template_id: null,
                      documentation_id: null,
                    }]
                  }
                  
                  const itemsCount = order.items_count || (orderItems ? orderItems.length : 1)
                  
                  return (
                    <>
                      {/* Main order row */}
                      <tr 
                        key={order.id} 
                        className="bg-gray-50 hover:bg-gray-100 cursor-pointer" 
                        onClick={() => toggleOrderExpansion(order.yandex_order_id)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          <div className="flex items-center gap-2">
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
                            {itemsCount} product{itemsCount !== 1 ? 's' : ''}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {order.customer_name || order.customer_email || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          ₽{order.total_amount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            order.status === 'finished' ? 'bg-purple-100 text-purple-800' :
                            order.status === 'completed' ? 'bg-green-100 text-green-800' :
                            order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            order.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {order.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDateTime(order.created_at)}
                        </td>
                      </tr>
                      
                      {/* Expanded product rows */}
                      {isExpanded && orderItems && orderItems.length > 0 && orderItems.map((item: any, idx: number) => (
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
                  <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                    No orders yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Extra Costs Modal */}
      {showExtraCostsModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-modal="true" role="dialog">
          <div className="flex min-h-screen items-center justify-center p-4">
            <div className="fixed inset-0 bg-black/50" onClick={closeExtraCostsModal} aria-hidden="true" />
            <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Manage extra costs</h3>
                <button
                  type="button"
                  onClick={closeExtraCostsModal}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded-md hover:bg-gray-100"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto flex-1 space-y-4">
                <p className="text-sm text-gray-500">
                  Costs for the selected period are shown. They are subtracted from profit and profit margin.
                </p>

                {/* Add new cost form */}
                <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                  <h4 className="text-sm font-medium text-gray-900">Add cost</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                    <div className="sm:col-span-5">
                      <label className="block text-xs font-medium text-gray-700 mb-1">What was the cost for?</label>
                      <input
                        type="text"
                        value={extraCostDescription}
                        onChange={(e) => setExtraCostDescription(e.target.value)}
                        placeholder="e.g. Ads, packaging..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Amount</label>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={extraCostAmount}
                        onChange={(e) => setExtraCostAmount(e.target.value)}
                        placeholder="0"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Date</label>
                      <input
                        type="date"
                        value={extraCostDate}
                        onChange={(e) => setExtraCostDate(e.target.value)}
                        max={todayStr}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="sm:col-span-3 flex items-end">
                      <button
                        type="button"
                        onClick={handleAddExtraCost}
                        className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={
                          !extraCostDescription.trim() ||
                          !extraCostDate ||
                          extraCostDate > todayStr ||
                          !extraCostAmount ||
                          Number(extraCostAmount) <= 0 ||
                          createExtraCostMutation.isPending
                        }
                      >
                        {createExtraCostMutation.isPending ? 'Adding…' : 'Add cost'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* List of extra costs */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Costs in current period</h4>
                  {extra_costs.length === 0 ? (
                    <p className="text-sm text-gray-500 py-2">No extra costs yet. Add one above.</p>
                  ) : (
                    <ul className="space-y-2">
                      {[...extra_costs]
                        .sort((a, b) => (a.date < b.date ? 1 : -1))
                        .map((cost) => (
                          <li
                            key={cost.id}
                            className="border border-gray-200 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center gap-2"
                          >
                            {editingCostId === cost.id ? (
                              <>
                                <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-2">
                                  <input
                                    type="text"
                                    value={editDescription}
                                    onChange={(e) => setEditDescription(e.target.value)}
                                    placeholder="Description"
                                    className="px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  />
                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={editAmount}
                                    onChange={(e) => setEditAmount(e.target.value)}
                                    className="px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  />
                                  <input
                                    type="date"
                                    value={editDate}
                                    onChange={(e) => setEditDate(e.target.value)}
                                    max={todayStr}
                                    className="px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                  />
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    onClick={saveEditingCost}
                                    disabled={updateExtraCostMutation.isPending || (editDate ? editDate > todayStr : false)}
                                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                                  >
                                    {updateExtraCostMutation.isPending ? 'Saving…' : 'Save'}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={cancelEditingCost}
                                    className="px-3 py-1.5 border border-gray-300 text-gray-700 text-sm rounded hover:bg-gray-50"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </>
                            ) : (
                              <>
                                <div className="flex-1 min-w-0">
                                  <span className="text-sm font-medium text-gray-900">{cost.description}</span>
                                  <span className="text-sm text-gray-500 ml-2">
                                    {format(parseISO(cost.date), 'MMM d, yyyy')}
                                  </span>
                                  <span className="text-sm font-semibold text-red-600 ml-2">
                                    -₽{cost.amount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                                  </span>
                                </div>
                                <div className="flex gap-1 shrink-0">
                                  <button
                                    type="button"
                                    onClick={() => startEditingCost(cost)}
                                    className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                                    title="Edit"
                                  >
                                    <Pencil className="h-4 w-4" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      if (window.confirm('Delete this extra cost?')) {
                                        deleteExtraCostMutation.mutate(cost.id)
                                      }
                                    }}
                                    disabled={deleteExtraCostMutation.isPending}
                                    className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                                    title="Delete"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              </>
                            )}
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="p-4 border-t border-gray-200 flex justify-end">
                <button
                  type="button"
                  onClick={closeExtraCostsModal}
                  className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
