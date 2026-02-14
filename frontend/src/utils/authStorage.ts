/**
 * Single session per browser (shared across all tabs).
 * Uses localStorage so the same login is used everywhere in this browser.
 */

const AUTH_TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY)
}
