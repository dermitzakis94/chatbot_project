// src/components/Capabilities.jsx
import React, { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

export default function Capabilities({ formData, handleInputChange, disabled = false }) {
  const { t } = useTranslation()

  const sectionTitle = 'text-lg sm:text-xl font-semibold text-slate-800'
  const groupTitle = 'text-xs sm:text-sm font-semibold text-slate-600'
  const checkboxLabel = 'text-sm sm:text-base text-slate-700 leading-tight break-words'
  const cardClasses = 'rounded-2xl border border-slate-200 bg-white p-4 md:p-6 shadow-sm'

  

  // Προσθέτουμε το feedback ως απλό toggle (χωρίς extra options panel)
  const coreFeatures = useMemo(
    () => [
      { key: 'leadCapture', label: t('features.leadCaptureForms') },
      { key: 'appointmentScheduling', label: t('features.appointmentScheduling') },
      { key: 'feedbackCollection', label: t('features.feedbackCollection') }
    ],
    [t]
  )

  const leadCaptureFields = useMemo(
    () => [
      { key: 'name', label: t('fields.name') },
      { key: 'email', label: t('fields.email') },
      { key: 'phone', label: t('fields.phone') },
      { key: 'company', label: t('fields.company') },
      { key: 'message', label: t('fields.message') },
    ],
    [t]
  )

  const core = formData?.coreFeatures || {}
  const fields = formData?.leadCaptureFields || {}
  const appointmentEnabled = !!core.appointmentScheduling//προσθήκες
  const settings = formData?.appointmentSettings || {}//προσθήκες
  const updateSetting = (key, value) => { //προσθηκες
    const next = { ...settings, [key]: value }//προσθηκες
    handleInputChange({ target: { name: 'appointmentSettings', value: next } })//προσθηκες
}

  const onToggle = (path, current) => {
    const [group, key] = path.split('.')
    const updated = { ...(formData[group] || {}), [key]: !current }
    handleInputChange({ target: { name: group, value: updated } })
  }

  const leadEnabled = !!core.leadCapture

  return (
    <div className={cardClasses}>
      <div className="mb-4 md:mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
          {t('capabilities.title')}
        </h2>
      </div>

      <div className="space-y-6 md:space-y-8">
        {/* Core features */}
        <section className="space-y-3 md:space-y-4">
          <h3 className={sectionTitle}>{t('capabilities.coreFeatures')}</h3>
          <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {coreFeatures.map(({ key, label }) => (
              <label key={key} className="inline-flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  checked={!!core[key]}
                  onChange={() => onToggle(`coreFeatures.${key}`, !!core[key])}
                  disabled={disabled}
                  aria-label={label}
                />
                <span className={checkboxLabel}>{label}</span>
              </label>
            ))}
          </div>
        </section>

        {appointmentEnabled && (   //προσθηκη
  <section className="space-y-3 md:space-y-4" aria-hidden={!appointmentEnabled}>
    <h4 className={groupTitle}>Ρυθμίσεις Ραντεβού</h4>

    <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-3">
      {/* Διάρκεια ραντεβού */}
      <label className="flex flex-col gap-1">
        <span className="text-sm text-slate-600">Διάρκεια ραντεβού</span>
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={settings.slotDuration ?? 30}
          onChange={(e) => updateSetting('slotDuration', Number(e.target.value))}
          disabled={disabled}
        >
          <option value={15}>15 λεπτά</option>
          <option value={30}>30 λεπτά</option>
          <option value={45}>45 λεπτά</option>
          <option value={60}>60 λεπτά</option>
        </select>
      </label>

      {/* Ώρα έναρξης */}
      <label className="flex flex-col gap-1">
        <span className="text-sm text-slate-600">Ώρα έναρξης</span>
        <input
          type="time"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={settings.workStart ?? '09:00'}
          onChange={(e) => updateSetting('workStart', e.target.value)}
          disabled={disabled}
        />
      </label>

      {/* Ώρα λήξης */}
      <label className="flex flex-col gap-1">
        <span className="text-sm text-slate-600">Ώρα λήξης</span>
        <input
          type="time"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={settings.workEnd ?? '17:00'}
          onChange={(e) => updateSetting('workEnd', e.target.value)}
          disabled={disabled}
        />
      </label>
    </div>

    {/* Μέρες λειτουργίας */}
    <div className="flex flex-col gap-1">
      <span className="text-sm text-slate-600">Μέρες λειτουργίας</span>
      <div className="grid grid-cols-2 gap-2 text-sm">
        {[
  {key: 'Mon', label: 'Δευ'}, 
  {key: 'Tue', label: 'Τρι'}, 
  {key: 'Wed', label: 'Τετ'}, 
  {key: 'Thu', label: 'Πεμ'}, 
  {key: 'Fri', label: 'Παρ'}, 
  {key: 'Sat', label: 'Σαβ'}, 
  {key: 'Sun', label: 'Κυρ'}
].map((day) => (
          <label key={day.key} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(settings.workDays ?? []).includes(day.key)}
              onChange={(e) => {
                const current = new Set(settings.workDays ?? [])
                if (e.target.checked) current.add(day.key)
                else current.delete(day.key)
                updateSetting('workDays', Array.from(current))
              }}
              disabled={disabled}
            />
            {day.label}
          </label>
        ))}
      </div>
    </div>
  </section>
)} 


        


        {/* Lead capture fields (εμφανίζεται μόνο αν είναι ενεργό το leadCapture) */}
        {leadEnabled && (
          <section className="space-y-3 md:space-y-4" aria-hidden={!leadEnabled}>
            <h4 className={groupTitle}>{t('capabilities.leadCaptureFields')}</h4>
            <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {leadCaptureFields.map(({ key, label }) => (
                <label key={key} className="inline-flex items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    checked={!!fields[key]}
                    onChange={() => onToggle(`leadCaptureFields.${key}`, !!fields[key])}
                    disabled={disabled}
                    aria-label={label}
                  />
                  <span className={checkboxLabel}>{label}</span>
                </label>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
