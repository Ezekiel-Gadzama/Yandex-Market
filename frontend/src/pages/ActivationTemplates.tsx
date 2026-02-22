import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { activationTemplatesApi, ActivationTemplate, ActivationTemplateCreate } from '../api/activationTemplates'
import { Plus, Edit, Trash2, X, Bold, Italic, Underline, Copy, Upload } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

// Component to preview template body with height-based truncation
function TemplateBodyPreview({ body }: { body: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [showEllipsis, setShowEllipsis] = useState(false)

  useEffect(() => {
    // Use a small delay to ensure DOM is fully rendered
    const checkOverflow = () => {
      if (containerRef.current) {
        // Check if content overflows the container
        const containerHeight = containerRef.current.clientHeight
        const contentHeight = containerRef.current.scrollHeight
        setShowEllipsis(contentHeight > containerHeight)
      }
    }
    
    // Check immediately and after a short delay
    checkOverflow()
    const timeoutId = setTimeout(checkOverflow, 100)
    
    return () => clearTimeout(timeoutId)
  }, [body])

  return (
    <div className="mt-3 relative">
      <div 
        ref={containerRef}
        className="text-sm text-gray-700 bg-gray-50 p-3 rounded border max-h-20 overflow-hidden relative"
        dangerouslySetInnerHTML={{ 
          __html: body
        }}
      />
      {showEllipsis && (
        <div className="absolute bottom-0 right-0 px-3 pb-1 bg-gray-50 text-gray-500 font-semibold">
          ...
        </div>
      )}
    </div>
  )
}

export default function ActivationTemplates() {
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<ActivationTemplate | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; templateId: number | null }>({ isOpen: false, templateId: null })
  const queryClient = useQueryClient()

  const { data: templates, isLoading } = useQuery({
    queryKey: ['email-templates', searchTerm],
    queryFn: () => activationTemplatesApi.getAll(searchTerm || undefined),
  })

  const createMutation = useMutation({
    mutationFn: (data: ActivationTemplateCreate) => activationTemplatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
      setShowModal(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ActivationTemplateCreate> }) =>
      activationTemplatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
      setShowModal(false)
      setEditingTemplate(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => activationTemplatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
    },
  })

  const createFromFileMutation = useMutation({
    mutationFn: (file: File) => activationTemplatesApi.createFromFile(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-templates'] })
      setShowModal(false)
    },
    onError: () => alert('Upload failed. Only .txt or .pdf are allowed.'),
  })

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-start mb-6">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Activation Templates</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage templates for digital product activation messages sent when completing orders.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingTemplate(null)
            setShowModal(true)
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 w-full sm:w-auto shrink-0"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Template
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

      {/* Templates List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="px-6 py-4 text-center">Loading...</div>
        ) : templates && templates.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {templates.map((template) => (
              <div key={template.id} className="p-4 sm:p-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-start">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
                    <div className="mt-2 flex space-x-4 text-sm">
                      <span className={`px-2 py-1 rounded ${template.random_key ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {template.random_key ? 'Auto Key' : 'Manual Key'}
                      </span>
                      {template.required_login && (
                        <span className="px-2 py-1 rounded bg-blue-100 text-blue-800">Requires Login</span>
                      )}
                    </div>
                    <TemplateBodyPreview body={template.body || ''} />
                  </div>
                  <div className="ml-0 sm:ml-4 flex flex-wrap items-center gap-2 shrink-0">
                    <div className="flex items-center border border-gray-300 rounded-md overflow-hidden">
                      <span className="px-2 py-1 text-xs text-gray-600 bg-gray-50 border-r border-gray-300">Download</span>
                      <select
                        className="text-sm py-1 pr-6 pl-2 text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                        value=""
                        onChange={(e) => {
                          const fmt = e.target.value as 'txt' | 'pdf'
                          if (fmt) {
                            activationTemplatesApi.export(template.id, fmt).catch(() => alert('Download failed'))
                            e.target.value = ''
                          }
                        }}
                      >
                        <option value="">Format</option>
                        <option value="txt">TXT</option>
                        <option value="pdf">PDF</option>
                      </select>
                    </div>
                    <button
                      onClick={() => {
                        // Create a copy with new name
                        const copyTemplate = {
                          ...template,
                          id: 0,
                          name: `${template.name} (Copy)`,
                        } as ActivationTemplate
                        setEditingTemplate(copyTemplate)
                        setShowModal(true)
                      }}
                      className="text-blue-600 hover:text-blue-900"
                      title="Duplicate"
                    >
                      <Copy className="h-5 w-5" />
                    </button>
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
                      onClick={() => setDeleteConfirm({ isOpen: true, templateId: template.id })}
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
            No activation templates found. Create one to get started.
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <TemplateModal
          template={editingTemplate}
          onClose={() => {
            setShowModal(false)
            setEditingTemplate(null)
          }}
          onSave={(data) => {
            if (editingTemplate && editingTemplate.id) {
              updateMutation.mutate({ id: editingTemplate.id, data })
            } else {
              createMutation.mutate(data)
            }
          }}
          onUploadFile={(file) => createFromFileMutation.mutate(file)}
          uploadPending={createFromFileMutation.isPending}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Confirmation Modal */}
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
    </div>
  )
}

