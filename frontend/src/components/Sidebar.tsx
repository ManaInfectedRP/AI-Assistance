import type { Conversation } from '../types/chat'

interface Props {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export function Sidebar({ conversations, activeId, onSelect, onNew }: Props) {
  return (
    <aside className="sidebar">
      <button onClick={onNew} className="btn btn-new" type="button">
        + New Chat
      </button>
      <ul className="conversation-list">
        {conversations.map((conv) => (
          <li
            key={conv.id}
            className={`conversation-item ${conv.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            {conv.title}
          </li>
        ))}
      </ul>
    </aside>
  )
}
