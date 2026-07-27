import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { commitFile, GitHubApiError, isGitHubConfigured } from '@/lib/github'

export async function POST(request: Request) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isGitHubConfigured) {
    return NextResponse.json({ error: 'GITHUB_TOKEN is not configured.' }, { status: 500 })
  }

  const body = await request.json().catch(() => null)
  const path = typeof body?.path === 'string' ? body.path : ''
  const content = typeof body?.content === 'string' ? body.content : null
  const sha = typeof body?.sha === 'string' ? body.sha : undefined
  const message = typeof body?.message === 'string' && body.message.trim() ? body.message.trim() : `Edit ${path} via admin IDE`

  if (!path || content === null) {
    return NextResponse.json({ error: 'Missing "path" or "content".' }, { status: 422 })
  }

  try {
    const result = await commitFile(path, content, message, sha, guard.user.email?.split('@')[0])
    return NextResponse.json(result)
  } catch (err) {
    const message = err instanceof GitHubApiError ? err.message : 'Failed to commit file.'
    return NextResponse.json({ error: message }, { status: err instanceof GitHubApiError ? err.status ?? 500 : 500 })
  }
}
