import { useEffect, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'

type CopyState = 'idle' | 'copied' | 'error'

export default function CopyButton({
  text,
  title = 'Copy',
  label = 'Copy',
  copiedLabel = 'Copied',
  className = 'inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200',
}: {
  text: string
  title?: string
  label?: string
  copiedLabel?: string
  className?: string
}) {
  const [state, setState] = useState<CopyState>('idle')
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [])

  const copy = async () => {
    const t = (text ?? '').toString()
    if (!t.trim()) return

    try {
      await navigator.clipboard.writeText(t)
      setState('copied')
    } catch {
      try {
        const textarea = document.createElement('textarea')
        textarea.value = t
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        setState('copied')
      } catch {
        setState('error')
      }
    }

    if (timerRef.current) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => setState('idle'), 1200)
  }

  const isCopied = state === 'copied'
  const isError = state === 'error'

  return (
    <button
      type="button"
      onClick={copy}
      className={[
        className,
        isCopied ? 'bg-green-100 text-green-800 hover:bg-green-200' : '',
        isError ? 'bg-red-100 text-red-800 hover:bg-red-200' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      title={isCopied ? copiedLabel : isError ? 'Copy failed' : title}
    >
      {isCopied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
      <span>{isCopied ? copiedLabel : isError ? 'Failed' : label}</span>
    </button>
  )
}

