import { useEffect, useRef } from 'react'
import type { Message } from '../types/chat'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: Message[]
  isStreaming: boolean
  highlightIds?: Set<string>
  currentMatchId?: string | null
}

export function ChatWindow({ messages, isStreaming, highlightIds, currentMatchId }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const currentMatchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (currentMatchId) {
      currentMatchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, currentMatchId])

  if (messages.length === 0) {
    return (
      <div className="chat-window empty" data-testid="message-list">
        <p className="empty-hint">Start a conversation below.</p>
      </div>
    )
  }

  return (
    <div className="chat-window" data-testid="message-list">
      {messages.map((msg) => {
        const isHighlighted = highlightIds?.has(msg.id) ?? false
        const isCurrent = msg.id === currentMatchId
        return (
          <div
            key={msg.id}
            ref={isCurrent ? currentMatchRef : undefined}
            className={isHighlighted ? `search-highlighted${isCurrent ? ' search-current' : ''}` : undefined}
          >
            <MessageBubble message={msg} />
          </div>
        )
      })}
      {isStreaming && <div className="streaming-cursor" aria-label="Thinking…" />}
      <div ref={bottomRef} />
    </div>
  )
}
