import { PROMPT_TEMPLATES } from '../constants/templates'

interface Props {
  value: string
  onChange: (templateId: string) => void
  disabled?: boolean
}

export function TemplateSelector({ value, onChange, disabled }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-label="Select prompt template"
      title="Prompt template"
    >
      {PROMPT_TEMPLATES.map((t) => (
        <option key={t.id} value={t.id}>
          {t.name}
        </option>
      ))}
    </select>
  )
}
