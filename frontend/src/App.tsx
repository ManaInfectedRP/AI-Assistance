import { useEffect } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { InputBar } from './components/InputBar'
import { ModelSelector } from './components/ModelSelector'
import { Sidebar } from './components/Sidebar'
import { useChat } from './hooks/useChat'
import { useConversations } from './hooks/useConversations'
import 'highlight.js/styles/github-dark.css'
import './index.css'

export default function App() {
  const {
    conversations,
    activeId,
    activeConversation,
    setActiveId,
    newConversation,
    updateMessages,
  } = useConversations()

  const { messages, isStreaming, model, setModel, sendMessage, stopStreaming } =
    useChat({
      conversationId: activeId,
      initialMessages: activeConversation?.messages ?? [],
      onMessagesChange: (msgs) => {
        if (activeId) updateMessages(activeId, msgs)
      },
    })

  useEffect(() => {
    if (!activeId) newConversation()
  }, [activeId, newConversation])

  return (
    <div className="app-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={newConversation}
      />
      <main className="main-panel">
        <header className="top-bar">
          <span className="app-title">AI Assistant</span>
          <ModelSelector value={model} onChange={setModel} disabled={isStreaming} />
        </header>
        <ChatWindow messages={messages} isStreaming={isStreaming} />
        <InputBar
          onSend={sendMessage}
          onStop={stopStreaming}
          disabled={false}
          isStreaming={isStreaming}
        />
      </main>
    </div>
  )
}
