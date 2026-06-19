import { useEffect, useRef } from 'react'

interface Props {
  query: string
  onQueryChange: (q: string) => void
  matchCount: number
  currentIndex: number
  onNext: () => void
  onPrev: () => void
  onClose: () => void
}

export function ChatSearchBar({
  query,
  onQueryChange,
  matchCount,
  currentIndex,
  onNext,
  onPrev,
  onClose,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onClose()
    if (e.key === 'Enter') e.shiftKey ? onPrev() : onNext()
  }

  const label =
    query.trim() && matchCount === 0
      ? 'No matches'
      : query.trim()
        ? `${currentIndex + 1} / ${matchCount}`
        : ''

  return (
    <div className="chat-search-bar">
      <input
        ref={inputRef}
        type="search"
        placeholder="Search in conversation…"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={handleKeyDown}
        className="chat-search-input"
      />
      {label && <span className="search-count">{label}</span>}
      <button onClick={onPrev} type="button" className="search-nav" title="Previous (Shift+Enter)" disabled={matchCount === 0}>↑</button>
      <button onClick={onNext} type="button" className="search-nav" title="Next (Enter)" disabled={matchCount === 0}>↓</button>
      <button onClick={onClose} type="button" className="search-close">✕</button>
    </div>
  )
}
