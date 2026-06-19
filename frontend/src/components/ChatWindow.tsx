import { useEffect, useRef } from 'react'
import type { Message } from '../types/chat'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: Message[]
  isStreaming: boolean
}

export function ChatWindow({ messages, isStreaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-window empty" data-testid="message-list">
        <p className="empty-hint">Start a conversation below.</p>
      </div>
    )
  }

  return (
    <div className="chat-window" data-testid="message-list">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isStreaming && <div className="streaming-cursor" aria-label="Thinking…" />}
      <div ref={bottomRef} />
    </div>
  )
}
