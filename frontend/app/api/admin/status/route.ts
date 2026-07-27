import { NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase/server'
import { isAdmin } from '@/lib/admin'

// Unlike other /api/admin/* routes, this doesn't require the caller to
// already be an admin - it just answers "am I one?" for the signed-in user,
// so the UI can decide whether to show an Admin link. Not a privileged read.
export async function GET() {
  const supabase = await createSupabaseServerClient()
  if (!supabase) return NextResponse.json({ isAdmin: false })

  const {
    data: { user },
  } = await supabase.auth.getUser()

  return NextResponse.json({ isAdmin: await isAdmin(user?.email) })
}
