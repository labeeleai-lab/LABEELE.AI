// Turns the backend's /tasks/submit response text into display parts. The
// backend appends its citation footer / "not in my knowledge base" note and
// a "⚡ [DUKE-LOCAL]:" origin prefix as plain text (see
// backend/coordinator_API/routers/tasks.py) - they're lifted out here so the
// UI can show them as metadata instead of raw text.

export type ResponseTone = 'answer' | 'warning' | 'error'

export interface ParsedResponse {
  body: string
  sources: string[]
  notice: string | null
  tone: ResponseTone
  // Human label for non-model answer paths (calculator, live data, ...)
  origin: string | null
}

const ORIGIN_LABELS: Record<string, string> = {
  math_solver: 'Calculator',
  grounding: 'Live date, time & weather',
  document_extract: 'From your attached file',
  web_fetch_extract: 'From the linked page',
  cache: 'Previously answered',
}

const PREFIX = /^\s*⚡\s*\[DUKE-LOCAL\]:\s*/
const SOURCES = /\n\n📚 Sources:\s*(.+)\s*$/
const NOTICE = /\n\nℹ️\s*(I couldn't find this in my knowledge base[\s\S]*)$/

export function parseResponse(raw: string, responseSource?: string, apiSources?: { source: string }[]): ParsedResponse {
  let body = (raw ?? '').replace(PREFIX, '')
  let sources: string[] = []
  let notice: string | null = null

  const s = body.match(SOURCES)
  if (s) {
    sources = s[1].split(';').map((t) => t.trim()).filter(Boolean)
    body = body.slice(0, s.index)
  }
  const n = body.match(NOTICE)
  if (n) {
    notice = n[1].trim()
    body = body.slice(0, n.index)
  }
  // Fallback for responses without the text footer (older backend builds)
  if (!sources.length && !notice && apiSources?.length) {
    sources = Array.from(new Set(apiSources.map((x) => x.source.replace(/\s*\(part \d+ of \d+\)\s*$/i, '').trim())))
  }

  body = body.trim()
  let tone: ResponseTone = 'answer'
  if (/^error:/i.test(body)) {
    tone = /busy|try again/i.test(body) ? 'warning' : 'error'
    body = body.replace(/^error:\s*/i, '')
  } else if (/^I couldn't (use|read)/.test(body) || responseSource?.endsWith('_error')) {
    tone = 'warning'
  }

  return {
    body: body || 'No response received.',
    sources,
    notice,
    tone,
    origin: responseSource ? ORIGIN_LABELS[responseSource] ?? null : null,
  }
}
