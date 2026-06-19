import { useCallback, useRef } from 'react'

interface Props {
  onSend: (text: string) => void
  onStop: () => void
  disabled: boolean
  isStreaming: boolean
}

export function InputBar({ onSend, onStop, disabled, isStreaming }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        const value = textareaRef.current?.value.trim()
        if (!value || disabled) return
        onSend(value)
        if (textareaRef.current) textareaRef.current.value = ''
      }
    },
    [onSend, disabled],
  )

  const handleSend = useCallback(() => {
    const value = textareaRef.current?.value.trim()
    if (!value || disabled) return
    onSend(value)
    if (textareaRef.current) textareaRef.current.value = ''
  }, [onSend, disabled])

  return (
    <div className="input-bar">
      <textarea
        ref={textareaRef}
        data-testid="input-bar"
        placeholder="Message… (Enter to send, Shift+Enter for newline)"
        onKeyDown={handleKeyDown}
        rows={3}
        disabled={disabled && !isStreaming}
      />
      {isStreaming ? (
        <button onClick={onStop} className="btn btn-stop" type="button">
          Stop
        </button>
      ) : (
        <button
          onClick={handleSend}
          className="btn btn-send"
          type="button"
          disabled={disabled}
        >
          Send
        </button>
      )}
    </div>
  )
}
