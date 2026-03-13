import { useEffect, useRef, useState } from 'react'

type State = 'idle' | 'success' | 'error'

export default function FeedbackButton({
  onAction,
  title,
  label,
  successLabel = 'Done',
  errorLabel = 'Failed',
  className,
  disabled,
  successClassName = 'bg-green-100 text-green-800 hover:bg-green-200',
  errorClassName = 'bg-red-100 text-red-800 hover:bg-red-200',
  resetMs = 1200,
  children,
  successChildren,
  errorChildren,
}: {
  onAction: () => void | Promise<void>
  title?: string
  label?: string
  successLabel?: string
  errorLabel?: string
  className: string
  disabled?: boolean
  successClassName?: string
  errorClassName?: string
  resetMs?: number
  children: React.ReactNode
  successChildren?: React.ReactNode
  errorChildren?: React.ReactNode
}) {
  const [state, setState] = useState<State>('idle')
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [])

  const run = async () => {
    try {
      await onAction()
      setState('success')
    } catch {
      setState('error')
    }

    if (timerRef.current) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => setState('idle'), resetMs)
  }

  const isSuccess = state === 'success'
  const isError = state === 'error'

  return (
    <button
      type="button"
      onClick={run}
      disabled={disabled}
      className={[
        className,
        isSuccess ? successClassName : '',
        isError ? errorClassName : '',
      ]
        .filter(Boolean)
        .join(' ')}
      title={isSuccess ? successLabel : isError ? errorLabel : title}
      aria-label={isSuccess ? successLabel : isError ? errorLabel : label || title}
    >
      {isSuccess ? (successChildren ?? children) : isError ? (errorChildren ?? children) : children}
    </button>
  )
}

