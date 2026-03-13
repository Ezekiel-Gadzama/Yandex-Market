import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi, User } from '../api/auth'
import { getToken, setToken as setStoredToken, clearToken } from '../utils/authStorage'

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (businessIdentifier: string, email: string, password: string, rememberMe?: boolean) => Promise<void>
  signup: (email: string, password: string, businessName?: string, businessUsername?: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

/** One-time migration from multi-session format to single token (if present). */
function migrateFromMultiSession(): string | null {
  try {
    const raw = localStorage.getItem('auth_sessions')
    if (!raw) return null
    const sessions = JSON.parse(raw) as Record<string, { token: string }>
    if (!sessions || typeof sessions !== 'object') return null
    const currentId = sessionStorage.getItem('auth_current_session_id')
    const session = currentId && sessions[currentId] ? sessions[currentId] : Object.values(sessions)[0]
    if (!session?.token) return null
    localStorage.removeItem('auth_sessions')
    sessionStorage.removeItem('auth_current_session_id')
    localStorage.setItem('auth_token', session.token)
    return session.token
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let storedToken = getToken()
    if (!storedToken) {
      storedToken = migrateFromMultiSession()
    }
    if (!storedToken) {
      setIsLoading(false)
      return
    }
    setToken(storedToken)
    const fetchUserWithRetry = async (retries = 5, delay = 1000) => {
      for (let i = 0; i < retries; i++) {
        try {
          const userData = await authApi.getMe()
          setUser(userData)
          setIsLoading(false)
          return
        } catch (error: any) {
          if ((error?.response?.status === 502 || error?.response?.status === 503) && i < retries - 1) {
            await new Promise((r) => setTimeout(r, delay))
            continue
          }
          clearToken()
          setToken(null)
          setUser(null)
          setIsLoading(false)
          return
        }
      }
      setIsLoading(false)
    }
    fetchUserWithRetry()
  }, [])

  const login = async (businessIdentifier: string, email: string, password: string, rememberMe: boolean = false) => {
    const response = await authApi.login({ business_identifier: businessIdentifier, email, password, remember_me: rememberMe })
    setStoredToken(response.access_token)
    setToken(response.access_token)
    setUser(response.user)
  }

  const signup = async (email: string, password: string, businessName?: string, businessUsername?: string) => {
    const response = await authApi.signup({ email, password, business_name: businessName, business_username: businessUsername })
    setStoredToken(response.access_token)
    setToken(response.access_token)
    setUser(response.user)
  }

  const logout = () => {
    clearToken()
    setToken(null)
    setUser(null)
  }

  const refreshUser = async () => {
    if (!getToken()) return
    try {
      const userData = await authApi.getMe()
      setUser(userData)
    } catch {
      logout()
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
