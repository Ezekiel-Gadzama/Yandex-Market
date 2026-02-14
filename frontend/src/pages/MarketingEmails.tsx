import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { marketingEmailsApi, MarketingEmailTemplateCreate, BroadcastFilters } from '../api/marketingEmails'
import { productsApi } from '../api/products'
import { mediaApi } from '../api/media'
import { Plus, Edit, Trash2, X, Send, Bold, Italic, Underline, X as XIcon, Copy, CheckCircle, AlertCircle } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

export default function MarketingEmails() {
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<any>(null)
  const [showBroadcastModal, setShowBroadcastModal] = useState(false)
  const [broadcastTemplate, setBroadcastTemplate] = useState<any>(null)
  const [selectedProducts, setSelectedProducts] = useState<number[]>([])
  const [sendToAllClients, setSendToAllClients] = useState(false)
  const [dateFilter, setDateFilter] = useState<string>('all')
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')
  const [minQuantity, setMinQuantity] = useState<number>(1)
  const [minTotalProducts, setMinTotalProducts] = useState<number>(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; templateId: number | null }>({ isOpen: false, templateId: null })
  const [broadcastConfirm, setBroadcastConfirm] = useState<{ isOpen: boolean; template: any | null }>({ isOpen: false, template: null })
  const [notification, setNotification] = useState<{ isOpen: boolean; type: 'success' | 'error'; message: string }>({ isOpen: false, type: 'success', message: '' })
  const queryClient = useQueryClient()

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ isOpen: true, type, message })
    // Auto-close after 4 seconds
    setTimeout(() => setNotification(prev => ({ ...prev, isOpen: false })), 4000)
  }

  const { data: templates, isLoading, error: templatesError } = useQuery({
    queryKey: ['marketing-templates', searchTerm],
    queryFn: () => marketingEmailsApi.getAll(searchTerm || undefined),
  })

  const { data: products = [] } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
  })

  const createMutation = useMutation({
    mutationFn: (data: MarketingEmailTemplateCreate) => marketingEmailsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-templates'] })
      setShowModal(false)
      setEditingTemplate(null)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      marketingEmailsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-templates'] })
      setShowModal(false)
      setEditingTemplate(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => marketingEmailsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-templates'] })
    },
  })

  const broadcastMutation = useMutation({
    mutationFn: ({ id, filters }: { id: number; filters: BroadcastFilters }) => 
      marketingEmailsApi.broadcast(id, filters),
    onSuccess: (data) => {
      const filterMsg = data.filters_applied && data.filters_applied.length > 0 
        ? ` (${data.filters_applied.join(', ')})` 
        : ''
      showNotification('success', `Email broadcast sent to ${data.sent_count} client${data.sent_count !== 1 ? 's' : ''}!${filterMsg}`)
      resetFilters()
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to send broadcast'
      showNotification('error', `Error: ${errorMessage}`)
    },
  })

  const resetFilters = () => {
    setSelectedProducts([])
    setSendToAllClients(false)
    setDateFilter('all')
    setCustomStartDate('')
    setCustomEndDate('')
    setMinQuantity(1)
    setMinTotalProducts(1)
  }

  const [templateName, setTemplateName] = useState('')
  const [templateSubject, setTemplateSubject] = useState('')
  const [templateBody, setTemplateBody] = useState('')
  const [frequencyDays, setFrequencyDays] = useState<number | undefined>(undefined)
  const [autoBroadcastEnabled, setAutoBroadcastEnabled] = useState(false)
  const [isDefault, setIsDefault] = useState(false)
  const [attachments, setAttachments] = useState<Array<{url: string, type: 'image' | 'video' | 'file', name: string}>>([])
  const [uploading, setUploading] = useState(false)

  // Update form when editing template changes
  useEffect(() => {
    if (editingTemplate) {
      setTemplateName(editingTemplate.name || '')
      setTemplateSubject(editingTemplate.subject || '')
      setTemplateBody(editingTemplate.body || '')
      setFrequencyDays(editingTemplate.frequency_days || undefined)
      setAutoBroadcastEnabled(editingTemplate.auto_broadcast_enabled || false)
      setIsDefault(editingTemplate.is_default || false)
      // Convert legacy format to unified attachments if needed
      if (editingTemplate.attachments && Array.isArray(editingTemplate.attachments) && editingTemplate.attachments.length > 0) {
        console.log('📎 Loading attachments:', editingTemplate.attachments)
        setAttachments(editingTemplate.attachments)
      } else if (editingTemplate.attachments && Array.isArray(editingTemplate.attachments)) {
        // Empty array - still set it
        console.log('📎 No attachments (empty array)')
        setAttachments([])
      } else {
        // Legacy format migration - check if template has old properties (using type assertion for backward compatibility)
        const legacyTemplate = editingTemplate as any
        if (legacyTemplate.template_files || legacyTemplate.template_images || legacyTemplate.template_videos) {
          const migrated: Array<{url: string, type: 'image' | 'video' | 'file', name: string}> = []
          if (legacyTemplate.template_images) {
            legacyTemplate.template_images.forEach((url: string) => {
              if (url) migrated.push({ url, type: 'image', name: url.split('/').pop() || url })
            })
          }
          if (legacyTemplate.template_videos) {
            legacyTemplate.template_videos.forEach((url: string) => {
              if (url) migrated.push({ url, type: 'video', name: url.split('/').pop() || url })
            })
          }
          if (legacyTemplate.template_files) {
            legacyTemplate.template_files.forEach((url: string) => {
              if (url) migrated.push({ url, type: 'file', name: url.split('/').pop() || url })
            })
          }
          setAttachments(migrated)
        } else {
          setAttachments([])
        }
      }
    } else if (showModal) {
      setTemplateName('')
      setTemplateSubject('')
      setTemplateBody('')
      setFrequencyDays(undefined)
      setAutoBroadcastEnabled(false)
      setIsDefault(false)
      setAttachments([])
    }
  }, [editingTemplate, showModal])

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    
    setUploading(true)
    try {
      const fileArray = Array.from(files)
      const uploadedAttachments = await mediaApi.uploadFiles(fileArray, 'marketing')
      setAttachments(prev => [...prev, ...uploadedAttachments])
    } catch (error) {
      alert('Failed to upload files: ' + (error as Error).message)
    } finally {
      setUploading(false)
    }
  }

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const isFormValid = templateName.trim().length > 0 && templateSubject.trim().length > 0 && templateBody.trim().length > 0

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!isFormValid) return
    
    const data = {
      name: templateName,
      subject: templateSubject,
      body: templateBody,
      attachments: attachments,
      frequency_days: frequencyDays || undefined,
      auto_broadcast_enabled: autoBroadcastEnabled,
      is_default: isDefault,
    }

    if (editingTemplate && editingTemplate.id) {
      updateMutation.mutate({ id: editingTemplate.id, data })
    } else {
      createMutation.mutate(data)
    }
  }


  const handleEdit = async (template: any) => {
    // Fetch fresh template data to ensure we have the latest attachments
    try {
      const freshTemplate = await marketingEmailsApi.getById?.(template.id) || template
      setEditingTemplate(freshTemplate)
      setTemplateName(freshTemplate.name || '')
      setTemplateSubject(freshTemplate.subject || '')
      setTemplateBody(freshTemplate.body || '')
      // Attachments will be set by useEffect
      setShowModal(true)
    } catch (error) {
      console.error('Failed to fetch template:', error)
      // Fallback to template from list
      setEditingTemplate(template)
      setTemplateName(template.name || '')
      setTemplateSubject(template.subject || '')
      setTemplateBody(template.body || '')
      setShowModal(true)
    }
  }

  const handleDelete = (id: number) => {
    const template = templates?.find(t => t.id === id)
    if (template?.is_default) {
      alert('Cannot delete default template')
      return
    }
    setDeleteConfirm({ isOpen: true, templateId: id })
  }

  const handleDuplicate = (template: any) => {
    if (template.is_default) {
      alert('Cannot duplicate default template')
      return
    }
    setEditingTemplate({
      ...template,
      id: 0,
      name: `${template.name} (Copy)`,
      is_default: false,  // Ensure copied template is not default
    })
    setTemplateName(`${template.name} (Copy)`)
    setTemplateSubject(template.subject || '')
    setTemplateBody(template.body || '')
    setFrequencyDays(template.frequency_days || undefined)
    setAutoBroadcastEnabled(template.auto_broadcast_enabled || false)
    setIsDefault(false)  // Ensure copied template is not default
    // Attachments will be set by useEffect when editingTemplate changes
    setShowModal(true)
  }


  const confirmBroadcast = () => {
    if (!broadcastTemplate) return
    
    // Store template ID before closing modal
    const templateId = broadcastTemplate.id
    
    // Build filters object - only include defined values
    const filters: BroadcastFilters = {}
    
    // If "Send to All Clients" is checked, don't filter by products
    if (!sendToAllClients && selectedProducts.length > 0) {
      filters.product_ids = selectedProducts
    }
    
    if (dateFilter && dateFilter !== 'all') {
      if (dateFilter === 'custom') {
        if (customStartDate && customEndDate) {
          filters.date_filter = 'custom'
          filters.custom_start_date = customStartDate
          filters.custom_end_date = customEndDate
        }
      } else {
        filters.date_filter = dateFilter as any
      }
    }
    
    if (minQuantity && minQuantity > 1 && selectedProducts.length > 0 && !sendToAllClients) {
      filters.min_product_quantity = minQuantity
    }
    
    if (minTotalProducts && minTotalProducts > 1) {
      filters.min_total_products = minTotalProducts
    }
    
    // Close modal immediately (don't wait for response)
    setShowBroadcastModal(false)
    setBroadcastTemplate(null)
    resetFilters()
    
    // Start the mutation
    broadcastMutation.mutate({
      id: templateId,
      filters
    })
  }

  const handleBroadcastClick = (template: any) => {
    setBroadcastTemplate(template)
    resetFilters() // Reset all filters when opening broadcast modal
    setShowBroadcastModal(true)
  }

  const toggleProduct = (productId: number) => {
    if (sendToAllClients) {
      // If "Send to All Clients" is checked, uncheck it first
      setSendToAllClients(false)
    }
    setSelectedProducts(prev =>
      prev.includes(productId)
        ? prev.filter(id => id !== productId)
        : [...prev, productId]
    )
  }

  const handleCheckAllProducts = () => {
    if (sendToAllClients) {
      // If "Send to All Clients" is checked, uncheck it first
      setSendToAllClients(false)
    }
    // Select all products
    const allProductIds = products.map(p => p.id)
    setSelectedProducts(allProductIds)
  }

  const handleUncheckAllProducts = () => {
    setSelectedProducts([])
  }

  const handleSendToAllClients = () => {
    if (selectedProducts.length > 0) {
      // If products are selected, clear them first
      setSelectedProducts([])
    }
    setSendToAllClients(true)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Marketing Emails</h1>
          <p className="mt-1 text-sm text-gray-600">
            Create email templates and broadcast them to all your clients
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
          New Template
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search templates..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading templates...</div>
      ) : templatesError ? (
        <div className="text-center py-12">
          <div className="text-red-600 font-medium mb-2">Error loading marketing email templates</div>
          <div className="text-gray-600 text-sm">
            {String((templatesError as any)?.response?.data?.detail?.message || 
                    (templatesError as any)?.response?.data?.detail || 
                    (templatesError as any)?.message || 
                    'Please try again or contact your administrator.')}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {templates && templates.length === 0 ? (
            <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
              No marketing email templates yet. Create your first template to get started.
            </div>
          ) : (
            // Sort templates: default templates first, then others
            [...(templates || [])]
              .sort((a, b) => {
                if (a.is_default && !b.is_default) return -1
                if (!a.is_default && b.is_default) return 1
                return 0
              })
              .map((template) => (
              <div key={template.id} className={`bg-white shadow rounded-lg p-6 ${template.is_default ? 'border-2 border-blue-500' : ''}`}>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
                      {template.is_default && (
                        <span className="px-2 py-1 text-xs font-semibold bg-blue-100 text-blue-800 rounded">
                          Default
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Subject: <span className="font-medium">{template.subject}</span>
                    </p>
                    {template.frequency_days && (
                      <p className="text-xs text-gray-500 mt-1">
                        Frequency: {template.frequency_days} days
                        {template.auto_broadcast_enabled && ' (Auto-broadcast enabled)'}
                      </p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleBroadcastClick(template)}
                      disabled={broadcastMutation.isPending}
                      className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                    >
                      <Send className="h-4 w-4 mr-1" />
                      Broadcast
                    </button>
                    {!template.is_default && (
                      <>
                        <button
                          onClick={() => handleDuplicate(template)}
                          className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                          title="Duplicate"
                        >
                          <Copy className="h-4 w-4 mr-1" />
                          Duplicate
                        </button>
                        <button
                          onClick={() => handleEdit(template)}
                          className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                        >
                          <Edit className="h-4 w-4 mr-1" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(template.id)}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-red-600 bg-red-50 hover:bg-red-100"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    )}
                    {template.is_default && (
                      <button
                        onClick={() => handleEdit(template)}
                        className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        <Edit className="h-4 w-4 mr-1" />
                        Edit
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-4 p-4 bg-gray-50 rounded-md">
                  <p className="text-sm text-gray-600">Preview:</p>
                  <div className="mt-2 text-sm" dangerouslySetInnerHTML={{ __html: template.body }} />
                </div>
                <p className="mt-3 text-xs text-gray-400">
                  Created: {new Date(template.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] flex flex-col p-6">
            {/* Sticky Header */}
            <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
              <h2 className="text-xl font-bold text-gray-900">
                {editingTemplate && editingTemplate.id ? 'Edit Template' : 'Create New Template'}
              </h2>
              <button
                onClick={() => {
                  setShowModal(false)
                  setEditingTemplate(null)
                  setTemplateName('')
                  setTemplateSubject('')
                  setTemplateBody('')
                  setAttachments([])
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <form id="marketing-form" onSubmit={handleSubmit} className="space-y-4 flex-1 overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Template Name *
                </label>
                <input
                  type="text"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  required
                  placeholder="e.g., Monthly Newsletter"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Subject *
                </label>
                <input
                  type="text"
                  value={templateSubject}
                  onChange={(e) => setTemplateSubject(e.target.value)}
                  required
                  placeholder="e.g., Check out our latest offers!"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {isDefault ? 'Additional Information *' : 'Email Body *'}
                </label>
                <RichTextEditor value={templateBody} onChange={setTemplateBody} />
                <p className="mt-1 text-xs text-gray-500">
                  {isDefault 
                    ? 'Additional information to add to the broadcasted email (for default template, this will be combined with unique client product information)'
                    : 'Rich text email body with formatting support.'}
                </p>
              </div>

              {/* Frequency and Auto-Broadcast Settings */}
              <div className="space-y-4 border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700">Broadcast Settings</h4>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Frequency (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={frequencyDays || ''}
                    onChange={(e) => setFrequencyDays(e.target.value ? parseInt(e.target.value) : undefined)}
                    placeholder="e.g., 30"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Frequency in days for auto-broadcast (e.g., 30 means every 30 days)
                  </p>
                </div>
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={autoBroadcastEnabled}
                      onChange={(e) => setAutoBroadcastEnabled(e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">Enable Auto-Broadcast</span>
                  </label>
                  <p className="mt-1 text-xs text-gray-500 ml-6">
                    If enabled, the email will automatically broadcast based on the frequency period. If disabled, the email only broadcasts when you click broadcast.
                  </p>
                </div>
                {(!editingTemplate?.id || !editingTemplate?.is_default) && (
                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={isDefault}
                        onChange={(e) => setIsDefault(e.target.checked)}
                        disabled={editingTemplate?.is_default}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                      />
                      <span className="ml-2 text-sm text-gray-700">Default Template</span>
                    </label>
                    <p className="mt-1 text-xs text-gray-500 ml-6">
                      Default template is pinned at the top and sends unique emails to each client based on expired subscriptions. Cannot be duplicated or deleted.
                    </p>
                  </div>
                )}
              </div>

              {/* Unified Media Attachments */}
              <div className="space-y-4 border-t pt-4">
                <h4 className="text-sm font-medium text-gray-700">Media Attachments</h4>
                <p className="text-xs text-gray-500">Upload images, videos, or any other files</p>
                <input
                  type="file"
                  multiple
                  onChange={(e) => handleFileUpload(e.target.files)}
                  disabled={uploading}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {uploading && <p className="text-sm text-gray-500">Uploading...</p>}
                {attachments.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {attachments.map((attachment, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                        <div className="flex items-center space-x-2 flex-1">
                          {attachment.type === 'image' ? (
                            <img 
                              src={mediaApi.getMediaUrl(attachment.url)} 
                              alt={attachment.name}
                              className="h-12 w-12 object-cover rounded cursor-pointer hover:opacity-75"
                              onClick={() => window.open(mediaApi.getMediaUrl(attachment.url), '_blank')}
                            />
                          ) : (
                            <span className="text-xs px-2 py-1 bg-gray-200 rounded">
                              {attachment.type === 'video' ? '🎥' : '📄'}
                            </span>
                          )}
                          <span 
                            className="text-sm text-gray-700 cursor-pointer hover:text-blue-600 hover:underline flex-1"
                            onClick={() => window.open(mediaApi.getMediaUrl(attachment.url), '_blank')}
                          >
                            {attachment.name}
                          </span>
                          <span className="text-xs text-gray-500 px-2 py-1 bg-gray-200 rounded">
                            {attachment.type}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeAttachment(idx)}
                          className="text-red-500 hover:text-red-700 ml-2"
                        >
                          <XIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </form>
            {/* Sticky Footer */}
            <div className="flex justify-end space-x-3 pt-4 border-t sticky bottom-0 bg-white mt-4">
              <button
                type="button"
                onClick={() => {
                  setShowModal(false)
                  setEditingTemplate(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="marketing-form"
                disabled={createMutation.isPending || updateMutation.isPending || !isFormValid || uploading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {(createMutation.isPending || updateMutation.isPending)
                  ? 'Saving...'
                  : editingTemplate && editingTemplate.id
                  ? 'Update Template'
                  : 'Create Template'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Broadcast Modal */}
      {showBroadcastModal && broadcastTemplate && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Broadcast Email</h2>
              <button
                onClick={() => {
                  setShowBroadcastModal(false)
                  setBroadcastTemplate(null)
                  setSelectedProducts([])
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-700">
                  Template: <span className="font-medium">{broadcastTemplate.name}</span>
                </p>
                <p className="text-sm text-gray-700">
                  Subject: <span className="font-medium">{broadcastTemplate.subject}</span>
                </p>
                <p className="text-sm text-gray-700 mt-2">
                  Recipients: <span className="font-medium text-blue-600">
                    {sendToAllClients 
                      ? 'All clients' 
                      : selectedProducts.length > 0 
                        ? `${selectedProducts.length} selected product(s) - clients who purchased these products`
                        : 'All clients (no products selected)'}
                  </span>
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Filter by Products
                  </label>
                  <div className="flex gap-2">
                    {selectedProducts.length > 0 && selectedProducts.length < products.length && (
                      <button
                        type="button"
                        onClick={handleCheckAllProducts}
                        disabled={sendToAllClients}
                        className="text-xs px-2 py-1 text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Check All
                      </button>
                    )}
                    {selectedProducts.length > 0 && (
                      <button
                        type="button"
                        onClick={handleUncheckAllProducts}
                        disabled={sendToAllClients}
                        className="text-xs px-2 py-1 text-gray-600 hover:text-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Uncheck All
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-xs text-gray-600 mb-2">
                  Select products to send only to clients who purchased them. This ensures clients only receive emails for products they own.
                </p>
                <div className="border border-gray-300 rounded-md max-h-40 overflow-y-auto p-2">
                  {products.length === 0 ? (
                    <p className="text-sm text-gray-500 p-2">No products available</p>
                  ) : (
                    products.map((product) => (
                      <label 
                        key={product.id} 
                        className={`flex items-center p-2 hover:bg-gray-50 cursor-pointer ${sendToAllClients ? 'opacity-50' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedProducts.includes(product.id)}
                          onChange={() => toggleProduct(product.id)}
                          disabled={sendToAllClients}
                          className="mr-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        />
                        <span className="text-sm">{product.name}</span>
                      </label>
                    ))
                  )}
                </div>
                {selectedProducts.length > 0 && (
                  <p className="mt-2 text-sm text-blue-600">
                    {selectedProducts.length} product(s) selected - will send to clients who purchased these products
                  </p>
                )}
              </div>

              {/* Send to All Clients Option */}
              <div className="border-t pt-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={sendToAllClients}
                    onChange={(e) => {
                      if (e.target.checked) {
                        handleSendToAllClients()
                      } else {
                        setSendToAllClients(false)
                      }
                    }}
                    disabled={selectedProducts.length > 0}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Send to All Clients
                  </span>
                </label>
                <p className="mt-1 text-xs text-gray-500 ml-6">
                  Send to all clients regardless of products purchased. This option is disabled when products are selected.
                </p>
                {sendToAllClients && (
                  <p className="mt-2 text-sm text-blue-600 ml-6">
                    Will send to all clients in the system
                  </p>
                )}
              </div>

              {/* Time Period Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter by Purchase Date (Optional)
                </label>
                <select
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Time</option>
                  <option value="last_month">Last Month</option>
                  <option value="last_3_months">Last 3 Months</option>
                  <option value="last_6_months">Last 6 Months</option>
                  <option value="last_year">Last Year</option>
                  <option value="custom">Custom Date Range</option>
                </select>
                {dateFilter === 'custom' && (
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Start Date</label>
                      <input
                        type="date"
                        value={customStartDate}
                        onChange={(e) => setCustomStartDate(e.target.value)}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">End Date</label>
                      <input
                        type="date"
                        value={customEndDate}
                        onChange={(e) => setCustomEndDate(e.target.value)}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Quantity Filters */}
              {selectedProducts.length > 0 && !sendToAllClients && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Minimum Purchase Quantity (Optional)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={minQuantity}
                    onChange={(e) => setMinQuantity(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Send only to clients who bought at least this many of the selected products
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Total Products (Optional)
                </label>
                <input
                  type="number"
                  min="1"
                  value={minTotalProducts}
                  onChange={(e) => setMinTotalProducts(parseInt(e.target.value) || 1)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Send only to clients who bought at least this many different products in total
                </p>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowBroadcastModal(false)
                    setBroadcastConfirm({ isOpen: false, template: null })
                    setBroadcastTemplate(null)
                    resetFilters()
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    // Show confirmation before sending
                    setBroadcastConfirm({ isOpen: true, template: broadcastTemplate })
                  }}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
                >
                  <Send className="h-4 w-4 mr-2" />
                  Send Broadcast
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteConfirm.isOpen}
        title="Delete Template"
        message="Are you sure you want to delete this template? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => {
          if (deleteConfirm.templateId) {
            deleteMutation.mutate(deleteConfirm.templateId)
          }
          setDeleteConfirm({ isOpen: false, templateId: null })
        }}
        onCancel={() => setDeleteConfirm({ isOpen: false, templateId: null })}
      />

      {/* Broadcast Confirmation Modal - Shows after clicking "Send Broadcast" */}
      <ConfirmationModal
        isOpen={broadcastConfirm.isOpen}
        title="Broadcast Email"
        message={`Are you sure you want to broadcast "${broadcastConfirm.template?.name}"? This will send the email to all selected clients.`}
        confirmText="Broadcast"
        cancelText="Cancel"
        variant="info"
        onConfirm={() => {
          if (broadcastConfirm.template) {
            setBroadcastConfirm({ isOpen: false, template: null })
            confirmBroadcast()
          }
        }}
        onCancel={() => setBroadcastConfirm({ isOpen: false, template: null })}
      />

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
    </div>
  )
}

// Rich Text Editor Component for Marketing Emails
function RichTextEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const editorRef = useRef<HTMLDivElement>(null)
  const [fontSize, setFontSize] = useState('14px')
  const lastSyncedValue = useRef<string>('')
  const isUpdatingFromUser = useRef(false)

  // Initialize and sync value from props only when it changes externally
  useEffect(() => {
    if (editorRef.current && !isUpdatingFromUser.current) {
      // Only update if the prop value is different from what we last synced
      if (value !== lastSyncedValue.current) {
        const currentContent = editorRef.current.innerHTML || ''
        // Only update if the content is actually different
        if (currentContent !== value) {
          editorRef.current.innerHTML = value || ''
          lastSyncedValue.current = value || ''
        }
      }
    }
    // Reset the flag after effect runs
    isUpdatingFromUser.current = false
  }, [value])

  const applyFormat = (command: string, value?: string) => {
    document.execCommand(command, false, value)
    editorRef.current?.focus()
    // Update value after formatting
    if (editorRef.current) {
      const newValue = editorRef.current.innerHTML || ''
      isUpdatingFromUser.current = true
      lastSyncedValue.current = newValue
      onChange(newValue)
    }
  }

  const handleInput = () => {
    if (editorRef.current) {
      const newValue = editorRef.current.innerHTML || ''
      isUpdatingFromUser.current = true
      lastSyncedValue.current = newValue
      onChange(newValue)
    }
  }

  return (
    <div className="border border-gray-300 rounded-md">
      {/* Toolbar */}
      <div className="flex items-center space-x-2 p-2 border-b border-gray-200 bg-gray-50">
        <button
          type="button"
          onClick={() => applyFormat('bold')}
          className="p-2 hover:bg-gray-200 rounded"
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => applyFormat('italic')}
          className="p-2 hover:bg-gray-200 rounded"
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => applyFormat('underline')}
          className="p-2 hover:bg-gray-200 rounded"
          title="Underline"
        >
          <Underline className="h-4 w-4" />
        </button>
        <div className="border-l border-gray-300 h-6 mx-2" />
        <select
          value={fontSize}
          onChange={(e) => {
            setFontSize(e.target.value)
            applyFormat('fontSize', e.target.value)
          }}
          className="px-2 py-1 border border-gray-300 rounded text-sm"
        >
          <option value="12px">12px</option>
          <option value="14px">14px</option>
          <option value="16px">16px</option>
          <option value="18px">18px</option>
          <option value="20px">20px</option>
          <option value="24px">24px</option>
        </select>
        <div className="border-l border-gray-300 h-6 mx-2" />
        <button
          type="button"
          onClick={() => {
            const selection = window.getSelection()
            if (selection && selection.rangeCount > 0) {
              const range = selection.getRangeAt(0)
              const span = document.createElement('span')
              span.style.backgroundColor = 'yellow'
              try {
                range.surroundContents(span)
                handleInput()
              } catch (e) {
                span.appendChild(range.extractContents())
                range.insertNode(span)
                handleInput()
              }
            }
          }}
          className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-200"
          title="Highlight"
        >
          Highlight
        </button>
      </div>
      {/* Editor */}
      <div
        ref={editorRef}
        contentEditable
        onInput={handleInput}
        className="min-h-[200px] p-3 focus:outline-none"
        style={{ fontSize }}
        suppressContentEditableWarning
      />
    </div>
  )
}
