import { NextResponse } from 'next/server'
import { supabaseAdmin, isSupabaseAdminConfigured } from '@/lib/supabase/admin'
import { requireAdminUser } from '@/lib/admin'

export async function DELETE(_request: Request, { params }: { params: Promise<{ email: string }> }) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isSupabaseAdminConfigured || !supabaseAdmin) {
    return NextResponse.json({ error: 'Admin client is not configured.' }, { status: 500 })
  }

  const { email } = await params
  const targetEmail = decodeURIComponent(email).toLowerCase()

  const { count } = await supabaseAdmin.from('admin_users').select('email', { count: 'exact', head: true })

  if ((count ?? 0) <= 1) {
    return NextResponse.json({ error: "Can't remove the last remaining admin." }, { status: 409 })
  }

  const { error: deleteError } = await supabaseAdmin.from('admin_users').delete().eq('email', targetEmail)

  if (deleteError) return NextResponse.json({ error: deleteError.message }, { status: 500 })
  return NextResponse.json({ success: true })
}
