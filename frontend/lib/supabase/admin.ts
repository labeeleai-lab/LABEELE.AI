import 'server-only'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY

export const isSupabaseAdminConfigured = Boolean(SUPABASE_URL && SERVICE_ROLE_KEY)

// Full admin access, bypasses row-level security - server-only (the `server-only`
// import throws a build error if this is ever pulled into a client bundle). Never
// pass a client-supplied user id to this client's admin methods without first
// verifying the caller's own session via lib/supabase/server.ts.
export const supabaseAdmin = isSupabaseAdminConfigured
  ? createClient(SUPABASE_URL!, SERVICE_ROLE_KEY!, {
      auth: { autoRefreshToken: false, persistSession: false },
    })
  : undefined
