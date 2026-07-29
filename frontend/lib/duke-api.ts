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

export interface IacStats {
  status: string
  total: number
  validated: number
}

export interface TrainingStats {
  data: {
    total_calls?: number
    estimated_cost_usd?: number
    training_samples_available?: number
    status?: string
    [key: string]: unknown
  }
}

export interface RetrainResult {
  status: 'success' | 'skipped'
  reason?: string
  model_version?: number
  epochs_run?: number
  train_samples?: number
  val_samples?: number
  validation_accuracy?: number
  best_val_loss?: number
  total_samples_considered?: number
  usable_samples?: number
  total_samples?: number
  skipped_error?: number
  skipped_short?: number
  skipped_duplicate?: number
  skipped_low_rated?: number
}

export interface DukeTask {
  id: string
  description: string
  complexity: number
  agent_name: string
  status: string
  result: string | null
  price_satoshis: number
}

export interface SubmitFeedbackRequest {
  request_id: string
  rating: number
  comment?: string
  agent_name: string
}

export interface PersonaConfig {
  persona_id: string
  name: string
  category: string
  reputation_multiplier: number
  min_response_tokens: number
  max_response_tokens: number
  temperature: number
  requires_validation: boolean
  system_prompt: string
  validation_keywords: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export type PersonaConfigCreate = {
  persona_id: string
  name: string
  system_prompt: string
} & Partial<
  Pick<
    PersonaConfig,
    'category' | 'reputation_multiplier' | 'min_response_tokens' | 'max_response_tokens' | 'temperature' | 'requires_validation' | 'validation_keywords'
  >
>

export type PersonaConfigUpdate = Partial<
  Pick<
    PersonaConfig,
    | 'name'
    | 'category'
    | 'reputation_multiplier'
    | 'min_response_tokens'
    | 'max_response_tokens'
    | 'temperature'
    | 'requires_validation'
    | 'system_prompt'
    | 'validation_keywords'
    | 'is_active'
  >
>

export interface TrainingExample {
  instruction: string
  output: string
  persona_id?: string
}

export interface TrainingUploadResult {
  inserted: number
  skipped_duplicate: number
  skipped_invalid: number
  total_submitted: number
}

export interface KnowledgeSource {
  source_id: string
  source_name: string
  source_type: 'text' | 'markdown' | 'pdf'
  persona_id: string | null
  chunk_count: number
  created_at: string
  preview: string
}

export interface KnowledgeChunkDetail {
  id: string
  chunk_index: number
  content: string
  content_length: number
}

export interface KnowledgeUploadResult {
  source_id: string
  chunks_created: number
  total_characters: number
}

export interface ModelVersionSummary {
  version_number: number
  created_at: string
  training_samples: number | null
  validation_accuracy: number | null
  is_production: boolean
  model_info: Record<string, unknown> | null
}

export interface SystemResources {
  cpu_percent: number
  memory_used_gb: number
  memory_total_gb: number
  memory_percent: number
  disk_used_gb: number
  disk_total_gb: number
  disk_percent: number
  gpu_available: boolean
  gpu_utilization: number | null
  gpu_memory_used_gb: number | null
  gpu_memory_total_gb: number | null
  timestamp: string
}

export interface DashboardSummary {
  total_tasks_completed: number
  total_training_samples: number
  total_knowledge_chunks: number
  knowledge_chunks_by_agent: Record<string, number>
  latest_model_version: number
  latest_validation_accuracy: number | null
  total_agents: number
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

// Admin-only calls never talk to the Duke backend directly from the browser -
// they go through /api/admin/duke/*, a same-origin Next.js route that
// re-verifies the caller is a signed-in admin and attaches the backend's
// shared admin secret server-side. See app/api/admin/duke/[...path]/route.ts.
async function adminRequest<T>(path: string, init: RequestInit = {}, timeoutMs = 15_000): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(`/api/admin/duke${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
      signal: controller.signal,
    })

    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      // no/invalid JSON body
    }

    if (!res.ok) {
      const detail =
        body && typeof body === 'object' && 'error' in body
          ? String((body as { error: unknown }).error)
          : res.statusText
      throw new DukeApiError(detail)
    }

    return body as T
  } catch (err) {
    if (err instanceof DukeApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new DukeApiError('Duke backend timed out. It can be slow to wake up - try again in a moment.', err)
    }
    throw new DukeApiError('Could not reach the Duke backend.', err)
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

  // Admin: overview (proxied - see adminRequest above)
  iacStats: () => adminRequest<IacStats>('/iac/stats'),
  trainingStats: () => adminRequest<TrainingStats>('/training/stats'),

  // Admin: training controls
  retrainAgents: () => adminRequest<RetrainResult>('/admin/retrain-agents', { method: 'POST' }, 60_000),
  clearTrainingCache: () => adminRequest<{ deleted: number }>('/admin/clear-cache', { method: 'POST' }),
  uploadTrainingData: (examples: TrainingExample[]) =>
    adminRequest<TrainingUploadResult>(
      '/admin/training-data/upload',
      { method: 'POST', body: JSON.stringify({ examples }) },
      30_000,
    ),

  // Admin: annotation suite
  listTasks: (limit = 50) => adminRequest<DukeTask[]>(`/tasks?limit=${limit}`),
  submitFeedback: (body: SubmitFeedbackRequest) =>
    adminRequest<{ status: string; message: string }>('/feedback/submit', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Admin: data-driven personas
  listPersonas: () => adminRequest<PersonaConfig[]>('/admin/personas'),
  getPersona: (personaId: string) => adminRequest<PersonaConfig>(`/admin/personas/${personaId}`),
  createPersona: (body: PersonaConfigCreate) =>
    adminRequest<PersonaConfig>('/admin/personas', { method: 'POST', body: JSON.stringify(body) }),
  updatePersona: (personaId: string, body: PersonaConfigUpdate) =>
    adminRequest<PersonaConfig>(`/admin/personas/${personaId}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  // Admin: knowledge system (Phase 1 - per-agent + DUKE-global RAG)
  listKnowledge: (scope: 'global' | 'agent', personaId?: string) =>
    adminRequest<KnowledgeSource[]>(
      `/admin/knowledge?scope=${scope}${personaId ? `&persona_id=${encodeURIComponent(personaId)}` : ''}`,
    ),
  getKnowledgeSourceChunks: (sourceId: string) =>
    adminRequest<KnowledgeChunkDetail[]>(`/admin/knowledge/sources/${sourceId}/chunks`),
  uploadKnowledgeText: (params: { personaId: string | null; sourceName: string; text: string; markdown?: boolean }) =>
    adminRequest<KnowledgeUploadResult>(
      '/admin/knowledge/upload',
      {
        method: 'POST',
        body: JSON.stringify({
          persona_id: params.personaId,
          source_name: params.sourceName,
          content_type: params.markdown ? 'markdown' : 'text',
          text: params.text,
        }),
      },
      90_000,
    ),
  uploadKnowledgePdf: (params: { personaId: string | null; sourceName: string; fileBase64: string }) =>
    adminRequest<KnowledgeUploadResult>(
      '/admin/knowledge/upload',
      {
        method: 'POST',
        body: JSON.stringify({
          persona_id: params.personaId,
          source_name: params.sourceName,
          content_type: 'pdf',
          file_base64: params.fileBase64,
        }),
      },
      90_000,
    ),
  deleteKnowledgeSource: (sourceId: string) =>
    adminRequest<{ status: string; deleted_chunks: number }>(`/admin/knowledge/sources/${sourceId}`, { method: 'DELETE' }),
  deleteKnowledgeChunk: (chunkId: string) =>
    adminRequest<{ status: string }>(`/admin/knowledge/chunks/${chunkId}`, { method: 'DELETE' }),

  // Admin: dashboard (Phase 1 - real data only, see backend/coordinator_api.py's
  // "ADMIN DASHBOARD" section for exactly what's real vs. intentionally omitted)
  trainingHistory: () => adminRequest<ModelVersionSummary[]>('/admin/training/history'),
  systemResources: () => adminRequest<SystemResources>('/admin/system/resources'),
  dashboardSummary: () => adminRequest<DashboardSummary>('/admin/dashboard/summary'),
}
