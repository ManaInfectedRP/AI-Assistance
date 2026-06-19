import { useCallback } from 'react'

interface Props {
  children: string
  className?: string
}

export function CodeBlock({ children, className }: Props) {
  const language = className?.replace('language-', '') ?? ''

  const copy = useCallback(() => {
    void navigator.clipboard.writeText(children)
  }, [children])

  return (
    <div className="code-block">
      <div className="code-block-header">
        {language && <span className="code-language">{language}</span>}
        <button onClick={copy} className="copy-btn" type="button">
          Copy
        </button>
      </div>
      <pre>
        <code className={className}>{children}</code>
      </pre>
    </div>
  )
}
