import { NextResponse } from 'next/server'
import { supabaseAdmin, isSupabaseAdminConfigured } from '@/lib/supabase/admin'
import { requireAdminUser } from '@/lib/admin'

export async function GET() {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isSupabaseAdminConfigured || !supabaseAdmin) {
    return NextResponse.json({ error: 'Admin client is not configured.' }, { status: 500 })
  }

  const { data, error: dbError } = await supabaseAdmin
    .from('admin_users')
    .select('email, added_by, created_at')
    .order('created_at', { ascending: true })

  if (dbError) return NextResponse.json({ error: dbError.message }, { status: 500 })
  return NextResponse.json({ admins: data })
}

export async function POST(request: Request) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isSupabaseAdminConfigured || !supabaseAdmin) {
    return NextResponse.json({ error: 'Admin client is not configured.' }, { status: 500 })
  }

  const body = await request.json().catch(() => null)
  const email = typeof body?.email === 'string' ? body.email.trim().toLowerCase() : ''

  if (!email || !email.includes('@')) {
    return NextResponse.json({ error: 'Enter a valid email address.' }, { status: 422 })
  }

  const { error: insertError } = await supabaseAdmin
    .from('admin_users')
    .insert({ email, added_by: guard.user.email })

  if (insertError) {
    const status = insertError.code === '23505' ? 409 : 500
    const message = insertError.code === '23505' ? 'That email is already an admin.' : insertError.message
    return NextResponse.json({ error: message }, { status })
  }

  return NextResponse.json({ success: true }, { status: 201 })
}
