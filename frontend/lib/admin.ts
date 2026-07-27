import 'server-only'
import { NextResponse } from 'next/server'
import type { User } from '@supabase/supabase-js'
import { supabaseAdmin, isSupabaseAdminConfigured } from './supabase/admin'
import { createSupabaseServerClient } from './supabase/server'

// admin_users has no client-facing RLS policies on purpose - every check and
// write goes through server code using the service-role client, never the
// browser directly. Used in middleware.ts to gate /admin/*, and re-checked
// independently inside every /api/admin/* route handler (those can trigger
// retraining, delete training data, or push commits - middleware alone
// isn't enough for actions that consequential).
export async function isAdmin(email: string | null | undefined): Promise<boolean> {
  if (!email || !isSupabaseAdminConfigured || !supabaseAdmin) return false

  const { data, error } = await supabaseAdmin
    .from('admin_users')
    .select('email')
    .eq('email', email.toLowerCase())
    .maybeSingle()

  if (error) {
    console.error('isAdmin check failed:', error.message)
    return false
  }
  return Boolean(data)
}

// Shared guard for /api/admin/* route handlers - re-verifies the caller's own
// session server-side rather than trusting middleware, since these routes can
// trigger retraining, delete data, or push commits to GitHub.
export async function requireAdminUser(): Promise<{ user: User } | { errorResponse: NextResponse }> {
  const supabase = await createSupabaseServerClient()
  if (!supabase) {
    return { errorResponse: NextResponse.json({ error: 'Supabase is not configured.' }, { status: 500 }) }
  }

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user?.email || !(await isAdmin(user.email))) {
    return { errorResponse: NextResponse.json({ error: 'Forbidden' }, { status: 403 }) }
  }

  return { user }
}
