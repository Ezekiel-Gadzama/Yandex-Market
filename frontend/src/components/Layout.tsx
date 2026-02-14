import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Package, 
  ShoppingCart, 
  Mail, 
  Settings,
  Menu,
  X,
  Users,
  Send,
  FileText,
  Star,
  UserCog,
  LogOut
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import NotificationIcon from './NotificationIcon'

interface LayoutProps {
  children: React.ReactNode
}

interface NavItem {
  name: string
  href: string
  icon: any
  permission?: string
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuth()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  
  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [userMenuOpen])

  const allNavItems: NavItem[] = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Products', href: '/products', icon: Package },
    { name: 'Orders', href: '/orders', icon: ShoppingCart },
    { name: 'Activation Templates', href: '/activation-templates', icon: Mail },
    { name: 'Reviews', href: '/reviews', icon: Star },
    { name: 'Clients', href: '/clients', icon: Users },
    { name: 'Marketing Emails', href: '/marketing-emails', icon: Send, permission: 'view_marketing_emails' },
    { name: 'Documentations', href: '/documentations', icon: FileText },
    { name: 'Staff', href: '/staff', icon: UserCog, permission: 'view_staff' },
    { name: 'Settings', href: '/settings', icon: Settings, permission: 'view_settings' },
  ]

  const hasPermission = (permission?: string) => {
    if (!permission) return true
    if (!user) return false
    if (user.is_admin) return true
    return user.permissions[permission as keyof typeof user.permissions] === true
  }

  const navigation = allNavItems.filter(item => hasPermission(item.permission))

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white">
          <div className="flex h-16 items-center justify-between px-4 border-b">
            <h1 className="text-xl font-bold text-gray-900">Yandex Market</h1>
            <button onClick={() => setSidebarOpen(false)} className="text-gray-500">
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
          <div className="border-t px-4 py-4">
            <div className="text-sm text-gray-700 mb-2">{user?.email}</div>
            {user?.is_admin && (
              <div className="text-xs text-blue-600 mb-2">Admin</div>
            )}
            <button
              onClick={() => {
                logout()
                setSidebarOpen(false)
              }}
              className="flex items-center text-sm text-gray-700 hover:text-gray-900"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-white border-r border-gray-200">
          <div className="flex h-16 items-center px-4 border-b">
            <h1 className="text-xl font-bold text-gray-900">Yandex Market</h1>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Mobile header */}
        <div className="sticky top-0 z-10 flex h-16 bg-white border-b border-gray-200 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="px-4 text-gray-500"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex items-center justify-between flex-1 px-4">
            <h1 className="text-lg font-semibold text-gray-900">Yandex Market</h1>
            <div className="text-sm text-gray-700">{user?.email}</div>
          </div>
        </div>
        
        {/* Desktop header */}
        <div className="hidden lg:block sticky top-0 z-10 h-16 bg-white border-b border-gray-200">
          <div className="flex items-center justify-end gap-4 h-full px-6">
            <NotificationIcon />
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center space-x-2 text-sm text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md hover:bg-gray-50"
              >
                <span>{user?.email}</span>
                {user?.is_admin && (
                  <span className="text-xs text-blue-600">(Admin)</span>
                )}
                <UserCog className="h-5 w-5" />
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200">
                  <button
                    onClick={() => {
                      logout()
                      setUserMenuOpen(false)
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        
        <main className="py-6">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
