import 'server-only'
import { NextRequest, NextResponse } from 'next/server'
import { dukeFetch } from '@/lib/duke-server'

// Same-origin proxy for the Duke backend's public (non-admin) endpoints -
// health, model/learning status, task submission, agency dispatch. The
// browser used to call the Hugging Face Space directly; now that the Space
// is private, every call has to go through here so the required Bearer
// token (see lib/duke-server.ts) stays server-only. lib/duke-api.ts's
// request() calls this route instead of the Space URL directly.

async function proxy(req: NextRequest, path: string[], method: string) {
  const targetPath = `/${path.join('/')}${req.nextUrl.search}`

  const init: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (method !== 'GET') {
    const body = await req.text()
    if (body) init.body = body
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 180_000)

  try {
    const res = await dukeFetch(targetPath, { ...init, signal: controller.signal })
    const text = await res.text()
    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') ?? 'application/json' },
    })
  } catch {
    return NextResponse.json(
      { detail: 'Could not reach the Duke backend. It may be offline or waking up.' },
      { status: 502 },
    )
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
