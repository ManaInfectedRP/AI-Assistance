import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/client'
import type { Message, ModelMode } from '../types/chat'

interface UseChatOptions {
  conversationId: string | null
  initialMessages?: Message[]
  systemPrompt?: string
  onMessagesChange?: (messages: Message[]) => void
}

export function useChat({
  conversationId,
  initialMessages = [],
  systemPrompt,
  onMessagesChange,
}: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [isStreaming, setIsStreaming] = useState(false)
  const [model, setModel] = useState<ModelMode>('chat')
  const [webSearch, setWebSearch] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  // Always holds the latest initialMessages so the switch effect reads fresh data
  const initialMessagesRef = useRef(initialMessages)
  initialMessagesRef.current = initialMessages

  // Reset messages when the active conversation changes
  useEffect(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
    setMessages(initialMessagesRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId])

  const updateMessages = useCallback(
    (updated: Message[]) => {
      setMessages(updated)
      onMessagesChange?.(updated)
    },
    [onMessagesChange],
  )

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text.trim(),
        model,
        timestamp: Date.now(),
      }
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        model,
        timestamp: Date.now(),
      }

      const nextMessages = [...messages, userMsg, assistantMsg]
      updateMessages(nextMessages)
      setIsStreaming(true)

      abortRef.current = new AbortController()
      const endpoint = model === 'code' ? '/api/code' : '/api/chat'

      // Build the API payload: optionally prepend the system prompt
      const visibleMessages = nextMessages
        .filter((m) => m.role !== 'assistant' || m.content)
        .map(({ role, content }) => ({ role, content }))

      const apiMessages = systemPrompt
        ? [{ role: 'system' as const, content: systemPrompt }, ...visibleMessages]
        : visibleMessages

      try {
        await streamChat(
          endpoint,
          { messages: apiMessages, stream: true, web_search: webSearch },
          (delta) => {
            setMessages((prev) => {
              const updated = prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: m.content + delta }
                  : m,
              )
              onMessagesChange?.(updated)
              return updated
            })
          },
          () => {
            setIsStreaming(false)
          },
          abortRef.current.signal,
        )
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsg.id
                ? { ...m, content: '[Error: could not reach the model]' }
                : m,
            ),
          )
        }
        setIsStreaming(false)
      }
    },
    [isStreaming, messages, model, webSearch, systemPrompt, updateMessages, onMessagesChange],
  )

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return {
    messages,
    isStreaming,
    model,
    setModel,
    webSearch,
    setWebSearch,
    sendMessage,
    stopStreaming,
  }
}
