import { NextResponse, type NextRequest } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase/server'

// Handles both email-verification links (signup) and password-recovery links
// (forgot-password) - both send the user here first with a `code` to exchange
// for a session, then we forward on to wherever `next` points.
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') || '/dashboard'

  if (code) {
    const supabase = await createSupabaseServerClient()
    if (supabase) {
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      if (!error) {
        return NextResponse.redirect(`${origin}${next}`)
      }
    }
  }

  const errorUrl = new URL('/login', origin)
  errorUrl.searchParams.set('error', 'auth_callback_failed')
  return NextResponse.redirect(errorUrl)
}
