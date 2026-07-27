import 'server-only'

// Server-only GitHub client, scoped to a single repo. GITHUB_TOKEN is a
// fine-grained PAT with Contents: Read and write on labeeleai-lab/LABEELE.AI
// only - never sent to the browser, only used from /api/admin/github/* route
// handlers, each of which re-verifies the caller is an admin first.

const GITHUB_API = 'https://api.github.com'
const OWNER = 'labeeleai-lab'
const REPO = 'LABEELE.AI'
const BRANCH = 'main'

const GITHUB_TOKEN = process.env.GITHUB_TOKEN

export const isGitHubConfigured = Boolean(GITHUB_TOKEN)

export class GitHubApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message)
    this.name = 'GitHubApiError'
  }
}

async function githubFetch(path: string, init: RequestInit = {}) {
  if (!GITHUB_TOKEN) {
    throw new GitHubApiError('GITHUB_TOKEN is not configured.')
  }

  const res = await fetch(`${GITHUB_API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      ...init.headers,
    },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}) as { message?: string })
    throw new GitHubApiError(body.message || `GitHub API error (${res.status})`, res.status)
  }

  return res.json()
}

function encodePath(path: string) {
  // Encode each path segment individually so slashes stay literal.
  return path.split('/').map(encodeURIComponent).join('/')
}

export interface GitHubTreeEntry {
  path: string
  type: 'blob' | 'tree'
  sha: string
  size?: number
}

export async function getRepoTree(): Promise<GitHubTreeEntry[]> {
  const data = await githubFetch(`/repos/${OWNER}/${REPO}/git/trees/${BRANCH}?recursive=1`)
  if (data.truncated) {
    console.warn('GitHub tree response was truncated - repo may be too large to list in one call.')
  }
  return (data.tree as Array<{ path: string; type: string; sha: string; size?: number }>)
    .filter((entry) => entry.type === 'blob' || entry.type === 'tree')
    .map((entry) => ({ path: entry.path, type: entry.type as 'blob' | 'tree', sha: entry.sha, size: entry.size }))
}

export interface GitHubFile {
  path: string
  content: string
  sha: string
}

export async function getFileContent(path: string): Promise<GitHubFile> {
  const data = await githubFetch(`/repos/${OWNER}/${REPO}/contents/${encodePath(path)}?ref=${BRANCH}`)
  if (Array.isArray(data) || data.type !== 'file') {
    throw new GitHubApiError(`'${path}' is not a file.`)
  }
  const content = Buffer.from(data.content, 'base64').toString('utf-8')
  return { path, content, sha: data.sha }
}

export async function commitFile(
  path: string,
  content: string,
  message: string,
  previousSha: string | undefined,
  authorName?: string,
): Promise<{ commitSha: string; contentSha: string }> {
  const body: Record<string, unknown> = {
    message,
    content: Buffer.from(content, 'utf-8').toString('base64'),
    branch: BRANCH,
  }
  if (previousSha) body.sha = previousSha
  if (authorName) {
    body.committer = { name: authorName, email: `${authorName}@users.noreply.github.com` }
  }

  const data = await githubFetch(`/repos/${OWNER}/${REPO}/contents/${encodePath(path)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  return { commitSha: data.commit?.sha, contentSha: data.content?.sha }
}

export const GITHUB_REPO_URL = `https://github.com/${OWNER}/${REPO}`
