import { NextResponse } from 'next/server'
import { requireAdminUser } from '@/lib/admin'
import { getRepoTree, GitHubApiError, isGitHubConfigured } from '@/lib/github'

export async function GET() {
  const guard = await requireAdminUser()
  if ('errorResponse' in guard) return guard.errorResponse

  if (!isGitHubConfigured) {
    return NextResponse.json({ error: 'GITHUB_TOKEN is not configured.' }, { status: 500 })
  }

  try {
    const tree = await getRepoTree()
    return NextResponse.json({ tree })
  } catch (err) {
    const message = err instanceof GitHubApiError ? err.message : 'Failed to load repo tree.'
    return NextResponse.json({ error: message }, { status: err instanceof GitHubApiError ? err.status ?? 500 : 500 })
  }
}
