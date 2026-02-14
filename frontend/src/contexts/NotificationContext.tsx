import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { useAuth } from './AuthContext'
import { settingsApi } from '../api/settings'
import { getToken } from '../utils/authStorage'

export interface Notification {
  id: string
  type: 'configuration' | 'info' | 'warning' | 'error'
  title: string
  message: string
  actionUrl?: string
  actionText?: string
  read: boolean
  createdAt: Date
}

interface NotificationContextType {
  notifications: Notification[]
  unreadCount: number
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  clearNotification: (id: string) => void
  clearAllNotifications: () => void
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState<Notification[]>([])

  const checkConfiguration = useCallback(async () => {
    // Only check if this tab has an authenticated session
    if (!user) return
    if (!getToken()) return

    try {
      const settings = await settingsApi.get()
      
      // Check for missing Yandex API configuration
      const missingYandexFields: string[] = []
      if (!settings.yandex_api_token || !settings.yandex_api_token.trim()) {
        missingYandexFields.push('Yandex API Token')
      }
      
      const isAcmaToken = settings.yandex_api_token?.startsWith('ACMA:')
      if (isAcmaToken) {
        if (!settings.yandex_campaign_id || !settings.yandex_campaign_id.trim()) {
          missingYandexFields.push('Yandex Campaign ID')
        }
      } else {
        if (!settings.yandex_business_id || !settings.yandex_business_id.trim()) {
          missingYandexFields.push('Yandex Business ID')
        }
      }

      // Check for missing SMTP configuration
      const missingSmtpFields: string[] = []
      const smtpUser = settings.smtp_user || settings.from_email
      if (!settings.smtp_host || !settings.smtp_host.trim()) {
        missingSmtpFields.push('SMTP Host')
      }
      if (!smtpUser || !smtpUser.trim()) {
        missingSmtpFields.push('SMTP User')
      }
      if (!settings.smtp_password || !settings.smtp_password.trim()) {
        missingSmtpFields.push('SMTP Password')
      }
      if (!settings.from_email || !settings.from_email.trim()) {
        missingSmtpFields.push('From Email')
      }

      // Update notifications
      setNotifications(prev => {
        const newNotifications: Notification[] = []
        const configNotificationIds = new Set(['config-yandex', 'config-smtp'])

        // Yandex API configuration notification
        if (missingYandexFields.length > 0) {
          const id = 'config-yandex'
          const existing = prev.find(n => n.id === id)
          if (existing) {
            // Keep existing notification (preserve read status)
            newNotifications.push(existing)
          } else {
            // Create new notification
            newNotifications.push({
              id,
              type: 'configuration',
              title: 'Yandex Market API Configuration Required',
              message: `Please configure the following Yandex Market API settings: ${missingYandexFields.join(', ')}`,
              actionUrl: '/settings',
              actionText: 'Go to Settings',
              read: false,
              createdAt: new Date()
            })
          }
        }

        // SMTP configuration notification
        if (missingSmtpFields.length > 0) {
          const id = 'config-smtp'
          const existing = prev.find(n => n.id === id)
          if (existing) {
            // Keep existing notification (preserve read status)
            newNotifications.push(existing)
          } else {
            // Create new notification
            newNotifications.push({
              id,
              type: 'configuration',
              title: 'SMTP Email Configuration Required',
              message: `Please configure the following email settings: ${missingSmtpFields.join(', ')}`,
              actionUrl: '/settings',
              actionText: 'Go to Settings',
              read: false,
              createdAt: new Date()
            })
          }
        }

        // Keep existing notifications that are not configuration-related or are still relevant
        prev.forEach(notif => {
          if (!configNotificationIds.has(notif.id)) {
            // Keep non-config notifications
            newNotifications.push(notif)
          }
          // Config notifications are already handled above
        })

        return newNotifications
      })
    } catch (error: any) {
      // Silently fail - don't show errors for configuration checks
      // 401 errors mean user is not authenticated, which is fine
      if (error?.response?.status !== 401) {
        console.error('Failed to check configuration:', error)
      }
    }
  }, [user])

  // Check configuration every 5 seconds when user is logged in
  useEffect(() => {
    if (!user) {
      setNotifications([])
      return
    }

    // Initial check
    checkConfiguration()

    // Set up interval to check every 5 seconds
    const interval = setInterval(() => {
      checkConfiguration()
    }, 5000)

    return () => clearInterval(interval)
  }, [user, checkConfiguration])

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(notif =>
        notif.id === id ? { ...notif, read: true } : notif
      )
    )
  }, [])

  const markAllAsRead = useCallback(() => {
    setNotifications(prev =>
      prev.map(notif => ({ ...notif, read: true }))
    )
  }, [])

  const clearNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(notif => notif.id !== id))
  }, [])

  const clearAllNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        markAsRead,
        markAllAsRead,
        clearNotification,
        clearAllNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}
