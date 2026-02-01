import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { emailTemplatesApi, EmailTemplate, EmailTemplateCreate } from '../api/emailTemplates'
import { Plus, Edit, Trash2 } from 'lucide-react'

export default function EmailTemplates() {
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null)
  const queryClient = useQueryClient()

  const { data: templates, isLoading } = useQuery({
    queryKey: ['email-templates'],
    queryFn: () => emailTemplatesApi.getAll(),
  })

  const createMutation = useMutation({
    mutationFn: (data: EmailTemplateCreate) => emailTemplatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
      setShowModal(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<EmailTemplateCreate> }) =>
      emailTemplatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
      setShowModal(false)
      setEditingTemplate(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => emailTemplatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
    },
  })

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const data: EmailTemplateCreate = {
      name: formData.get('name') as string,
      subject: formData.get('subject') as string,
      body: formData.get('body') as string,
    }

    if (editingTemplate) {
      updateMutation.mutate({ id: editingTemplate.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Email Templates</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage email templates for activation codes. Use placeholders: {'{order_number}'}, {'{product_name}'}, {'{activation_code}'}, {'{expiry_date}'}, {'{customer_name}'}, {'{instructions}'}
          </p>
        </div>
        <button
          onClick={() => {
            setEditingTemplate(null)
            setShowModal(true)
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Template
        </button>
      </div>

      {/* Templates List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="px-6 py-4 text-center">Loading...</div>
        ) : templates && templates.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {templates.map((template) => (
              <div key={template.id} className="p-6">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
                    <p className="mt-1 text-sm text-gray-500">Subject: {template.subject}</p>
                    <div className="mt-2 text-sm text-gray-700 bg-gray-50 p-3 rounded border max-h-32 overflow-y-auto">
                      <div dangerouslySetInnerHTML={{ __html: template.body.substring(0, 200) + '...' }} />
                    </div>
                  </div>
                  <div className="ml-4 flex space-x-2">
                    <button
                      onClick={() => {
                        setEditingTemplate(template)
                        setShowModal(true)
                      }}
                      className="text-indigo-600 hover:text-indigo-900"
                    >
                      <Edit className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this template?')) {
                          deleteMutation.mutate(template.id)
                        }
                      }}
                      className="text-red-600 hover:text-red-900"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">
            No email templates found. Create one to get started.
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-full max-w-3xl shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {editingTemplate ? 'Edit Template' : 'Add Template'}
            </h3>
            <form onSubmit={handleSubmit}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Name</label>
                  <input
                    type="text"
                    name="name"
                    required
                    defaultValue={editingTemplate?.name}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Subject</label>
                  <input
                    type="text"
                    name="subject"
                    required
                    defaultValue={editingTemplate?.subject}
                    placeholder="e.g., Digital Product Activation Code"
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Body (HTML with placeholders)
                  </label>
                  <textarea
                    name="body"
                    rows={15}
                    required
                    defaultValue={editingTemplate?.body}
                    placeholder='<html><body><h2>Digital Product Activation</h2><p>Hello, {{ customer_name }}!</p><p>Order: {{ order_number }}</p><p>Code: {{ activation_code }}</p></body></html>'
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Available placeholders: {'{order_number}'}, {'{product_name}'}, {'{activation_code}'}, {'{expiry_date}'}, {'{customer_name}'}, {'{instructions}'}
                  </p>
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingTemplate(null)
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  {editingTemplate ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
