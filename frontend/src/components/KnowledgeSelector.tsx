import { useKnowledge } from '../hooks/useKnowledge'

interface KnowledgeSelectorProps {
  value: string | null
  onChange: (project: string | null) => void
  disabled?: boolean
}

export function KnowledgeSelector({ value, onChange, disabled }: KnowledgeSelectorProps) {
  const projects = useKnowledge()

  // Don't render until projects are loaded so the select doesn't flash
  if (projects.length === 0) return null

  return (
    <div className="knowledge-selector" title="Inject project knowledge docs as context">
      <span className="knowledge-selector-icon">📚</span>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
        aria-label="Project knowledge context"
      >
        <option value="">No project</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name} ({p.doc_count} docs)
          </option>
        ))}
      </select>
    </div>
  )
}
