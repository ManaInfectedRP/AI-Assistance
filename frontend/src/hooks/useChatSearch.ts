import { useCallback, useEffect, useState } from 'react'
import type { Message } from '../types/chat'

export function useChatSearch(messages: Message[]) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [matchingIds, setMatchingIds] = useState<Set<string>>(new Set())
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0)
  const [matchList, setMatchList] = useState<string[]>([])

  useEffect(() => {
    const trimmed = query.trim().toLowerCase()
    if (!trimmed) {
      setMatchingIds(new Set())
      setMatchList([])
      setCurrentMatchIndex(0)
      return
    }
    const matched = messages.filter((m) =>
      m.content.toLowerCase().includes(trimmed),
    )
    setMatchingIds(new Set(matched.map((m) => m.id)))
    setMatchList(matched.map((m) => m.id))
    setCurrentMatchIndex(0)
  }, [query, messages])

  const open = useCallback(() => setIsOpen(true), [])

  const close = useCallback(() => {
    setIsOpen(false)
    setQuery('')
  }, [])

  const nextMatch = useCallback(() => {
    setCurrentMatchIndex((i) => (i + 1) % Math.max(matchList.length, 1))
  }, [matchList.length])

  const prevMatch = useCallback(() => {
    setCurrentMatchIndex(
      (i) => (i - 1 + Math.max(matchList.length, 1)) % Math.max(matchList.length, 1),
    )
  }, [matchList.length])

  const currentMatchId = matchList[currentMatchIndex] ?? null

  return {
    query,
    setQuery,
    isOpen,
    open,
    close,
    matchingIds,
    matchList,
    currentMatchId,
    currentMatchIndex,
    nextMatch,
    prevMatch,
  }
}
