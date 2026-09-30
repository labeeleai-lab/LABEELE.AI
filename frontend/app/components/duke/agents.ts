import { Shield, Brain, Server, Code2, Rocket, Eye, Network, TrendingUp, type LucideIcon } from 'lucide-react'

export interface DukeAgent {
  id: string
  name: string
  // Short capability line shown in the selector and on responses
  focus: string
  icon: LucideIcon
  isCoordinator?: boolean
}

// DUKE first and visually distinct - it's the central coordinator, not an eighth
// specialist. Drawing on every specialist's knowledge at once (see backend
// /tasks/submit's cross_agent retrieval mode), not just its own slice of it.
// ids must match the backend persona ids exactly.
export const AGENTS: DukeAgent[] = [
  { id: 'duke', name: 'DUKE', focus: 'Coordinates every specialist', icon: Network, isCoordinator: true },
  { id: 'security-expert', name: 'Security Expert', focus: 'Security architecture & risk', icon: Shield },
  { id: 'ml-expert', name: 'ML Expert', focus: 'Machine learning research', icon: Brain },
  { id: 'systems-expert', name: 'Systems Expert', focus: 'Cloud & distributed systems', icon: Server },
  { id: 'backend-expert', name: 'Backend Expert', focus: 'APIs & backend engineering', icon: Code2 },
  { id: 'devops-expert', name: 'DevOps Expert', focus: 'Delivery, CI/CD & operations', icon: Rocket },
  { id: 'vision-expert', name: 'Vision Expert', focus: 'Computer vision', icon: Eye },
  { id: 'advanced-expert', name: 'Emerging Tech Strategist', focus: 'Technology strategy', icon: TrendingUp },
]

export function getAgent(id: string): DukeAgent {
  return AGENTS.find((a) => a.id === id) ?? { id, name: id, focus: 'Specialist', icon: Network }
}
