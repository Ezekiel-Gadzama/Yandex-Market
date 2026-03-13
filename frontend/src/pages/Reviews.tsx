import { useMemo, useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Star, MessageSquareText, RefreshCw, Search } from 'lucide-react'
import { reviewsApi } from '../api/reviews'
import { productsApi } from '../api/products'
import { useTimeZone } from '../contexts/TimeZoneContext'
import CopyButton from '../components/CopyButton'

type Tab = 'shop' | 'product'

function getRating(review: any): number {
  const r = review?.rating ?? review?.grade ?? review?.stars
  const n = typeof r === 'number' ? r : Number(r)
  return Number.isFinite(n) ? n : 0
}

function extractStructuredTextFromPythonDictString(text: string): { advantages?: string; disadvantages?: string; comment?: string } | null {
  if (!text || typeof text !== 'string') return null
  const t = text.trim()
  if (!t.startsWith('{')) return null
  if (!t.includes('advantages') && !t.includes('comment') && !t.includes('disadvantages')) return null

  const grab = (key: 'advantages' | 'disadvantages' | 'comment') => {
    // matches: 'key': 'value' OR "key": "value"
    const re = new RegExp(String.raw`['"]${key}['"]\s*:\s*['"]([^'"]*)['"]`)
    const m = t.match(re)
    return m?.[1]?.trim() || undefined
  }

  return {
    advantages: grab('advantages'),
    disadvantages: grab('disadvantages'),
    comment: grab('comment'),
  }
}

function getTextParts(review: any): { advantages?: string; disadvantages?: string; comment?: string; raw?: string } {
  const text = review?.text
  if (typeof text === 'string' && text.trim()) {
    const structured = extractStructuredTextFromPythonDictString(text)
    if (structured && (structured.advantages || structured.disadvantages || structured.comment)) return structured
    return { raw: text }
  }

  const desc = review?.description
  if (desc && typeof desc === 'object') {
    const advantages = typeof desc.advantages === 'string' ? desc.advantages : undefined
    const disadvantages = typeof desc.disadvantages === 'string' ? desc.disadvantages : undefined
    const comment = typeof desc.comment === 'string' ? desc.comment : undefined
    if (advantages || disadvantages || comment) return { advantages, disadvantages, comment }
  }
  if (typeof desc === 'string' && desc.trim()) {
    const structured = extractStructuredTextFromPythonDictString(desc)
    if (structured && (structured.advantages || structured.disadvantages || structured.comment)) return structured
    return { raw: desc }
  }

  const comment = review?.comment
  if (typeof comment === 'string' && comment.trim()) return { raw: comment }

  return {}
}

function getAuthorName(review: any): string {
  return review?.author?.name ?? review?.authorName ?? review?.user?.name ?? 'Anonymous'
}

function getCreatedAt(review: any): string | undefined {
  return review?.created_at ?? review?.createdAt ?? review?.created ?? review?.date
}

function Stars({ value }: { value: number }) {
  const v = Math.max(0, Math.min(5, Math.round(value)))
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 5 }).map((_, idx) => (
        <Star
          key={idx}
          className={`h-4 w-4 ${idx < v ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'}`}
        />
      ))}
    </div>
  )
}

function RatingPill({ value }: { value: number }) {
  const v = Math.max(0, Math.min(5, Math.round(Number(value) || 0)))
  return (
    <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded-full">
      {v}/5
    </span>
  )
}

