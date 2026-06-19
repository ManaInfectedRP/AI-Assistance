import { useCallback, useRef, useState } from 'react'
import type { Conversation } from '../types/chat'

interface Props {
  conversations: Conversation[]
  activeId: string | null
  searchQuery: string
  onSearchChange: (q: string) => void
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
}

interface ItemProps {
  conv: Conversation
  isActive: boolean
  onSelect: () => void
  onRename: (title: string) => void
  onDelete: () => void
}

function ConversationItem({ conv, isActive, onSelect, onRename, onDelete }: ItemProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(conv.title)
  const inputRef = useRef<HTMLInputElement>(null)

  const startEdit = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      setDraft(conv.title)
      setEditing(true)
      setTimeout(() => inputRef.current?.select(), 0)
    },
    [conv.title],
  )

  const commitEdit = useCallback(() => {
    const trimmed = draft.trim()
    if (trimmed && trimmed !== conv.title) onRename(trimmed)
    setEditing(false)
  }, [draft, conv.title, onRename])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') commitEdit()
    if (e.key === 'Escape') setEditing(false)
  }

  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation()
    onDelete()
  }

  return (
    <li
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={onSelect}
      title={conv.title}
    >
      {editing ? (
        <input
          ref={inputRef}
          className="rename-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
          onClick={(e) => e.stopPropagation()}
          autoFocus
        />
      ) : (
        <>
          <span className="conv-title" onDoubleClick={startEdit}>
            {conv.title}
          </span>
          <button
            className="conv-delete"
            onClick={handleDelete}
            type="button"
            title="Delete"
            aria-label="Delete conversation"
          >
            ✕
          </button>
        </>
      )}
    </li>
  )
}

export function Sidebar({
  conversations,
  activeId,
  searchQuery,
  onSearchChange,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: Props) {
  return (
    <aside className="sidebar">
      <button onClick={onNew} className="btn btn-new" type="button">
        + New Chat
      </button>
      <div className="sidebar-search">
        <input
          type="search"
          placeholder="Search conversations…"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="sidebar-search-input"
        />
      </div>
      <ul className="conversation-list">
        {conversations.map((conv) => (
          <ConversationItem
            key={conv.id}
            conv={conv}
            isActive={conv.id === activeId}
            onSelect={() => onSelect(conv.id)}
            onRename={(title) => onRename(conv.id, title)}
            onDelete={() => onDelete(conv.id)}
          />
        ))}
        {conversations.length === 0 && searchQuery && (
          <li className="no-results">No matches</li>
        )}
      </ul>
    </aside>
  )
}
