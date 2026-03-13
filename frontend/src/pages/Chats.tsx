import { useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatApi, ChatListItem, ChatMessage } from '../api/chat'
import { MessageCircle, Send, RefreshCw, CheckCheck, Check } from 'lucide-react'
import { useTimeZone } from '../contexts/TimeZoneContext'
import FeedbackButton from '../components/FeedbackButton'

function mapChatTitle(chat: ChatListItem): string {
  const ctxType = chat?.context?.type
  if (ctxType === 'DIRECT') return `Direct chat #${chat.chatId}`
  if (chat.orderId) return `Order #${chat.orderId}`
  if (chat.returnId) return `Return #${chat.returnId}`
  return `Chat #${chat.chatId}`
}

function mapAuthor(a: ChatMessage['author']) {
  if (a === 'SELLER') return 'You'
  if (a === 'CUSTOMER') return 'Customer'
  return 'System'
}

export default function Chats() {
  const { formatDateTime } = useTimeZone()
  const queryClient = useQueryClient()
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const [messageText, setMessageText] = useState('')
  const [chatFilter, setChatFilter] = useState<'all' | 'orders' | 'direct' | 'returns'>('all')
  const [listPage, setListPage] = useState(0)
  const messagesScrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)
  const initialAutoScrollDoneRef = useRef(false)
  const openedLastSeenRef = useRef<string | null>(null)
  const autoMarkedOrderIdsRef = useRef<Record<string, boolean>>({})

  const getLastSeenForChat = (chat: ChatListItem): string | null => {
    if (chat.orderId != null) {
      const v = localStorage.getItem(`order_chat_last_seen_${chat.orderId}`)
      if (v) return v
    }
    return localStorage.getItem(`chat_last_seen_${chat.chatId}`)
  }

  const setLastSeenForChat = (chat: ChatListItem, iso: string) => {
    localStorage.setItem(`chat_last_seen_${chat.chatId}`, iso)
    if (chat.orderId != null) localStorage.setItem(`order_chat_last_seen_${chat.orderId}`, iso)
  }

  const chatsPageSize = 15
  const {
    data: chatsPages,
    isFetching: isFetchingChats,
    refetch: refetchChats,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['chats', 'list', chatsPageSize],
    queryFn: ({ pageParam }) => chatApi.listChats(chatsPageSize, pageParam as string | undefined),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage?.nextPageToken ?? undefined,
    placeholderData: (prev) => prev,
  })

  const chats = useMemo(() => {
    const pages = chatsPages?.pages ?? []
    return pages.flatMap((p) => p?.chats ?? [])
  }, [chatsPages])

  const filteredChats = useMemo(() => {
    if (chatFilter === 'all') return chats
    return chats.filter((c) => {
      const ctxType = c?.context?.type
      const isOrder = c.orderId != null || ctxType === 'ORDER'
      const isReturn = c.returnId != null || ctxType === 'RETURN'
      const isDirect = ctxType === 'DIRECT' || (!isOrder && !isReturn)
      if (chatFilter === 'orders') return isOrder
      if (chatFilter === 'returns') return isReturn
      return isDirect
    })
  }, [chats, chatFilter])

  useEffect(() => {
    setListPage(0)
  }, [chatFilter])

  const visibleChats = useMemo(() => {
    const start = listPage * chatsPageSize
    return filteredChats.slice(start, start + chatsPageSize)
  }, [filteredChats, listPage])

  const { data: messagesData, isFetching: isFetchingMessages, isLoading: isLoadingMessages } = useQuery({
    queryKey: ['chats', 'messages', selectedChatId],
    queryFn: () => chatApi.getChatMessages(selectedChatId as number, 100),
    enabled: selectedChatId != null,
    refetchInterval: 5000,
    placeholderData: (prev) => prev,
  })

  const messages = messagesData?.messages ?? []

  useEffect(() => {
    if (!selectedChatId) {
      initialAutoScrollDoneRef.current = false
      return
    }
    const el = messagesScrollRef.current
    if (!el) return

    // Initial load: scroll to bottom once
    if (!initialAutoScrollDoneRef.current && messages.length > 0) {
      const lastSeen = openedLastSeenRef.current
      let didScrollToUnread = false
      if (lastSeen) {
        const lastSeenMs = new Date(lastSeen).getTime()
        if (!Number.isNaN(lastSeenMs)) {
          const firstUnread = messages.find((m) => {
            if (!m.created_at) return false
            const ms = new Date(m.created_at).getTime()
            return !Number.isNaN(ms) && ms > lastSeenMs
          })
          if (firstUnread) {
            const node = el.querySelector(`[data-message-id="${firstUnread.id}"]`) as HTMLElement | null
            if (node) {
              node.scrollIntoView({ block: 'center' })
              didScrollToUnread = true
            }
          }
        }
      }

      if (!didScrollToUnread) {
        el.scrollTop = el.scrollHeight
      }
      initialAutoScrollDoneRef.current = true
      return
    }

    // New messages: only stick if user is near bottom
    if (stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight
    }
  }, [selectedChatId, messages.length])

  const sendMutation = useMutation({
    mutationFn: (payload: { chatId: number; text: string }) => chatApi.sendChatMessage(payload.chatId, payload.text),
    onSuccess: () => {
      setMessageText('')
      queryClient.invalidateQueries({ queryKey: ['chats', 'messages', selectedChatId] })
      queryClient.invalidateQueries({ queryKey: ['chats', 'list'] })
    },
  })

  const selectedChat = chats.find((c) => c.chatId === selectedChatId) ?? null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Chats</h1>
          <p className="text-gray-600 mt-1">All customer chats</p>
        </div>
        <button
          onClick={() => refetchChats()}
          className="inline-flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetchingChats ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-3">
          {/* Chat list */}
          <div className="border-b lg:border-b-0 lg:border-r border-gray-200">
            <div className="p-4 border-b border-gray-200 flex items-center gap-2">
              <MessageCircle className="h-5 w-5 text-gray-600" />
              <h2 className="text-sm font-semibold text-gray-900">Chats</h2>
            </div>
            <div className="p-3 border-b border-gray-200 bg-white">
              <div className="inline-flex rounded-md border border-gray-200 overflow-hidden text-xs">
                {([
                  { id: 'all', label: 'All' },
                  { id: 'orders', label: 'Orders' },
                  { id: 'direct', label: 'Direct' },
                  { id: 'returns', label: 'Returns' },
                ] as const).map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setChatFilter(opt.id)}
                    className={`px-3 py-1.5 font-medium ${
                      chatFilter === opt.id ? 'bg-blue-50 text-blue-700' : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-[70vh] overflow-y-auto">
              {filteredChats.length === 0 ? (
                <div className="p-4 text-sm text-gray-500">No chats found.</div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {visibleChats.map((chat) => {
                    const isActive = chat.chatId === selectedChatId
                    const status = chat.status
                    const updatedAt = chat.updatedAt || chat.createdAt
                    const isUnread = (() => {
                      if (!updatedAt) return false
                      const lastSeen = getLastSeenForChat(chat)
                      if (!lastSeen) return true
                      const u = new Date(updatedAt).getTime()
                      const s = new Date(lastSeen).getTime()
                      if (Number.isNaN(u) || Number.isNaN(s)) return false
                      return u > s
                    })()

                    const markThisAsRead = async () => {
                      const fallback = updatedAt || new Date().toISOString()
                      setLastSeenForChat(chat, fallback)
                      if (chat.orderId != null) {
                        const orderKey = String(chat.orderId)
                        queryClient.setQueryData(['order-chat-unread', orderKey], 0)
                        await chatApi.markAsRead(orderKey)
                        queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderKey] })
                      }
                      queryClient.invalidateQueries({ queryKey: ['chats', 'list'] })
                    }
                    return (
                      <li key={chat.chatId}>
                        <div
                          className={`w-full px-4 py-3 hover:bg-gray-50 flex items-start justify-between gap-2 ${
                            isActive ? 'bg-blue-50' : ''
                          }`}
                        >
                          <button
                            type="button"
                            onClick={() => {
                              openedLastSeenRef.current = getLastSeenForChat(chat)
                              initialAutoScrollDoneRef.current = false
                              autoMarkedOrderIdsRef.current = {}
                              setSelectedChatId(chat.chatId)
                            }}
                            className="flex-1 min-w-0 text-left"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              {isUnread && <span className="h-2.5 w-2.5 rounded-full bg-red-500 shrink-0" aria-label="Unread" />}
                              <div className="font-medium text-sm text-gray-900 truncate">{mapChatTitle(chat)}</div>
                            </div>
                            {updatedAt && (
                              <div className="text-xs text-gray-500 mt-1">
                                Updated: {formatDateTime(updatedAt)}
                              </div>
                            )}
                          </button>

                          <div className="shrink-0 flex items-center gap-2">
                            {isUnread && (
                              <FeedbackButton
                                onAction={markThisAsRead}
                                title="Mark as read"
                                label="Mark as read"
                                successLabel="Marked"
                                className="inline-flex items-center justify-center rounded-md border border-gray-200 bg-white px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                                successClassName="border-green-300 bg-green-50 text-green-800 hover:bg-green-100"
                                successChildren={<Check className="h-4 w-4" />}
                              >
                                <CheckCheck className="h-4 w-4" />
                              </FeedbackButton>
                            )}
                            <span
                              className={`text-[11px] px-2 py-0.5 rounded-full ${
                                status === 'WAITING_FOR_PARTNER' || status === 'NEW'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : status === 'FINISHED'
                                    ? 'bg-gray-100 text-gray-700'
                                    : 'bg-blue-100 text-blue-800'
                              }`}
                            >
                              {status}
                            </span>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            <div className="p-3 border-t border-gray-200 bg-white flex items-center justify-between gap-3">
              <div className="text-xs text-gray-600">
                Page <span className="font-semibold">{listPage + 1}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setListPage((p) => Math.max(0, p - 1))}
                  disabled={listPage === 0}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    const nextStart = (listPage + 1) * chatsPageSize
                    if (nextStart < filteredChats.length) {
                      setListPage((p) => p + 1)
                      return
                    }
                    if (hasNextPage) {
                      await fetchNextPage()
                      setListPage((p) => p + 1)
                    }
                  }}
                  disabled={isFetchingNextPage || (!hasNextPage && (listPage + 1) * chatsPageSize >= filteredChats.length)}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  {isFetchingNextPage ? 'Loading…' : 'Next'}
                </button>
              </div>
            </div>
            </div>
          </div>

          {/* Chat details */}
          <div className="lg:col-span-2">
            <div className="p-4 border-b border-gray-200">
              <div className="text-sm font-semibold text-gray-900">
                {selectedChat ? mapChatTitle(selectedChat) : 'Select a chat'}
              </div>
              {selectedChat?.context?.customer?.name && (
                <div className="text-xs text-gray-500 mt-1">Customer: {selectedChat.context.customer.name}</div>
              )}
              {selectedChatId != null && isFetchingMessages && (
                <div className="text-xs text-gray-400 mt-1">Refreshing…</div>
              )}
            </div>

            <div
              ref={messagesScrollRef}
              onScroll={() => {
                const el = messagesScrollRef.current
                if (!el) return
                const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
                stickToBottomRef.current = distanceFromBottom < 120
                if (distanceFromBottom < 30 && selectedChatId != null && messages.length > 0) {
                  // Auto-mark as read only when user actually reaches bottom.
                  const latest = [...messages]
                    .map((m) => m.created_at)
                    .filter(Boolean)
                    .sort()
                    .slice(-1)[0] as string | undefined
                  if (latest && selectedChat) {
                    setLastSeenForChat(selectedChat, latest)
                    queryClient.invalidateQueries({ queryKey: ['chats', 'list'] })
                    if (selectedChat.orderId != null) {
                      const orderKey = String(selectedChat.orderId)
                      if (!autoMarkedOrderIdsRef.current[orderKey]) {
                        autoMarkedOrderIdsRef.current[orderKey] = true
                      queryClient.setQueryData(['order-chat-unread', orderKey], 0)
                        chatApi
                          .markAsRead(orderKey)
                          .then(() => queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderKey] }))
                          .catch(() => queryClient.refetchQueries({ queryKey: ['order-chat-unread', orderKey] }))
                      }
                    }
                  }
                }
              }}
              className="p-4 space-y-3 max-h-[55vh] overflow-y-auto bg-gray-50"
            >
              {selectedChatId == null ? (
                <div className="text-sm text-gray-500 py-10 text-center">Choose a chat on the left.</div>
              ) : isLoadingMessages && messages.length === 0 ? (
                <div className="text-sm text-gray-500">Loading messages…</div>
              ) : messages.length === 0 ? (
                <div className="text-sm text-gray-500">No messages yet.</div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    data-message-id={m.id}
                    className={`flex ${m.author === 'SELLER' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-4 py-2 text-sm break-words whitespace-pre-wrap ${
                        m.author === 'SELLER'
                          ? 'bg-blue-600 text-white'
                          : m.author === 'CUSTOMER'
                            ? 'bg-white text-gray-900 border border-gray-200'
                            : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      <div className="text-[11px] opacity-75 mb-1">{mapAuthor(m.author)}</div>
                      <div>{m.text}</div>
                      {m.created_at && (
                        <div className="text-[11px] opacity-75 mt-1">
                          {formatDateTime(m.created_at)}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-gray-200">
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  if (!selectedChatId) return
                  const text = messageText.trim()
                  if (!text) return
                  sendMutation.mutate({ chatId: selectedChatId, text })
                }}
                className="flex gap-2"
              >
                <input
                  type="text"
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  placeholder={selectedChatId ? 'Type a message…' : 'Select a chat first…'}
                  disabled={!selectedChatId || sendMutation.isPending}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                />
                <button
                  type="submit"
                  disabled={!selectedChatId || !messageText.trim() || sendMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                  title="Send"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
              {isFetchingMessages && selectedChatId && (
                <div className="text-xs text-gray-500 mt-2">Refreshing…</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

