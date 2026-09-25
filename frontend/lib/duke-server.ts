import 'server-only'
import { DUKE_API_URL } from './duke-api'

// The Duke backend Space is private on Hugging Face, so every server-to-server
// call to it needs this Bearer token attached - the browser never sees it.
// Must be a Hugging Face User Access Token with at least read access to
// LABEELEA1/LABEELE-DUKE-PROD.
const HF_SPACE_TOKEN = process.env.HF_SPACE_TOKEN

// Thin wrapper around fetch() for every Next.js API route talking to the Duke
// backend - attaches the Space auth header so callers don't have to repeat it.
export function dukeFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${DUKE_API_URL}${path}`, {
    ...init,
    headers: {
      ...(HF_SPACE_TOKEN ? { Authorization: `Bearer ${HF_SPACE_TOKEN}` } : {}),
      ...init.headers,
    },
  })
}