// Rich Text Editor Component
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
                // If surroundContents fails, try alternative
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

// Template Modal Component
function TemplateModal({
  template,
  onClose,
  onSave,
  onUploadFile,
  uploadPending,
  isLoading,
}: {
  template: ActivationTemplate | null
  onClose: () => void
  onSave: (data: ActivationTemplateCreate) => void
  onUploadFile?: (file: File) => void
  uploadPending?: boolean
  isLoading: boolean
}) {
  const [name, setName] = useState('')
  const [body, setBody] = useState('')
  const [randomKey, setRandomKey] = useState(true)
  const [requiredLogin, setRequiredLogin] = useState(false)
  const [activateTillDays, setActivateTillDays] = useState(30)
  const uploadFileInputRef = useRef<HTMLInputElement>(null)
  const isCreate = !template || !template.id

  // Sync with template prop
  useEffect(() => {
    if (template) {
      setName(template.name || '')
      setBody(template.body || '')
      setRandomKey(template.random_key !== false)
      setRequiredLogin(template.required_login || false)
      setActivateTillDays(template.activate_till_days || 30)
    } else {
      setName('')
      setBody('')
      setRandomKey(true)
      setRequiredLogin(false)
      setActivateTillDays(30)
    }
  }, [template])


  const isFormValid = name.trim().length > 0 && body.trim().length > 0

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isFormValid) return
    
    if (template && template.id) {
      // Update existing template
      onSave({
        name,
        body,
        random_key: randomKey,
        required_login: requiredLogin,
        activate_till_days: activateTillDays,
      })
    } else {
      // Create new template (including duplicates)
      onSave({
        name,
        body,
        random_key: randomKey,
        required_login: requiredLogin,
        activate_till_days: activateTillDays,
      })
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        {/* Sticky Header */}
        <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
          <h3 className="text-lg font-medium text-gray-900">
            {template && template.id ? 'Edit Template' : 'Create New Template'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-6 w-6" />
          </button>
        </div>
        <form id="template-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          {isCreate && onUploadFile && (
            <div className="pb-4 mb-4 border-b border-gray-200">
              <p className="text-sm font-medium text-gray-700 mb-2">Create from file (TXT or PDF)</p>
              <div className="flex items-center gap-2">
                <input
                  ref={uploadFileInputRef}
                  type="file"
                  accept=".txt,.pdf"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) onUploadFile(file)
                    e.target.value = ''
                  }}
                />
                <button
                  type="button"
                  onClick={() => uploadFileInputRef.current?.click()}
                  disabled={uploadPending}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  {uploadPending ? 'Uploading...' : 'Upload TXT or PDF'}
                </button>
                <span className="text-xs text-gray-500">Or fill the form below</span>
              </div>
            </div>
          )}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="e.g., Netflix Subscription Template"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Body (Plain Text) *
              </label>
              <RichTextEditor value={body} onChange={setBody} />
              <p className="mt-2 text-xs text-gray-500">
                This is the main instruction text. The activation code, expiry date, and footer will be automatically added when sending.
              </p>
            </div>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={randomKey}
                  onChange={(e) => setRandomKey(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Random Key (Auto-generated activation code)</span>
              </label>
              <p className="text-xs text-gray-500 ml-6">
                If checked, activation codes will be automatically generated. If unchecked, you'll need to provide codes manually.
              </p>
            </div>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={requiredLogin}
                  onChange={(e) => setRequiredLogin(e.target.checked)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Required Login</span>
              </label>
              <p className="text-xs text-gray-500 ml-6">
                If checked, adds "Done! The operator will log in to your account..." text after the template body.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Activation Expiry Period (Days) *
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={activateTillDays}
                onChange={(e) => setActivateTillDays(parseInt(e.target.value) || 30)}
                required
                placeholder="30"
                className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
              />
              <p className="mt-1 text-xs text-gray-500">
                Number of days until the activation code expires. This is sent to Yandex Market when completing orders. Default: 30 days.
              </p>
            </div>

          </div>
        </form>
        {/* Sticky Footer */}
        <div className="mt-6 flex justify-end space-x-3 pt-4 border-t sticky bottom-0 bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="template-form"
            disabled={isLoading || !isFormValid}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : template && template.id ? 'Update Template' : 'Create Template'}
          </button>
        </div>
      </div>
    </div>
  )
}
