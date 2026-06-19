import { useCallback, useRef, useState } from 'react'
import { streamChat } from '../api/client'
import type { Message, ModelMode } from '../types/chat'

interface UseChatOptions {
  conversationId: string | null
  initialMessages?: Message[]
  onMessagesChange?: (messages: Message[]) => void
}

export function useChat({
  conversationId,
  initialMessages = [],
  onMessagesChange,
}: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [isStreaming, setIsStreaming] = useState(false)
  const [model, setModel] = useState<ModelMode>('chat')
  const abortRef = useRef<AbortController | null>(null)

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

      try {
        await streamChat(
          endpoint,
          {
            messages: nextMessages
              .filter((m) => m.role !== 'assistant' || m.content)
              .map(({ role, content }) => ({ role, content })),
            stream: true,
          },
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
    [isStreaming, messages, model, updateMessages, onMessagesChange],
  )

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  const clearMessages = useCallback(() => {
    updateMessages([])
  }, [updateMessages])

  return {
    messages,
    isStreaming,
    model,
    setModel,
    sendMessage,
    stopStreaming,
    clearMessages,
  }
}
