import 'server-only'
import { NextRequest, NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { DUKE_API_URL } from '@/lib/duke-api'

// Server-only proxy for admin-only Duke backend calls (training controls,
// persona CRUD, annotation feedback, stats, training-data upload). The
// browser never talks to these Duke endpoints directly and never sees
// DUKE_ADMIN_SECRET - it calls this route, which re-verifies the caller is a
// real signed-in admin (requireAdminUser) and only then forwards the request
// with the shared secret attached. Keeps the secret out of client JS entirely.

const ADMIN_SECRET = process.env.DUKE_ADMIN_SECRET

async function proxy(req: NextRequest, path: string[], method: string) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!ADMIN_SECRET) {
    return NextResponse.json({ error: 'DUKE_ADMIN_SECRET is not configured on the server.' }, { status: 500 })
  }

  const targetUrl = `${DUKE_API_URL}/${path.join('/')}${req.nextUrl.search}`

  const init: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Secret': ADMIN_SECRET,
    },
  }
  if (method !== 'GET') {
    const body = await req.text()
    if (body) init.body = body
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 60_000)

  try {
    const res = await fetch(targetUrl, { ...init, signal: controller.signal })
    const text = await res.text()
    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') ?? 'application/json' },
    })
  } catch {
    return NextResponse.json({ error: 'Could not reach the Duke backend. It may be offline or waking up.' }, { status: 502 })
  } finally {
    clearTimeout(timeout)
  }
}

type RouteParams = { params: Promise<{ path: string[] }> }

export async function GET(req: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return proxy(req, path, 'GET')
}

export async function POST(req: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return proxy(req, path, 'POST')
}

export async function PUT(req: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return proxy(req, path, 'PUT')
}
