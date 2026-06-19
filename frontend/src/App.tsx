import { useEffect } from 'react'
import { ChatSearchBar } from './components/ChatSearchBar'
import { ChatWindow } from './components/ChatWindow'
import { InputBar } from './components/InputBar'
import { ModelSelector } from './components/ModelSelector'
import { Sidebar } from './components/Sidebar'
import { TemplateSelector } from './components/TemplateSelector'
import { DEFAULT_TEMPLATE_ID, getTemplate } from './constants/templates'
import { useChat } from './hooks/useChat'
import { useChatSearch } from './hooks/useChatSearch'
import { useConversations } from './hooks/useConversations'
import 'highlight.js/styles/github-dark.css'
import './index.css'

export default function App() {
  const {
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
  } = useConversations()

  const templateId = activeConversation?.templateId ?? DEFAULT_TEMPLATE_ID
  const template = getTemplate(templateId)

  const { messages, isStreaming, model, setModel, webSearch, setWebSearch, sendMessage, stopStreaming } =
    useChat({
      conversationId: activeId,
      initialMessages: activeConversation?.messages ?? [],
      systemPrompt: template.systemPrompt,
      onMessagesChange: (msgs) => {
        if (activeId) updateMessages(activeId, msgs)
      },
    })

  const chatSearch = useChatSearch(messages)

  useEffect(() => {
    if (!activeId) newConversation()
  }, [activeId, newConversation])

  function handleTemplateChange(id: string) {
    if (activeId) setTemplateId(activeId, id)
    const hint = getTemplate(id).modelHint
    setModel(hint)
  }

  function handleKeyDown(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault()
      chatSearch.open()
    }
  }

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  return (
    <div className="app-layout">
      <Sidebar
        conversations={filteredConversations}
        activeId={activeId}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSelect={setActiveId}
        onNew={() => newConversation(templateId)}
        onRename={renameConversation}
        onDelete={deleteConversation}
      />
      <main className="main-panel">
        <header className="top-bar">
          <span className="app-title">AI Assistant</span>
          <div className="top-bar-controls">
            <TemplateSelector
              value={templateId}
              onChange={handleTemplateChange}
              disabled={isStreaming}
            />
            <ModelSelector value={model} onChange={setModel} disabled={isStreaming} />
            <button
              type="button"
              className="btn-icon"
              onClick={chatSearch.open}
              title="Search in conversation (Ctrl+F)"
              aria-label="Search"
            >
              ⌕
            </button>
          </div>
        </header>

        {chatSearch.isOpen && (
          <ChatSearchBar
            query={chatSearch.query}
            onQueryChange={chatSearch.setQuery}
            matchCount={chatSearch.matchList.length}
            currentIndex={chatSearch.currentMatchIndex}
            onNext={chatSearch.nextMatch}
            onPrev={chatSearch.prevMatch}
            onClose={chatSearch.close}
          />
        )}

        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          highlightIds={chatSearch.matchingIds}
          currentMatchId={chatSearch.currentMatchId}
        />
        <InputBar
          onSend={sendMessage}
          onStop={stopStreaming}
          disabled={false}
          isStreaming={isStreaming}
          webSearch={webSearch}
          onWebSearchToggle={() => setWebSearch((v) => !v)}
        />
      </main>
    </div>
  )
}
