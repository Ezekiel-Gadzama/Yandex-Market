import React, { createContext, useContext, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { settingsApi } from '../api/settings'

type TimeZoneContextValue = {
  timeZone: string
  formatDateTime: (isoOrDate: string | undefined, opts?: { withSeconds?: boolean }) => string | undefined
}

const TimeZoneContext = createContext<TimeZoneContextValue | null>(null)

export function TimeZoneProvider({ children }: { children: React.ReactNode }) {
  const { data: settings } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => settingsApi.get(),
  })

  const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  const defaultYandexTz = 'Europe/Moscow'

  const isTimeZoneSupported = (tz: string) => {
    try {
      // Throws RangeError if tz is invalid/unsupported
      new Intl.DateTimeFormat(undefined, { timeZone: tz }).format(new Date())
      return true
    } catch {
      return false
    }
  }

  // Yandex timestamps are already provided in Moscow time (e.g. +03:00).
  // If user hasn't selected a timezone yet, default to Europe/Moscow instead of device timezone.
  const timeZone = settings?.timezone || (isTimeZoneSupported(defaultYandexTz) ? defaultYandexTz : localTz)

  const value = useMemo<TimeZoneContextValue>(() => {
    const formatDateTime = (isoOrDate: string | undefined, opts?: { withSeconds?: boolean }) => {
      if (!isoOrDate) return undefined
      const raw = isoOrDate.trim()

      // If it's a date-only string, show only the date (avoid timezone shifting and showing "00:00").
      if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        const [yy, mm, dd] = raw.split('-').map((x) => Number(x))
        if (Number.isFinite(yy) && Number.isFinite(mm) && Number.isFinite(dd)) {
          // Use UTC noon to avoid date rollover when formatting in different timezones.
          const dNoonUtc = new Date(Date.UTC(yy, mm - 1, dd, 12, 0, 0))
          const dateFmt = new Intl.DateTimeFormat(undefined, {
            timeZone,
            year: 'numeric',
            month: 'short',
            day: '2-digit',
          })
          return dateFmt.format(dNoonUtc)
        }
      }

      // Yandex generally returns timezone-aware ISO strings (e.g. +03:00).
      // If we ever receive a timezone-naive ISO datetime, assume it's Moscow time.
      const hasExplicitZone =
        /[zZ]$/.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw) || /[+-]\d{4}$/.test(raw)
      const normalized = !hasExplicitZone && raw.includes('T') ? `${raw}+03:00` : raw

      const d = new Date(normalized)
      if (Number.isNaN(d.getTime())) return isoOrDate
      const fmt = new Intl.DateTimeFormat(undefined, {
        timeZone,
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: opts?.withSeconds ? '2-digit' : undefined,
      })
      return fmt.format(d)
    }
    return { timeZone, formatDateTime }
  }, [timeZone])

  return <TimeZoneContext.Provider value={value}>{children}</TimeZoneContext.Provider>
}

export function useTimeZone() {
  const ctx = useContext(TimeZoneContext)
  if (!ctx) {
    const fallbackTz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
    return {
      timeZone: fallbackTz,
      formatDateTime: (isoOrDate: string | undefined) => (isoOrDate ? new Date(isoOrDate).toString() : undefined),
    }
  }
  return ctx
}