export default function Reviews() {
  const { formatDateTime } = useTimeZone()
  const [tab, setTab] = useState<Tab>('shop')
  const [productId, setProductId] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 15
  const [productSearchTerm, setProductSearchTerm] = useState('')
  const [showProductDropdown, setShowProductDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const buildCopyText = (textParts: { advantages?: string; disadvantages?: string; comment?: string; raw?: string }) => {
    return (
      textParts.raw ||
      [
        textParts.advantages ? `Advantages: ${textParts.advantages}` : '',
        textParts.disadvantages ? `Disadvantages: ${textParts.disadvantages}` : '',
        textParts.comment ? `Comment: ${textParts.comment}` : '',
      ]
        .filter(Boolean)
        .join('\n')
    )
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowProductDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch products for search
  const { data: products = [] } = useQuery({
    queryKey: ['products', productSearchTerm],
    queryFn: () => productsApi.getAll({ search: productSearchTerm || undefined }),
    enabled: tab === 'product' && productSearchTerm.length > 0,
  })

  useEffect(() => {
    setPage(0)
  }, [tab, productId])

  const queryKey = useMemo(() => ['reviews', tab, productId, page, pageSize], [tab, productId, page, pageSize])

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey,
    queryFn: async () => {
      // Yandex reviews endpoints don't expose reliable page tokens in our current integration,
      // so we emulate paging by increasing limit.
      const limit = (page + 1) * pageSize
      if (tab === 'shop') return await reviewsApi.getShopReviews(limit)
      return await reviewsApi.getProductReviews(productId || undefined, limit)
    },
  })

  const reviewsAll = (data as any)?.reviews ?? []
  const reviews = reviewsAll.slice(page * pageSize, page * pageSize + pageSize)
  const average = (data as any)?.average_rating ?? 0
  const total = (data as any)?.total_reviews ?? 0
  const breakdown = (data as any)?.rating_breakdown ?? {}

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Reviews</h1>
          <p className="text-gray-600 mt-1">Pulled from Yandex Market API</p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col md:flex-row md:items-end gap-4">
          <div className="flex gap-2">
            <button
              onClick={() => setTab('shop')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                tab === 'shop' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              Shop reviews
            </button>
            <button
              onClick={() => setTab('product')}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                tab === 'product' ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              Product reviews
            </button>
          </div>

          {tab === 'product' && (
            <div className="flex-1 relative" ref={dropdownRef}>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product (Search by name or ID)</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  value={productSearchTerm}
                  onChange={(e) => {
                    setProductSearchTerm(e.target.value)
                    setShowProductDropdown(e.target.value.length > 0)
                    if (e.target.value.length === 0) {
                      setProductId('')
                    }
                  }}
                  onFocus={() => setShowProductDropdown(productSearchTerm.length > 0)}
                  placeholder="Search by product name or ID..."
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {showProductDropdown && products.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                    {products.map((product) => (
                      <button
                        key={product.id}
                        type="button"
                        onClick={() => {
                          setProductId(product.yandex_market_id || product.id.toString())
                          setProductSearchTerm(product.name)
                          setShowProductDropdown(false)
                        }}
                        className="w-full text-left px-4 py-2 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none"
                      >
                        <div className="text-sm font-medium text-gray-900">{product.name}</div>
                        <div className="text-xs text-gray-500">ID: {product.id} {product.yandex_market_id && `| Yandex ID: ${product.yandex_market_id}`}</div>
                      </button>
                    ))}
                  </div>
                )}
                {showProductDropdown && productSearchTerm.length > 0 && products.length === 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-4 text-sm text-gray-500">
                    No products found
                  </div>
                )}
              </div>
              {productId && (
                <p className="mt-1 text-xs text-gray-500">
                  Selected: {products.find(p => (p.yandex_market_id || p.id.toString()) === productId)?.name || `ID: ${productId}`}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Leave empty to fetch latest reviews
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Pagination */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="text-sm text-gray-600">
          Page <span className="font-semibold">{page + 1}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isFetching}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((p) => p + 1)}
            disabled={isFetching || reviewsAll.length < (page + 1) * pageSize}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Average rating</div>
          <div className="mt-2 flex items-center gap-3">
            <div className="text-2xl font-bold text-gray-900">{Number(average).toFixed(2)}</div>
            <Stars value={Number(average)} />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total reviews</div>
          <div className="mt-2 text-2xl font-bold text-gray-900">{total}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Rating breakdown</div>
          <div className="mt-2 space-y-1">
            {[5, 4, 3, 2, 1].map((k) => (
              <div key={k} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-4 text-gray-700">{k}</span>
                  <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                </div>
                <span className="text-gray-900 font-medium">{(breakdown as any)?.[k] ?? 0}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <MessageSquareText className="h-5 w-5 text-gray-600" />
          <h2 className="text-lg font-semibold text-gray-900">Latest</h2>
        </div>

        {isLoading ? (
          <div className="p-6 text-gray-600">Loading reviews…</div>
        ) : error ? (
          <div className="p-6 text-gray-500 text-center">
            Reviews are not available at this time.
          </div>
        ) : reviews.length === 0 ? (
          <div className="p-6 text-gray-600">No reviews found.</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {reviews.map((r: any) => {
              const rating = getRating(r)
              const textParts = getTextParts(r)
              const author = getAuthorName(r)
              const created = formatDateTime(getCreatedAt(r))
              const copyText = buildCopyText(textParts)
              return (
                <div
                  key={r?.id ?? `${author}-${created}-${String(rating)}-${(textParts.raw ?? '').slice(0, 20)}`}
                  className="p-6"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3">
                        <Stars value={rating} />
                        <RatingPill value={rating} />
                        <div className="text-sm text-gray-700 font-medium">{author}</div>
                        {created && <div className="text-sm text-gray-500">{String(created)}</div>}
                      </div>
                      <div className="mt-3 text-gray-900 space-y-2">
                        {(textParts.advantages || textParts.disadvantages || textParts.comment) ? (
                          <>
                            {textParts.advantages && (
                              <div className="text-sm">
                                <div className="text-xs font-semibold text-gray-600 mb-0.5">Advantages</div>
                                <div className="whitespace-pre-wrap break-words">{textParts.advantages}</div>
                              </div>
                            )}
                            {textParts.disadvantages && (
                              <div className="text-sm">
                                <div className="text-xs font-semibold text-gray-600 mb-0.5">Disadvantages</div>
                                <div className="whitespace-pre-wrap break-words">{textParts.disadvantages}</div>
                              </div>
                            )}
                            {textParts.comment && (
                              <div className="text-sm">
                                <div className="text-xs font-semibold text-gray-600 mb-0.5">Comment</div>
                                <div className="whitespace-pre-wrap break-words">{textParts.comment}</div>
                              </div>
                            )}
                          </>
                        ) : textParts.raw ? (
                          <div className="whitespace-pre-wrap break-words text-sm">{textParts.raw}</div>
                        ) : (
                          <span className="text-gray-500 text-sm">No review text provided.</span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {r?.id && <div className="text-sm text-gray-500">{`ID: ${r.id}`}</div>}
                      {!!copyText?.trim() && <CopyButton text={copyText} title="Copy review text" />}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

