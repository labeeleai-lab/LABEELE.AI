// Subpath import (not the top-level `jose` barrel) - the barrel pulls in JWE
// (encryption) support, which drags CompressionStream/DecompressionStream
// into the Edge Runtime bundle (middleware.ts) even though this file only
// ever verifies signed (JWS) tokens.
import { jwtVerify } from 'jose/jwt/verify'

// Shared session cookie for the site's own local account system (backend:
// backend/coordinator_API/routers/accounts.py). Replaces Supabase Auth's
// cookies. JWT_SECRET must be set to the exact same value as JWT_SECRET on
// the Hugging Face Space backend - that's what lets this cookie be verified
// here without ever calling the backend.
export const SESSION_COOKIE = 'session_token'

export interface SessionPayload {
  sub: string
  email: string
  is_admin: boolean
  kind: string
  exp: number
}

const JWT_SECRET = process.env.JWT_SECRET

export async function verifySessionToken(token: string | undefined): Promise<SessionPayload | null> {
  if (!token || !JWT_SECRET) return null

  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(JWT_SECRET))
    if (payload.kind !== 'account_session') return null
    return payload as unknown as SessionPayload
  } catch {
    return null
  }
}
