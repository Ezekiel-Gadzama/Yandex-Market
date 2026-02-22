import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi, AppSettingsUpdate } from '../api/settings'
import { syncApi } from '../api/sync'
import { useAuth } from '../contexts/AuthContext'
import { RefreshCw, CheckCircle, Save, Edit2, X, AlertCircle } from 'lucide-react'

export default function Settings() {
  const [syncStatus, setSyncStatus] = useState<string>('')
  const [isEditing, setIsEditing] = useState(false)
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
  const queryClient = useQueryClient()

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ isOpen: true, type, message })
    // Auto-close after 4 seconds
    setTimeout(() => setNotification(prev => ({ ...prev, isOpen: false })), 4000)
  }

  const { data: settings, isLoading: settingsLoading, error: settingsError } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => settingsApi.get(),
  })

  const { user } = useAuth()
  const updateSettingsMutation = useMutation({
    mutationFn: (data: AppSettingsUpdate) => settingsApi.update(data),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['app-settings'] })
      showNotification('success', 'Settings saved successfully!')
      
      // Check if Yandex API is now configured and trigger sync
      // Wait a bit for the settings to be fully saved, then fetch fresh settings
      setTimeout(async () => {
        try {
          const freshSettings = await settingsApi.get()
          const hasYandexConfig = freshSettings.yandex_api_token && 
            (freshSettings.yandex_business_id || freshSettings.yandex_campaign_id)
          
          if (hasYandexConfig && user?.is_admin) {
            try {
              // Trigger automatic sync
              await syncApi.syncAll(false)
              showNotification('success', 'Settings saved and data sync started!')
            } catch (syncError: any) {
              // Don't show error for sync - it might fail if API is still being configured
              const errorMsg = syncError?.response?.data?.detail || syncError?.message || 'Sync started in background'
              console.log('Auto-sync:', errorMsg)
            }
          }
        } catch (error) {
          // Silently fail - sync will happen automatically later
          console.log('Could not check settings for auto-sync')
        }
      }, 1500)
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail?.message || 
                          error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to save settings. Please try again.'
      showNotification('error', errorMessage)
    },
  })

  const syncAllMutation = useMutation({
    mutationFn: (force: boolean) => syncApi.syncAll(force),
    onSuccess: (data) => {
      setSyncStatus(
        `Synced ${data.products_synced} products (Created: ${data.products_created}, Updated: ${data.products_updated})`
      )
      // Invalidate orders query to refresh the UI with latest data
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      if (data.errors.length > 0) {
        setSyncStatus((prev) => prev + ` Errors: ${data.errors.length}`)
      }
    },
    onError: () => {
      setSyncStatus('Sync failed. Please check your Yandex Market API configuration.')
    },
  })

  const handleConfigSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const data: AppSettingsUpdate = {
      yandex_api_token: (formData.get('yandex_api_token') as string) || undefined,
      yandex_business_id: (formData.get('yandex_business_id') as string) || undefined,
      yandex_campaign_id: (formData.get('yandex_campaign_id') as string) || undefined,
      smtp_host: (formData.get('smtp_host') as string) || undefined,
      smtp_port: formData.get('smtp_port') ? parseInt(formData.get('smtp_port') as string) : undefined,
      smtp_user: (formData.get('smtp_user') as string) || undefined,
      smtp_password: (formData.get('smtp_password') as string) || undefined,
      from_email: (formData.get('from_email') as string) || undefined,
      secret_key: (formData.get('secret_key') as string) || undefined,
      processing_time_min: formData.get('processing_time_min') ? parseInt(formData.get('processing_time_min') as string) : undefined,
      processing_time_max: formData.get('processing_time_max') ? parseInt(formData.get('processing_time_max') as string) : undefined,
      maximum_wait_time_value: formData.get('maximum_wait_time_value') ? parseInt(formData.get('maximum_wait_time_value') as string) : undefined,
      maximum_wait_time_unit: (formData.get('maximum_wait_time_unit') as string) || undefined,
      working_hours_text: (formData.get('working_hours_text') as string) || undefined,
      company_email: (formData.get('company_email') as string) || undefined,
      auto_activation_enabled: formData.get('auto_activation_enabled') === 'on',
      auto_append_clients: formData.get('auto_append_clients') === 'on',
    }
    
    updateSettingsMutation.mutate(data)
  }

  if (settingsLoading) {
    return <div className="text-center py-12">Loading settings...</div>
  }

  if (settingsError) {
    const errorMessage = (settingsError as any)?.response?.data?.detail?.message || 
                        (settingsError as any)?.response?.data?.detail || 
                        (settingsError as any)?.message || 
                        'Error loading settings. Please try again or contact your administrator.'
    return (
      <div className="text-center py-12">
        <div className="text-red-600 font-medium mb-2">Error loading settings</div>
        <div className="text-gray-600 text-sm">{errorMessage}</div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-xl sm:text-3xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="space-y-6">
        {/* Sync Section */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Yandex Market Sync</h2>
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-800 font-medium mb-1">✓ Automatic Sync Enabled</p>
            <p className="text-xs text-green-700">
              Products and orders are automatically synced every 5 minutes. 
              Orders are also received in real-time via webhooks when configured.
            </p>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Manual sync buttons below are available for on-demand syncing if needed.
          </p>

          <div className="flex space-x-4">
            <button
              onClick={() => syncAllMutation.mutate(false)}
              disabled={syncAllMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
            >
              {syncAllMutation.isPending ? (
                <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-5 w-5 mr-2" />
              )}
              Sync
            </button>

            <button
              onClick={() => syncAllMutation.mutate(true)}
              disabled={syncAllMutation.isPending}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              {syncAllMutation.isPending ? (
                <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-5 w-5 mr-2" />
              )}
              Force Sync
            </button>
          </div>

          {syncStatus && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-blue-600 mr-2" />
                <p className="text-sm text-blue-800">{syncStatus}</p>
              </div>
            </div>
          )}
        </div>

        {/* Configuration Form */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-medium text-gray-900">Application Configuration</h2>
              <p className="text-sm text-gray-600 mt-1">
                Configure API credentials, SMTP settings, and other application parameters. Database values override .env file settings.
              </p>
            </div>
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <Edit2 className="h-4 w-4 mr-2" />
                Edit Configuration
              </button>
            )}
          </div>
          
          {settingsLoading ? (
            <div className="text-center py-4">Loading settings...</div>
          ) : settings ? (
            <form onSubmit={(e) => {
              if (!isEditing) {
                e.preventDefault()
                return
              }
              handleConfigSubmit(e)
              setIsEditing(false)
            }} className="space-y-6">
              {/* Yandex Market API */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-3">Yandex Market API</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Token
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="yandex_api_token"
                        placeholder="Your Yandex Market API Token"
                        defaultValue={settings.yandex_api_token || ''}
                        autoComplete="off"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.yandex_api_token || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Business ID <span className="text-red-500">*</span>
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="yandex_business_id"
                        defaultValue={settings.yandex_business_id || ''}
                        autoComplete="off"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.yandex_business_id || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                    <p className="text-xs text-gray-500 mt-1">Required for Business API</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Campaign ID <span className="text-gray-400">(Legacy)</span>
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="yandex_campaign_id"
                        defaultValue={settings.yandex_campaign_id || ''}
                        autoComplete="off"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.yandex_campaign_id || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* SMTP Settings */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-3">SMTP Settings (Optional)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Host
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="smtp_host"
                        placeholder="smtp.gmail.com"
                        defaultValue={settings.smtp_host || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.smtp_host || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Port
                    </label>
                    {isEditing ? (
                      <input
                        type="number"
                        name="smtp_port"
                        placeholder="587"
                        defaultValue={settings.smtp_port || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.smtp_port || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP User (Email)
                    </label>
                    {isEditing ? (
                      <input
                        type="email"
                        name="smtp_user"
                        defaultValue={settings.smtp_user || settings.from_email || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.smtp_user || settings.from_email || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                    <p className="text-xs text-gray-500 mt-1">Usually the same as From Email</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SMTP Password
                    </label>
                    {isEditing ? (
                      <input
                        type="password"
                        name="smtp_password"
                        placeholder="App Password"
                        defaultValue={settings.smtp_password || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.smtp_password ? '••••••••••••' : <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      From Email
                    </label>
                    {isEditing ? (
                      <input
                        type="email"
                        name="from_email"
                        placeholder="noreply@example.com"
                        defaultValue={settings.from_email || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.from_email || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Security */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-3">Security</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Secret Key
                    </label>
                    {isEditing ? (
                      <input
                        type="password"
                        name="secret_key"
                        placeholder="Application Secret Key"
                        defaultValue={settings.secret_key || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.secret_key ? '••••••••••••' : <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Email Message Settings */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-3">Email Message Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Processing Time Min (minutes)
                    </label>
                    {isEditing ? (
                      <input
                        type="number"
                        name="processing_time_min"
                        placeholder="20"
                        defaultValue={settings.processing_time_min || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.processing_time_min || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Processing Time Max (minutes)
                    </label>
                    {isEditing ? (
                      <input
                        type="number"
                        name="processing_time_max"
                        placeholder="30"
                        defaultValue={settings.processing_time_max || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.processing_time_max || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Maximum Wait Time (Optional)
                    </label>
                    {isEditing ? (
                      <>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="number"
                            name="maximum_wait_time_value"
                            min="1"
                            placeholder="6"
                            defaultValue={settings.maximum_wait_time_value || ''}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <select
                            name="maximum_wait_time_unit"
                            defaultValue={settings.maximum_wait_time_unit || 'hours'}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="minutes">Minutes</option>
                            <option value="hours">Hours</option>
                            <option value="days">Days</option>
                            <option value="weeks">Weeks</option>
                          </select>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          Leave empty to omit maximum wait time from activation emails
                        </p>
                      </>
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.maximum_wait_time_value 
                          ? `${settings.maximum_wait_time_value} ${settings.maximum_wait_time_unit || 'hours'}`
                          : <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Company Email
                    </label>
                    {isEditing ? (
                      <input
                        type="email"
                        name="company_email"
                        placeholder="support@example.com"
                        defaultValue={settings.company_email || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900">
                        {settings.company_email || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                  
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Working Hours Text
                    </label>
                    {isEditing ? (
                      <textarea
                        name="working_hours_text"
                        rows={2}
                        placeholder="We are open seven days a week from 10:00 AM to 12:00 AM Moscow time."
                        defaultValue={settings.working_hours_text || ''}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    ) : (
                      <div className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900 whitespace-pre-wrap">
                        {settings.working_hours_text || <span className="text-gray-400">Not set</span>}
                      </div>
                    )}
                  </div>
                </div>
              </div>


              {/* Order Activation Settings */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Order Activation Settings</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure how orders are activated when they come in.
                </p>
                
                <div className="space-y-4">
                  {isEditing ? (
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        name="auto_activation_enabled"
                        defaultChecked={settings.auto_activation_enabled}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Enable Automatic Activation</span>
                    </label>
                  ) : (
                    <div className="flex items-center">
                      <div className={`h-4 w-4 rounded border-2 flex items-center justify-center ${
                        settings.auto_activation_enabled ? 'bg-gray-400 border-gray-400' : 'bg-gray-200 border-gray-300'
                      }`}>
                        {settings.auto_activation_enabled && (
                          <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <span className="ml-2 text-sm text-gray-500">Enable Automatic Activation</span>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 ml-6">
                    {settings.auto_activation_enabled 
                      ? "Orders will automatically be completed and activation codes sent to Yandex Market when they arrive. No need to manually click 'Send Activation'."
                      : "Orders will be fulfilled locally but you'll need to manually click 'Send Activation' to complete them on Yandex Market."}
                  </p>
                </div>
              </div>

              {/* Client Management Settings */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Client Management Settings</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Configure how clients are managed from orders.
                </p>
                
                <div className="space-y-4">
                  {isEditing ? (
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        name="auto_append_clients"
                        defaultChecked={settings.auto_append_clients}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="ml-2 text-sm text-gray-700">Automatically Append Client Orders</span>
                    </label>
                  ) : (
                    <div className="flex items-center">
                      <div className={`h-4 w-4 rounded border-2 flex items-center justify-center ${
                        settings.auto_append_clients ? 'bg-gray-400 border-gray-400' : 'bg-gray-200 border-gray-300'
                      }`}>
                        {settings.auto_append_clients && (
                          <svg className="h-3 w-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <span className="ml-2 text-sm text-gray-500">Automatically Append Client Orders</span>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 ml-6">
                    {settings.auto_append_clients 
                      ? "When an order is finished, if the customer name already exists in the database, automatically append the order information to the client (order IDs, products, and purchase dates)."
                      : "Client orders must be manually created from the Orders page."}
                  </p>
                </div>
              </div>

              {isEditing && (
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updateSettingsMutation.isPending}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                  >
                    <Save className="h-5 w-5 mr-2" />
                    {updateSettingsMutation.isPending ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              )}
            </form>
          ) : (
            <div className="text-center py-4 text-red-600">Failed to load settings</div>
          )}
        </div>
      </div>

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
