// Typed client for the real Duke backend (backend/coordinator_api.py), deployed at
// https://labeelea1-labeele-duke-prod.hf.space. Only wraps endpoints that don't require
// the backend's own bespoke JWT auth (website auth is handled separately, by Supabase).
//
// Replaces lib/api-client.ts, which pointed at endpoints (`/api/agents`, `/api/train/*`)
// that don't exist on the real backend.

export const DUKE_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://labeelea1-labeele-duke-prod.hf.space'

export interface DukeAgent {
  id: string
  name: string
  category: string
  status: 'idle' | 'active' | 'training'
  reputation_multiplier: number
  success_rate: number
  total_tasks_completed: number
  balance_satoshis: number
  capabilities: string[]
  created_at: string
  last_active: string
}

export interface ModelStatus {
  status: 'ready' | 'training' | 'not_initialized'
  version: number
  accuracy: number
  training_samples: number
}

export interface LearningStatus {
  status: string
  last_training_time: string
  total_samples_trained: number
  memory_size: number
  agent_personas: string[]
  model_version: string
  validation_accuracy: number
  estimated_cost_usd: number
  total_inferences: number
  recent_loss: number
}

export interface HealthStatus {
  status: string
  service: string
}

export interface SubmitTaskRequest {
  description: string
  complexity: number
  target_agent?: string
  buyer_id?: string
}

export interface SubmitTaskResponse {
  response: string
  confidence: number
  agent_name: string
  request_id: string
  status: string
  price_satoshis: number
}

export interface DispatchRequest {
  prompt: string
  context_code?: string
  current_persona?: string
  complexity?: number
}

export interface DispatchResponse {
  assigned_agent: string
  action_type: string
  reply: string
  data: unknown
  tools_used: string[]
}

export class DukeApiError extends Error {
  constructor(message: string, public readonly cause?: unknown) {
    super(message)
    this.name = 'DukeApiError'
  }
}

// The backend's local-model + validation pipeline is genuinely slow (a real round trip can
// take 30-60s on the free HF Space tier) - status polls get a short timeout, task/dispatch
// calls get a long one. Callers should show "this can take up to a minute" copy, not a
// spinner that looks stuck.
async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 10_000): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(`${DUKE_API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
      signal: controller.signal,
    })

    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = await res.json()
        detail = body.detail || body.message || detail
      } catch {
        // response wasn't JSON; fall back to statusText
      }
      throw new DukeApiError(`Duke backend error (${res.status}): ${detail}`)
    }

    return (await res.json()) as T
  } catch (err) {
    if (err instanceof DukeApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new DukeApiError('Duke backend timed out. It can be slow to wake up - try again in a moment.', err)
    }
    throw new DukeApiError('Could not reach the Duke backend. It may be offline or waking up.', err)
  } finally {
    clearTimeout(timeout)
  }
}

export const dukeApi = {
  health: () => request<HealthStatus>('/health'),
  modelStatus: () => request<ModelStatus>('/model/status'),
  learningStatus: () => request<LearningStatus>('/learning/status'),
  listAgents: () => request<DukeAgent[]>('/agents'),

  submitTask: (body: SubmitTaskRequest) =>
    request<SubmitTaskResponse>(
      '/tasks/submit',
      { method: 'POST', body: JSON.stringify(body) },
      90_000,
    ),

  dispatch: (body: DispatchRequest) =>
    request<DispatchResponse>(
      '/agency/dispatch',
      { method: 'POST', body: JSON.stringify(body) },
      90_000,
    ),
}
