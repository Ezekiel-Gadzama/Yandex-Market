import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { syncApi } from '../api/sync'
import { RefreshCw, CheckCircle } from 'lucide-react'

export default function Settings() {
  const [syncStatus, setSyncStatus] = useState<string>('')

  const syncAllMutation = useMutation({
    mutationFn: (force: boolean) => syncApi.syncAll(force),
    onSuccess: (data) => {
      setSyncStatus(
        `Synced ${data.products_synced} products (Created: ${data.products_created}, Updated: ${data.products_updated})`
      )
      if (data.errors.length > 0) {
        setSyncStatus((prev) => prev + ` Errors: ${data.errors.length}`)
      }
    },
    onError: () => {
      setSyncStatus('Sync failed. Please check your Yandex Market API configuration.')
    },
  })

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

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

        {/* Webhook Configuration */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Webhook Configuration (Real-time Orders)</h2>
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800 font-medium mb-2">Webhook URL for Yandex Market:</p>
            <code className="block text-xs bg-white p-2 rounded border border-blue-200 break-all">
              {typeof window !== 'undefined' ? window.location.origin.replace(':3000', ':8000') : 'http://localhost:8000'}/api/webhooks/yandex-market/orders
            </code>
            <p className="text-xs text-blue-700 mt-2">
              Configure this URL in Yandex Market Partner Dashboard → API and modules → API notifications → Order notifications
            </p>
            <p className="text-xs text-blue-700 mt-1">
              When configured, orders will be received instantly instead of waiting for the 5-minute sync.
            </p>
          </div>
        </div>

        {/* API Configuration Info */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">API Configuration</h2>
          <p className="text-sm text-gray-600 mb-4">
            Your Yandex Market API credentials are configured in the backend <code className="bg-gray-100 px-2 py-1 rounded">.env</code> file.
            The values shown below are examples - your actual credentials are stored securely on the backend.
          </p>
          <div className="bg-gray-50 p-4 rounded-md font-mono text-sm">
            <div>YANDEX_MARKET_API_TOKEN=*** (configured)</div>
            <div>YANDEX_MARKET_CAMPAIGN_ID=*** (configured)</div>
            <div>YANDEX_MARKET_API_URL=https://api.partner.market.yandex.ru</div>
            <div className="mt-2 text-xs text-green-600">✓ API credentials are configured in .env file</div>
            <div className="mt-1 text-xs text-gray-600">To update: Edit backend/.env file and restart backend container</div>
          </div>
        </div>

        {/* Email Configuration Info */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Email Configuration (Optional)</h2>
          <p className="text-sm text-gray-600 mb-4">
            <strong>Note:</strong> Yandex Market automatically sends activation emails when you complete orders via API.
            SMTP settings are only needed if you want to send additional/custom emails to customers.
          </p>
          <p className="text-sm text-gray-600 mb-4">
            Configure SMTP settings in the backend <code className="bg-gray-100 px-2 py-1 rounded">.env</code> file (optional):
          </p>
          <div className="bg-gray-50 p-4 rounded-md font-mono text-sm">
            <div>SMTP_HOST=smtp.gmail.com</div>
            <div>SMTP_PORT=587</div>
            <div>SMTP_USER=your_email@gmail.com</div>
            <div>SMTP_PASSWORD=your_app_password</div>
            <div>FROM_EMAIL=noreply@market.yandex.ru</div>
            <div className="mt-2 text-xs text-gray-500">Leave empty if you only use Yandex Market's automatic emails</div>
          </div>
        </div>
      </div>
    </div>
  )
}
