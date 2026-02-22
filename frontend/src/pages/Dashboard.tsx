import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
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
  ChevronRight
} from 'lucide-react'
import { format } from 'date-fns'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const { user } = useAuth()
  const hasDashboardRight = user?.is_admin || user?.permissions.dashboard_right
  const [period, setPeriod] = useState<string>('all')
  const [dateRange, setDateRange] = useState<DateRange>({})
  const [tempDateRange, setTempDateRange] = useState<DateRange>({})
  const [showDatePicker, setShowDatePicker] = useState(false)
  const datePickerRef = useRef<HTMLDivElement>(null)
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  const hasCheckedSyncRef = useRef(false)
  
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

  const { stats, top_products, recent_orders } = data

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
                        {stats.profit_margin.toFixed(2)}%
                      </dd>
                      <dd className="text-sm text-gray-500">
                        {stats.successful_orders} successful
                      </dd>
                    </dl>
                  </div>
                </div>
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
          <h2 className="text-lg font-medium text-gray-900">Recent Orders</h2>
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
              {recent_orders.length > 0 ? (
                recent_orders.map((order) => {
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
                          {format(new Date(order.created_at), 'MMM d, yyyy')}
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
    </div>
  )
}
