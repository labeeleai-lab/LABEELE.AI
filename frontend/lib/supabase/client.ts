import { createBrowserClient } from '@supabase/ssr'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)

// Supabase isn't configured until NEXT_PUBLIC_SUPABASE_URL/ANON_KEY are set (see env.example).
// Callers must check isSupabaseConfigured before use and show a real "not configured" state -
// this stays undefined rather than constructing a client against an empty URL, which
// @supabase/ssr throws on immediately.
export const supabaseBrowser = isSupabaseConfigured
  ? createBrowserClient(SUPABASE_URL!, SUPABASE_ANON_KEY!)
  : undefined
