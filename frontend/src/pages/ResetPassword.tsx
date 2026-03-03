import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import apiClient from '../api/client'
import { authApi } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import Layout from '../components/Layout'
import { Eye, EyeOff } from 'lucide-react'

export default function ResetPassword() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  // Token mode fields
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Logged-in change password fields
  const [showChangePw, setShowChangePw] = useState({ current: false, new: false, confirm: false })
  const [previousPassword, setPreviousPassword] = useState('')
  const [changeNewPassword, setChangeNewPassword] = useState('')
  const [changeConfirmPassword, setChangeConfirmPassword] = useState('')

  // Previous password mode (not logged in) fields
  const [isOwnerReset, setIsOwnerReset] = useState(false)
  const [businessEmail, setBusinessEmail] = useState('')
  const [staffEmail, setStaffEmail] = useState('')
  const [prevPassword, setPrevPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  const isLoggedIn = !!user


  const handleTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long')
      return
    }
    if (!token) {
      setError('Invalid reset token')
      return
    }

    setIsLoading(true)
    try {
      await apiClient.post('/auth/reset-password', {
        token,
        new_password: password
      })
      setSuccess('Password reset successfully! Redirecting to login...')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (changeNewPassword !== changeConfirmPassword) {
      setError('New passwords do not match')
      return
    }
    if (changeNewPassword.length < 8) {
      setError('New password must be at least 8 characters long')
      return
    }
    setIsLoading(true)
    try {
      await authApi.changePassword({
        previous_password: previousPassword,
        new_password: changeNewPassword
      })
      setSuccess('Password changed successfully!')
      setPreviousPassword('')
      setChangeNewPassword('')
      setChangeConfirmPassword('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePreviousPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (newPassword !== confirmNewPassword) {
      setError('New passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long')
      return
    }
    const effectiveStaffEmail = isOwnerReset ? businessEmail.trim() : staffEmail.trim()
    if (!businessEmail.trim() || !effectiveStaffEmail || !prevPassword) {
      setError('Please fill in all fields')
      return
    }

    setIsLoading(true)
    try {
      await authApi.resetPasswordWithPrevious({
        business_identifier: businessEmail.trim(),
        staff_email: effectiveStaffEmail,
        previous_password: prevPassword,
        new_password: newPassword
      })
      setSuccess('Password reset successfully! Redirecting to login...')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setIsLoading(false)
    }
  }

  const formContent = (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            {isLoggedIn ? 'Change Password' : 'Reset Password'}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {isLoggedIn
              ? 'Enter your current password and choose a new one. No need to enter business email—we know which account you\'re in.'
              : token
                ? 'Enter your new password'
                : 'Reset using your previous password (business email/username, staff email, and current password)'}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            {success}
          </div>
        )}

        {isLoggedIn ? (
          <form className="mt-8 space-y-6" onSubmit={handleChangePasswordSubmit}>
            <div className="rounded-md shadow-sm space-y-4">
              <div>
                <label htmlFor="previousPassword" className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
                <div className="relative">
                  <input
                    id="previousPassword"
                    name="previousPassword"
                    type={showChangePw.current ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    className="appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Your current password"
                    value={previousPassword}
                    onChange={(e) => setPreviousPassword(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowChangePw(s => ({ ...s, current: !s.current }))} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700" title={showChangePw.current ? 'Hide' : 'Show'}>
                    {showChangePw.current ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="changeNewPassword" className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    id="changeNewPassword"
                    name="changeNewPassword"
                    type={showChangePw.new ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    className="appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="New password (min 8 characters)"
                    value={changeNewPassword}
                    onChange={(e) => setChangeNewPassword(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowChangePw(s => ({ ...s, new: !s.new }))} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700" title={showChangePw.new ? 'Hide' : 'Show'}>
                    {showChangePw.new ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label htmlFor="changeConfirmPassword" className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
                <div className="relative">
                  <input
                    id="changeConfirmPassword"
                    name="changeConfirmPassword"
                    type={showChangePw.confirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    className="appearance-none relative block w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Confirm new password"
                    value={changeConfirmPassword}
                    onChange={(e) => setChangeConfirmPassword(e.target.value)}
                  />
                  <button type="button" onClick={() => setShowChangePw(s => ({ ...s, confirm: !s.confirm }))} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700" title={showChangePw.confirm ? 'Hide' : 'Show'}>
                    {showChangePw.confirm ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
            </div>
            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isLoading ? 'Changing...' : 'Change Password'}
              </button>
            </div>
          </form>
        ) : token ? (
          <form className="mt-8 space-y-6" onSubmit={handleTokenSubmit}>
            <div className="rounded-md shadow-sm -space-y-px">
              <div>
                <label htmlFor="password" className="sr-only">New Password</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="New Password (min 8 characters)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="confirmPassword" className="sr-only">Confirm Password</label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Confirm Password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>
            <div>
              <button
                type="submit"
                disabled={isLoading || !token}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isLoading ? 'Resetting...' : 'Reset Password'}
              </button>
            </div>
          </form>
        ) : (
          <form className="mt-8 space-y-6" onSubmit={handlePreviousPasswordSubmit}>
            <div className="rounded-md shadow-sm space-y-4">
              <div>
                <label htmlFor="businessIdentifier" className="block text-sm font-medium text-gray-700 mb-1">Business email or username</label>
                <input
                  id="businessIdentifier"
                  name="businessIdentifier"
                  type="text"
                  autoComplete="username"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="admin@yourbusiness.com or @Goal_sale"
                  value={businessEmail}
                  onChange={(e) => setBusinessEmail(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={isOwnerReset} onChange={(e) => setIsOwnerReset(e.target.checked)} className="rounded border-gray-300" />
                  <span className="text-sm text-gray-700">Owner</span>
                </label>
              </div>
              {!isOwnerReset && (
                <div>
                  <label htmlFor="staffEmail" className="block text-sm font-medium text-gray-700 mb-1">Your email</label>
                  <input
                    id="staffEmail"
                    name="staffEmail"
                    type="email"
                    autoComplete="email"
                    required
                    className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="your@email.com"
                    value={staffEmail}
                    onChange={(e) => setStaffEmail(e.target.value)}
                  />
                </div>
              )}
              <div>
                <label htmlFor="prevPasswordField" className="block text-sm font-medium text-gray-700 mb-1">
                  Previous Password
                </label>
                <input
                  id="prevPasswordField"
                  name="prevPassword"
                  type="password"
                  autoComplete="current-password"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Your current password (e.g. EasyPlay#111)"
                  value={prevPassword}
                  onChange={(e) => setPrevPassword(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="New password (min 8 characters)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="confirmNewPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  id="confirmNewPassword"
                  name="confirmNewPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Confirm new password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                />
              </div>
            </div>
            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isLoading ? 'Resetting...' : 'Reset Password'}
              </button>
            </div>
          </form>
        )}

        <div className="text-center">
          {isLoggedIn ? (
            <Link to="/dashboard" className="text-sm text-blue-600 hover:text-blue-500">Back to Dashboard</Link>
          ) : (
            <Link to="/login" className="text-sm text-blue-600 hover:text-blue-500">Back to Login</Link>
          )}
        </div>
      </div>
    </div>
  )

  return isLoggedIn ? <Layout>{formContent}</Layout> : formContent
}
