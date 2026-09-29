import 'server-only'
import { DUKE_API_URL } from './duke-api'

// The Duke backend Space is private on Hugging Face, so every server-to-server
// call to it needs this Bearer token attached - the browser never sees it.
// Must be a Hugging Face User Access Token with at least read access to
// LABEELEA1/LABEELE-DUKE-PROD.
const HF_SPACE_TOKEN = process.env.HF_SPACE_TOKEN

// Hugging Face's front proxy intermittently answers with an instant 502/503
// ("Sorry, there is an error on our side") even while the Space is healthy -
// a retry a moment later succeeds. GETs are safe to repeat, so they get a
// couple of quick retries before the error reaches the dashboard. Never
// retried: non-GETs (e.g. task submission, retrain - not safe to repeat).
const RETRYABLE_STATUSES = new Set([502, 503])
const GET_RETRIES = 2
const RETRY_DELAY_MS = 300

// Thin wrapper around fetch() for every Next.js API route talking to the Duke
// backend - attaches the Space auth header so callers don't have to repeat it.
export async function dukeFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const doFetch = () =>
    fetch(`${DUKE_API_URL}${path}`, {
      ...init,
      headers: {
        ...(HF_SPACE_TOKEN ? { Authorization: `Bearer ${HF_SPACE_TOKEN}` } : {}),
        ...init.headers,
      },
    })

  const method = (init.method ?? 'GET').toUpperCase()
  if (method !== 'GET') return doFetch()

  for (let attempt = 0; ; attempt++) {
    const res = await doFetch()
    if (!RETRYABLE_STATUSES.has(res.status) || attempt >= GET_RETRIES || init.signal?.aborted) {
      return res
    }
    await res.body?.cancel()
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS * (attempt + 1)))
  }
}
