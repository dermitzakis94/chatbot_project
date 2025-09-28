// src/components/Analytics.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChatBubbleOvalLeftEllipsisIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  ArrowTrendingUpIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

const StatCard = ({ title, value, trend, icon: Icon, color = '#2563eb', loading = false }) => (
  <div className="flex items-start justify-between rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
    <div>
      <div className="text-xs sm:text-sm text-slate-500">{title}</div>
      <div className="mt-1 text-2xl sm:text-3xl font-semibold text-slate-900">
        {loading ? <div className="h-7 sm:h-8 w-24 animate-pulse rounded bg-slate-200" /> : value}
      </div>
      {trend && !loading && (
        <div className="mt-2 inline-flex items-center gap-1 text-xs sm:text-sm font-medium text-emerald-600">
          <ArrowTrendingUpIcon className="h-4 w-4" />
          <span>{trend}</span>
        </div>
      )}
      {loading && <div className="mt-3 h-3 sm:h-4 w-36 animate-pulse rounded bg-slate-200" />}
    </div>
    <div className="ml-3 sm:ml-4 grid h-9 w-9 sm:h-10 sm:w-10 place-items-center rounded-full bg-slate-50" style={{ color }}>
      <Icon className="h-5 w-5 sm:h-6 sm:w-6" />
    </div>
  </div>
)

const Progress = ({ value = 0, color = '#3b82f6' }) => (
  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
    <div
      className="h-full rounded-full"
      style={{ width: `${Math.max(0, Math.min(100, value))}%`, backgroundColor: color }}
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      role="progressbar"
    />
  </div>
)

const Dot = ({ color = '#16a34a' }) => (
  <span className="mt-1 inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
)

export default function Analytics({
  endpoint = import.meta?.env?.VITE_ANALYTICS_URL || '/api/analytics',
  headers = {},
  refreshMs = 60000,
  autoRefreshDefault = true,
}) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(autoRefreshDefault)
  const abortRef = useRef(null)

  const fetchData = async () => {
    setError('')
    setLoading(prev => !data || prev)
    try {
      abortRef.current?.abort?.()
      const ctrl = new AbortController()
      abortRef.current = ctrl
      const res = await fetch(endpoint, { headers, signal: ctrl.signal })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(json)
      setLastUpdated(new Date())
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message || 'Network error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    return () => abortRef.current?.abort?.()
  }, [endpoint])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(fetchData, refreshMs)
    return () => clearInterval(id)
  }, [autoRefresh, refreshMs, endpoint, JSON.stringify(headers)])

  const { stats, intents, activity } = useMemo(() => {
    const s = data?.stats || {}
    return {
      stats: {
        totalChats: { value: s.totalChats?.value ?? s.totalChats ?? '—', trend: s.totalChats?.trend ?? '', icon: ChatBubbleOvalLeftEllipsisIcon, color: '#2563eb' },
        avgResponseTime: { value: s.avgResponseTime?.value ?? s.avgResponseTime ?? '—', trend: s.avgResponseTime?.trend ?? '', icon: ChartBarIcon, color: '#16a34a' },
        deflectionRate: { value: s.deflectionRate?.value ?? s.deflectionRate ?? '—', trend: s.deflectionRate?.trend ?? '', icon: ShieldCheckIcon, color: '#8b5cf6' },
        satisfaction: { value: s.satisfaction?.value ?? s.satisfaction ?? '—', trend: s.satisfaction?.trend ?? '', icon: UserGroupIcon, color: '#d97706' },
      },
      intents: Array.isArray(data?.intents) ? data.intents : [],
      activity: Array.isArray(data?.activity) ? data.activity : [],
    }
  }, [data])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200 p-4 md:p-6">
        <h2 className="text-xl md:text-2xl font-semibold text-slate-900">{t('analytics.title')}</h2>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-500">
              {t('analytics.lastUpdated', { time: lastUpdated.toLocaleTimeString() })}
            </span>
          )}
          <label className="flex cursor-pointer select-none items-center gap-2 text-xs sm:text-sm text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            {t('analytics.autoRefresh')}
          </label>
          <button
            type="button"
            onClick={fetchData}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs sm:text-sm font-medium text-slate-700 hover:bg-slate-50"
            disabled={loading}
          >
            <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {t('analytics.refresh')}
          </button>
        </div>
      </div>

      <div className="max-h-[70vh] md:max-h-[72vh] overflow-y-auto p-4 md:p-6">
        {error && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {t('analytics.error', { error })}
          </div>
        )}

        <div className="grid gap-4 sm:gap-5 md:grid-cols-2">
          <StatCard title={t('analytics.stats.totalChats')} value={stats.totalChats.value} trend={stats.totalChats.trend} icon={stats.totalChats.icon} color={stats.totalChats.color} loading={loading && !data} />
          <StatCard title={t('analytics.stats.avgResponseTime')} value={stats.avgResponseTime.value} trend={stats.avgResponseTime.trend} icon={stats.avgResponseTime.icon} color={stats.avgResponseTime.color} loading={loading && !data} />
          <StatCard title={t('analytics.stats.deflectionRate')} value={stats.deflectionRate.value} trend={stats.deflectionRate.trend} icon={stats.deflectionRate.icon} color={stats.deflectionRate.color} loading={loading && !data} />
          <StatCard title={t('analytics.stats.satisfaction')} value={stats.satisfaction.value} trend={stats.satisfaction.trend} icon={stats.satisfaction.icon} color={stats.satisfaction.color} loading={loading && !data} />
        </div>

        <div className="mt-6 sm:mt-8 grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 p-4 sm:p-5">
            <div className="mb-3 sm:mb-4 text-base sm:text-lg font-semibold text-slate-900">{t('analytics.intents.title')}</div>
            {loading && !data ? (
              <div className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="space-y-2">
                    <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
                    <div className="h-2 w-full animate-pulse rounded-full bg-slate-200" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {intents.map((it, idx) => (
                  <div key={idx} className="flex items-center gap-3 sm:gap-4">
                    <div className="flex-1">
                      <div className="text-sm sm:text-base text-slate-700">{it.label}</div>
                      <div className="mt-2">
                        <Progress value={it.value} color={it.color || '#3b82f6'} />
                      </div>
                    </div>
                    <div className="w-10 sm:w-12 text-right text-sm sm:text-base font-medium text-slate-900">
                      {typeof it.value === 'number' ? `${it.value}%` : it.value}
                    </div>
                  </div>
                ))}
                {(!intents || intents.length === 0) && (<div className="text-sm text-slate-500">{t('analytics.intents.noData')}</div>)}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-200 p-4 sm:p-5">
            <div className="mb-3 sm:mb-4 text-base sm:text-lg font-semibold text-slate-900">{t('analytics.activity.title')}</div>
            {loading && !data ? (
              <ul className="space-y-4">
                {[...Array(4)].map((_, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className="mt-1 h-2.5 w-2.5 animate-pulse rounded-full bg-slate-200" />
                    <div className="space-y-2">
                      <div className="h-4 w-64 animate-pulse rounded bg-slate-200" />
                      <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <ul className="space-y-4">
                {activity.map((a, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <Dot color={a.color} />
                    <div>
                      <div className="text-sm sm:text-base text-slate-800">{a.text}</div>
                      <div className="text-[11px] sm:text-xs text-slate-500">{a.time}</div>
                    </div>
                  </li>
                ))}
                {(!activity || activity.length === 0) && (<div className="text-sm text-slate-500">{t('analytics.activity.noData')}</div>)}
              </ul>
            )}
          </div>
        </div>
        <div className="h-2" />
      </div>
    </div>
  )
}
