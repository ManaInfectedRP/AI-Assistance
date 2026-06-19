import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_TEMPLATE_ID } from '../constants/templates'
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
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    save(conversations)
  }, [conversations])

  const newConversation = useCallback((templateId?: string): string => {
    const id = crypto.randomUUID()
    const conv: Conversation = {
      id,
      title: 'New chat',
      messages: [],
      templateId: templateId ?? DEFAULT_TEMPLATE_ID,
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
          const firstUserText = messages.find((m) => m.role === 'user')?.content
          const title = firstUserText
            ? firstUserText.slice(0, 40) + (firstUserText.length > 40 ? '…' : '')
            : c.title
          return { ...c, messages, title, updatedAt: Date.now() }
        }),
      )
    },
    [],
  )

  const renameConversation = useCallback((id: string, title: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c)),
    )
  }, [])

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id)
        if (activeId === id) {
          // Switch to the conversation that was adjacent
          const idx = prev.findIndex((c) => c.id === id)
          const fallback = next[idx] ?? next[idx - 1] ?? null
          setActiveId(fallback?.id ?? null)
        }
        return next
      })
    },
    [activeId],
  )

  const setTemplateId = useCallback((id: string, templateId: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, templateId } : c)),
    )
  }, [])

  const filteredConversations = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return conversations
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.messages.some((m) => m.content.toLowerCase().includes(q)),
    )
  }, [conversations, searchQuery])

  const activeConversation =
    conversations.find((c) => c.id === activeId) ?? null

  return {
    conversations,
    filteredConversations,
    activeId,
    activeConversation,
    setActiveId,
    newConversation,
    updateMessages,
    renameConversation,
    deleteConversation,
    setTemplateId,
    searchQuery,
    setSearchQuery,
  }
}
