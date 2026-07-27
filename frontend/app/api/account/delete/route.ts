import { NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase/server'
import { supabaseAdmin, isSupabaseAdminConfigured } from '@/lib/supabase/admin'

// Deletes the CALLING user's own account. The user id always comes from their own
// verified session cookie (auth.getUser()) - never from the request body - so this
// can't be used to delete an arbitrary account.
export async function POST() {
  const supabase = await createSupabaseServerClient()
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase is not configured.' }, { status: 500 })
  }

  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser()

  if (userError || !user) {
    return NextResponse.json({ error: 'Not signed in.' }, { status: 401 })
  }

  if (!isSupabaseAdminConfigured || !supabaseAdmin) {
    return NextResponse.json(
      { error: 'Account deletion is not configured on the server yet.' },
      { status: 501 },
    )
  }

  // agent_queries rows cascade-delete automatically (FK: on delete cascade).
  const { error: deleteError } = await supabaseAdmin.auth.admin.deleteUser(user.id)

  if (deleteError) {
    return NextResponse.json({ error: deleteError.message }, { status: 500 })
  }

  const response = NextResponse.json({ success: true })
  response.cookies.getAll().forEach((cookie) => response.cookies.delete(cookie.name))
  return response
}
