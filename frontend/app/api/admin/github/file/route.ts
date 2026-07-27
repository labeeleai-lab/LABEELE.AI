import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { getFileContent, GitHubApiError, isGitHubConfigured } from '@/lib/github'

export async function GET(request: Request) {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isGitHubConfigured) {
    return NextResponse.json({ error: 'GITHUB_TOKEN is not configured.' }, { status: 500 })
  }

  const path = new URL(request.url).searchParams.get('path')
  if (!path) {
    return NextResponse.json({ error: 'Missing "path" query parameter.' }, { status: 422 })
  }

  try {
    const file = await getFileContent(path)
    return NextResponse.json(file)
  } catch (err) {
    const message = err instanceof GitHubApiError ? err.message : 'Failed to load file.'
    return NextResponse.json({ error: message }, { status: err instanceof GitHubApiError ? err.status ?? 500 : 500 })
  }
}
