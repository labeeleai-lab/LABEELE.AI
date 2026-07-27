export interface Agent {
  id: string
  name: string
  category: string
  reputation_multiplier: number
  status: 'idle' | 'active' | 'training'
  tasks_completed: number
  success_rate: number
}

export interface Task {
  id: string
  description: string
  agent_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  result?: string
  created_at: string
  completed_at?: string
}

export interface TrainingMetrics {
  model_version: string
  total_inferences: number
  recent_loss: number
  status: 'idle' | 'training' | 'complete'
}

export interface VisionNodeStatus {
  health: string
  images_processed: number
  avg_latency: number
  uptime: number
}
