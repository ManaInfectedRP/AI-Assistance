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
  createdAt: number
  updatedAt: number
}

export interface ChatRequest {
  messages: Pick<Message, 'role' | 'content'>[]
  model?: ModelMode
  stream: boolean
  temperature?: number
}

export interface StreamChunk {
  delta: string
  done: boolean
}
