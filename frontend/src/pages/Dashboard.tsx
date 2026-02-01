import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, DateRange } from '../api/dashboard'
import { 
  Package, 
  ShoppingCart, 
  DollarSign, 
  TrendingUp,
  Calendar
} from 'lucide-react'
import { format } from 'date-fns'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const [period, setPeriod] = useState<string>('all')
  const [dateRange, setDateRange] = useState<DateRange>({})
  const [showDatePicker, setShowDatePicker] = useState(false)
  const datePickerRef = useRef<HTMLDivElement>(null)
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', period, dateRange],
    queryFn: () => dashboardApi.getData(period, dateRange),
  })
  
  // Close date picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setShowDatePicker(false)
      }
    }
    
    if (showDatePicker) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showDatePicker])
  
  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod)
    if (newPeriod === 'custom') {
      setShowDatePicker(true)
    } else {
      setShowDatePicker(false)
      setDateRange({})
    }
  }
  
  const handleDateRangeApply = () => {
    if (dateRange.startDate && dateRange.endDate) {
      setShowDatePicker(false)
    }
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
    return <div className="text-center py-12 text-red-600">Error loading dashboard</div>
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
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
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
          
          {/* Date Range Picker */}
          {showDatePicker && (
            <div ref={datePickerRef} className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-10 p-4">
              <div className="flex items-center mb-3">
                <Calendar className="h-5 w-5 text-gray-400 mr-2" />
                <h3 className="text-sm font-medium text-gray-900">Select Date Range</h3>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateRange.startDate || ''}
                    onChange={(e) => setDateRange({ ...dateRange, startDate: e.target.value })}
                    max={dateRange.endDate || undefined}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateRange.endDate || ''}
                    onChange={(e) => setDateRange({ ...dateRange, endDate: e.target.value })}
                    min={dateRange.startDate || undefined}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex space-x-2 pt-2">
                  <button
                    onClick={handleDateRangeApply}
                    disabled={!dateRange.startDate || !dateRange.endDate}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => {
                      setShowDatePicker(false)
                      setDateRange({})
                      setPeriod('all')
                    }}
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
            <div className="mt-2 text-sm text-gray-600">
              {getPeriodLabel()}
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
                  <dd className="text-sm text-gray-500">{stats.pending_orders} pending</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

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
                    {stats.completed_orders} completed
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Products Chart */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Top Products</h2>
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

        {/* Top Products List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Top Selling Products</h2>
          {top_products.length > 0 ? (
            <div className="space-y-4">
              {top_products.slice(0, 5).map((product) => (
                <div key={product.product_id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{product.product_name}</p>
                    <p className="text-sm text-gray-500">{product.total_sales} sales</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      ₽{product.total_revenue.toLocaleString('ru-RU')}
                    </p>
                    <p className="text-sm text-green-600">
                      ₽{product.total_profit.toLocaleString('ru-RU')} profit
                    </p>
                  </div>
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
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Orders</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Order ID
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
                recent_orders.map((order) => (
                  <tr key={order.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {order.yandex_order_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {order.customer_name || order.customer_email || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₽{order.total_amount.toLocaleString('ru-RU', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
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
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
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
