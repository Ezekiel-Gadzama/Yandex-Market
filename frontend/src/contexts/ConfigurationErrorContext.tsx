import { createContext, useContext, useState, ReactNode, useEffect } from 'react'
import ConfigurationErrorModal from '../components/ConfigurationErrorModal'
import { setConfigurationErrorHandler } from '../api/client'

interface ConfigurationError {
  error?: string
  message?: string
  missing_fields?: string[]
  action_required?: string
}

interface ConfigurationErrorContextType {
  showError: (error: ConfigurationError) => void
  hideError: () => void
}

const ConfigurationErrorContext = createContext<ConfigurationErrorContextType | undefined>(undefined)

export function ConfigurationErrorProvider({ children }: { children: ReactNode }) {
  const [error, setError] = useState<ConfigurationError | null>(null)
  const [isOpen, setIsOpen] = useState(false)

  const showError = (err: ConfigurationError) => {
    setError(err)
    setIsOpen(true)
  }

  const hideError = () => {
    setIsOpen(false)
    setError(null)
  }

  // Register the error handler with the API client
  useEffect(() => {
    setConfigurationErrorHandler(showError)
  }, [])

  return (
    <ConfigurationErrorContext.Provider value={{ showError, hideError }}>
      {children}
      <ConfigurationErrorModal isOpen={isOpen} onClose={hideError} error={error} />
    </ConfigurationErrorContext.Provider>
  )
}

export function useConfigurationError() {
  const context = useContext(ConfigurationErrorContext)
  if (!context) {
    throw new Error('useConfigurationError must be used within ConfigurationErrorProvider')
  }
  return context
}
