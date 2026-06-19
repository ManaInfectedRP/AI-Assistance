import { useCallback, useEffect, useState } from 'react'
import type { Conversation, Message } from '../types/chat'

const STORAGE_KEY = 'ai-assistant-conversations'

function load(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Conversation[]) : []
  } catch {
    return []
  }
}

function save(conversations: Conversation[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
}

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(load)
  const [activeId, setActiveId] = useState<string | null>(
    () => load()[0]?.id ?? null,
  )

  useEffect(() => {
    save(conversations)
  }, [conversations])

  const newConversation = useCallback((): string => {
    const id = crypto.randomUUID()
    const conv: Conversation = {
      id,
      title: 'New chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    setConversations((prev) => [conv, ...prev])
    setActiveId(id)
    return id
  }, [])

  const updateMessages = useCallback(
    (conversationId: string, messages: Message[]) => {
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id !== conversationId) return c
          const title =
            messages.find((m) => m.role === 'user')?.content.slice(0, 40) ??
            c.title
          return { ...c, messages, title, updatedAt: Date.now() }
        }),
      )
    },
    [],
  )

  const activeConversation =
    conversations.find((c) => c.id === activeId) ?? null

  return {
    conversations,
    activeId,
    activeConversation,
    setActiveId,
    newConversation,
    updateMessages,
  }
}
