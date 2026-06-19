# React 19 — Patterns & New APIs

Version in use: **React 19.2.6** with **TypeScript 6.0**, Vite 8.

---

## What changed in React 19

| Feature | Old way | React 19 |
|---|---|---|
| Forward refs | `forwardRef()` wrapper | `ref` as a regular prop |
| Context reading | `useContext(ctx)` | `use(ctx)` anywhere |
| Async in render | Not possible | `use(promise)` + Suspense |
| Optimistic UI | Manual state juggling | `useOptimistic()` |
| Form actions | `onSubmit` + `useState` | `useActionState()` |

---

## ref as a prop

```tsx
// ✅ React 19 — no forwardRef wrapper needed
function Input({ ref, className, ...props }: React.ComponentProps<'input'>) {
  return <input ref={ref} className={`input ${className ?? ''}`} {...props} />
}

// Usage
const inputRef = useRef<HTMLInputElement>(null)
<Input ref={inputRef} placeholder="Type here" />
```

---

## use() — context and promises

```tsx
import { use, Suspense } from 'react'

// ── Context ──────────────────────────────────────────────
const ThemeContext = React.createContext<'dark' | 'light'>('dark')

function DeepChild() {
  // use() can be called conditionally, unlike useContext
  const theme = use(ThemeContext)
  return <div data-theme={theme} />
}

// ── Async data ────────────────────────────────────────────
// Pass a promise as a prop → use() suspends until it resolves
async function fetchUser(id: string): Promise<User> {
  const res = await fetch(`/api/users/${id}`)
  return res.json() as Promise<User>
}

function UserCard({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise)   // suspends here
  return <div>{user.name}</div>
}

function App() {
  const promise = fetchUser('123')   // create once outside render
  return (
    <Suspense fallback={<Spinner />}>
      <UserCard userPromise={promise} />
    </Suspense>
  )
}
```

---

## useOptimistic

```tsx
import { useOptimistic } from 'react'

interface Message { id: string; content: string; pending?: boolean }

function MessageList({ messages, onSend }: {
  messages: Message[]
  onSend: (text: string) => Promise<void>
}) {
  const [optimistic, addOptimistic] = useOptimistic(
    messages,
    (current, newMsg: Message) => [...current, newMsg],
  )

  async function handleSend(text: string) {
    // Immediately show the message
    addOptimistic({ id: crypto.randomUUID(), content: text, pending: true })
    // Real async operation — optimistic list reverts if this throws
    await onSend(text)
  }

  return (
    <ul>
      {optimistic.map(m => (
        <li key={m.id} style={{ opacity: m.pending ? 0.6 : 1 }}>
          {m.content}
        </li>
      ))}
    </ul>
  )
}
```

---

## useTransition — keep UI responsive during slow updates

```tsx
import { useTransition, useState } from 'react'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<string[]>([])
  const [isPending, startTransition] = useTransition()

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setQuery(val)   // urgent — update input immediately

    startTransition(() => {
      // non-urgent — React may batch/defer this
      setResults(expensiveFilter(val))
    })
  }

  return (
    <>
      <input value={query} onChange={handleInput} />
      {isPending
        ? <p>Filtering…</p>
        : <ul>{results.map(r => <li key={r}>{r}</li>)}</ul>
      }
    </>
  )
}
```

---

## useActionState — async form/button actions

```tsx
import { useActionState } from 'react'

async function submitMessage(
  prevState: string,
  formData: FormData,
): Promise<string> {
  const text = formData.get('message') as string
  await sendToServer(text)
  return 'Sent!'
}

function MessageForm() {
  const [status, formAction, isPending] = useActionState(submitMessage, '')

  return (
    <form action={formAction}>
      <input name="message" required />
      <button type="submit" disabled={isPending}>
        {isPending ? 'Sending…' : 'Send'}
      </button>
      {status && <p>{status}</p>}
    </form>
  )
}
```

---

## Error Boundaries (class component — still required in React 19)

```tsx
class ErrorBoundary extends React.Component<
  { fallback: React.ReactNode; children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(error, info)
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children
  }
}

// Usage
<ErrorBoundary fallback={<p>Something went wrong.</p>}>
  <ChatWindow />
</ErrorBoundary>
```

---

## SSE Streaming with ReadableStream (this project's pattern)

```ts
// src/api/client.ts
export async function streamChat(
  endpoint: string,
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

  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

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
      const chunk = JSON.parse(line.slice('data:'.length).trim()) as StreamChunk
      if (chunk.done) { onDone(); return }
      if (chunk.delta) onDelta(chunk.delta)
    }
  }
  onDone()
}
```

Note: use `fetch` + `ReadableStream`, **not** `EventSource`. EventSource is GET-only.

---

## useState vs useReducer

```tsx
// useState — simple values and independent state
const [isOpen, setIsOpen] = useState(false)
const [query, setQuery] = useState('')

// useReducer — multiple related fields that change together
type ChatState = {
  messages: Message[]
  isStreaming: boolean
  error: string | null
}

type ChatAction =
  | { type: 'append_delta'; id: string; delta: string }
  | { type: 'set_streaming'; value: boolean }
  | { type: 'set_error'; message: string }

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'append_delta':
      return {
        ...state,
        messages: state.messages.map(m =>
          m.id === action.id ? { ...m, content: m.content + action.delta } : m
        ),
      }
    case 'set_streaming':
      return { ...state, isStreaming: action.value }
    case 'set_error':
      return { ...state, error: action.message, isStreaming: false }
  }
}
```
