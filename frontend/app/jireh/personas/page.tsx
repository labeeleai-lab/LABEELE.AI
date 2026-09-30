'use client'

import { useEffect, useState } from 'react'
import { Loader2, Plus, Save, CheckCircle2, AlertTriangle, Users2 } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import { dukeApi, DukeApiError, type PersonaConfig } from '@/lib/duke-api'
import { EmptyState, LoadingRow, PageHeader } from '../../components/ui'

interface FormState {
  persona_id: string
  name: string
  category: string
  system_prompt: string
  temperature: number
  min_response_tokens: number
  max_response_tokens: number
  reputation_multiplier: number
  requires_validation: boolean
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  persona_id: '',
  name: '',
  category: 'specialist',
  system_prompt: '',
  temperature: 0.7,
  min_response_tokens: 200,
  max_response_tokens: 2000,
  reputation_multiplier: 1.5,
  requires_validation: true,
  is_active: true,
}

function toForm(p: PersonaConfig): FormState {
  return {
    persona_id: p.persona_id,
    name: p.name,
    category: p.category,
    system_prompt: p.system_prompt,
    temperature: p.temperature,
    min_response_tokens: p.min_response_tokens,
    max_response_tokens: p.max_response_tokens,
    reputation_multiplier: p.reputation_multiplier,
    requires_validation: p.requires_validation,
    is_active: p.is_active,
  }
}

