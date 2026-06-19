import type { ModelMode } from '../types/chat'

interface Props {
  value: ModelMode
  onChange: (mode: ModelMode) => void
  disabled?: boolean
}

export function ModelSelector({ value, onChange, disabled }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as ModelMode)}
      disabled={disabled}
      aria-label="Select model mode"
    >
      <option value="chat">Chat — qwen3</option>
      <option value="code">Code — qwen3-coder</option>
    </select>
  )
}
