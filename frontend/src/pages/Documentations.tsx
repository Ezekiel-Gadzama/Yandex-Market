import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentationsApi, Documentation, DocumentationCreate } from '../api/documentations'
import { mediaApi } from '../api/media'
import { Plus, Edit, Trash2, X, FileText, Link as LinkIcon, Copy, Bold, Italic, Underline } from 'lucide-react'
import ConfirmationModal from '../components/ConfirmationModal'

export default function Documentations() {
  const [showModal, setShowModal] = useState(false)
  const [editingDoc, setEditingDoc] = useState<Documentation | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; docId: number | null }>({ isOpen: false, docId: null })
  const queryClient = useQueryClient()

  const { data: documentations, isLoading } = useQuery({
    queryKey: ['documentations', searchTerm],
    queryFn: () => documentationsApi.getAll(searchTerm || undefined),
  })

  const createMutation = useMutation({
    mutationFn: (data: DocumentationCreate) => documentationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentations'] })
      setShowModal(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<DocumentationCreate> }) =>
      documentationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentations'] })
      setShowModal(false)
      setEditingDoc(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documentations'] })
    },
  })

  const handleDuplicate = (doc: Documentation) => {
    setEditingDoc({
      ...doc,
      id: 0, // Reset ID to create new
      name: `${doc.name} (Copy)`,
    } as Documentation)
    setShowModal(true)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Documentations</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage documentation files and links for order fulfillment processes.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingDoc(null)
            setShowModal(true)
          }}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Documentation
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search documentations..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Documentations List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="px-6 py-4 text-center">Loading...</div>
        ) : documentations && documentations.length > 0 ? (
          <div className="divide-y divide-gray-200">
            {documentations.map((doc) => (
              <div key={doc.id} className="p-6">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      {doc.type === 'file' ? (
                        <FileText className="h-5 w-5 text-gray-400" />
                      ) : (
                        <LinkIcon className="h-5 w-5 text-gray-400" />
                      )}
                      <h3 className="text-lg font-medium text-gray-900">{doc.name}</h3>
                      <span className={`px-2 py-1 text-xs rounded ${
                        doc.type === 'file' ? 'bg-blue-100 text-blue-800' : 
                        doc.type === 'link' ? 'bg-green-100 text-green-800' : 
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {doc.type === 'file' ? 'File' : doc.type === 'link' ? 'Link' : 'Text'}
                      </span>
                    </div>
                    {doc.description && (
                      <p className="mt-2 text-sm text-gray-600">{doc.description}</p>
                    )}
                    <div className="mt-3 flex items-center space-x-4 text-sm text-gray-500">
                      {doc.type === 'file' && doc.file_url && (
                        <span className="flex items-center">
                          <FileText className="h-4 w-4 mr-1" />
                          {mediaApi.decodeFileName(doc.file_url)}
                        </span>
                      )}
                      {doc.type === 'link' && doc.link_url && (
                        <span className="flex items-center">
                          <LinkIcon className="h-4 w-4 mr-1" />
                          {doc.link_url}
                        </span>
                      )}
                      {doc.type === 'text' && doc.content && (
                        <span className="flex items-center">
                          <FileText className="h-4 w-4 mr-1" />
                          Rich text content ({doc.content.length} characters)
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex space-x-2">
                    <button
                      onClick={() => handleDuplicate(doc)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                      title="Duplicate"
                    >
                      <Copy className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => {
                        setEditingDoc(doc)
                        setShowModal(true)
                      }}
                      className="p-2 text-gray-600 hover:bg-gray-50 rounded"
                      title="Edit"
                    >
                      <Edit className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm({ isOpen: true, docId: doc.id })}
                      className="p-2 text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="px-6 py-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No documentations</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new documentation.</p>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <DocumentationModal
          documentation={editingDoc}
          onClose={() => {
            setShowModal(false)
            setEditingDoc(null)
          }}
          onSave={(data) => {
            if (editingDoc && editingDoc.id) {
              updateMutation.mutate({ id: editingDoc.id, data })
            } else {
              createMutation.mutate(data)
            }
          }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={deleteConfirm.isOpen}
        title="Delete Documentation"
        message="Are you sure you want to delete this documentation? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => {
          if (deleteConfirm.docId) {
            deleteMutation.mutate(deleteConfirm.docId)
          }
          setDeleteConfirm({ isOpen: false, docId: null })
        }}
        onCancel={() => setDeleteConfirm({ isOpen: false, docId: null })}
      />
    </div>
  )
}

function DocumentationModal({
  documentation,
  onClose,
  onSave,
  isLoading,
}: {
  documentation: Documentation | null
  onClose: () => void
  onSave: (data: DocumentationCreate) => void
  isLoading: boolean
}) {
  const [name, setName] = useState(documentation?.name || '')
  const [description, setDescription] = useState(documentation?.description || '')
  const [type, setType] = useState<'file' | 'link' | 'text'>(documentation?.type || 'file')
  const [fileUrl, setFileUrl] = useState(documentation?.file_url || '')
  const [linkUrl, setLinkUrl] = useState(documentation?.link_url || '')
  const [content, setContent] = useState(documentation?.content || '')
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const result = await documentationsApi.uploadFile(file)
      setFileUrl(result.file_url)
    } catch (error) {
      alert('Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    if (type === 'file' && !fileUrl) {
      alert('Please upload a file or provide a file URL')
      return
    }
    if (type === 'link' && !linkUrl) {
      alert('Please provide a link URL')
      return
    }
    if (type === 'text' && !content.trim()) {
      alert('Please provide content')
      return
    }

    onSave({
      name: name.trim(),
      description: description.trim() || undefined,
      type,
      file_url: type === 'file' ? fileUrl : undefined,
      link_url: type === 'link' ? linkUrl : undefined,
      content: type === 'text' ? content : undefined,
    })
  }

  const formValid = name.trim() && (
    (type === 'file' && fileUrl) || 
    (type === 'link' && linkUrl) || 
    (type === 'text' && content.trim())
  )

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white max-h-[90vh] flex flex-col">
        {/* Sticky Header */}
        <div className="flex justify-between items-center mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
          <h3 className="text-lg font-medium text-gray-900">
            {documentation && documentation.id ? 'Edit Documentation' : 'Create New Documentation'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 flex-1 overflow-y-auto">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <span className={`text-xs font-medium ${description.length > 120 ? 'text-red-600' : description.length > 96 ? 'text-yellow-600' : 'text-gray-500'}`}>
                {120 - description.length} characters remaining
              </span>
            </div>
            <textarea
              value={description}
              onChange={(e) => {
                if (e.target.value.length <= 120) {
                  setDescription(e.target.value)
                }
              }}
              rows={3}
              maxLength={120}
              className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                description.length > 120 ? 'border-red-300' : description.length > 96 ? 'border-yellow-300' : 'border-gray-300'
              }`}
            />
            {description.length >= 120 && (
              <p className="mt-1 text-xs text-red-600 font-medium">
                Character limit reached (120 characters)
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
            <select
              value={type}
              onChange={(e) => {
                setType(e.target.value as 'file' | 'link' | 'text')
                setFileUrl('')
                setLinkUrl('')
                setContent('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="file">File Upload</option>
              <option value="link">External Link</option>
              <option value="text">Rich Text Content</option>
            </select>
          </div>

          {type === 'file' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">File *</label>
              <div className="space-y-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {uploading ? 'Uploading...' : 'Choose File'}
                </button>
                {fileUrl && (
                  <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <a
                      href={mediaApi.encodeFileUrl(fileUrl)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-800 hover:underline flex items-center"
                    >
                      <FileText className="h-4 w-4 mr-1" />
                      {mediaApi.decodeFileName(fileUrl)}
                    </a>
                    <button
                      type="button"
                      onClick={() => setFileUrl('')}
                      className="text-red-600 hover:text-red-700"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                )}
                <p className="text-xs text-gray-500">Or enter file URL manually:</p>
                <input
                  type="text"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://example.com/file.pdf"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : type === 'link' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Link URL *</label>
              <input
                type="url"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                required
                placeholder="https://example.com/documentation"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Content *</label>
              <RichTextEditor value={content} onChange={setContent} />
            </div>
          )}
          
          {/* Sticky Footer */}
          <div className="flex justify-end space-x-3 pt-4 border-t sticky bottom-0 bg-white mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !formValid}
              className={`px-4 py-2 border border-transparent rounded-md shadow-sm text-white disabled:opacity-50 disabled:cursor-not-allowed ${
                formValid && !isLoading 
                  ? 'bg-blue-600 hover:bg-blue-700' 
                  : 'bg-gray-400 cursor-not-allowed'
              }`}
            >
              {isLoading ? 'Saving...' : documentation && documentation.id ? 'Update Documentation' : 'Create Documentation'}
            </button>
          </div>
        </form>
      </div>
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
