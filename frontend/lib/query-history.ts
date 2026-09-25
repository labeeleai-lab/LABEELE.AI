export interface AgentQuery {
  id: string
  agent_id: string
  query: string
  response: string | null
  created_at: string
}

export async function listRecentQueries(limit = 20): Promise<AgentQuery[]> {
  try {
    const res = await fetch(`/api/history?limit=${limit}`)
    if (!res.ok) return []
    return await res.json()
  } catch {
    return []
  }
}

export async function saveQuery(agentId: string, query: string, response: string) {
  try {
    await fetch('/api/history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, query, response }),
    })
  } catch {
    // best-effort - a failed history save shouldn't surface as a user-facing error
  }
}
