import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { staffApi, StaffCreate, StaffCreateResponse, BusinessAccountUpdate } from '../api/staff'
import { User, UserPermissions } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import { UserPlus, Edit2, Trash2, X, Mail, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

export default function Staff() {
  const { user: currentUser, refreshUser, logout } = useAuth()
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [selectedStaff, setSelectedStaff] = useState<User | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [editName, setEditName] = useState('')
  const [editNewPassword, setEditNewPassword] = useState('')
  const [editConfirmPassword, setEditConfirmPassword] = useState('')
  const [showEditPassword, setShowEditPassword] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; staffId: number | null }>({ isOpen: false, staffId: null })
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
  const [isBusinessModalOpen, setIsBusinessModalOpen] = useState(false)
  const [businessEmail, setBusinessEmail] = useState('')
  const [businessNewPassword, setBusinessNewPassword] = useState('')
  const [businessConfirmPassword, setBusinessConfirmPassword] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [businessUsername, setBusinessUsername] = useState('')
  const [showBusinessPassword, setShowBusinessPassword] = useState(false)
  const queryClient = useQueryClient()

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ isOpen: true, type, message })
    // Auto-close after 4 seconds
    setTimeout(() => setNotification(prev => ({ ...prev, isOpen: false })), 4000)
  }

  const { data: staff = [], isLoading } = useQuery({
    queryKey: ['staff'],
    queryFn: () => staffApi.getAll(),
  })

  const { data: businessAccount } = useQuery({
    queryKey: ['staff', 'business-account'],
    queryFn: () => staffApi.getBusinessAccount(),
    enabled: isBusinessModalOpen,
  })

  const createMutation = useMutation({
    mutationFn: (data: StaffCreate) => staffApi.create(data),
    onSuccess: (data: StaffCreateResponse) => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setIsAddModalOpen(false)
      setName('')
      setEmail('')
      setPassword('')
      setShowPassword(false)
      if (!data.invitation_email_sent) {
        showNotification('error', 'Staff created, but the invitation email could not be sent. Check SMTP settings or use "Resend password reset" after fixing network/SMTP.')
      } else {
        showNotification('success', 'Staff member added. They will receive an email to set their password.')
      }
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { permissions?: UserPermissions; is_active?: boolean; name?: string } }) =>
      staffApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setIsEditModalOpen(false)
      setSelectedStaff(null)
      setEditName('')
      setEditNewPassword('')
      setEditConfirmPassword('')
      setShowEditPassword(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => staffApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setDeleteConfirm({ isOpen: false, staffId: null })
    },
  })

  const updateBusinessMutation = useMutation({
    mutationFn: (data: BusinessAccountUpdate) => staffApi.updateBusinessAccount(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      queryClient.invalidateQueries({ queryKey: ['staff', 'business-account'] })
      setIsBusinessModalOpen(false)
      setBusinessEmail('')
      setBusinessNewPassword('')
      setBusinessConfirmPassword('')
      setBusinessName('')
      setBusinessUsername('')
      setShowBusinessPassword(false)
      if (variables.new_email && currentUser?.is_admin) {
        showNotification('success', 'Business account updated. Please sign in with your new email.')
        logout()
      } else {
        refreshUser()
        showNotification('success', 'Business account updated')
      }
    },
    onError: (error: any) => {
      showNotification('error', error?.response?.data?.detail || 'Failed to update business account')
    },
  })

  const resendPasswordResetMutation = useMutation({
    mutationFn: (id: number) => staffApi.resendPasswordReset(id),
    onSuccess: () => {
      showNotification('success', 'Password reset link has been sent to the staff member\'s email')
    },
    onError: (error: any) => {
      const d = error?.response?.data?.detail
      const errorMessage = (typeof d === 'string' ? d : d?.message) ||
                          error?.message ||
                          'Failed to send password reset link. Check SMTP settings and that the server can reach the email server (e.g. firewall allows outbound port 587).'
      showNotification('error', errorMessage)
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      email,
      ...(name.trim() ? { name: name.trim() } : {}),
      ...(password && password.trim() ? { password } : {}),
    })
  }

  const handleEdit = (staff: User) => {
    setSelectedStaff(staff)
    setEditName(staff.name || '')
    setEditNewPassword('')
    setEditConfirmPassword('')
    setShowEditPassword(false)
    setIsEditModalOpen(true)
  }

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedStaff) return

    if (editNewPassword && editNewPassword !== editConfirmPassword) {
      showNotification('error', 'New passwords do not match')
      return
    }
    if (editNewPassword && editNewPassword.length < 8) {
      showNotification('error', 'Password must be at least 8 characters')
      return
    }

    const formData = new FormData(e.currentTarget as HTMLFormElement)
    const permissions: UserPermissions = {
      view_staff: formData.get('view_staff') === 'on',
      view_settings: formData.get('view_settings') === 'on',
      client_right: formData.get('client_right') === 'on',
      view_marketing_emails: formData.get('view_marketing_emails') === 'on',
      dashboard_right: formData.get('dashboard_right') === 'on',
      view_product_prices: formData.get('view_product_prices') === 'on',
    }
    const is_active = formData.get('is_active') === 'on'

    updateMutation.mutate({
      id: selectedStaff.id,
      data: {
        permissions,
        is_active,
        ...(editName.trim() !== (selectedStaff.name || '').trim() ? { name: editName.trim() } : {}),
        ...(editNewPassword ? { new_password: editNewPassword } : {}),
      },
    })
  }

  const handleDelete = (staffId: number) => {
    setDeleteConfirm({ isOpen: true, staffId })
  }

  const confirmDelete = () => {
    if (deleteConfirm.staffId) {
      deleteMutation.mutate(deleteConfirm.staffId)
    }
  }

  useEffect(() => {
    if (businessAccount && isBusinessModalOpen) {
      setBusinessEmail(businessAccount.email)
      setBusinessName(businessAccount.business_name || '')
      setBusinessUsername(businessAccount.business_username || '')
    }
  }, [businessAccount, isBusinessModalOpen])

  const handleOpenBusinessModal = () => {
    setBusinessNewPassword('')
    setBusinessConfirmPassword('')
    setShowBusinessPassword(false)
    setIsBusinessModalOpen(true)
  }

  const BUSINESS_USERNAME_REGEX = /^@[a-zA-Z0-9_]+$/

  const handleBusinessUpdate = (e: React.FormEvent) => {
    e.preventDefault()
    if (businessNewPassword && businessNewPassword !== businessConfirmPassword) {
      showNotification('error', 'New passwords do not match')
      return
    }
    if (businessNewPassword && businessNewPassword.length < 8) {
      showNotification('error', 'Password must be at least 8 characters')
      return
    }
    const trimmedUsername = businessUsername.trim()
    if (trimmedUsername && !BUSINESS_USERNAME_REGEX.test(trimmedUsername)) {
      showNotification('error', 'Business username must start with @ and contain only letters, numbers, and underscores (e.g. @Goal_sale)')
      return
    }
    const data: BusinessAccountUpdate = {}
    if (businessAccount && businessEmail.trim() !== businessAccount.email) {
      data.new_email = businessEmail.trim()
    }
    if (businessNewPassword) data.new_password = businessNewPassword
    if (businessAccount && businessName.trim() !== (businessAccount.business_name || '').trim()) {
      data.business_name = businessName.trim() || ''
    }
    if (businessAccount && trimmedUsername !== (businessAccount.business_username || '').trim()) {
      data.new_business_username = trimmedUsername  // "" clears username
    }
    if (Object.keys(data).length === 0) {
      showNotification('error', 'No changes to save')
      return
    }
    updateBusinessMutation.mutate(data)
  }

  // Check if current user can manage staff
  const canManageStaff = currentUser?.is_admin || currentUser?.permissions.view_staff

  if (!canManageStaff) {
    return (
      <div className="bg-white shadow rounded-lg p-4 sm:p-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4">Staff Management</h1>
        <p className="text-gray-600">You don't have permission to view this page.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Staff Management</h1>
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <button
            onClick={handleOpenBusinessModal}
            className="flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 w-full sm:w-auto"
          >
            <Edit2 className="mr-2 h-5 w-5" />
            Edit Business Account
          </button>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 w-full sm:w-auto"
          >
            <UserPlus className="mr-2 h-5 w-5" />
            Add Staff
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : staff.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
          No staff members found
        </div>
      ) : (
        <>
          {/* Desktop: table */}
          <div className="hidden md:block bg-white shadow rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Permissions</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {staff.map((member) => (
                    <tr key={member.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{member.email}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{member.name || '—'}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${member.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {member.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <div className="flex flex-wrap gap-1">
                          {member.permissions.view_staff && <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Staff</span>}
                          {member.permissions.view_settings && <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">Settings</span>}
                          {member.permissions.client_right && <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Clients</span>}
                          {member.permissions.view_marketing_emails && <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">Marketing</span>}
                          {member.permissions.dashboard_right && <span className="px-2 py-1 bg-indigo-100 text-indigo-800 text-xs rounded">Dashboard</span>}
                          {member.permissions.view_product_prices && <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">Prices</span>}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(member.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end space-x-2">
                          <button onClick={() => handleEdit(member)} className="text-blue-600 hover:text-blue-900" title="Edit permissions"><Edit2 className="h-5 w-5" /></button>
                          {currentUser?.is_admin && (
                            <>
                              <button onClick={() => resendPasswordResetMutation.mutate(member.id)} disabled={resendPasswordResetMutation.isPending} className="text-green-600 hover:text-green-900 disabled:opacity-50" title="Resend password reset"><Mail className="h-5 w-5" /></button>
                              <button onClick={() => handleDelete(member.id)} className="text-red-600 hover:text-red-900" title="Delete staff"><Trash2 className="h-5 w-5" /></button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile: cards */}
          <div className="md:hidden space-y-4">
            {staff.map((member) => (
              <div key={member.id} className="bg-white shadow rounded-lg p-4 border border-gray-100">
                <div className="flex justify-between items-start gap-2 mb-3">
                  <div>
                    <span className="text-sm font-medium text-gray-900 break-all block">{member.email}</span>
                    {member.name && <span className="text-sm text-gray-500">{member.name}</span>}
                  </div>
                  <span className={`shrink-0 px-2 py-1 text-xs font-semibold rounded-full ${member.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {member.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="mb-2">
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Permissions</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {member.permissions.view_staff && <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">Staff</span>}
                    {member.permissions.view_settings && <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-xs rounded">Settings</span>}
                    {member.permissions.client_right && <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded">Clients</span>}
                    {member.permissions.view_marketing_emails && <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded">Marketing</span>}
                    {member.permissions.dashboard_right && <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-xs rounded">Dashboard</span>}
                    {member.permissions.view_product_prices && <span className="px-2 py-0.5 bg-gray-100 text-gray-800 text-xs rounded">Prices</span>}
                  </div>
                </div>
                <div className="text-xs text-gray-500 mb-3">Created {new Date(member.created_at).toLocaleDateString()}</div>
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
                  <button onClick={() => handleEdit(member)} className="p-2 text-blue-600 hover:bg-blue-50 rounded" title="Edit permissions"><Edit2 className="h-5 w-5" /></button>
                  {currentUser?.is_admin && (
                    <>
                      <button onClick={() => resendPasswordResetMutation.mutate(member.id)} disabled={resendPasswordResetMutation.isPending} className="p-2 text-green-600 hover:bg-green-50 rounded disabled:opacity-50" title="Resend password reset"><Mail className="h-5 w-5" /></button>
                      <button onClick={() => handleDelete(member.id)} className="p-2 text-red-600 hover:bg-red-50 rounded" title="Delete staff"><Trash2 className="h-5 w-5" /></button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Add Staff Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 p-4">
          <div className="relative top-4 sm:top-20 mx-auto p-4 sm:p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Add Staff Member</h3>
              <button
                onClick={() => {
                  setIsAddModalOpen(false)
                  setName('')
                  setEmail('')
                  setPassword('')
                  setShowPassword(false)
                }}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleAdd}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="John Doe"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="staff@example.com"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Initial Password <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={8}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Min 8 characters. Staff can reset at /reset-password"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  If set, give this password to the staff. They can login or go to /reset-password to set their own password.
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddModalOpen(false)
                    setName('')
                    setEmail('')
                    setPassword('')
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Staff Modal */}
      {isEditModalOpen && selectedStaff && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 p-4">
          <div className="relative top-4 sm:top-20 mx-auto p-4 sm:p-5 border w-full max-w-md shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Edit Staff Permissions</h3>
              <button
                onClick={() => {
                  setIsEditModalOpen(false)
                  setSelectedStaff(null)
                  setEditName('')
                  setEditNewPassword('')
                  setEditConfirmPassword('')
                  setShowEditPassword(false)
                }}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleUpdate}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email: {selectedStaff.email}
                </label>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="John Doe"
                />
              </div>

              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="is_active"
                    defaultChecked={selectedStaff.is_active}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Active</span>
                </label>
              </div>

              <div className="mb-4 space-y-2">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Permissions:</h4>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="view_staff"
                    defaultChecked={selectedStaff.permissions.view_staff}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">View Staff</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="view_settings"
                    defaultChecked={selectedStaff.permissions.view_settings}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">View Settings</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="client_right"
                    defaultChecked={selectedStaff.permissions.client_right}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Client Rights (Delete, Edit, Add, Subtract)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="view_marketing_emails"
                    defaultChecked={selectedStaff.permissions.view_marketing_emails}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">View Marketing Emails</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="dashboard_right"
                    defaultChecked={selectedStaff.permissions.dashboard_right}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Dashboard Analytics (Revenue, Profit, Charts)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="view_product_prices"
                    defaultChecked={selectedStaff.permissions.view_product_prices}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">View Product Prices</span>
                </label>
              </div>

              {currentUser?.is_admin && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Password <span className="text-gray-500 font-normal">(optional)</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showEditPassword ? 'text' : 'password'}
                      value={editNewPassword}
                      onChange={(e) => setEditNewPassword(e.target.value)}
                      minLength={8}
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Set new password for this staff"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowEditPassword(!showEditPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      title={showEditPassword ? 'Hide password' : 'Show password'}
                    >
                      {showEditPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                  <input
                    type={showEditPassword ? 'text' : 'password'}
                    value={editConfirmPassword}
                    onChange={(e) => setEditConfirmPassword(e.target.value)}
                    minLength={8}
                    className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Confirm new password"
                    autoComplete="new-password"
                  />
                </div>
              )}

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditModalOpen(false)
                    setSelectedStaff(null)
                    setEditNewPassword('')
                    setEditConfirmPassword('')
                    setShowEditPassword(false)
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Business Account Modal */}
      {isBusinessModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 p-4">
          <div className="relative top-4 sm:top-20 mx-auto p-4 sm:p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Edit Business Account</h3>
              <button
                onClick={() => {
                  setIsBusinessModalOpen(false)
                  setBusinessEmail('')
                  setBusinessNewPassword('')
                  setBusinessConfirmPassword('')
                  setBusinessName('')
                  setShowBusinessPassword(false)
                }}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            {!businessAccount ? (
              <div className="py-4 text-gray-500">Loading...</div>
            ) : (
              <form onSubmit={handleBusinessUpdate}>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Email</label>
                  <input
                    type="email"
                    required
                    value={businessEmail}
                    onChange={(e) => setBusinessEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="admin@business.com"
                  />
                  <p className="mt-1 text-xs text-gray-500">Change the business (admin) login email.</p>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Name</label>
                  <input
                    type="text"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="My Business"
                  />
                  <p className="mt-1 text-xs text-gray-500">Displayed at the top of the app.</p>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Business Username</label>
                  <input
                    type="text"
                    value={businessUsername}
                    onChange={(e) => setBusinessUsername(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="@Goal_sale"
                  />
                  <p className="mt-1 text-xs text-gray-500">Optional. Used for login instead of email. Must start with @, letters, numbers, underscores only.</p>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Password <span className="text-gray-500 font-normal">(optional)</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showBusinessPassword ? 'text' : 'password'}
                      value={businessNewPassword}
                      onChange={(e) => setBusinessNewPassword(e.target.value)}
                      minLength={8}
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Set new password for business account"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowBusinessPassword(!showBusinessPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                      title={showBusinessPassword ? 'Hide password' : 'Show password'}
                    >
                      {showBusinessPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                  <input
                    type={showBusinessPassword ? 'text' : 'password'}
                    value={businessConfirmPassword}
                    onChange={(e) => setBusinessConfirmPassword(e.target.value)}
                    minLength={8}
                    className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Confirm new password"
                    autoComplete="new-password"
                  />
                </div>
                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setIsBusinessModalOpen(false)
                      setBusinessEmail('')
                      setBusinessNewPassword('')
                      setBusinessConfirmPassword('')
                      setBusinessName('')
                      setShowBusinessPassword(false)
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={updateBusinessMutation.isPending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {updateBusinessMutation.isPending ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

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

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteConfirm.isOpen}
        onCancel={() => setDeleteConfirm({ isOpen: false, staffId: null })}
        onConfirm={confirmDelete}
        title="Delete Staff Member"
        message="Are you sure you want to delete this staff member? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
      />
    </div>
  )
}
