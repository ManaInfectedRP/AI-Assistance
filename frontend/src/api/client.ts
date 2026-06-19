import type { ChatRequest, StreamChunk } from '../types/chat'

export async function streamChat(
  endpoint: '/api/chat' | '/api/code',
  body: ChatRequest,
  onDelta: (delta: string) => void,
  onDone: () => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }

  if (!res.body) {
    throw new Error('No response body')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const raw = line.slice('data:'.length).trim()
      const chunk: StreamChunk = JSON.parse(raw)
      if (chunk.done) {
        onDone()
        return
      }
      if (chunk.delta) {
        onDelta(chunk.delta)
      }
    }
  }

  onDone()
}
