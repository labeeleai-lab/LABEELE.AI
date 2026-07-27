import { supabaseBrowser } from './supabase/client'

export interface AgentQuery {
  id: string
  agent_id: string
  query: string
  response: string | null
  created_at: string
}

export async function listRecentQueries(userId: string, limit = 20): Promise<AgentQuery[]> {
  if (!supabaseBrowser) return []

  const { data, error } = await supabaseBrowser
    .from('agent_queries')
    .select('id, agent_id, query, response, created_at')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    console.error('Failed to load query history:', error.message)
    return []
  }

  return data ?? []
}

export async function saveQuery(userId: string, agentId: string, query: string, response: string) {
  if (!supabaseBrowser) return

  const { error } = await supabaseBrowser
    .from('agent_queries')
    .insert({ user_id: userId, agent_id: agentId, query, response })

  if (error) {
    console.error('Failed to save query to history:', error.message)
  }
}