export default function AdminPersonasPage() {
  const [personas, setPersonas] = useState<PersonaConfig[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const load = async () => {
    setListError(null)
    try {
      const data = await dukeApi.listPersonas()
      setPersonas(data)
      if (!selectedId && data.length > 0 && !creating) {
        setSelectedId(data[0].persona_id)
        setForm(toForm(data[0]))
      }
    } catch (err) {
      setListError(err instanceof DukeApiError ? err.message : 'Could not reach the Duke backend.')
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectPersona = (p: PersonaConfig) => {
    setCreating(false)
    setSelectedId(p.persona_id)
    setForm(toForm(p))
    setNotice(null)
  }

  const startCreate = () => {
    setCreating(true)
    setSelectedId(null)
    setForm(EMPTY_FORM)
    setNotice(null)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.max_response_tokens < form.min_response_tokens) {
      setNotice({ type: 'error', message: 'Max response tokens must be greater than or equal to min.' })
      return
    }

    setSaving(true)
    setNotice(null)
    try {
      if (creating) {
        const created = await dukeApi.createPersona({
          persona_id: form.persona_id,
          name: form.name,
          category: form.category,
          system_prompt: form.system_prompt,
          temperature: form.temperature,
          min_response_tokens: form.min_response_tokens,
          max_response_tokens: form.max_response_tokens,
          reputation_multiplier: form.reputation_multiplier,
          requires_validation: form.requires_validation,
        })
        setNotice({ type: 'success', message: `Persona "${created.name}" created and live.` })
        setCreating(false)
        setSelectedId(created.persona_id)
      } else if (selectedId) {
        await dukeApi.updatePersona(selectedId, {
          name: form.name,
          category: form.category,
          system_prompt: form.system_prompt,
          temperature: form.temperature,
          min_response_tokens: form.min_response_tokens,
          max_response_tokens: form.max_response_tokens,
          reputation_multiplier: form.reputation_multiplier,
          requires_validation: form.requires_validation,
          is_active: form.is_active,
        })
        setNotice({ type: 'success', message: 'Saved - takes effect on the next query.' })
      }
      await load()
    } catch (err) {
      setNotice({ type: 'error', message: err instanceof DukeApiError ? err.message : 'Failed to save.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <AdminShell>
      <PageHeader
        eyebrow="JIREH · Model"
        title="Personas"
        description="Edit how each persona thinks and speaks. Changes take effect on the very next query - no redeploy needed."
        actions={
          <button type="button" onClick={startCreate} className="btn btn-primary">
            <Plus className="w-4 h-4" aria-hidden="true" /> New persona
          </button>
        }
      />

      {listError && (
        <div role="alert" className="alert mb-6 alert-error">
          {listError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <nav aria-label="Personas" className="surface h-fit p-3 lg:col-span-1">
          <p className="px-3 pt-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-gray-500">All personas</p>
          {listError && !personas ? (
            <p className="px-3 pb-2 text-xs text-gray-500">Unavailable - see the error above.</p>
          ) : !personas ? (
            <LoadingRow label="Loading personas…" className="px-3" />
          ) : personas.length === 0 ? (
            <p className="px-3 pb-2 text-sm text-gray-400">None yet.</p>
          ) : (
            <ul className="space-y-0.5">
              {personas.map((p) => {
                const active = selectedId === p.persona_id && !creating
                return (
                  <li key={p.persona_id}>
                    <button
                      type="button"
                      onClick={() => selectPersona(p)}
                      aria-current={active ? 'true' : undefined}
                      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer ${
                        active ? 'bg-white/[0.07] font-medium text-white' : 'text-gray-400 hover:bg-white/[0.04] hover:text-gray-100'
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${p.is_active ? 'bg-emerald-400' : 'bg-gray-600'}`}
                      />
                      <span className="truncate">{p.name}</span>
                      {!p.is_active && <span className="badge badge-neutral ml-auto">Inactive</span>}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </nav>

        <GlassCard className="lg:col-span-2">
          {!creating && !selectedId ? (
            <EmptyState
              icon={Users2}
              title="No persona selected"
              description="Pick a persona on the left to edit its instructions, or create a new one."
              action={
                <button type="button" onClick={startCreate} className="btn btn-secondary btn-sm">
                  <Plus className="h-4 w-4" aria-hidden="true" /> New persona
                </button>
              }
            />
          ) : (
            <form onSubmit={handleSave} className="space-y-5">
              <h2 className="text-lg font-semibold text-white">{creating ? 'New persona' : form.name}</h2>

              {notice && (
                <div
                  role="alert"
                  className={`alert ${
                    notice.type === 'success' ? 'alert-success' : 'alert-error'
                  }`}
                >
                  {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                  {notice.message}
                </div>
              )}

              {creating && (
                <div>
                  <label className="label">
                    Persona ID <span className="text-gray-500 font-normal">(lowercase, hyphens only - e.g. web-developer)</span>
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^[a-z0-9\-]+$"
                    value={form.persona_id}
                    onChange={(e) => setForm({ ...form, persona_id: e.target.value })}
                    className="input w-full font-mono"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Name</label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white focus:outline-none focus:border-gold-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="label">Category</label>
                  <input
                    type="text"
                    required
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white focus:outline-none focus:border-gold-500 transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="label">System prompt</label>
                <textarea
                  required
                  rows={10}
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  className="input w-full font-mono resize-y"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    min={0}
                    max={2}
                    value={form.temperature}
                    onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-white/5 border border-gold-500/20 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Min tokens</label>
                  <input
                    type="number"
                    min={1}
                    value={form.min_response_tokens}
                    onChange={(e) => setForm({ ...form, min_response_tokens: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 bg-white/5 border border-gold-500/20 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Max tokens</label>
                  <input
                    type="number"
                    min={1}
                    value={form.max_response_tokens}
                    onChange={(e) => setForm({ ...form, max_response_tokens: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 bg-white/5 border border-gold-500/20 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Reputation</label>
                  <input
                    type="number"
                    step="0.05"
                    min={1}
                    max={2.5}
                    value={form.reputation_multiplier}
                    onChange={(e) => setForm({ ...form, reputation_multiplier: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-white/5 border border-gold-500/20 rounded-lg text-white text-sm focus:outline-none focus:border-gold-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.requires_validation}
                    onChange={(e) => setForm({ ...form, requires_validation: e.target.checked })}
                    className="rounded border-gold-500/30"
                  />
                  Requires validation
                </label>
                {!creating && (
                  <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.is_active}
                      onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                      className="rounded border-gold-500/30"
                    />
                    Active
                  </label>
                )}
              </div>

              <button
                type="submit"
                disabled={saving}
                className="btn btn-primary btn-lg"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {creating ? 'Create persona' : 'Save changes'}
              </button>
            </form>
          )}
        </GlassCard>
      </div>
    </AdminShell>
  )
}
