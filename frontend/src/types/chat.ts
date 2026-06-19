export type ModelMode = 'chat' | 'code'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  model: ModelMode
  timestamp: number
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  templateId: string
  createdAt: number
  updatedAt: number
}

export interface ChatApiMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatRequest {
  messages: ChatApiMessage[]
  stream: boolean
  temperature?: number
  web_search?: boolean
  knowledge_project?: string | null
}

export interface StreamChunk {
  delta: string
  done: boolean
}
