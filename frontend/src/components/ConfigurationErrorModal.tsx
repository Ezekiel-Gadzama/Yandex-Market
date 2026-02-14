import { X, Settings, AlertCircle } from 'lucide-react'

interface ConfigurationErrorModalProps {
  isOpen: boolean
  onClose: () => void
  error: {
    error?: string
    message?: string
    missing_fields?: string[]
    action_required?: string
  } | null
}

export default function ConfigurationErrorModal({ isOpen, onClose, error }: ConfigurationErrorModalProps) {
  if (!isOpen || !error) return null

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-6 w-6 text-yellow-600" />
            <h3 className="text-lg font-semibold text-gray-900">
              Configuration Required
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6">
          <p className="text-gray-700 mb-4">
            {error.message || 'Some required configuration is missing.'}
          </p>

          {error.missing_fields && error.missing_fields.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Missing configuration:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {error.missing_fields.map((field, idx) => (
                  <li key={idx}>{field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
            <p className="text-sm text-blue-800">
              {error.action_required || 'Please configure the required settings in the Settings page, or contact your administrator to configure the setup.'}
            </p>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Close
            </button>
            <a
              href="/settings"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center space-x-2"
            >
              <Settings className="h-4 w-4" />
              <span>Go to Settings</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
