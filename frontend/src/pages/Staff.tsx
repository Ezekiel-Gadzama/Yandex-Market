import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { staffApi, StaffCreate } from '../api/staff'
import { User, UserPermissions } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import { UserPlus, Edit2, Trash2, X, Mail, CheckCircle, AlertCircle } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

export default function Staff() {
  const { user: currentUser } = useAuth()
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [selectedStaff, setSelectedStaff] = useState<User | null>(null)
  const [email, setEmail] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; staffId: number | null }>({ isOpen: false, staffId: null })
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
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

  const createMutation = useMutation({
    mutationFn: (data: StaffCreate) => staffApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setIsAddModalOpen(false)
      setEmail('')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { permissions?: UserPermissions; is_active?: boolean } }) =>
      staffApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setIsEditModalOpen(false)
      setSelectedStaff(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => staffApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] })
      setDeleteConfirm({ isOpen: false, staffId: null })
    },
  })

  const resendPasswordResetMutation = useMutation({
    mutationFn: (id: number) => staffApi.resendPasswordReset(id),
    onSuccess: () => {
      showNotification('success', 'Password reset link has been sent to the staff member\'s email')
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail?.message || 
                          error?.response?.data?.detail || 
                          error?.message || 
                          'Failed to send password reset link'
      showNotification('error', errorMessage)
    },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({ email })
  }

  const handleEdit = (staff: User) => {
    setSelectedStaff(staff)
    setIsEditModalOpen(true)
  }

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedStaff) return

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
      data: { permissions, is_active },
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

  // Check if current user can manage staff
  const canManageStaff = currentUser?.is_admin || currentUser?.permissions.view_staff

  if (!canManageStaff) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Staff Management</h1>
        <p className="text-gray-600">You don't have permission to view this page.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Staff Management</h1>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <UserPlus className="mr-2 h-5 w-5" />
          Add Staff
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-500">Loading...</div>
      ) : staff.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
          No staff members found
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Permissions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {staff.map((member) => (
                <tr key={member.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {member.email}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        member.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {member.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <div className="flex flex-wrap gap-1">
                      {member.permissions.view_staff && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Staff</span>
                      )}
                      {member.permissions.view_settings && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">Settings</span>
                      )}
                      {member.permissions.client_right && (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Clients</span>
                      )}
                      {member.permissions.view_marketing_emails && (
                        <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">Marketing</span>
                      )}
                      {member.permissions.dashboard_right && (
                        <span className="px-2 py-1 bg-indigo-100 text-indigo-800 text-xs rounded">Dashboard</span>
                      )}
                      {member.permissions.view_product_prices && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">Prices</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(member.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => handleEdit(member)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Edit permissions"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      {currentUser?.is_admin && (
                        <>
                          <button
                            onClick={() => resendPasswordResetMutation.mutate(member.id)}
                            disabled={resendPasswordResetMutation.isPending}
                            className="text-green-600 hover:text-green-900 disabled:opacity-50"
                            title="Resend password reset link"
                          >
                            <Mail className="h-5 w-5" />
                          </button>
                          <button
                            onClick={() => handleDelete(member.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete staff"
                          >
                            <Trash2 className="h-5 w-5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Staff Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Add Staff Member</h3>
              <button
                onClick={() => {
                  setIsAddModalOpen(false)
                  setEmail('')
                }}
                className="text-gray-400 hover:text-gray-500"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleAdd}>
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
                <p className="mt-1 text-xs text-gray-500">
                  A password reset link will be sent to this email
                </p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsAddModalOpen(false)
                    setEmail('')
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
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Edit Staff Permissions</h3>
              <button
                onClick={() => {
                  setIsEditModalOpen(false)
                  setSelectedStaff(null)
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

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditModalOpen(false)
                    setSelectedStaff(null)
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
