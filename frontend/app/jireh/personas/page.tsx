'use client'

import { useEffect, useState } from 'react'
import { Loader2, Plus, Save, CheckCircle2, AlertTriangle, Circle } from 'lucide-react'
import AdminShell from '../../components/AdminShell'
import GlassCard from '../../components/GlassCard'
import { dukeApi, DukeApiError, type PersonaConfig } from '@/lib/duke-api'

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
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-3xl font-bold text-white">Personas</h1>
        <button
          onClick={startCreate}
          className="flex items-center gap-2 px-4 py-2 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" /> New persona
        </button>
      </div>
      <p className="text-gray-400 mb-8">
        Edits take effect on the next query - no redeploy needed once this backend change is live.
      </p>

      {listError && (
        <div role="alert" className="mb-6 p-4 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300 text-sm">
          {listError}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-1 h-fit">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">All personas</h2>
          {!personas ? (
            <div className="flex items-center gap-2 text-gray-400 text-sm py-4">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading&hellip;
            </div>
          ) : personas.length === 0 ? (
            <p className="text-gray-400 text-sm">None yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {personas.map((p) => (
                <li key={p.persona_id}>
                  <button
                    onClick={() => selectPersona(p)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer ${
                      selectedId === p.persona_id && !creating
                        ? 'bg-gold-500/15 text-gold-500 border border-gold-500/30'
                        : 'text-gray-300 hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Circle className={`w-2 h-2 shrink-0 ${p.is_active ? 'fill-emerald-400 text-emerald-400' : 'fill-gray-600 text-gray-600'}`} />
                      {p.name}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <GlassCard className="lg:col-span-2">
          {!creating && !selectedId ? (
            <p className="text-gray-400 text-sm">Select a persona, or create a new one.</p>
          ) : (
            <form onSubmit={handleSave} className="space-y-5">
              <h2 className="text-lg font-semibold text-white">{creating ? 'New persona' : form.name}</h2>

              {notice && (
                <div
                  role="alert"
                  className={`p-3 rounded-lg border text-sm flex items-start gap-2 ${
                    notice.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-red-500/10 border-red-500/30 text-red-300'
                  }`}
                >
                  {notice.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" /> : <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                  {notice.message}
                </div>
              )}

              {creating && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">
                    Persona ID <span className="text-gray-500 font-normal">(lowercase, hyphens only - e.g. web-developer)</span>
                  </label>
                  <input
                    type="text"
                    required
                    pattern="^[a-z0-9\-]+$"
                    value={form.persona_id}
                    onChange={(e) => setForm({ ...form, persona_id: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors font-mono text-sm"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Name</label>
                  <input
                    type="text"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/5 border border-gold-500/20 rounded-lg text-white focus:outline-none focus:border-gold-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Category</label>
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
                <label className="block text-sm font-medium text-gray-300 mb-1.5">System prompt</label>
                <textarea
                  required
                  rows={10}
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  className="w-full px-4 py-3 bg-white/5 border border-gold-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gold-500 transition-colors font-mono text-sm resize-y"
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
                className="flex items-center gap-2 px-6 py-3 bg-gold-500 text-royal-blue-900 font-semibold rounded-lg hover:bg-gold-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
