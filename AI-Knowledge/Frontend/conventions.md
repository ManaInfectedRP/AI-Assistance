# Frontend Conventions

Stack: **React 19.2**, **TypeScript 6.0**, **Vite 8**, **Vitest 4**, **Playwright 1.61**

---

## TypeScript — Strict Mode

`tsconfig.app.json` enables: `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.

### Key patterns

```ts
// ✅ Explicit prop interfaces — never inline
interface ButtonProps {
  label: string
  onClick: () => void
  disabled?: boolean   // optional = may be undefined
}

// ✅ noUncheckedIndexedAccess — array access returns T | undefined
const first = items[0]          // type: Item | undefined
const safe = items[0] ?? fallback

// ✅ exactOptionalPropertyTypes — don't pass undefined for optional props
// WRONG: <Btn disabled={undefined} />
// RIGHT: {show && <Btn disabled />}  or just omit the prop

// ✅ Discriminated unions instead of boolean flags
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

// ✅ satisfies — validate shape without widening type
const palette = {
  red: '#ef4444',
  green: '#22c55e',
} satisfies Record<string, string>

// ✅ Template literal types
type Endpoint = `/api/${'chat' | 'code' | 'health'}`

// ✅ unknown + narrowing over any
function handle(value: unknown) {
  if (typeof value === 'string') return value.toUpperCase()
  if (value instanceof Error) return value.message
}
```

---

## React 19 — Component Patterns

### Function components + explicit props
```tsx
// ✅ Named export, explicit interface
export function MessageBubble({ message, highlight = false }: {
  message: Message
  highlight?: boolean
}) {
  return <div className={highlight ? 'highlighted' : ''}>{message.content}</div>
}
```

### ref as a prop (React 19 — no forwardRef needed)
```tsx
// ✅ React 19: ref is a regular prop
function TextInput({ ref, ...props }: React.ComponentProps<'input'> & {
  ref?: React.Ref<HTMLInputElement>
}) {
  return <input ref={ref} {...props} />
}
// Usage:
const inputRef = useRef<HTMLInputElement>(null)
<TextInput ref={inputRef} />
```

### use() hook — read a promise or context in render
```tsx
import { use } from 'react'

// Read context anywhere (not just at top level)
function ThemeButton() {
  const theme = use(ThemeContext)   // replaces useContext
  return <button className={theme}>Click</button>
}

// Unwrap a promise (must be wrapped in Suspense)
function UserName({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise)   // suspends until resolved
  return <span>{user.name}</span>
}
```

### useOptimistic — instant UI before server confirms
```tsx
import { useOptimistic } from 'react'

function MessageList({ messages, onSend }: Props) {
  const [optimisticMsgs, addOptimistic] = useOptimistic(
    messages,
    (state, newMsg: Message) => [...state, newMsg],
  )

  async function handleSend(text: string) {
    addOptimistic({ id: crypto.randomUUID(), content: text, role: 'user' })
    await onSend(text)   // real update follows
  }
  // ...
}
```

### useTransition — mark slow state updates as non-urgent
```tsx
import { useTransition } from 'react'

function SearchBox() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Result[]>([])
  const [isPending, startTransition] = useTransition()

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value)
    startTransition(() => {
      setResults(expensiveSearch(e.target.value))
    })
  }

  return (
    <>
      <input value={query} onChange={handleChange} />
      {isPending ? <Spinner /> : <ResultList items={results} />}
    </>
  )
}
```

---

## React 19 — Hook Patterns

### Custom hooks own all side effects
```ts
// ✅ All fetching, subscriptions, and timers live in hooks
export function useStreamingChat(conversationId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<'idle' | 'streaming' | 'error'>('idle')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => abortRef.current?.abort()   // cleanup on unmount
  }, [])

  // ...
  return { messages, status }
}
```

### useCallback / useMemo — only for real bottlenecks
```ts
// ❌ Don't do this everywhere — adds overhead, not saves it
const label = useMemo(() => text.toUpperCase(), [text])

// ✅ Do this when the value is passed as a dep to a child hook or effect
const handleSend = useCallback((msg: string) => {
  // ...
}, [conversationId, model])   // stable reference for child components
```

### useRef for mutable state that shouldn't trigger re-render
```ts
const abortRef = useRef<AbortController | null>(null)
const latestCallbackRef = useRef(callback)
latestCallbackRef.current = callback   // always fresh without re-renders
```

---

## CSS

- Single `index.css` — no CSS modules, no styled-components
- CSS custom properties (`--var`) for all colours/sizes
- Dark theme via `color-scheme: dark` on `:root`
- BEM-lite naming: `.sidebar`, `.sidebar-search`, `.sidebar-search-input`
- No inline `style={{}}` except for truly dynamic values (e.g. width from a calculation)

```css
/* ✅ Custom property theming */
:root {
  --bg: #0f1117;
  --accent: #6366f1;
  --text: #d1d5db;
}

/* ✅ Component namespace */
.message-bubble { ... }
.message-bubble.user { ... }
.message-bubble .message-content { ... }
```

---

## Testing — Vitest + Testing Library

```tsx
// ✅ Test behaviour: what the user sees
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

describe('ModelSelector', () => {
  it('calls onChange with the new value', () => {
    const onChange = vi.fn()
    render(<ModelSelector value="chat" onChange={onChange} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'code' } })
    expect(onChange).toHaveBeenCalledWith('code')
  })
})

// ✅ Async: use findBy* (waits) not getBy* (throws immediately)
it('shows error message after failed fetch', async () => {
  render(<ChatWindow ... />)
  expect(await screen.findByText(/error/i)).toBeInTheDocument()
})
```

### Vitest config (in vite.config.ts)
```ts
test: {
  globals: true,           // no import { describe, it } needed
  environment: 'jsdom',
  setupFiles: ['./src/test-setup.ts'],
  exclude: ['e2e/**', 'node_modules/**'],
}
```

### Playwright e2e
```ts
// e2e/chat.spec.ts
test('user sends message and sees reply', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('input-bar').fill('Hello')
  await page.getByTestId('input-bar').press('Enter')
  await expect(page.getByTestId('message-list')).toContainText('Hello')
  await expect(page.getByTestId('assistant-message')).not.toBeEmpty({ timeout: 30_000 })
})
```

